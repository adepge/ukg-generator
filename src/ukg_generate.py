"""
UKG Generator — CLI orchestrator.

Chains PDF extraction, post-processing, and triple generation into a single
pipeline invoked from the command line.

Usage:
    python -m src.ukg_generate <pdf_path> [options]
    python src/ukg_generate.py <pdf_path> [options]

Options
    -o, --output:           Path for the RDF output file (default: output/<name>/<name>.ttl).
    -f, --format:           RDF serialization format (default: turtle).
    -m, --model:            spaCy model to use (default: en_core_web_lg).
    -n, --namespace:        Base RDF namespace URI (default: http://example.org/ukg#).
    -l, --label-file:       Path to a JSON file containing entity and relation labels (default: resources/labels/biomedical_labels.json).
    -b, --blacklist:        Path to a CSV file containing blacklist terms or a directory containing blacklist CSV files (default: resources/blacklists).
    -g, --ontology:         Path to an ontology .txt file or directory containing ontology .txt files (default: resources/ontologies).
    -r, --require-ontology: Drop triples that don't match any ontology term (default: False).
    --write-json:           Write the JSON file extracted from the PDF to disk.
    --read-json:            Read the JSON file extracted from the PDF from disk instead of a PDF file.
    --write-tuples:         Write tuples.txt file from the extracted results and skip triple generation.
    --write-references:     Write references.txt file from the extracted results and skip triple generation.
    --no-span-extraction:   Disable GLiNER entity and relation extraction (use only natural language pattern matching).
    --disable-enrichment:   Disable enrichment of extracted DOI metadata using an external provider (default: False).
    --span-model:           (GLiNER) Hugging Face model for span extraction (default: gliner-relex-large-v0.5).

By default, the blacklists, ontology files, and label file are adapted to the biomedical domain.
Here is the default structure of the resources/ directory:
resources
├── blacklists                     <-- applied by default
│   ├── biomedical_blacklist.csv   
│   └── default_blacklist.csv      
├── labels
│   ├── biomedical_labels.json     <-- applied by default
│   └── generic_labels.json
└── ontologies                     <-- applied by default
    ├── cadro.txt                  
    ├── snowmed_ct.txt             
    └── umls_terms.txt               

Examples:
    python src/ukg_generate.py corpus/open_access/paper.pdf
    python src/ukg_generate.py corpus/open_access/paper.pdf --format xml
    python src/ukg_generate.py corpus/open_access/paper.pdf --require-ontology
"""

from __future__ import annotations

import argparse
import sys
import os
import json
from pathlib import Path

try:
    from src.extraction_module import extract_json_data, post_process_json_data
    from src.generate_triples import generate_triples
except ModuleNotFoundError:
    from extraction_module import extract_json_data, post_process_json_data
    from generate_triples import generate_triples
    from pipeline_io import (
        load_blacklist_files,
        build_blacklist_sets,
        load_ontology_terms,
    )


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
        "-l", "--label-file", type=str, default="resources/labels/biomedical_labels.json",
        help="Path to a JSON file containing entity and relation labels (default: resources/labels/biomedical_labels.json).",
    )
    parser.add_argument(
        "-b", "--blacklist", type=str, default="resources/blacklists",
        help="Path to a CSV file containing blacklist terms or a directory containing blacklist CSV files.",
    )
    parser.add_argument(
        "-g", "--ontology", type=str, default="resources/ontologies",
        help="Path to an ontology .txt file or directory containing ontology .txt files (default: resources/ontologies).",
    )
    parser.add_argument(
        "-r", "--require-ontology", action="store_true",
        help="Drop triples that don't match any ontology term.",
    )
    parser.add_argument(
        "--write-json", action="store_true",
        help="Write the JSON file extracted from the PDF to disk.",
    )
    parser.add_argument(
        "--read-json", type=str, default=None,
        help=f"Read the JSON file extracted from the PDF from disk instead of a PDF file (default: None).",
        required=False,
    )
    parser.add_argument(
        "--write-tuples", action="store_true",
        help="Write tuples.txt file from the PDF and skip triple generation.",
    )
    parser.add_argument(
        "--write-references", action="store_true",
        help="Write references.txt file from the PDF and skip triple generation.",
    )
    parser.add_argument(
        "--no-span-extraction", action="store_true",
        help="Disable span-based ML extraction (use only natural language pattern matching).",
    )
    parser.add_argument(
        "-d","--disable-enrichment", action="store_true",
        help="Disable enrichment of extracted DOI metadata using an external provider.",
    )
    parser.add_argument(
        "--span-model", type=str,
        default="knowledgator/gliner-relex-large-v0.5",
        help="Hugging Face model for span extraction (default: gliner-relex-large-v0.5).",
    )

    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf)

    # Determine (heading, text) tuples — either from a pre-existing file or
    # by running the full PDF extraction pipeline.
    extraction_result = None

    # Check if output directory exists
    target_output_dir = Path("output") / pdf_path.stem
    if not target_output_dir.exists():
        print(f"Output directory not found: {target_output_dir}. Creating it...")
        target_output_dir.mkdir(parents=True, exist_ok=True)
        # Get absolute path to output directory
    abs_output_dir = target_output_dir.absolute()
    json_path = None
    pdf_data = None

    if args.write_tuples or args.write_references:
        if not args.read_json:
            print(f"[1/2] Extracting JSON from {pdf_path} ...")
            json_path, pdf_data = extract_json_data(str(pdf_path), write_json=args.write_json, output_dir=abs_output_dir)
            if pdf_data is None:
                print("Error: PDF extraction failed.", file=sys.stderr)
                sys.exit(1)
        else:
            json_path = args.read_json
            if not Path(json_path).exists():
                print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
                sys.exit(1)

        # Generate the tuples file
        if args.write_tuples:
            print(f"[2/2] Writing (heading, text) tuples to {Path('output') / pdf_path.stem / f'{pdf_path.stem}.txt'} ...")
        if args.write_references:
            print(f"[2/2] Writing references to {Path('output') / pdf_path.stem / f'{pdf_path.stem}.references.txt'} ...")

        
        extraction_result = post_process_json_data(
            str(json_path) if json_path else None,
            data=pdf_data,
            write_tuples=args.write_tuples,
            write_references=args.write_references,
            enrich_metadata=(not args.disable_enrichment),
            enrich_references=(not args.disable_enrichment),
            output_basename=pdf_path.stem,
            output_dir=abs_output_dir,
        )
        if extraction_result is None:
            print("Error: Failed to generate tuples or references.", file=sys.stderr)
            sys.exit(1)

        if args.write_tuples:
            print(f"Tuples file saved to: {abs_output_dir / pdf_path.stem / f'{pdf_path.stem}.tuples.txt'}")
        if args.write_references:
            print(f"References file saved to: {abs_output_dir / pdf_path.stem / f'{pdf_path.stem}.references.txt'}")
        sys.exit(0)
    else:
        if not pdf_path.is_file():
            print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

        # Parse the blacklist and ontology files
        if args.blacklist:
            blacklist_sets = parse_blacklist_files(args.blacklist)
        else:
            blacklist_sets = ([], [], [], [])
        
        # Parse the ontology files into an in-memory term set. Keeping the term set
        # as the boundary value (rather than file paths) means downstream callers
        # — including out-of-process workers like Modal — don't need filesystem access.
        if args.ontology:
            ontology_paths = parse_ontology_files(args.ontology)
            ontology_terms = load_ontology_terms(tuple(ontology_paths))
        else:
            ontology_terms = frozenset()

        # Parse the label file
        if args.label_file:
            entity_labels, relation_labels = parse_label_file(args.label_file)
        else:
            entity_labels, relation_labels = None, None

        if not args.read_json:
            print(f"[1/3] Extracting JSON from {pdf_path} ...")
            json_path, pdf_data = extract_json_data(str(pdf_path), write_json=args.write_json, output_dir=abs_output_dir)
            if pdf_data is None:
                print("Error: PDF extraction failed.", file=sys.stderr)
                sys.exit(1)
        else:
            json_path = args.read_json
            if not Path(json_path).exists():
                print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
                sys.exit(1)

        print(f"[2/3] Post-processing JSON → (heading, text) tuples ...")
        extraction_result = post_process_json_data(
            str(json_path) if json_path else None,
            data=pdf_data,
            enrich_metadata=(not args.disable_enrichment),
            enrich_references=(not args.disable_enrichment),
            output_basename=pdf_path.stem,
            output_dir=abs_output_dir,
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
        ontology_terms=ontology_terms,
        blacklist_sets=blacklist_sets,
        entity_labels=entity_labels,
        relation_labels=relation_labels,
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

def parse_blacklist_files(filepath: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Parse a blacklist file into a a tuple of lists (subject_excl_str, object_excl_str, subject_excl_word, object_excl_word).
    The blacklist file is a CSV file with the following columns: term,category,rule,subject,object.
    The headers of the CSV file are expected to be: term,category,rule,subject,object:
        - term: The term to blacklist
        - category: The category of the term
        - rule: The rule to apply to the term (excl_only or excl)
        - subject: Whether the term is a subject (1) or object (0)
        - object: Whether the term is an object (1) or subject (0)

    Input:
        filepath: The path to the blacklist file or directory.
    Returns:
        A tuple of lists (subject_excl_str, object_excl_str, subject_excl_word, object_excl_word). 
        See build_blacklist_sets() in generate_triples.py for more details.
    """
    files = []

    # Check if the filepath is a directory.
    if os.path.isdir(filepath):
        for file in os.listdir(filepath):
            if file.endswith(".csv"):
                files.append(os.path.join(filepath, file))
    else:
        files.append(filepath)
    blacklists = load_blacklist_files(files)
    return build_blacklist_sets(blacklists)

def parse_ontology_files(filepath: str) -> list[str]:
    """
    Parse an ontology file or directory into a list of ontology term filepaths.
    The ontology file is a text file with the following format:
        - Each line is a single term.
        - Terms are case-insensitive and spaces are normalized to underscores.
    
    Input:
        filepath: The path to the ontology file or directory.
    Returns:
        A list of filepaths.
    """
    files = []
    if os.path.isdir(filepath):
        for file in os.listdir(filepath):
            if file.endswith(".txt"):
                files.append(os.path.join(filepath, file))
    else:
        files.append(filepath)
    return files

def parse_label_file(filepath: str) -> tuple[list[str], list[str]]:
    """
    Parse a label file into a tuple of lists (entity_labels, relation_labels).
    The label file is a JSON file with the following format:
        - entity_labels: A list of entity labels.
        - relation_labels: A list of relation labels.
    """
    with open(filepath, "r") as f:
        data = json.load(f)
        return data["entity_labels"], data["relation_labels"]

if __name__ == "__main__":
    main()