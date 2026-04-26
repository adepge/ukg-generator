"""
Simple spaCy dependency parsing demo
This script demonstrates how to use spaCy to parse a sentence and visualize the dependency tree using displaCy.
"""

import sys
import spacy
from spacy import displacy
from pathlib import Path

def main() -> None:
    sentence = "This study involved many participants"
    output_path = Path(__file__).with_name("dep_parsing_tree.svg")

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Missing spaCy model 'en_core_web_sm'. Install it with:\n python -m spacy download en_core_web_sm", file=sys.stderr)
        raise SystemExit(1)

    doc = nlp(sentence)

    print(f"Sentence: {sentence}\n")
    print(f"{'TOKEN':<12}{'DEP':<12}{'HEAD':<12}{'POS':<8}")
    print("-" * 44)

    for token in doc:
        print(f"{token.text:<12}{token.dep_:<12}{token.head.text:<12}{token.pos_:<8}")

    # Render the dependency tree using displaCy (see https://demos.explosion.ai/displacy)
    svg = displacy.render(doc, style="dep")
    output_path.write_text(svg, encoding="utf-8")
    print(f"\nDependency tree written to: {output_path}")


if __name__ == "__main__":
    main()