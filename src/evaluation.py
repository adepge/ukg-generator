"""
LLM-as-judge evaluation for generated triples.

This module generates a report of the quality of the triples produced by the UKG generation pipeline
according to the following criteria:

 1. correctness         how true is the information given based on general world knowledge
 2. relevance           how informative and meaningful is the triple
 3. well_formedness     how well-formed is the triple according to the provided entity/relation label 
                        schema used during generation.

Configuration is read from the environment (see ``.env.example``):

    OPENAI_API_KEY
    OPENAI_BASE_URL
    OPENAI_MODEL
    OPENAI_BATCH_SIZE
    OPENAI_MAX_WORKERS
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Default OpenAI configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_BATCH_SIZE = 15
DEFAULT_MAX_WORKERS = 4
DEFAULT_LABEL_FILE = "resources/labels/biomedical_labels.json"

# Criteria scored per triple (each on an integer 1-5 scale).
CRITERIA = ("correctness", "relevance", "well_formedness")

# Number of times to retry a failed judge request before giving up.
MAX_RETRIES = 4


def _repo_root() -> Path:
    """Return the repository root (parent of the src/ directory)."""
    return Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TripleRecord:
    """
    Data structure for a triple which will be evaluated by the judge.
    """
    sub: str
    pred: str
    obj: str
    conf: float = 0.0
    source: str = ""
    section: str = ""

    def as_text(self) -> str:
        """Render the triple as a human-readable string."""
        return f"({self.sub}, {self.pred}, {self.obj})"


@dataclass
class TripleEvaluation:
    """
    Data structure for the results of a single triple evaluation.
    """
    triple: TripleRecord
    correctness: int | None = None
    relevance: int | None = None
    well_formedness: int | None = None
    rationale: str = ""
    error: str | None = None

    @property
    def scored(self) -> bool:
        """
        Return True when all criteria received a valid score.
        """
        return self.error is None and all(
            getattr(self, criterion) is not None for criterion in CRITERIA
        )

    @property
    def normalized(self) -> float | None:
        """
        Return the mean of the three criteria mapped from 1-5 onto 0-1.
        """
        if not self.scored:
            return None
        unnormalized_mean = sum(getattr(self, criterion) for criterion in CRITERIA) / len(CRITERIA)
        return (unnormalized_mean - 1.0) / 4.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the evaluation to a dictionary (used for JSON report).
        """
        return {
            "subject": self.triple.sub,
            "predicate": self.triple.pred,
            "object": self.triple.obj,
            "confidence": self.triple.conf,
            "source": self.triple.source,
            "section": self.triple.section,
            "correctness": self.correctness,
            "relevance": self.relevance,
            "well_formedness": self.well_formedness,
            "normalized": self.normalized,
            "rationale": self.rationale,
            "error": self.error,
        }

@dataclass
class EvaluationReport:
    """
    Data structure for the aggregated results across all evaluated triples.
    """
    model: str
    evaluations: list[TripleEvaluation] = field(default_factory=list)

    @property
    def total(self) -> int:
        # Get the total number of evaluated triples.
        return len(self.evaluations)

    @property
    def scored_evaluations(self) -> list[TripleEvaluation]:
        # Get the list of successfully scored triples.
        return [e for e in self.evaluations if e.scored]

    @property
    def failed(self) -> int:
        # Get the number of triples that failed to be scored.
        return self.total - len(self.scored_evaluations)

    def dimension_means(self) -> dict[str, float | None]:
        """
        Return the mean 1-5 score per criterion across successfully scored triples.
        """
        scored = self.scored_evaluations
        means: dict[str, float | None] = {}
        for criterion in CRITERIA:
            values = [getattr(e, criterion) for e in scored]
            means[criterion] = round(sum(values) / len(values), 3) if values else None
        return means

    def overall_mean(self) -> float | None:
        """
        Return the mean normalized (0-1) score across successfully scored triples.
        """
        values = [e.normalized for e in self.scored_evaluations if e.normalized is not None]
        return round(sum(values) / len(values), 3) if values else None

    def dimension_distributions(self) -> dict[str, dict[int, int]]:
        """
        Return the distribution of each integer score 1-5 per criterion.
        """
        dist: dict[str, dict[int, int]] = {criterion: {s: 0 for s in range(1, 6)} for criterion in CRITERIA}
        for e in self.scored_evaluations:
            for criterion in CRITERIA:
                score = getattr(e, criterion)
                if score in dist[criterion]:
                    dist[criterion][score] += 1
        return dist

    def breakdown_by_source(self) -> dict[str, dict[str, Any]]:
        """
        Return the mean normalized score and count grouped by triple source.
        """
        groups: dict[str, list[float]] = {}
        for e in self.scored_evaluations:
            # Skip triples that failed to be scored.
            if e.normalized is None:
                continue
            
            # Group by triple source.
            groups.setdefault(e.triple.source or "<unknown>", []).append(e.normalized)
        return {
            source: {"count": len(values), "mean_normalized": round(sum(values) / len(values), 3)}
            for source, values in sorted(groups.items())
        }

    def breakdown_by_confidence(self, bin_size: float = 0.2) -> dict[str, dict[str, Any]]:
        """
        Return the mean normalized score and count grouped by pipeline-confidence bin.
        """
        groups: dict[str, list[float]] = {}
        for e in self.scored_evaluations:
            # Skip triples that failed to be scored.
            if e.normalized is None:
                continue
            
            # Calculate the confidence bin.
            conf = max(0.0, min(1.0, float(e.triple.conf)))
            lower = min(int(conf / bin_size) * bin_size, 1.0 - bin_size)
            label = f"{lower:.1f}-{lower + bin_size:.1f}"
            groups.setdefault(label, []).append(e.normalized)
        return {
            label: {"count": len(values), "mean_normalized": round(sum(values) / len(values), 3)}
            for label, values in sorted(groups.items())
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the report to a dictionary (used for JSON report).
        """
        return {
            "model": self.model,
            "total": self.total,
            "scored": len(self.scored_evaluations),
            "failed": self.failed,
            "overall_mean_normalized": self.overall_mean(),
            "dimension_means": self.dimension_means(),
            "dimension_distributions": self.dimension_distributions(),
            "breakdown_by_source": self.breakdown_by_source(),
            "breakdown_by_confidence": self.breakdown_by_confidence(),
            "evaluations": [e.to_dict() for e in self.evaluations],
        }

    def summary_text(self) -> str:
        """A compact human-readable summary for terminal output."""
        try:
            from tabulate import tabulate
        except ImportError:
            tabulate = None

        # Create the lines for the summary text.
        lines: list[str] = []
        lines.append(f"Model: {self.model}")
        lines.append(
            f"Triples evaluated: {len(self.scored_evaluations)}/{self.total} "
            f"(failed: {self.failed})"
        )

        # Add the overall mean score.
        overall = self.overall_mean()
        lines.append(f"Overall mean (0-1): {overall if overall is not None else 'n/a'}")
        lines.append("")

        # Construct the table rows for the per-criterion scores.
        means = self.dimension_means()
        dist = self.dimension_distributions()
        criteria_rows = [
            [criterion, means[criterion]] + [dist[criterion][s] for s in range(1, 6)]
            for criterion in CRITERIA
        ]
        criteria_headers = ["criterion", "mean(1-5)", "1", "2", "3", "4", "5"]

        source_rows = [
            [src, d["count"], d["mean_normalized"]]
            for src, d in self.breakdown_by_source().items()
        ]
        confidence_rows = [
            [label, d["count"], d["mean_normalized"]]
            for label, d in self.breakdown_by_confidence().items()
        ]

        lines.append("Per-criterion scores:")
        lines.append(tabulate(criteria_rows, headers=criteria_headers, tablefmt="github"))
        lines.append("")
        lines.append("By source method:")
        lines.append(tabulate(source_rows, headers=["source", "count", "mean(0-1)"], tablefmt="github"))
        lines.append("")
        lines.append("By pipeline confidence:")
        lines.append(tabulate(confidence_rows, headers=["bin", "count", "mean(0-1)"], tablefmt="github"))
        return "\n".join(lines)

    def to_csv_rows(self) -> list[dict[str, Any]]:
        # Convert the report to a list of dictionaries (used for CSV report).
        return [e.to_dict() for e in self.evaluations]


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------

def normalize_triple(obj: Any) -> TripleRecord:
    """
    Convert a pipeline Triple object, dictionary, or positional sequence
    into a TripleRecord. This allows for flexible input formats from the pipeline.

    Args:
        obj: The triple-like object to normalize.
    Returns:
        A TripleRecord.
    """
    if isinstance(obj, TripleRecord):
        return obj

    # Pipeline Triple object (and any object with sub, pred, and obj attributes).
    if all(hasattr(obj, attr) for attr in ("sub", "pred", "obj")):
        return TripleRecord(
            sub=str(obj.sub),
            pred=str(obj.pred),
            obj=str(obj.obj),
            conf=float(getattr(obj, "conf", 0.0) or 0.0),
            source=str(getattr(obj, "source", "") or ""),
            section=str(getattr(obj, "section", "") or ""),
        )

    # Convert a dictionary to a TripleRecord.
    if isinstance(obj, dict):
        sub = obj.get("sub", obj.get("subject"))
        pred = obj.get("pred", obj.get("predicate"))
        objp = obj.get("obj", obj.get("object"))
        return TripleRecord(
            sub=str(sub),
            pred=str(pred),
            obj=str(objp),
            conf=float(obj.get("conf", obj.get("confidence", 0.0)) or 0.0),
            source=str(obj.get("source", "") or ""),
            section=str(obj.get("section", "") or ""),
        )

    # Positional sequence (list or tuple).
    if isinstance(obj, (list, tuple)):
        sub = obj[0] if len(obj) > 0 else ""
        pred = obj[1] if len(obj) > 1 else ""
        objp = obj[2] if len(obj) > 2 else ""
        conf = obj[3] if len(obj) > 3 else 0.0
        source = obj[4] if len(obj) > 4 else ""
        section = obj[5] if len(obj) > 5 else ""
        return TripleRecord(
            sub=str(sub), pred=str(pred), obj=str(objp),
            conf=float(conf or 0.0), source=str(source or ""), section=str(section or ""),
        )

    raise TypeError(f"Cannot interpret object as a triple: {obj!r}")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_schema_block(
    entity_labels: dict[str, str] | list[str] | None,
    relation_labels: list[str] | None,
) -> str:
    """
    Render the entity/relation labels into a compact schema description that
    tells the judge what the target domain looks like. Returns an empty string
    when no labels are supplied.
    """
    parts: list[str] = []

    # Add the entity labels.
    if entity_labels:
        parts.append("Entity types in the target domain:")
        if isinstance(entity_labels, dict):
            for label, description in entity_labels.items():
                desc = (description or "").strip()
                parts.append(f"- {label}: {desc}" if desc else f"- {label}")
        else:
            for label in entity_labels:
                parts.append(f"- {label}")

    # Add the relation labels.
    if relation_labels:
        readable = ", ".join(relation_labels)
        parts.append(f"Allowed/expected relation types: {readable}")
    
    # Return the schema block as a string.
    return "\n".join(parts)


def build_system_prompt(schema_block: str) -> str:
    """
    Construct the system prompt, adapting the well-formedness guidance to the schema.
    This is the prompt that the judge will use to evaluate the triples.
    """

    # Determine the well-formedness guidance based on the presence of the schema provided.
    if schema_block:
        well_formed_clause = (
            "Is it structurally a good triple - a clear subject entity, a meaningful "
            "predicate, and a clear object that the predicate genuinely relates? Use the "
            "domain schema below: prefer triples whose subject and object correspond to "
            "the listed entity types and whose predicate matches or paraphrases one of the "
            "listed relations. Penalize triples that do not fit the schema."
        )
    else:
        well_formed_clause = (
            "Is it structurally a good triple - a clear subject entity, a meaningful "
            "predicate, and a clear object that the predicate genuinely relates? Judge on "
            "general sensibility."
        )

    # Return the system prompt as a string.
    return (
        "You are a meticulous, domain-agnostic evaluator of knowledge-graph triples. "
        "A triple is (subject, predicate, object) extracted automatically from documents. "
        "Score the QUALITY of each triple along three independent dimensions, each on an "
        "integer scale from 1 (very poor) to 5 (excellent):\n\n"
        "1. correctness - Is the statement factually accurate and plausible according to "
        "general world knowledge? You are NOT given the source document, so judge "
        "plausibility, not provenance. Clearly true/sensible claims score high; false, "
        "contradictory, or nonsensical claims score low.\n"
        "2. relevance - Is the triple informative and meaningful rather than trivial, "
        "vague, or boilerplate? Generic or near-empty relations score low.\n"
        f"3. well_formedness - {well_formed_clause}\n\n"
        "Note: subjects, predicates, and objects are normalized - words are lowercased and "
        "joined by underscores (e.g. 'cognitive_impairment', 'risk_factor_of'). Read "
        "underscores as spaces.\n\n"
        "Return STRICT JSON only, with no surrounding prose, in exactly this shape:\n"
        '{"results": [{"index": <int>, "correctness": <1-5>, "relevance": <1-5>, '
        '"well_formedness": <1-5>, "rationale": "<one short sentence>"}]}\n'
        "Provide exactly one result object per input triple, preserving the given index."
    )


def build_user_prompt(batch: Sequence[TripleRecord], schema_block: str) -> str:
    """
    Construct the per-batch user prompt listing the triples to score.
    This is the prompt that the judge will use to evaluate the triples.
    """

    # Create the lines for the user prompt.
    lines: list[str] = []

    # Add the schema block if provided.
    if schema_block:
        lines.append(schema_block)
        lines.append("")
    lines.append("Evaluate the following triples:")
    for i, triple in enumerate(batch, start=1):
        lines.append(f"{i}. {triple.as_text()}")
    lines.append("")
    lines.append("Return the JSON object now.")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Judge client
# ---------------------------------------------------------------------------

class JudgeClient:
    """Thin wrapper around an OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        """
        Args:
            api_key: API key (defaults to OPENAI_API_KEY).
            base_url: API base URL (defaults to OPENAI_BASE_URL or OpenAI).
            model: Model name (defaults to OPENAI_MODEL or gpt-5-mini).
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
        self.model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

        if not self.api_key:
            raise ValueError(
                "No judge API key found. Set OPENAI_API_KEY in the environment "
                "or .env (see .env.example)."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for evaluation. "
                "Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a chat-completion request expecting a JSON object response, with
        exponential-backoff retries.

        Returns:
            The raw JSON string content of the response.
        """
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_exc = exc
                wait = 2 ** attempt
                print(
                    f"Judge request failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"{exc}. Retrying in {wait}s."
                )
                time.sleep(wait)
        raise RuntimeError(f"Judge request failed after {MAX_RETRIES} attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def clamp_score(value: Any) -> int | None:
    """Convert a judge-provided score to an integer in [1, 5], or None if invalid."""
    try:
        # Convert the score to an integer.
        score = int(round(float(value)))
    except (TypeError, ValueError):
        # Return None if the score is invalid.
        return None
    return max(1, min(5, score))

def parse_judge_response(content: str, batch_size: int) -> list[dict[str, Any]]:
    """
    Parse the judge's JSON response into a list of result dicts keyed by 1-based
    index. Tolerates minor deviations (missing wrapper key, fenced code blocks).

    Returns:
        A list of length ``batch_size`` where each entry is a result dict or {}.
    """
    results_by_index: dict[int, dict[str, Any]] = {}

    text = content.strip()
    # Strip Markdown code fences if the model wrapped its JSON.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("Could not parse judge response as JSON.")
        return [{} for _ in range(batch_size)]

    # Determine whether the response is a dictionary or a list.
    if isinstance(data, dict):
        raw_results = data.get("results")
        if raw_results is None:
            for value in data.values():
                if isinstance(value, list):
                    raw_results = value
                    break
    elif isinstance(data, list):
        raw_results = data
    else:
        raw_results = None

    if not isinstance(raw_results, list):
        return [{} for _ in range(batch_size)]

    # Process the raw results.
    for position, item in enumerate(raw_results, start=1):
        if not isinstance(item, dict):
            continue

        # Get the index of the result.
        index = item.get("index", position)
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = position
        results_by_index[index] = item

    return [results_by_index.get(i + 1, {}) for i in range(batch_size)]


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def evaluate_batch(
    client: JudgeClient,
    batch: Sequence[TripleRecord],
    system_prompt: str,
    schema_block: str,
) -> list[TripleEvaluation]:
    """
    Score a single batch of triples and return their evaluations.
    """

    # Build the user prompt.
    user_prompt = build_user_prompt(batch, schema_block)

    # Send the request to the judge.
    try:
        content = client.complete_json(system_prompt, user_prompt)
    except Exception as exc:
        return [TripleEvaluation(triple=t, error=str(exc)) for t in batch]

    # Parse the judge's response.
    parsed = parse_judge_response(content, len(batch))

    # Create the list of evaluations.
    evaluations: list[TripleEvaluation] = []
    for triple, result in zip(batch, parsed):
        if not result:
            evaluations.append(TripleEvaluation(triple=triple, error="no result returned"))
            continue
        evaluation = TripleEvaluation(
            triple=triple,
            correctness=clamp_score(result.get("correctness")),
            relevance=clamp_score(result.get("relevance")),
            well_formedness=clamp_score(result.get("well_formedness")),
            rationale=str(result.get("rationale", "")).strip(),
        )
        if not evaluation.scored:
            evaluation.error = "missing or invalid scores"
        evaluations.append(evaluation)
    return evaluations

# Main evaluation function.
def evaluate_triples(
    triples: Iterable[Any],
    entity_labels: dict[str, str] | list[str] | None = None,
    relation_labels: list[str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    batch_size: int | None = None,
    max_workers: int | None = None,
    client: JudgeClient | None = None,
    progress: bool = False,
) -> EvaluationReport:
    """
    Score triples with an LLM judge along correctness, relevance, and
    well-formedness. No source text is sent to the judge.

    Args:
        triples: Iterable of pipeline ``Triple`` objects, dicts, or sequences.
        entity_labels: Entity labels (optionally with descriptions) describing
            the target domain, same shape as passed to ``generate_triples``.
        relation_labels: Relation labels describing the target domain.
        model: Judge model name override.
        base_url: API base-URL override.
        api_key: API key override.
        batch_size: Triples scored per request (default: env or 15).
        max_workers: Concurrent judge requests (default: env or 4).
        client: Pre-built JudgeClient (mainly for testing); created if omitted.
        progress: When True, log batch completion progress.

    Returns:
        An EvaluationReport with per-triple scores and aggregates.
    """
    records = [normalize_triple(t) for t in triples]

    # Set the batch size and max workers.
    if batch_size is None:
        batch_size = int(os.environ.get("OPENAI_BATCH_SIZE", DEFAULT_BATCH_SIZE))
    if max_workers is None:
        max_workers = int(os.environ.get("OPENAI_MAX_WORKERS", DEFAULT_MAX_WORKERS))
    batch_size = max(1, batch_size)
    max_workers = max(1, max_workers)

    # Build the client if not provided.
    if client is None:
        client = JudgeClient(api_key=api_key, base_url=base_url, model=model)

    report = EvaluationReport(model=client.model)
    if not records:
        return report

    # Build the schema block and system prompt.
    schema_block = build_schema_block(entity_labels, relation_labels)
    system_prompt = build_system_prompt(schema_block)

    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]
    # Preserve input order in the final report regardless of completion order.
    results: list[list[TripleEvaluation] | None] = [None] * len(batches)

    # Evaluate the batches in parallel.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(evaluate_batch, client, batch, system_prompt, schema_block): idx
            for idx, batch in enumerate(batches)
        }
        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            completed += 1
            if progress:
                print(f"Evaluated batch {completed}/{len(batches)}")

    # Aggregate the results.
    for batch_result in results:
        if batch_result:
            report.evaluations.extend(batch_result)
    return report


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

# Matches a line like: (subject, predicate, object, 0.42)
_TXT_TRIPLE_RE = re.compile(r"^\((.*),\s*([-\d.]+)\)\s*$")


def parse_label_file(filepath: str | os.PathLike) -> tuple[Any, list[str] | None]:
    """
    Parse a labels JSON file into (entity_labels, relation_labels). The file is expected to
    contain entity_labels and relation_labels keys.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entity_labels"), data.get("relation_labels")


def load_triples_from_json(filepath: str | os.PathLike) -> list[TripleRecord]:
    """
    Load triples from a *.triples.json sidecar (list of dicts).
    """

    # Load the data from the file.
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "triples" in data:
        data = data["triples"]
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of triples in {filepath}")
    return [normalize_triple(item) for item in data]


def load_triples_from_txt(filepath: str | os.PathLike) -> list[TripleRecord]:
    """
    Load triples from the legacy ``(sub, pred, obj, conf)`` text output.

    The text format carries no source/section metadata, so those fields are
    left blank (source/confidence breakdowns will be limited).
    """
    # Load the triples from the file.
    records: list[TripleRecord] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            # Match the line to the regex.
            match = _TXT_TRIPLE_RE.match(line)
            if not match:
                continue
            body, conf_str = match.groups()
            parts = [p.strip() for p in body.split(",")]
            if len(parts) < 3:
                continue
            sub, pred = parts[0], parts[1]

            # Re-join any extra commas into the object field.
            obj = ", ".join(parts[2:])
            try:
                conf = float(conf_str)
            except ValueError:
                conf = 0.0
            records.append(TripleRecord(sub=sub, pred=pred, obj=obj, conf=conf))
    return records


def load_triples(filepath: str | os.PathLike) -> list[TripleRecord]:
    """
    Load triples from a .triples.json sidecar or a legacy .txt file by extension.
    """

    # Load the triples from the file.
    path = Path(filepath)
    if path.suffix == ".json" or path.name.endswith(".triples.json"):
        return load_triples_from_json(path)
    return load_triples_from_txt(path)


def resolve_run_inputs(run_dir: str | os.PathLike) -> Path:
    """
    Given an output/<name> directory, return the best triples file to load.
    preferring the richer <name>.triples.json sidecar over <name>.txt.
    """

    # Resolve the directory.
    directory = Path(run_dir)
    stem = directory.name

    # Prioritise the sidecar json file.
    sidecar = directory / f"{stem}.triples.json"
    if sidecar.exists():
        return sidecar
    txt = directory / f"{stem}.txt"
    if txt.exists():
        return txt
    
    # Fall back to any triples sidecar / text file in the directory.
    for candidate in sorted(directory.glob("*.triples.json")):
        return candidate
    for candidate in sorted(directory.glob("*.txt")):
        return candidate
    raise FileNotFoundError(f"No triples file (.triples.json or .txt) found in {directory}")


def write_report_json(report: EvaluationReport, output_path: str | os.PathLike) -> None:
    """
    Write the full evaluation report (aggregates + per-triple) as JSON.
    """

    # Create the directory if it doesn't exist.
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def write_report_csv(report: EvaluationReport, output_path: str | os.PathLike) -> None:
    """
    Write per-triple scores as a flat CSV.
    """

    # Create the directory if it doesn't exist.
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report.to_csv_rows()
    fieldnames = [
        "subject", "predicate", "object", "confidence", "source", "section",
        "correctness", "relevance", "well_formedness", "normalized",
        "rationale", "error",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def derive_output_path(triples_path: Path) -> Path:
    """
    Derive a default <name>.eval.json path next to the triples file.
    """

    # Resolve the name of the triples file.
    name = triples_path.name
    for suffix in (".triples.json", ".txt", ".json"):
        if name.endswith(suffix):
            stem = name[: -len(suffix)]
            break
    else:
        stem = triples_path.stem
    return triples_path.parent / f"{stem}.eval.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="LLM-as-judge evaluation of generated triples.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--triples", type=str, default=None,
        help="Path to a triples file (.triples.json sidecar or legacy .txt).",
    )
    source.add_argument(
        "--run-dir", type=str, default=None,
        help="Path to an output/<name> run directory (auto-finds the triples file).",
    )
    parser.add_argument(
        "-l", "--label-file", type=str, default=DEFAULT_LABEL_FILE,
        help=f"JSON file with entity/relation labels for the domain schema "
             f"(default: {DEFAULT_LABEL_FILE}). Pass 'none' to disable.",
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Randomly evaluate at most N triples (useful for large runs).",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Random seed used when --sample is set (default: 0).",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Judge model name (default: OPENAI_MODEL or gpt-5-mini).",
    )
    parser.add_argument(
        "--base-url", type=str, default=None,
        help="OpenAI-compatible API base URL (default: OPENAI_BASE_URL).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=None,
        help="Triples scored per request (default: OPENAI_BATCH_SIZE or 15).",
    )
    parser.add_argument(
        "--max-workers", type=int, default=None,
        help="Concurrent judge requests (default: OPENAI_MAX_WORKERS or 4).",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Path for the JSON report (default: <name>.eval.json next to triples).",
    )
    parser.add_argument(
        "--csv", action="store_true",
        help="Also write a per-triple CSV report alongside the JSON.",
    )

    args = parser.parse_args(argv)

    # Load the environment variables.
    load_dotenv(_repo_root() / ".env")

    # Resolve the triples file.
    if args.run_dir:
        try:
            triples_path = resolve_run_inputs(args.run_dir)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        triples_path = Path(args.triples)
        if not triples_path.exists():
            print(f"Error: triples file not found: {triples_path}", file=sys.stderr)
            return 1

    records = load_triples(triples_path)
    if not records:
        print(f"Error: no triples loaded from {triples_path}", file=sys.stderr)
        return 1

    # Optional sampling.
    if args.sample is not None and args.sample < len(records):
        rng = random.Random(args.seed)
        records = rng.sample(records, args.sample)

    # Load the domain schema labels.
    entity_labels: dict[str, str] | None = None
    relation_labels: list[str] | None = None
    if args.label_file and args.label_file.lower() != "none":
        # Resolve the label file path.
        label_path = Path(args.label_file)
        if label_path.exists():
            entity_labels, relation_labels = parse_label_file(label_path)
        else:
            print(
                f"Warning: label file not found: {label_path}. "
                f"Running schema-agnostic.",
                file=sys.stderr,
            )

    # Evaluate the triples.
    print(f"Evaluating {len(records)} triples from {triples_path} ...")
    try:
        report = evaluate_triples(
            records,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
            model=args.model,
            base_url=args.base_url,
            batch_size=args.batch_size,
            max_workers=args.max_workers,
            progress=True,
        )
    except (ValueError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Write the report.
    output_path = Path(args.output) if args.output else derive_output_path(triples_path)
    write_report_json(report, output_path)
    print(f"\n{report.summary_text()}\n")
    print(f"Report saved to: {output_path}")

    if args.csv:
        csv_path = output_path.with_suffix(".csv")
        write_report_csv(report, csv_path)
        print(f"CSV report saved to: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
