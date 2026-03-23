"""
Triple generation module for the UKG Generator.

Extracts subject-predicate-object triples from natural language text using
spaCy dependency parsing, named entity recognition, and PoS tagging.
Also uses GLiNER-relex for ML-based span relation extraction.
Serializes output as RDF via rdflib.
"""

from __future__ import annotations
import spacy
import re
from gliner import GLiNER
from pathlib import Path
from typing import NamedTuple
from spacy.tokens import Span
from rdflib import Graph, Literal, Namespace, URIRef
from extraction_module import Section


# Words and characters which do not provide much lexical information (or are generic words) about the relations as entities
blacklist_words = {
    "we",
    "us",
    "our",
    "ourselves",
    "this",
    "that",
    "these",
    "those",
    "these",
    "they",
    "it",
    "i",
    "who",
    "whom",
    "whose",
    "former",
    "latter",
    "service",
    "others",
    "other",
    "another",
    "some",
    "any",
    "all",
    "most",
    "many",
    "few",
    "object",
    "so",
    "such",
    "basic",
    "part",
    "core",
    "go",
    "area",
    "odds",
    "part",
    "view",
    "set",
    "fig",
    "figs",
    "chart",
    "charts",
    "plot",
    "plots",
    "photo",
    "picture",
    "video",
    "audio",
    "tries",
    "sum",
    "information",
    "similar",
    "moment",
    "dataset",
    "datasets",
    "access",
    "threshold",
    "object",
    "means",
    "index",
    "indices",
    "metrics",
    "exception",
    "exceptions",
    "using",
    "percentile",
    "prevalent",
    "validated",
    "predict",
    "improved",
    "self",
    "with",
    "within",
    "roles",
    "role"
    "big",
    "small",
    "medium",
    "large",
    "few",
    "more",
    "many",
    "specific",
    "need",
    "supporting",
    "science",
    "other hand",
    "machine learning",
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "for",
    "to",
    "with",
    "by",
    "from",
    "at",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "this",
    "that",
    "these",
    "those",
    "it",
    "they",
    "we",
    "our",
    "next",
    "last",
    "previous",
    "other",
    "higher",
    "lower",
}

GENERIC_ENTITY_WORDS = {
    "approach",
    "case",
    "cases",
    "cause",
    "data",
    "details",
    "example",
    "examples",
    "factor",
    "factors",
    "feature",
    "features",
    "figure",
    "figures",
    "graph",
    "graphs",
    "image",
    "images",
    "information",
    "item",
    "items",
    "measure",
    "measures",
    "method",
    "methods",
    "model",
    "models",
    "point",
    "points",
    "result",
    "results",
    "risk",
    "risks",
    "score",
    "scores",
    "state",
    "study",
    "studies",
    "table",
    "tables",
    "tool",
    "tools",
    "type",
    "types",
    "variable",
    "variables",
}

SPECIAL_ENTITY_CHARS = ["%", "±", "(", ")", "[", "]", "{", "}", "<", ">", "="]


def is_low_information_entity(text: str, custom_blacklist: list[str] | None = None) -> bool:
    """Return True when an entity-like span is too generic to keep."""
    normalized = text.replace("_", " ").strip().lower()

    if len(normalized) < 3:
        return True

    if normalized in blacklist_words:
        return True
    
    if custom_blacklist and normalized in custom_blacklist:
        return True

    if re.search(r"\d+(\.\d+)?%?", normalized):
        return True

    if any(char in normalized for char in SPECIAL_ENTITY_CHARS):
        return True

    tokens = re.findall(r"[a-z]+", normalized)
    if not tokens:
        return True

    meaningful_tokens = [
        token
        for token in tokens
        if token not in STOPWORDS and token not in GENERIC_ENTITY_WORDS
    ]

    if not meaningful_tokens:
        return True

    if len(tokens) == 1 and tokens[0] in GENERIC_ENTITY_WORDS:
        return True

    return False

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
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)

    # -- public API ---------------------------------------------------------

    def extract_from_text(self, text: str, section: str = "") -> list[Triple]:
        """Extract all triples from *text*, deduplicating by (sub, pred, obj)."""
        doc = self.nlp(text)
        triples: list[Triple] = []

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

    # Subject-Verb-Object extraction
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
        if subject is None or is_low_information_entity(subject):
            return triples

        # Direct objects / attributes
        for child in verb.children:
            if child.dep_ in ("dobj", "attr", "oprd"):
                obj = self.get_compound_noun(child)
                if obj is None or is_low_information_entity(obj):
                    continue
                predicate = self.get_verb_phrase(verb)
                triples.append(Triple(subject, predicate, obj, 0.15, "svo"))

        # Prepositional objects attached to the verb
        for child in verb.children:
            if child.dep_ == "prep":
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        obj = self.get_compound_noun(pobj)
                        if obj is None or is_low_information_entity(obj):
                            continue
                        predicate = f"{verb.lemma_}_{child.text}".lower()
                        triples.append(Triple(subject, predicate, obj, 0.15, "svo"))

        # Passive voice: "X was done by Y"
        if any(c.dep_ == "nsubjpass" for c in verb.children):
            for child in verb.children:
                if child.dep_ == "agent":
                    for pobj in child.children:
                        if pobj.dep_ == "pobj":
                            agent = self.get_compound_noun(pobj)
                            if agent is None or is_low_information_entity(agent):
                                continue
                            predicate = self.get_verb_phrase(verb)
                            triples.append(
                                Triple(agent, predicate, subject, 0.15, "svo")
                            )

        return triples

    # -- Copular constructions ----------------------------------------------

    def extract_copular(self, sent: Span) -> list[Triple]:
        """
        Extract copular constructions (e.g. 'X is Y', 'X becomes Y').
        For example, 'Cancer is a disease'.
        Input:
            sent: The sentence to extract copular relations from.
        Returns:
            A list of triples.
        """
        triples: list[Triple] = []

        for token in sent:
            # Check if the token is a copular verb
            if token.lemma_ not in ("be", "become", "remain"):
                continue
            # Check if the token is not a verb
            if token.pos_ != "AUX" and token.dep_ != "ROOT":
                continue

            subject = None
            obj = None

            # Find clauses associated with the copular verb
            children = (
                token.head.children if token.dep_ == "aux" else token.children
            )

            # First look for subject and object in these clauses
            for child in children:
                if child.dep_ == "nsubj":
                    subject = self.get_compound_noun(child)
                elif child.dep_ in ("attr", "acomp"):
                    obj = self.get_compound_noun(child)

            # Extract the subject and object from the root of the sentence (copular verb)
            if token.dep_ == "ROOT":
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = self.get_compound_noun(child)
                    elif child.dep_ in ("attr", "acomp"):
                        obj = self.get_compound_noun(child)

            if subject and obj:
                # Check if the subject or object is a non-lexical word
                if is_low_information_entity(subject) or is_low_information_entity(obj):
                    continue
                triples.append(Triple(subject, "is_a", obj, 0.1, "copular"))

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
                if is_low_information_entity(subject):
                    continue
                prep = token.text.replace(" ", "_").lower()

                # Find the object of the prepositional phrase
                for child in token.children:
                    if child.dep_ == "pobj":
                        obj = self.get_compound_noun(child)
                        if is_low_information_entity(obj):
                            continue
                        triples.append(Triple(subject, prep, obj, 0.1, "prep"))

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
        max_window = 5

        for i, tok in enumerate(tokens):
            if tok.pos_ != "VERB":
                continue

            left_noun = None
            for j in range(i - 1, max(i - max_window - 1, -1), -1):
                if tokens[j].pos_ in noun_tags:
                    left_noun = tokens[j]
                    break

            right_noun = None
            for j in range(i + 1, min(i + max_window + 1, len(tokens))):
                if tokens[j].pos_ in noun_tags:
                    right_noun = tokens[j]
                    break

            if left_noun is not None and right_noun is not None:
                sub = self.get_compound_noun(left_noun)
                pred = tok.lemma_.lower()
                obj = self.get_compound_noun(right_noun)
                if is_low_information_entity(sub) or is_low_information_entity(obj):
                    continue
                triples.append(Triple(sub, pred, obj, 0.05, "pos"))

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

    def remove_duplicates(self, triples: list[Triple]) -> list[Triple]:
        """
        Remove duplicates, keeping the first (highest-confidence) occurrence.
        Boost the confidence of the existing triple by 0.005 for each duplicate.
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


# ---------------------------------------------------------------------------
# Span-based relation extraction (GLiNER-relex)
# ---------------------------------------------------------------------------

# Default entity and relation labels for scientific/medical text
DEFAULT_SPAN_ENTITY_LABELS = [
    "disease",
    "condition",
    "treatment",
    "observation",
    "method",
    "measurement",
    "gene",
    "organization",
    "date",
    "location",
    "factor",
    "lifestyle",
    "behaviour",
    "symptom",
    "diagnosis",
]
DEFAULT_SPAN_RELATION_LABELS = [
    "causes",
    "treats",
    "associated_with",
    "part_of",
    "measured_by",
    "developed_by",
    "located_in",
    "occurs_in",
    "predicts",
    "prevents",
    "manages",
    "reduces",
    "increases",
    "decreases",
    "improves",
    "worsens",
]


class SpanRelationExtractor:
    """
    Extracts triples from text using GLiNER-relex, a zero-shot span-based
    NER + relation extraction model.
    """

    def __init__(
        self,
        model_name: str = "knowledgator/gliner-relex-large-v0.5",
        entity_labels: list[str] | None = None,
        relation_labels: list[str] | None = None,
        relation_threshold: float = 0.5,
    ):
        """
        Initialize the span relation extractor.

        Args:
            model_name: Hugging Face model name for GLiNER-relex.
            entity_labels: Entity types to extract. Defaults to scientific/medical.
            relation_labels: Relation types to extract. Defaults to scientific/medical.
            relation_threshold: Minimum confidence for relations (0–1).
        """

        self.model = GLiNER.from_pretrained(model_name)
        self.entity_labels = entity_labels or DEFAULT_SPAN_ENTITY_LABELS
        self.relation_labels = relation_labels or DEFAULT_SPAN_RELATION_LABELS
        self.relation_threshold = relation_threshold

    def _triples_from_relations(
        self,
        relations: list[dict],
        section: str = "",
    ) -> list[Triple]:
        """Convert raw GLiNER relation output into Triple objects."""
        triples: list[Triple] = []
        for rel in relations:
            if rel["score"] < self.relation_threshold:
                continue
            head = rel["head"]["text"]
            tail = rel["tail"]["text"]
            pred = rel["relation"]
            score = max(0.5, float(rel["score"]) / 2.0)
            sub = self.normalize_span_text(head)
            obj = self.normalize_span_text(tail)
            if is_low_information_entity(sub) or is_low_information_entity(obj):
                continue
            pred_norm = pred.replace(" ", "_").lower()
            triples.append(Triple(sub, pred_norm, obj, score, "span", section))
        return triples

    def extract_from_texts(
        self,
        texts: list[str],
        sections: list[str] | None = None,
    ) -> list[Triple]:
        """Extract triples from many texts in one GLiNER inference call."""
        valid_items = [
            (text, sections[idx] if sections else "")
            for idx, text in enumerate(texts)
            if text.strip()
        ]
        if not valid_items:
            return []

        entities, relations = self.model.inference(
            texts=[text for text, _ in valid_items],
            labels=self.entity_labels,
            relations=self.relation_labels,
            threshold=0.3,
            adjacency_threshold=0.5,
            relation_threshold=self.relation_threshold,
            return_relations=True,
            flat_ner=False,
        )

        triples: list[Triple] = []
        for (_, section), relation_group in zip(valid_items, relations):
            triples.extend(self._triples_from_relations(relation_group, section=section))
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
        subject_uri = self._make_uri(triple.sub)
        predicate_uri = self._make_uri(triple.pred)

        if triple.pred == "is_a":
            obj_node = self._make_uri(triple.obj)
        else:
            obj_node = Literal(triple.obj)

        self.graph.add((subject_uri, predicate_uri, obj_node))

    def add_triples(self, triples: list[Triple]):
        for triple in triples:
            self.add_triple(triple)

    def _make_uri(self, text: str) -> URIRef:
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

class OntologyFilter:
    """
    Loads domain term lists from resources/ontology/ and adjusts triple
    confidence when subjects or objects match known ontology terms.
    """

    def __init__(self, resources_dir: str | Path | None = None):
        if resources_dir is None:
            resources_dir = Path(__file__).resolve().parent.parent / "resources" / "ontology"
        self.resources_dir = Path(resources_dir)
        self.terms: set[str] = set()
        self._load_terms()

    def _load_terms(self):
        for terms_file in self.resources_dir.rglob("*.txt"):
            with open(terms_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    term = line.strip().lower()
                    if term:
                        self.terms.add(term)

    def _normalize(self, text: str) -> str:
        return text.replace("_", " ").lower()

    def matches(self, text: str) -> bool:
        return self._normalize(text) in self.terms

    def boost(
        self,
        triples: list[Triple],
        boost_amount: float = 0.02,
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
# Pipeline entry point
# ---------------------------------------------------------------------------

def generate_triples(
    sections: list[Section],
    model_name: str = "en_core_web_lg",
    base_namespace: str = "http://ukg-data.org/ukg#",
    output_path: str | None = None,
    output_format: str = "turtle",
    ontology_dir: str | Path | None = None,
    require_ontology_match: bool = False,
    use_span_extraction: bool = True,
    span_model: str = "knowledgator/gliner-relex-large-v0.5",
) -> list[Triple]:
    """
    End-to-end triple generation from (heading, text) tuples.

    Args:
        tuples: List of (heading, text) pairs (e.g. from
                extraction_module.post_process_json_data).
        model_name: spaCy model to use for NLP.
        base_namespace: RDF namespace URI.
        output_path: If provided, serialize results to this file.
        output_format: RDF serialization format ('turtle', 'xml', 'n3', 'nt').
        ontology_dir: Path to ontology resources directory.  ``None`` uses the
                      default ``resources/ontology/`` directory.
        require_ontology_match: When True, drop triples that don't match any
                                ontology term.
        use_span_extraction: When True, run GLiNER-relex for span-based extraction.
        span_model: Hugging Face model name for span extraction.

    Returns:
        List of extracted Triple objects.
    """
    extractor = TripleExtractor(model_name)

    all_triples: list[Triple] = []
    for section in sections:
        section_triples = extractor.extract_from_text(section.text, section=section.heading)
        all_triples.extend(section_triples)

    if use_span_extraction:
        span_extractor = SpanRelationExtractor(model_name=span_model)
        sentence_texts: list[str] = []
        sentence_sections: list[str] = []
        docs = extractor.nlp.pipe((section.text for section in sections), batch_size=1024)
        for section, doc in zip(sections, docs):
            for sent in doc.sents:
                sentence_texts.append(sent.text)
                sentence_sections.append(section.heading)
        all_triples.extend(
            span_extractor.extract_from_texts(sentence_texts, sections=sentence_sections)
        )

    all_triples = extractor.remove_duplicates(all_triples)

    # Use the default ontology directory if no ontology directory is provided.
    ont_dir = Path(ontology_dir) if ontology_dir else None
    if ont_dir is None:
        default_dir = Path(__file__).resolve().parent.parent / "resources" / "ontology"
        if default_dir.exists():
            ont_dir = default_dir

    # If the ontology directory exists, use the ontology filter to boost the confidence of the triples.
    if ont_dir is not None and ont_dir.exists():
        ont_filter = OntologyFilter(ont_dir)
        all_triples = ont_filter.boost(
            all_triples, require_match=require_ontology_match,
        )

    # If an output path is provided, serialize the triples to the output file.
    if output_path:
        serializer = RDFSerializer(base_namespace)
        serializer.add_triples(all_triples)
        serializer.save(output_path, fmt=output_format)

    return all_triples
