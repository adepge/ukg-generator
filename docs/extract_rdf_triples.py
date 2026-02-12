"""
RDF Triple Extraction from Text using Natural Language Processing

This script extracts subject-predicate-object triples from natural language text
and formats them as RDF (Resource Description Framework) triples.

Dependencies:
    pip install spacy rdflib
    python -m spacy download en_core_web_sm
"""

import re
from pathlib import Path
from typing import NamedTuple

# Check for spaCy availability
try:
    import spacy
    from spacy.tokens import Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not installed. Run: pip install spacy")
    print("Then download the model: python -m spacy download en_core_web_sm")

# Check for rdflib availability (optional, for RDF serialization)
try:
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False
    print("Warning: rdflib not installed. Run: pip install rdflib")
    print("RDF serialization will be disabled.")


class Triple(NamedTuple):
    """Represents an RDF triple (subject, predicate, object)."""
    subject: str
    predicate: str
    obj: str

    def __str__(self):
        return f"({self.subject}, {self.predicate}, {self.obj})"


class TripleExtractor:
    """
    Extracts RDF triples from natural language text using spaCy's
    dependency parsing and named entity recognition.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the triple extractor with a spaCy model.

        Args:
            model_name: Name of the spaCy model to use.
        """
        if not SPACY_AVAILABLE:
            raise RuntimeError("spaCy is required. Install with: pip install spacy")

        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Model '{model_name}' not found. Downloading...")
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)

    def extract_from_text(self, text: str) -> list[Triple]:
        """
        Extract triples from a text string.

        Args:
            text: Input text to process.

        Returns:
            List of extracted Triple objects.
        """
        doc = self.nlp(text)
        triples = []

        for sent in doc.sents:
            sent_triples = self._extract_from_sentence(sent)
            triples.extend(sent_triples)

        return triples

    def _extract_from_sentence(self, sent: Span) -> list[Triple]:
        """
        Extract triples from a single sentence using dependency parsing.

        This method uses multiple extraction patterns:
        1. Subject-Verb-Object (SVO) patterns
        2. Subject-Verb-Prepositional Object patterns
        3. Copular constructions (X is Y)
        4. Passive voice patterns
        """
        triples = []

        # Find the root verb of the sentence
        root = None
        for token in sent:
            if token.dep_ == "ROOT":
                root = token
                break

        if root is None:
            return triples

        # Extract SVO triples
        triples.extend(self._extract_svo(root))

        # Extract copular constructions (X is Y)
        triples.extend(self._extract_copular(sent))

        # Extract prepositional relations
        triples.extend(self._extract_prep_relations(sent))

        return triples

    def _extract_svo(self, verb) -> list[Triple]:
        """Extract Subject-Verb-Object triples from a verb."""
        triples = []

        # Find subject
        subject = None
        for child in verb.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                subject = self._get_compound_noun(child)
                break

        if subject is None:
            return triples

        # Find direct object
        for child in verb.children:
            if child.dep_ in ("dobj", "attr", "oprd"):
                obj = self._get_compound_noun(child)
                predicate = self._get_verb_phrase(verb)
                triples.append(Triple(subject, predicate, obj))

        # Find prepositional objects
        for child in verb.children:
            if child.dep_ == "prep":
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        obj = self._get_compound_noun(pobj)
                        predicate = f"{verb.lemma_}_{child.text}"
                        triples.append(Triple(subject, predicate, obj))

        return triples

    def _extract_copular(self, sent: Span) -> list[Triple]:
        """Extract copular constructions (e.g., 'X is Y', 'X are Y')."""
        triples = []

        for token in sent:
            if token.lemma_ in ("be", "become", "remain") and token.pos_ == "AUX":
                subject = None
                obj = None

                for child in token.head.children if token.dep_ == "aux" else token.children:
                    if child.dep_ == "nsubj":
                        subject = self._get_compound_noun(child)
                    elif child.dep_ in ("attr", "acomp"):
                        obj = self._get_compound_noun(child)

                # Check the token itself if it's the root
                if token.dep_ == "ROOT":
                    for child in token.children:
                        if child.dep_ == "nsubj":
                            subject = self._get_compound_noun(child)
                        elif child.dep_ in ("attr", "acomp"):
                            obj = self._get_compound_noun(child)

                if subject and obj:
                    triples.append(Triple(subject, "is_a", obj))

        return triples

    def _extract_prep_relations(self, sent: Span) -> list[Triple]:
        """Extract relations from prepositional phrases."""
        triples = []

        for token in sent:
            if token.dep_ == "prep" and token.head.pos_ in ("NOUN", "PROPN"):
                subject = self._get_compound_noun(token.head)
                prep = token.text

                for child in token.children:
                    if child.dep_ == "pobj":
                        obj = self._get_compound_noun(child)
                        predicate = prep.replace(" ", "_")
                        triples.append(Triple(subject, predicate, obj))

        return triples

    def _get_compound_noun(self, token) -> str:
        """
        Get the full compound noun phrase for a token.
        E.g., 'cognitive impairment' instead of just 'impairment'
        """
        compounds = []

        # Get left modifiers (compound nouns, adjectives)
        for child in token.lefts:
            if child.dep_ in ("compound", "amod", "nmod"):
                compounds.append(child.text)

        compounds.append(token.text)

        # Get right modifiers
        for child in token.rights:
            if child.dep_ in ("compound",):
                compounds.append(child.text)

        return "_".join(compounds).lower()

    def _get_verb_phrase(self, verb) -> str:
        """Get the verb phrase including auxiliaries and particles."""
        parts = []

        # Get auxiliaries
        for child in verb.children:
            if child.dep_ == "aux":
                parts.append(child.text)

        parts.append(verb.lemma_)

        # Get particles (e.g., 'give up')
        for child in verb.children:
            if child.dep_ == "prt":
                parts.append(child.text)

        return "_".join(parts).lower()

    def extract_entities_as_triples(self, text: str) -> list[Triple]:
        """
        Extract named entities and create type triples.
        E.g., (NHANES, is_a, Organization)
        """
        doc = self.nlp(text)
        triples = []

        for ent in doc.ents:
            entity_name = ent.text.replace(" ", "_").lower()
            entity_type = ent.label_
            triples.append(Triple(entity_name, "is_a", entity_type))

        return triples


class RDFSerializer:
    """Serializes triples to various RDF formats."""

    def __init__(self, base_namespace: str = "http://example.org/cognition#"):
        """
        Initialize the serializer.

        Args:
            base_namespace: The base URI namespace for the RDF graph.
        """
        if not RDFLIB_AVAILABLE:
            raise RuntimeError("rdflib is required. Install with: pip install rdflib")

        self.namespace = Namespace(base_namespace)
        self.graph = Graph()
        self.graph.bind("cog", self.namespace)

    def add_triple(self, triple: Triple):
        """Add a triple to the RDF graph."""
        # Create URIs for subject and predicate, literal for object
        subject_uri = self._make_uri(triple.subject)
        predicate_uri = self._make_uri(triple.predicate)

        # Decide if object should be URI or Literal
        if triple.predicate == "is_a":
            obj_node = self._make_uri(triple.obj)
        else:
            obj_node = Literal(triple.obj)

        self.graph.add((subject_uri, predicate_uri, obj_node))

    def add_triples(self, triples: list[Triple]):
        """Add multiple triples to the RDF graph."""
        for triple in triples:
            self.add_triple(triple)

    def _make_uri(self, text: str) -> URIRef:
        """Convert text to a valid URI."""
        # Clean the text for URI
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', text)
        return self.namespace[clean]

    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize the graph to a string.

        Args:
            format: Output format ('turtle', 'xml', 'n3', 'nt')

        Returns:
            Serialized RDF string.
        """
        return self.graph.serialize(format=format)

    def save(self, filepath: str, format: str = "turtle"):
        """Save the RDF graph to a file."""
        with open(filepath, "w") as f:
            f.write(self.serialize(format))


def parse_tuples_file(filepath: str) -> dict[str, str]:
    """
    Parse the tuples.txt file format (heading: text).

    Args:
        filepath: Path to the tuples file.

    Returns:
        Dictionary mapping headings to text content.
    """
    sections = {}

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Split on first colon
            if ":" in line:
                heading, text = line.split(":", 1)
                heading = heading.strip()
                text = text.strip()

                if heading in sections:
                    sections[heading] += " " + text
                else:
                    sections[heading] = text

    return sections


def main():
    """Main function demonstrating triple extraction."""

    # Sample text from the research paper
    sample_text = """
    Between 29% and 76% of patients with dementia may remain undiagnosed.
    Increasing age and the ε4 allele of the apolipoprotein E gene are the strongest predictors of impaired cognition.
    Blood pressure, diabetes, smoking, alcohol use, diet, and physical activity are risk factors.
    The goal of this study was to create and validate a score predicting the prevalence of impaired cognition.
    We used data from the Third National Health and Nutrition Examination Survey.
    The logistic and SVM models had similar discriminatory abilities in predicting poor cognition.
    """

    print("=" * 60)
    print("RDF Triple Extraction Demo")
    print("=" * 60)

    if not SPACY_AVAILABLE:
        print("\nPlease install spaCy to run this demo:")
        print("  pip install spacy")
        print("  python -m spacy download en_core_web_sm")
        return

    # Initialize the extractor
    extractor = TripleExtractor()

    # Extract triples from sample text
    print("\n1. Extracting triples from sample text...")
    print("-" * 40)

    triples = extractor.extract_from_text(sample_text)

    print(f"\nFound {len(triples)} triples:")
    for triple in triples:
        print(f"  {triple}")

    # Extract named entity triples
    print("\n2. Extracting named entity types...")
    print("-" * 40)

    entity_triples = extractor.extract_entities_as_triples(sample_text)

    print(f"\nFound {len(entity_triples)} entity type triples:")
    for triple in entity_triples:
        print(f"  {triple}")

    # Serialize to RDF if rdflib is available
    if RDFLIB_AVAILABLE:
        print("\n3. Serializing to RDF (Turtle format)...")
        print("-" * 40)

        serializer = RDFSerializer()
        serializer.add_triples(triples)
        serializer.add_triples(entity_triples)

        rdf_output = serializer.serialize("turtle")
        print(f"\n{rdf_output}")

        # Save to file
        output_path = Path(__file__).parent / "test" / "triples.ttl"
        serializer.save(str(output_path), "turtle")
        print(f"\nSaved RDF to: {output_path}")

    # Process the actual tuples file if it exists
    tuples_file = Path(__file__).parent / "test" / "tuples.txt"

    if tuples_file.exists():
        print("\n4. Processing tuples.txt file...")
        print("-" * 40)

        sections = parse_tuples_file(str(tuples_file))

        all_triples = []
        for heading, text in sections.items():
            print(f"\nSection: {heading}")
            section_triples = extractor.extract_from_text(text)
            all_triples.extend(section_triples)
            print(f"  Extracted {len(section_triples)} triples")

            # Show first 3 triples from each section
            for triple in section_triples[:3]:
                print(f"    - {triple}")
            if len(section_triples) > 3:
                print(f"    ... and {len(section_triples) - 3} more")

        print(f"\nTotal triples extracted: {len(all_triples)}")

        # Save all triples to RDF
        if RDFLIB_AVAILABLE:
            serializer = RDFSerializer(base_namespace="http://example.org/dementia-study#")
            serializer.add_triples(all_triples)

            output_path = Path(__file__).parent / "test" / "paper_triples.ttl"
            serializer.save(str(output_path), "turtle")
            print(f"Saved all triples to: {output_path}")


if __name__ == "__main__":
    main()
