"""
Triple generation module for the UKG Generator.

Extracts subject-predicate-object triples from natural language text using
spaCy dependency parsing, named entity recognition, and PoS tagging.
Also uses GLiNER-relex for ML-based span relation extraction.
Serializes output as RDF via rdflib.
"""

import logging
import os
import re
import threading
import spacy
import csv

from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from gliner import GLiNER
from spacy.tokens import Doc, Span
from rdflib import Graph, Literal, Namespace, URIRef
from extraction_module import Section

logger = logging.getLogger(__name__)

SPECIAL_ENTITY_CHARS = ["%", "±", "(", ")", "[", "]", "{", "}", "<", ">", "=", "*", "+", "≤", "≥"]


# ---------------------------------------------------------------------------
# Model / resource caches
# ---------------------------------------------------------------------------
#
# Cache fully-initialised extractor instances at module level with the same model name 
# so repeated invocations within a single process share the same in-memory model weights.

gpu_enabled: bool | None = None
spacy_lock = threading.Lock()
spacy_cache: dict[str, "spacy.Language"] = {}
gliner_lock = threading.Lock()
gliner_cache: dict[str, GLiNER] = {}


def ensure_gpu() -> bool:
    """
    Best-effort GPU activation for spaCy/transformers. Called once per process.
    If the UKG_DISABLE_GPU environment variable is set to 1, the GPU is disabled.

    Returns:
        True if the GPU is enabled, False if the GPU is disabled or not available.
    """
    global gpu_enabled
    if gpu_enabled is not None:
        return gpu_enabled

    if os.environ.get("UKG_DISABLE_GPU") == "1":
        gpu_enabled = False
        return False

    try:
        # Uses the GPU if available, otherwise uses the CPU.
        gpu_enabled = bool(spacy.prefer_gpu())
    except Exception as exc:
        logger.debug("spacy.prefer_gpu() failed: %s", exc)
        gpu_enabled = False
    return gpu_enabled


def load_spacy(model_name: str) -> "spacy.Language":
    """
    Return a cached spaCy pipeline for model_name, loading it if needed.
    Prevents multiple instances of the same model from being loaded into memory.

    Args:
        model_name: The name of the spaCy model to load.

    Returns:
        A spaCy pipeline for the model.
    """
    with spacy_lock:
        # Return the cached spaCy pipeline if it exists.
        nlp = spacy_cache.get(model_name)
        if nlp is not None:
            return nlp

        # Otherwise, ensure the GPU is enabled and load the model.
        ensure_gpu()
        try:
            nlp = spacy.load(model_name)
        except OSError:
            # If the model is not found, download it.
            from spacy.cli import download
            download(model_name)
            nlp = spacy.load(model_name)
        
        # Cache the spaCy pipeline for future use.
        spacy_cache[model_name] = nlp
        return nlp


def load_gliner(model_name: str) -> GLiNER:
    """
    Return a cached GLiNER model, moving it to CUDA when available.
    Prevents multiple instances of the same model from being loaded into memory.

    Args:
        model_name: The name of the GLiNER model to load.

    Returns:
        A GLiNER model.
    """
    with gliner_lock:
        # Return the cached GLiNER model if it exists.
        model = gliner_cache.get(model_name)
        if model is not None:
            return model

        # Otherwise, load the GLiNER model.
        model = GLiNER.from_pretrained(model_name)
        if os.environ.get("UKG_DISABLE_GPU") != "1":
            try:
                import torch
                # If the GPU is available, move the GLiNER model to the GPU.
                if torch.cuda.is_available():
                    model = model.to("cuda")
            except Exception as exc:
                logger.debug("Could not move GLiNER to CUDA: %s", exc)
        
        # Cache the GLiNER model for future use.
        gliner_cache[model_name] = model
        return model


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Triple(NamedTuple):
    """Represents an extracted triple with provenance metadata."""
    sub: str                            # Subject of the triple.
    pred: str                           # Predicate of the triple.
    obj: str                            # Object of the triple.
    conf: float = 0.0                   # Confidence score of the triple.
    source: str = ""                    # Source of the triple (its extraction method).
    section: str = ""                   # Section of the triple.

    def __str__(self):
        return f"({self.sub}, {self.pred}, {self.obj})"


# ---------------------------------------------------------------------------
# Triple extraction
# ---------------------------------------------------------------------------

class TripleExtractor:
    """
    Extracts triples from natural language text using spaCy's dependency
    parsing, named entity recognition, and PoS tagging.
    """

    def __init__(self, model_name: str = "en_core_web_lg"):
        """
        Initialize the triple extractor with a spaCy model.
        Defaults to using the en_core_web_lg model.

        Args:
            model_name: Name of the spaCy model to use.
        """
        self.nlp = load_spacy(model_name)

    def extract_from_doc(self, doc: Doc, section: str = "") -> list[Triple]:
        """
        Extract all triples from a parsed spaCy Doc.

        Input:
            doc: The spaCy Doc to extract triples from.
            section: The heading of the section that the document belongs to.
        Returns:
            A list of triples.
        """
        triples: list[Triple] = []

        # Extract triples from each sentence in the document.
        for sent in doc.sents:
            triples.extend(self.extract_svo(sent))                 # Extract subject-verb-object triples.
            triples.extend(self.extract_copular(sent))             # Extract copular triples.
            triples.extend(self.extract_prep_relations(sent))      # Extract prepositional triples.
            triples.extend(self.extract_pos_triples(sent))         # Extract PoS-tagging triples.

        if section:
            triples = [
                t._replace(section=section) for t in triples
            ]

        return triples

    # -- subject-verb-object patterns -----------------------------------------

    def extract_svo(self, sent: Span) -> list[Triple]:
        """
        Extract Subject-Verb-Object triples from a sentence.

        Input:
            sent: The sentence to extract triples from.
        Returns:
            A list of triples.
         """
        root = None
        for token in sent:
            if token.dep_ == "ROOT":
                root = token
                break
        if root is None:
            return []
        return self.svo_from_verb(root)

    def svo_from_verb(self, verb) -> list[Triple]:
        """
        Extract Subject-Verb-Object triples from a verb (the root of the sentence).
        This uses the dependency parser to identify the subject and object of the triple.
        """
        triples: list[Triple] = []

        subject = None
        for child in verb.children:
            # Identify the subject using a proper noun or a passive nominal subject.
            if child.dep_ in ("nsubj", "nsubjpass"):
                # Get the compound noun for the subject using the child branch of the dependency tree.
                subject = self.get_compound_noun(child)
                break
        if subject is None:
            return triples

        # Direct objects / attributes
        for child in verb.children:
            if child.dep_ in ("dobj", "attr", "oprd"):
                obj = self.get_compound_noun(child)
                if obj is None:
                    continue
                predicate = self.get_verb_phrase(verb)
                triples.append(Triple(subject, predicate, obj, 0.3, "svo"))

        # Prepositional objects attached to the verb
        for child in verb.children:
            if child.dep_ == "prep":
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        obj = self.get_compound_noun(pobj)
                        if obj is None:
                            continue
                        predicate = f"{verb.lemma_}_{child.text}".lower()
                        triples.append(Triple(subject, predicate, obj, 0.3, "svo"))

        # Passive voice: "X was done by Y"
        if any(c.dep_ == "nsubjpass" for c in verb.children):
            for child in verb.children:
                if child.dep_ == "agent":
                    for pobj in child.children:
                        if pobj.dep_ == "pobj":
                            agent = self.get_compound_noun(pobj)
                            if agent is None:
                                continue
                            predicate = self.get_verb_phrase(verb)
                            triples.append(
                                Triple(agent, predicate, subject, 0.3, "svo")
                            )

        return triples

    # -- Copular constructions ----------------------------------------------

    # Mapping from copular verb lemma to the predicate used in triples.
    COPULAR_PREDICATES: dict[str, str] = {
        "be":     "is_a",
        "become": "becomes",
        "remain": "remains",
        "seem":   "seems",
        "appear": "appears",
        "look":   "looks",
        "feel":   "feels",
        "stay":   "stays",
        "turn":   "turns",
        "grow":   "grows",
        "get":    "gets",
        "go":     "goes",
        "prove":  "proves",
    }

    def extract_copular(self, sent: Span) -> list[Triple]:
        """
        Extract copular constructions (e.g. 'X is Y', 'X becomes Y',
        'X remains Y', 'X seems Y', 'X appears Y').
        Input:
            sent: The sentence to extract copular relations from.
        Returns:
            A list of triples.
        """
        triples: list[Triple] = []

        for token in sent:
            predicate = self.COPULAR_PREDICATES.get(token.lemma_)
            if predicate is None:
                continue
            if token.pos_ not in ("AUX", "VERB") and token.dep_ != "ROOT":
                continue

            subject = None
            obj = None

            # Find clauses associated with the copular verb
            children = (
                token.head.children if token.dep_ == "aux" else token.children
            )

            for child in children:
                if child.dep_ == "nsubj":
                    subject = self.get_compound_noun(child)
                elif child.dep_ in ("attr", "acomp"):
                    obj = self.get_compound_noun(child)

            if token.dep_ == "ROOT":
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = self.get_compound_noun(child)
                    elif child.dep_ in ("attr", "acomp"):
                        obj = self.get_compound_noun(child)

            if subject and obj:
                triples.append(Triple(subject, predicate, obj, 0.2, "copular"))

        return triples

    # -- Prepositional relations --------------------------------------------

    def extract_prep_relations(self, sent: Span) -> list[Triple]:
        """
        Extract noun-preposition-noun relations.
        For example, 'A cure for cancer'.
        Input:
            sent: The sentence to extract prepositional relations from.
        Returns:
            A list of triples.
        """
        triples: list[Triple] = []

        for token in sent:
            # Check if the token is a preposition and the head is a noun or proper noun
            if token.dep_ == "prep" and token.head.pos_ in ("NOUN", "PROPN"):
                subject = self.get_compound_noun(token.head)
                prep = token.text.replace(" ", "_").lower()

                # Find the object of the prepositional phrase
                for child in token.children:
                    if child.dep_ == "pobj":
                        obj = self.get_compound_noun(child)
                        triples.append(Triple(subject, prep, obj, 0.2, "prep"))

        return triples

    # -- PoS-tagging heuristic extraction -----------------------------------

    def extract_pos_triples(self, sent: Span) -> list[Triple]:
        """
        Fallback extraction using PoS tags: find NOUN-VERB-NOUN windows that
        the dependency parser may have missed.

        These triples receive a lower confidence score (0.1) since the
        heuristic is less precise than dependency-based extraction.
        """
        triples: list[Triple] = []
        tokens = list(sent)
        noun_tags = {"NOUN", "PROPN"}

        # Only allow a maximum window of 5 tokens on the left and right of the verb.
        max_window = 5

        for i, tok in enumerate(tokens):
            if tok.pos_ != "VERB":
                continue

            # Find the left head noun.
            left_noun = None
            for j in range(i - 1, max(i - max_window - 1, -1), -1):
                if tokens[j].pos_ in noun_tags:
                    left_noun = tokens[j]
                    break

            # Find the right head noun.
            right_noun = None
            for j in range(i + 1, min(i + max_window + 1, len(tokens))):
                if tokens[j].pos_ in noun_tags:
                    right_noun = tokens[j]
                    break

            if left_noun is not None and right_noun is not None:
                sub = self.get_compound_noun(left_noun)
                pred = tok.lemma_.lower()
                obj = self.get_compound_noun(right_noun)
                triples.append(Triple(sub, pred, obj, 0.1, "pos"))

        return triples

    # -- helper utilities ---------------------------------------------------

    def get_compound_noun(self, token) -> str:
        """
        Expand a token into its full compound-noun phrase.
        For example, 'cognitive impairment' instead of just 'impairment'.

        Input:
            token: The token to expand.
        Returns:
            A string representing the compound noun.
        """
        parts: list[str] = []

        # Get left modifiers (compound nouns, adjectives)
        for child in token.lefts:
            if child.dep_ in ("compound", "amod", "nmod"):
                parts.append(child.text)

        parts.append(token.text)

        # Get right modifiers
        for child in token.rights:
            if child.dep_ == "compound":
                parts.append(child.text)

        return "_".join(parts).lower()

    def get_verb_phrase(self, verb) -> str:
        """
        Expand a verb into its full verb phrase (aux + verb + particle).
        For example, 'give up' instead of just 'give'.

        Input:
            verb: The verb to expand.
        Returns:
            A string representing the verb phrase.
        """
        parts: list[str] = []

        for child in verb.children:
            if child.dep_ == "aux":
                parts.append(child.text)

        parts.append(verb.lemma_)

        for child in verb.children:
            if child.dep_ == "prt":
                parts.append(child.text)

        return "_".join(parts).lower()

# ---------------------------------------------------------------------------
# Span-based relation extraction (GLiNER-relex)
# ---------------------------------------------------------------------------

# Default entity and relation labels for domain independent text.
DEFAULT_SPAN_ENTITY_LABELS = {
    "person": "A person, individual, or human being.",
    "organization": "An organization, institution, or group of people.",
    "location": "A location, place, or geographical area.",
    "event": "An event, occurrence, or happening.",
    "product": "A product, item, or object.",
    "concept": "A concept, idea, or notion.",
    "method": "A method, technique, or process.",
    "other": "Other entities that do not fit into the other categories.",
}

DEFAULT_SPAN_RELATION_LABELS = [
    "linked to",
    "part of",
    "creates",
    "causes",
    "uses",
    "describes",
    "measures",
    "evaluates",
    "tests",
    "classifies",
]

class SpanRelationExtractor:
    """
    Extracts triples from text using GLiNER-relex, a zero-shot span-based
    NER + relation extraction model.
    """

    def __init__(
        self,
        model_name: str = "knowledgator/gliner-relex-large-v0.5",
        entity_labels: dict[str, str] | list[str] | None = None,
        relation_labels: list[str] | None = None,
        relation_threshold: float = 0.5,
        batch_size: int = 4,
    ):
        """
        Initialize the span relation extractor.

        Args:
            model_name: Hugging Face model name for GLiNER-relex.
            entity_labels: Entity types to extract, optionally with descriptions.
            relation_labels: Relation types to extract.
            relation_threshold: Minimum confidence for relations (0–1).
            batch_size: Number of texts sent to GLiNER per inference call.
        """

        configured_batch_size = os.environ.get("UKG_SPAN_BATCH_SIZE")
        if configured_batch_size:
            batch_size = int(configured_batch_size)

        self.model = load_gliner(model_name)
        self.entity_labels = entity_labels if entity_labels is not None else DEFAULT_SPAN_ENTITY_LABELS
        self.relation_labels = relation_labels if relation_labels is not None else DEFAULT_SPAN_RELATION_LABELS
        self.relation_threshold = relation_threshold
        self.batch_size = max(1, int(batch_size))
        max_model_tokens = getattr(getattr(self.model, "config", None), "max_len", 1024)
        self.max_words_per_text = max(64, min(220, int(max_model_tokens) // 4))
        self.word_overlap = min(32, max(8, self.max_words_per_text // 8))

    def triples_from_relations(
        self,
        relations: list[dict],
        section: str = "",
    ) -> list[Triple]:
        """
        Convert raw GLiNER relation output into Triple objects.
        The confidence score is multiplied by 0.75 to downweight the span extraction.

        Input:
            relations: The list of relations to convert into triples.
        Returns:
            A list of triples.
        """
        triples: list[Triple] = []
        for rel in relations:
            if rel["score"] < self.relation_threshold:
                continue
            head = rel["head"]["text"]
            tail = rel["tail"]["text"]
            pred = rel["relation"]
            score = float(rel["score"]) * 0.75
            sub = self.normalize_span_text(head)
            obj = self.normalize_span_text(tail)
            pred_key = re.sub(r"\s+", " ", pred).strip().lower()
            pred_norm = pred_key.replace(" ", "_")
            triples.append(Triple(sub, pred_norm, obj, score, "span", section))
        return triples

    @staticmethod
    def is_cuda_oom(exc: Exception) -> bool:
        """
        Check if the exception is a CUDA OOM error.
        Input:
            exc: The exception to check.
        Returns:
            True if the exception is a CUDA OOM error, False otherwise.
        """
        message = str(exc).lower()
        return "cuda out of memory" in message or exc.__class__.__name__ == "OutOfMemoryError"
    
    @staticmethod
    def clear_cuda_cache() -> None:
        """
        Clear the CUDA cache.
        """
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            logger.debug("Unable to clear CUDA cache after GLiNER inference failure.", exc_info=True)

    def split_long_text(self, text: str, section: str) -> list[tuple[str, str]]:
        """
        Split oversized inputs so one sentence cannot monopolize GPU memory.
        Input:
            text: The text to split.
            section: The section of the text.
        Returns:
            A list of tuples, each containing a window of the text and the section.
        """
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        words = normalized.split()
        if len(words) <= self.max_words_per_text:
            return [(normalized, section)]

        stride = max(1, self.max_words_per_text - self.word_overlap)
        windows: list[tuple[str, str]] = []
        for start in range(0, len(words), stride):
            window_words = words[start : start + self.max_words_per_text]
            if not window_words:
                break
            windows.append((" ".join(window_words), section))
            if start + self.max_words_per_text >= len(words):
                break

        logger.warning(
            "Split long span-extraction input in section '%s' into %s windows (%s words total).",
            section or "<unknown>",
            len(windows),
            len(words),
        )
        return windows

    def infer_relations(self, chunk: list[tuple[str, str]], batch_size: int | None = None) -> list[list[dict]]:
        """
        Run GLiNER inference on a chunk of text.
        
        Input:
            chunk: The chunk of text to infer relations from.
            batch_size: The batch size to use for the inference.
        Returns:
            A list of lists of relations.
        """
        effective_batch_size = min(batch_size or self.batch_size, len(chunk))
        try:
            _, relations = self.model.inference(
                texts=[text for text, _ in chunk],
                labels=self.entity_labels,
                relations=self.relation_labels,              
                threshold=0.4,                               # entity confidence threshold
                adjacency_threshold=0.55,                    # threshold for entity pair candidates
                relation_threshold=self.relation_threshold,  # relation confidence threshold
                batch_size=effective_batch_size,             # batch size for the inference
                return_relations=True,                       # return the relations (instead of only entities)    
                flat_ner=False,                              # do not enforce non-overlapping entities
            )
        except Exception as exc:
            if not self.is_cuda_oom(exc):
                raise

            # If the exception is a CUDA OOM error, clear the CUDA cache and retry with a smaller batch size.
            self.clear_cuda_cache()
            if effective_batch_size > 1:
                next_batch_size = max(1, effective_batch_size // 2)
                logger.warning(
                    "CUDA OOM during GLiNER inference for %s texts; retrying with micro-batch size %s.",
                    len(chunk),
                    next_batch_size,
                )
                return self.infer_relations(chunk, batch_size=next_batch_size)

            # If the exception is a CUDA OOM error, and the chunk is only one text, skip the span extraction.
            if len(chunk) == 1:
                logger.warning(
                    "Skipping span extraction for one text in section '%s' after repeated CUDA OOM.",
                    chunk[0][1] or "<unknown>",
                )
                return [[]]

            # If the exception is a CUDA OOM error, and the chunk is more than one text, split the chunk into two smaller chunks and retry.
            # Calls the function recursively to handle the smaller chunks.
            midpoint = len(chunk) // 2
            logger.warning(
                "CUDA OOM persisted at micro-batch size 1; splitting %s texts into smaller chunks.",
                len(chunk),
            )
            return self.infer_relations(chunk[:midpoint], batch_size=1) + self.infer_relations(
                chunk[midpoint:], batch_size=1
            )

        if len(relations) != len(chunk):
            raise RuntimeError(
                "GLiNER returned "
                f"{len(relations)} relation groups for {len(chunk)} input texts."
            )
        return relations

    def extract_from_texts(
        self,
        texts: list[str],
        sections: list[str] | None = None,
    ) -> list[Triple]:
        """
        Extract triples from many texts, batching the GLiNER inference call
        so the model sees a manageable slice at a time. This keeps the GPU
        warm across batches without using up all available GPU memory.

        Input:
            texts: The list of texts to extract triples from.
            sections: The list of sections of the texts.
        Returns:
            A list of triples.
        """

        # Filter out empty texts and split long texts into smaller chunks.
        valid_items: list[tuple[str, str]] = []
        for idx, text in enumerate(texts):
            if not text.strip():
                continue
            section = sections[idx] if sections else ""
            valid_items.extend(self.split_long_text(text, section))

        if not valid_items:
            return []

        # Run GLiNER inference on the valid items in batches.
        triples: list[Triple] = []
        for start in range(0, len(valid_items), self.batch_size):
            chunk = valid_items[start : start + self.batch_size]
            relations = self.infer_relations(chunk)
            for (_, section), relation_group in zip(chunk, relations):
                triples.extend(
                    self.triples_from_relations(relation_group, section=section)
                )
        return triples

    def normalize_span_text(self, text: str) -> str:
        """Normalize span text to match Triple format (underscores, lowercase)."""
        return text.replace(" ", "_").lower()


# ---------------------------------------------------------------------------
# RDF serialization
# ---------------------------------------------------------------------------

class RDFSerializer:
    """Serializes Triple objects to various RDF formats via rdflib."""

    def __init__(
        self,
        base_namespace: str = "http://example.org/ukg#",
        prefix: str = "ukg",
    ):
        self.namespace = Namespace(base_namespace)
        self.graph = Graph()
        self.graph.bind(prefix, self.namespace)

    def add_triple(self, triple: Triple):
        subject_uri = self.make_uri(triple.sub)
        predicate_uri = self.make_uri(triple.pred)

        if triple.pred == "is_a":
            obj_node = self.make_uri(triple.obj)
        else:
            obj_node = Literal(triple.obj)

        self.graph.add((subject_uri, predicate_uri, obj_node))

    def add_triples(self, triples: list[Triple]):
        for triple in triples:
            self.add_triple(triple)

    def make_uri(self, text: str) -> URIRef:
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", text)
        return self.namespace[clean]

    def serialize(self, fmt: str = "turtle") -> str:
        return self.graph.serialize(format=fmt)

    def save(self, filepath: str, fmt: str = "turtle"):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(self.serialize(fmt))


# ---------------------------------------------------------------------------
# Ontology-aware confidence boosting
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
# A frozen set is a set that is immutable (used to cache the ontology terms).
def load_ontology_terms(ontology_list: tuple[str, ...]) -> frozenset[str]:
    """
    Load and cache ontology terms for a given list of ontology files.
    Expects each line to be a single term.

    Input:
        ontology_list: The list of ontology files to load.
    Returns:
        A frozen set of ontology terms.
    """
    terms: set[str] = set()
    for ontology_file in ontology_list:
        with open(ontology_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                term = line.strip().lower()
                if term:
                    terms.add(term)
    return frozenset(terms)

class OntologyFilter:
    """
    Loads domain term lists from resources/ontology/ and adjusts triple
    confidence when subjects or objects match known ontology terms.

    Term sets are cached per resources directory across calls so repeated
    invocations within a process don't re-walk the filesystem or re-parse
    the (large) UMLS / SNOMED text files.
    """

    def __init__(self, ontology_list: list[str] | tuple[str, ...]):
        self.terms: frozenset[str] = load_ontology_terms(tuple(ontology_list))

    def normalize(self, text: str) -> str:
        return text.replace("_", " ").lower()

    def matches(self, text: str) -> bool:
        return self.normalize(text) in self.terms

    def boost(
        self,
        triples: list[Triple],
        boost_amount: float = 0.05,
        require_match: bool = False,
    ) -> list[Triple]:
        """
        Boost confidence of triples whose subject or object matches a known
        ontology term. When require_match is True, triples with no matching
        term are dropped entirely.
        """
        result: list[Triple] = []
        for t in triples:
            sub_match = self.matches(t.sub)
            obj_match = self.matches(t.obj)

            if require_match and not (sub_match or obj_match):
                continue

            new_conf = t.conf
            if sub_match:
                new_conf = min(new_conf + boost_amount, 1.0)
            if obj_match:
                new_conf = min(new_conf + boost_amount, 1.0)

            result.append(t._replace(conf=new_conf))

        return result

# ---------------------------------------------------------------------------
# Triple filtering and validation
# ---------------------------------------------------------------------------
def remove_duplicates(triples: list[Triple]) -> list[Triple]:
    """
    Remove duplicates, keeping the first (highest-confidence) occurrence.
    Boost the confidence of the existing triple by 0.001 for each duplicate.
    For example, if there are 3 duplicates, the confidence will be boosted by 0.015.
    
    Input:
        triples: The list of triples to remove duplicates from.
    Returns:
        A list of unique triples.
    """
    seen: set[tuple[str, str, str]] = set()
    unique: list[Triple] = []
    for t in triples:
        key = (t.sub, t.pred, t.obj)
        if key not in seen:
            seen.add(key)
            unique.append(t)
        else:
            # Add to the confidence of the existing triple
            existing = next(t for t in unique if t.sub == key[0] and t.pred == key[1] and t.obj == key[2])
            existing = existing._replace(conf=existing.conf + 0.001)
    return unique

def is_invalid_string(text: str) -> bool:
    """
    Return True when a string is an invalid entity or predicate.
    Used to filter out invalid triples.

    Input:
        text: The string to check.
    Returns:
        True if the string is an invalid entity or predicate, False if it is valid.
    """
    normalized = text.replace("_", " ").strip().lower()

    # String must be at least 3 characters long.
    if len(normalized) < 3:
        return True

    # String must not contain any numbers.
    if re.search(r"\d+(\.\d+)?%?", normalized):
        return True

    # String must not contain any special characters.
    if any(char in normalized for char in SPECIAL_ENTITY_CHARS):
        return True
    return False

def load_blacklist_files(filepaths: list[str]) -> frozenset[tuple[str, str, str, str, str]]:
    """
    Load a blacklist from a csv file.
    The headers of the CSV file are expected to be: term,category,rule,subject,object:
        - term: The term to blacklist
        - category: The category of the term
        - rule: The rule to apply to the term (excl_only or excl)
        - subject: Whether the term is a subject (1) or object (0)
        - object: Whether the term is an object (1) or subject (0)
    
    Input:
        filepath: The path to the blacklist csv file.
    Returns:
        A list of tuples, each containing the term, category, rule, subject, and object.
    """
    blacklists: list[frozenset[tuple[str, str, str, str, str]]] = []
    for filepath in filepaths:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            # Ignore the header row.
            next(reader)
            blacklist = []
            for row in reader:
                term, category, rule, subject, object = row
                blacklist.append((term, category, rule, subject, object))
            blacklists.append(frozenset(blacklist))
    return blacklists

def build_blacklist_sets(blacklists: list[frozenset[tuple[str, str, str, str, str]]]):
    """
    Filter out triples that match any of the terms in the blacklist with specific rules.
    Blacklist rules:
        - excl: Exclude the triple if the blacklisted term is a substring of the subject or object.
        - excl_only: Exclude when the subject or object equals the term (case-insensitive, spaces
          normalized to underscores), not substring match.
    
    Input:
        blacklists: The list of blacklists to use. To see the format of the blacklists, see load_blacklist_files().
    Returns:
        A tuple of lists, each containing the blacklisted terms for the subject and object.
    """
    subject_excl_str = []
    object_excl_str = []
    subject_excl_word = []
    object_excl_word = []
    
    for blacklist in blacklists:
        for term, category, rule, subject, object in blacklist:
            if rule == "excl":
                if subject == "1":
                    subject_excl_str.append(term)
                if object == "1":
                    object_excl_str.append(term)
            elif rule == "excl_only":
                if subject == "1":
                    subject_excl_word.append(term)
                if object == "1":
                    object_excl_word.append(term)
    
    # Remove duplicates from the blacklist sets.
    subject_excl_str = list(set(subject_excl_str))
    object_excl_str = list(set(object_excl_str))
    subject_excl_word = list(set(subject_excl_word))
    object_excl_word = list(set(object_excl_word))

    return subject_excl_str, object_excl_str, subject_excl_word, object_excl_word

def normalize_blacklist_entity(text: str) -> str:
    return text.strip().replace(" ", "_").lower()

def match_entity_string(text: str, blacklist: list[str]) -> bool:
    """
    Check if an entity contains a substring from the blacklist.

    Input:
        text: The string to check.
        blacklist: The list of substrings to check for.
    Returns:
        True if the entity contains the substring, False otherwise.
    """
    text_norm = normalize_blacklist_entity(text)
    for substring in blacklist:
        substring = normalize_blacklist_entity(substring)
        if substring in text_norm:
            return True
    return False

def match_entity_exact(text: str, blacklist: list[str]) -> bool:
    """
    Check if an entity is exactly the same as any term from the blacklist.

    Input:
        text: The string to check.
        blacklist: The list of terms to check for.
    Returns:
        True if the entity is exactly the same as the term, False otherwise.
    """
    text_norm = normalize_blacklist_entity(text)
    for term in blacklist:
        if text_norm == normalize_blacklist_entity(term):
            return True
    return False

def match_stopwords(text:str, stopwords: list[str]) -> bool:
    """
    Check if a string is a stopword (exact match).
    """
    return text.strip().lower() in stopwords

def is_identity_triple(subject: str, object: str) -> bool:
    """
    Check if a triple is an identity triple.
    """
    return subject == object

def filter_triples(triples: list[Triple], blacklist_sets: tuple[list[str], list[str], list[str], list[str]], stopwords: list[str] = []):
    """
    Filter out triples that match any of the terms in the blacklist with specific rules.

    Input:
        triples: The list of triples to filter.
        blacklist_sets: The blacklist sets to use.
        stopwords: The list of stopwords to filter out.
    Returns:
        A list of triples that do not match any of the terms in the blacklist.
    """
    result: list[Triple] = []
    subject_excl_str, object_excl_str, subject_excl_word, object_excl_word = blacklist_sets
    for triple in triples:
        # Filter out triples with invalid entities or predicates.
        if is_invalid_string(triple.sub) or is_invalid_string(triple.pred) or is_invalid_string(triple.obj):
            continue
        # Filter out triples with stopwords.
        if match_stopwords(triple.sub, stopwords) or match_stopwords(triple.obj, stopwords):
            continue
        # Filter out triples with entities or objects that contain the substring blacklist terms.
        if match_entity_string(triple.sub, subject_excl_str) or match_entity_string(triple.obj, object_excl_str):
            continue
        # Filter out triples with entities or objects that contain the word blacklist terms.
        if match_entity_exact(triple.sub, subject_excl_word) or match_entity_exact(triple.obj, object_excl_word):
            continue
        # Filter out identity triples.
        if is_identity_triple(triple.sub, triple.obj):
            continue
        result.append(triple)
    return result

# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def generate_triples(
    sections: list[Section],
    model_name: str = "en_core_web_lg",
    base_namespace: str = "http://ukg-data.org/ukg#",
    output_path: str | None = None,
    output_format: str = "turtle",
    ontology_files: list[str] = [],
    require_ontology_match: bool = False,
    use_span_extraction: bool = True,
    span_model: str = "knowledgator/gliner-relex-large-v0.5",
    blacklist_sets: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
    entity_labels: dict[str, str] | list[str] | None = None,
    relation_labels: list[str] | None = None,
) -> list[Triple]:
    """
    End-to-end triple generation from (heading, text) tuples.

    Args:
        sections: List of sections to extract triples from.
        model_name: The name of the spaCy model to use.
        base_namespace: The RDF namespace URI.
        output_path: The path to the output file.
        output_format: The format of the output file.
        ontology_files: The list of ontology files to use.
        require_ontology_match: Whether to require ontology matches.
        use_span_extraction: Whether to use span extraction.
        span_model: The name of the span extraction model to use.
        blacklist_sets: The tuple of blacklist sets (subject_excl_str, object_excl_str, subject_excl_word, object_excl_word)
                        see build_blacklist_sets() for more details.
        entity_labels: The optional entity labels to pass to the span extractor.
                       When None, the extractor's own defaults are used.
        relation_labels: The optional relation labels to pass to the span extractor.
                         When None, the extractor's own defaults are used.

    Returns:
        List of extracted Triple objects.
    """
    extractor = TripleExtractor(model_name)

    all_triples: list[Triple] = []
    sentence_texts: list[str] = []
    sentence_sections: list[str] = []
    stopwords: list[str] = list(extractor.nlp.Defaults.stop_words)

    # Run the spaCy pipeline on the sections once and then extract the triples from the docs.
    docs = extractor.nlp.pipe((section.text for section in sections), batch_size=32)
    for section, doc in zip(sections, docs):
        all_triples.extend(extractor.extract_from_doc(doc, section=section.heading))
        if use_span_extraction:
            for sent in doc.sents:
                sentence_texts.append(sent.text)
                sentence_sections.append(section.heading)

    # If span extraction is enabled, extract the triples from the sentences using GLiNER-relex.
    if use_span_extraction:
        span_extractor = SpanRelationExtractor(
            model_name=span_model,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
        )
        all_triples.extend(
            span_extractor.extract_from_texts(sentence_texts, sections=sentence_sections)
        )

    all_triples = remove_duplicates(all_triples)
    all_triples = filter_triples(all_triples, blacklist_sets, stopwords)

    # Check if the ontology directory exists and if not, use the default directory.
    ont_filter = OntologyFilter(ontology_files) if ontology_files else None
    if ont_filter:
        all_triples = ont_filter.boost(
            all_triples, require_match=require_ontology_match,
        )

    # If an output path is provided, serialize the triples to the output file.
    if output_path:
        serializer = RDFSerializer(base_namespace)
        serializer.add_triples(all_triples)
        serializer.save(output_path, fmt=output_format)

    return all_triples