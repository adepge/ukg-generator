"""
UKG Generator — CLI orchestrator.

Chains PDF extraction, post-processing, and triple generation into a single
pipeline invoked from the command line.

Usage:
    python -m src.ukg_generate <pdf_path> [options]
    python src/ukg_generate.py <pdf_path> [options]

Examples:
    python src/ukg_generate.py corpus/open_access/paper.pdf
    python src/ukg_generate.py corpus/open_access/paper.pdf --format xml
    python src/ukg_generate.py corpus/open_access/paper.pdf --require-ontology
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from src.extraction_module import extract_json_data, post_process_json_data
    from src.generate_triples import generate_triples
except ModuleNotFoundError:
    from extraction_module import extract_json_data, post_process_json_data
    from generate_triples import generate_triples


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Generate RDF triples from a PDF research paper.",
    )
    parser.add_argument(
        "pdf", type=str, help="Path to the input PDF file.",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Path for the RDF output file (default: output/<name>/<name>.ttl).",
    )
    parser.add_argument(
        "-f", "--format", type=str, default="turtle",
        choices=["turtle", "xml", "n3", "nt"],
        help="RDF serialization format (default: turtle).",
    )
    parser.add_argument(
        "-m", "--model", type=str, default="en_core_web_lg",
        help="spaCy model to use (default: en_core_web_lg).",
    )
    parser.add_argument(
        "-n", "--namespace", type=str, default="http://example.org/ukg#",
        help="Base RDF namespace URI.",
    )
    parser.add_argument(
        "--ontology-dir", type=str, default=None,
        help="Path to ontology resources directory.",
    )
    parser.add_argument(
        "--require-ontology", action="store_true",
        help="Drop triples that don't match any ontology term.",
    )
    parser.add_argument(
        "--tuples", type=str, default=None,
        help="Path to an existing tuples.txt file (skip PDF extraction).",
    )
    parser.add_argument(
        "--no-span-extraction", action="store_true",
        help="Disable span-based ML extraction (use only rule-based SVO).",
    )
    parser.add_argument(
        "--enrich-metadata", action="store_true",
        help="Optionally enrich extracted DOI metadata using an external provider.",
    )
    parser.add_argument(
        "--span-model", type=str,
        default="knowledgator/gliner-relex-large-v0.5",
        help="Hugging Face model for span extraction (default: gliner-relex-large).",
    )

    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf)

    # Determine (heading, text) tuples — either from a pre-existing file or
    # by running the full PDF extraction pipeline.
    extraction_result = None
    if args.tuples:
        tuples = _parse_tuples_file(args.tuples)
    else:
        if not pdf_path.is_file():
            print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

        print(f"[1/3] Extracting JSON from {pdf_path} ...")
        json_path = extract_json_data(str(pdf_path))
        if json_path is None:
            print("Error: PDF extraction failed.", file=sys.stderr)
            sys.exit(1)

        print(f"[2/3] Post-processing JSON → (heading, text) tuples ...")
        extraction_result = post_process_json_data(
            str(json_path),
            enrich_metadata=args.enrich_metadata,
        )
        sections = extraction_result.sections

    if not sections:
        print("No text sections found — nothing to extract.", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    ext_map = {"turtle": ".ttl", "xml": ".rdf", "n3": ".n3", "nt": ".nt"}
    if args.output:
        output_path = args.output
    else:
        stem = pdf_path.stem
        output_dir = Path("output") / stem
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{stem}{ext_map.get(args.format, '.ttl')}")

    print(f"[3/3] Generating triples → {output_path} ...")
    triples = generate_triples(
        sections=sections,
        model_name=args.model,
        base_namespace=args.namespace,
        output_path=output_path,
        output_format=args.format,
        ontology_dir=args.ontology_dir,
        require_ontology_match=args.require_ontology,
        use_span_extraction=not args.no_span_extraction,
        span_model=args.span_model,
    )

    print(f"\nDone. Extracted {len(triples)} triples.")
    print(f"Output saved to: {output_path}")
    if extraction_result is not None:
        print(
            f"Sections: {len(extraction_result.sections)} | "
            f"References: {len(extraction_result.references)}"
        )
        if extraction_result.metadata.title:
            print(f"Title: {extraction_result.metadata.title}")
        if extraction_result.metadata.doi:
            print(f"DOI: {extraction_result.metadata.doi}")

    # Save triples to a text file
    text_output_path = output_path.replace(".ttl", ".txt")
    with open(text_output_path, "w+", encoding="utf-8") as f:
        for t in triples:
            f.write(f"({t.sub}, {t.pred}, {t.obj}, {t.conf})\n")  
    print(f"Text output saved to: {text_output_path}")

    for t in triples[:10]:
        print(f"  {t}")
    if len(triples) > 10:
        print(f"  ... and {len(triples) - 10} more")


def _parse_tuples_file(filepath: str) -> list[tuple[str, str]]:
    """Parse a heading: text file into a list of (heading, text) pairs."""
    results: list[tuple[str, str]] = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            heading, text = line.split(":", 1)
            results.append((heading.strip(), text.strip()))
    return results


if __name__ == "__main__":
    main()
