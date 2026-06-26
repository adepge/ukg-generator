"""
Finds the best N triples scored by the judge from all the evaluation reports.
"""

import json
import csv
from dataclasses import dataclass
from pathlib import Path

EVALUATION_REPORT_DIR = Path(__file__).resolve().parent.parent / "backend" / "media" / "evaluations"
EVALUATION_DIR = Path(__file__).resolve().parent / "sample_triples"

@dataclass
class EvaluationRecord:
    subject: str
    predicate: str
    object: str
    confidence: float
    source: str
    section: str
    correctness: int
    relevance: int
    well_formedness: int
    normalized: float
    rationale: str
    error: str

def load_evaluation_reports() -> list[EvaluationRecord]:
    """
    Load the evaluation reports from the evaluation report directory.
    """
    records = []
    for report_file in EVALUATION_REPORT_DIR.glob("*.eval.json"):
        with open(report_file, "r") as f:
            report = json.load(f)
            for evaluation in report["evaluations"]:
                records.append(EvaluationRecord(
                    subject=evaluation["subject"],
                    predicate=evaluation["predicate"],
                    object=evaluation["object"],
                    confidence=evaluation["confidence"],
                    source=evaluation["source"],
                    section=evaluation["section"],
                    correctness=evaluation["correctness"],
                    relevance=evaluation["relevance"],
                    well_formedness=evaluation["well_formedness"],
                    normalized=float(evaluation["normalized"]) if evaluation.get("normalized") is not None else 0.0,
                    rationale=evaluation["rationale"],
                    error=evaluation["error"],
                ))
    return records


def find_best_triples(records: list[EvaluationRecord], n: int) -> list[EvaluationRecord]:
    """
    Find the best N triples scored by the judge by normalized score first, then by confidence.

    Input:
        records: The list of evaluation records.
        n: The number of best triples to find.
    Returns:
        The list of best N triples.
    """
    return sorted(records, key=lambda x: (x.normalized, x.confidence), reverse=True)[:n]

def main() -> None:
    # Load the evaluation reports.
    records = load_evaluation_reports()

    # Find the best N triples scored by the judge.
    best_triples = find_best_triples(records, n=500)

    # Save the best triples to a CSV file
    with open(EVALUATION_DIR / "best_judged_triples.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "predicate", "object", "confidence", "source", "section", "correctness", "relevance", "well_formedness", "normalized_score", "rationale", "error"])
        for triple in best_triples:
            writer.writerow([triple.subject, triple.predicate, triple.object, triple.confidence, triple.source, triple.section, triple.correctness, triple.relevance, triple.well_formedness, triple.normalized, triple.rationale, triple.error])

if __name__ == "__main__":
    main()