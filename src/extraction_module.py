"""
Extraction Module

This module is used to extract the data from a PDF file.
It supports the extraction of unstructured text from a PDF file (expected to be a research article).
It will attempt to extract the following:
- Document metadata
- Sections
- References/Citations

The PDF is first converted to a JSON file using pymupdf4llm.
The JSON file is then post-processed to extract the data.
"""

import json
import os
import re
import threading
import pymupdf.layout
import pymupdf4llm
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol
from lingua import Language, LanguageDetectorBuilder
from pipeline_types import ( 
    DocumentMetadata,
    ExtractionResult,
    LearnedAcronyms,
    Reference,
    Section,
)

# Regular expressions for extracting the DOI, URL, and PMID from the text.
DOI_REGEX = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)
PMID_REGEX = re.compile(r"\bPMID:\s*(\d+)\b", re.IGNORECASE)
CITATION_PATTERN = re.compile(
    r"\[(?:\s*\d{1,3}\s*(?:[-–]\s*\d{1,3}\s*)?)(?:\s*,\s*\d{1,3}\s*(?:[-–]\s*\d{1,3}\s*)?)*\s*\]"
)
FALLBACK_CITATION_PATTERN = re.compile(
    r"\((?:\s*\d{1,3}\s*(?:[-–]\s*\d{1,3}\s*)?)(?:\s*,\s*\d{1,3}\s*(?:[-–]\s*\d{1,3}\s*)?)*\s*\)"
)
AUTHOR_YEAR_PATTERN = re.compile(r'\((?=[^)]*[A-Z])(?=[^)]*,)(?=[^)]*(?:19|20)[0-9][0-9])[A-Za-z0-9,&;.\’\'\s-]*\)')

# Regular expression for extracting acronyms.
ACRONYM_REGEX = re.compile(
    r"(?P<full_form>[A-Za-z][A-Za-z\s\u2019'-]{2,}?)\s*\((?P<acronym>[A-Za-z][A-Za-z0-9-]{1,})\)"
)

# Stopwords for acronym matching.
STOPWORDS = {"of", "on", "and", "the", "in", "for", "to", "a", "an"}

# Build English-only language detector
detector = LanguageDetectorBuilder.from_languages(Language.ENGLISH).build()

# Heading aliases for the reference list.
REFERENCE_HEADINGS = {
    "references",
    "reference list",
    "bibliography",
    "works cited",
    "citations",
    "literature cited",
}

HEADING_ALIASES = {
    "reference list": "References",
    "bibliography": "References",
    "works cited": "References",
    "citations": "References",
    "literature cited": "References",
}

# Noise prefixes to ignore in the text.
IGNORE_PREFIXES = (
    "open access",
    "citation:",
    "editor:",
    "received:",
    "accepted:",
    "published:",
    "copyright:",
    "data availability statement:",
)

# Top-level headings to extract.
TOP_LEVEL_HEADINGS = {
    "abstract",
    "introduction",
    "methods",
    "materials and methods",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "supporting information",
    "author contributions",
    "references",
    "acknowledgements",
    "acknowledgments",
    "summary",
    "article highlights",
}

# Subheadings to extract from the abstract.
ABSTRACT_SUBHEADINGS = {
    "abstract",
    "summary",
    "introduction",
    "background",
    "methods",
    "results",
    "conclusion",
}

# Headings to ignore as filler text.
FILLER_HEADINGS = {
    "open access",
    "research article",
}

# Special characters to filter out of the text.
SPECIAL_CHARS = {
    "�",
    "\u00a0",
}

@dataclass
class LayoutStats:
    """Stores the document font size statistics."""
    body_font_size: float
    min_body_font_size: float


@dataclass
class HeadingCandidate:
    """Stores the heading candidate."""
    page_number: int
    box_index: int
    text: str
    font_size: float
    level: int = 1
    is_title: bool = False

    @property
    def key(self) -> tuple[int, int]:
        return (self.page_number, self.box_index)


class MetadataEnricher(Protocol):
    # Template for a metadata enricher
    def enrich(self, doi: str) -> dict[str, Any]:
        """
        Enriches the metadata for a DOI.
        """

class CrossrefEnricher:
    """
    Best-effort DOI metadata enrichment using the Crossref API.

    Responses are cached per-process so that repeated calls for the same DOI
    do not make additional API calls.
    """

    # Caches the metadata for the DOIs (if the DOI already exists in the cache, it returns the cached metadata)
    cache: dict[str, dict[str, Any]] = {}
    cache_lock = threading.Lock()

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def enrich(self, doi: str) -> dict[str, Any]:
        if not doi:
            return {}

        with self.cache_lock:
            cached = self.cache.get(doi)
        if cached is not None:
            return cached

        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ukg-generator/1.0 (mailto:no-reply@example.org)"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        message = payload.get("message", {})
        authors = []

        # Extract author given and family names from the Crossref API response
        for author in message.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = " ".join(part for part in [given, family] if part).strip()
            if full_name:
                authors.append(full_name)

        # Extract the citations count from the Crossref API response
        citations_count = message.get("is-referenced-by-count", 0)
        title = " ".join(message.get("title", [])).strip()
        journal = " ".join(message.get("container-title", [])).strip() or None
        published_date = extract_date(message.get("published-print")) or extract_date(message.get("published-online"))
        result = {
            "title": title or None,
            "authors": authors,
            "journal": journal,
            "published_date": published_date,
            "citations_count": citations_count,
            "references": message.get("reference", []),
        }
        with self.cache_lock:
            self.cache[doi] = result
        return result

    @classmethod
    def clear_cache(cls) -> None:
        with cls.cache_lock:
            cls.cache.clear()

def extract_json_data(file_path: str, write_json: bool = True, output_dir: Path | None = None):
    """
    Extract PDF layout data.

    Args:
        file_path: The path to the PDF file.
        write_json: Whether to write the JSON file to disk.

    Returns a (output_path, data) tuple where:
        data: is the parsed JSON dict.  
        output_path: is the location the JSON file was written to if write_json is True.

    Returns:
        (None, None) if the PDF cannot be opened.
    """

    file_name = Path(file_path).stem
    output_dir = output_dir or Path(__file__).parent / "output" / file_name
    output_path = None

    try:
        doc = pymupdf.open(file_path)
    except Exception as exc:
        print(f"Error: {exc}")
        return None, None

    extracted_json = pymupdf4llm.to_json(
        doc,
        write_images=False,
        show_progress=False,
        use_ocr=False,
    )

    # Load the extract JSON data into a dictionary 
    data = json.loads(extracted_json) if isinstance(extracted_json, str) else extracted_json

    # Write the extracted JSON data to a file if write_json is True
    if write_json:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{file_name}.json"
        with open(output_path, "w", encoding="utf-8") as handle:
            if isinstance(extracted_json, str):
                handle.write(extracted_json)
            else:
                json.dump(data, handle)

    return output_path, data


def post_process_json_data(
    json_path: str | None = None,
    write_tuples: bool = False,
    write_references: bool = False,
    enrich_metadata: bool = False,
    enrich_references: bool = False,
    metadata_enricher: MetadataEnricher | None = None,
    data: dict[str, Any] | None = None,
    output_basename: str | None = None,
    output_dir: str | Path | None = None,
) -> ExtractionResult:
    """
    Transforms extracted PDF data into structured metadata, sections, and references.
    Expects either the json_path or data (dict) to be provided.

    Args:
        json_path: The path to the JSON file.
        write_tuples: Whether to write the tuples file (heading, text) to disk.
        write_references: Whether to write the references file (reference number, main URL, reference text) to disk.
        enrich_metadata: Whether to enrich the metadata using the DOI if available.
        enrich_references: Whether to enrich the references using the DOI if available.
        metadata_enricher: The metadata enricher to use (defaults to the Crossref API enricher).
        data: The data from the JSON file.
        output_basename: The basename of the output file (only required for writing the tuples and references files).
        output_dir: The directory to write the output files to (only required for writing the tuples and references files).
    Returns:
        An ExtractionResult object.
    """
    if data is None:
        if not json_path:
            raise ValueError("post_process_json_data requires either json_path or data")
        with open(json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

    if json_path:
        file_name = json_path.split("/")[-1].split(".")[0]
        folder_path = "/".join(json_path.split("/")[:-1]) or "."
    else:
        file_name = output_basename or "document"
        folder_path = str(output_dir) if output_dir else "."
    text_file = folder_path + "/" + file_name + ".tuples.txt"
    reference_file = folder_path + "/" + file_name + ".references.txt"

    layout_stats = compute_layout_stats(data)
    heading_candidates = detect_heading_candidates(data, layout_stats)
    metadata = extract_document_metadata(
        data,
        heading_candidates,
        enrich_metadata=enrich_metadata,
        metadata_enricher=metadata_enricher,
    )

    # Filters out the title candidates and sets the is_title flag to True for the title candidate
    filter_title_candidates(heading_candidates, metadata)

    sections = build_sections(data, heading_candidates, layout_stats)

    # Performs the citation litmus test to determine the citation pattern used in the document
    citation_pattern = citation_litmus(sections)
    if citation_pattern:
        # Associate citations with each section.
        sections = associate_citations(sections, citation_pattern)
        reference_boxes = extract_reference_block(data, heading_candidates)
        references = []

        # If the DOI is available and enrich_references is True, enrich the references using the DOI
        if metadata.doi and enrich_references:
            references = enrich_document_references(metadata.doi, metadata_enricher)
        else:
            # Otherwise, parse the references from the reference boxes from the document manually
            references = parse_references(reference_boxes)
            if any(len(reference.text) > 250 for reference in references):
                # If any reference text is longer than 250 characters, clear the references as the returned data is likely to be malformed
                references = []
        
        # Count the total "is-referenced-by-count" of the citations in the sections
        count_reference_citations(sections, references, metadata_enricher)
    else:
        # If no citation pattern is found, do not extract any references
        references = []
    result = ExtractionResult(metadata=metadata, sections=sections, references=references)

    if write_tuples:
        with open(text_file, "w", encoding="utf-8") as handle:
            for heading, text, citations in result.to_tuples():
                if citations:
                    text = f"{text} {citations}"
                else:
                    text = f"{text}"
                handle.write(f"{heading}: {text}\n")

    if write_references:
        with open(reference_file, "w", encoding="utf-8") as handle:
            for reference_number, main_url, reference_text in [ref.as_legacy_tuple() for ref in references]:
                handle.write(f"{reference_number} | {main_url} | {reference_text}\n")

    return result


# =======================================================
# Document Metadata Extraction
# =======================================================
def extract_document_metadata(
    data: dict[str, Any],
    heading_candidates: dict[tuple[int, int], HeadingCandidate],
    enrich_metadata: bool = False,
    metadata_enricher: MetadataEnricher | None = None,
) -> DocumentMetadata:
    """
    Extracts the document metadata from the data.
    Looks at the extracted metadata from the JSON file and the text of the first 2 pages.

    Input:
        data: The data from the JSON file.
        heading_candidates: The heading candidates from the data.
        enrich_metadata: Whether to enrich the metadata using the DOI if available.
        metadata_enricher: The metadata enricher to use.
    Returns:
        A DocumentMetadata object.
    """
    raw_metadata = data.get("metadata", {})
    first_pages_text = collect_text_snippets(data, limit=2)

    title = strip_special_chars(raw_metadata.get("title", ""))
    if not title:
        title = next((candidate.text for candidate in heading_candidates.values() if candidate.is_title), "")

    authors = split_authors(raw_metadata.get("author", ""))
    if not authors:
        authors = extract_authors_from_front_matter(first_pages_text, title)

    doi = find_primary_doi(data, first_pages_text)
    metadata = DocumentMetadata(
        title=title,
        authors=authors,
        doi=doi,
        journal=extract_journal(first_pages_text),
        article_type=extract_article_type(data, first_pages_text),
        received_date=extract_labelled_value(first_pages_text, "Received"),
        accepted_date=extract_labelled_value(first_pages_text, "Accepted"),
        published_date=extract_labelled_value(first_pages_text, "Published"),
        raw=raw_metadata,
    )

    if enrich_metadata and metadata.doi:
        metadata = enrich_metadata_from_doi(metadata, metadata_enricher)

    return metadata


def enrich_metadata_from_doi(
    metadata: DocumentMetadata,
    metadata_enricher: MetadataEnricher | None = None,
) -> DocumentMetadata:
    """
    Enriches the metadata from the DOI using the metadata enricher.
    Defaults to using the Crossref API enricher when no enricher is provided.

    Input:
        metadata: The metadata from the document.
        metadata_enricher: The metadata enricher to use.
    Returns:
        The enriched metadata.
    """
    enricher = metadata_enricher or CrossrefEnricher()
    try:
        enriched = enricher.enrich(metadata.doi or "")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return metadata
    except Exception:
        return metadata

    # If any of the metadata is not found, use the enriched metadata
    # Override the metadata with the enriched metadata (this keeps the display behaviour more consistent on the frontend)
    if enriched.get("title"):
        metadata.title = enriched["title"]
    if enriched.get("authors"):
        metadata.authors = enriched["authors"]
    if enriched.get("journal"):
        metadata.journal = enriched["journal"]
    if enriched.get("published_date"):
        metadata.published_date = enriched["published_date"]
    if enriched.get("citations_count"):
        metadata.citations_count = enriched["citations_count"]
    return metadata

def collect_text_snippets(data: dict[str, Any], limit: int = 2) -> str:
    """
    Collects the text snippets from the first N pages of the document.
    Used to extract the metadata from the document.
    """
    snippets = []
    for page in data.get("pages", [])[:limit]:
        for box in page.get("boxes", []):
            box_text = extract_box_text(box)
            if box_text:
                snippets.append(box_text)
    return "\n".join(snippets)


def extract_labelled_value(text: str, label: str) -> str | None:
    """
    Extracts the labelled value from the text using a regular expression.

    Input:
        text: The text of the document.
        label: The label to extract.
    Returns:
        The labelled value. If no labelled value is found, returns None.
    """
    pattern = re.compile(rf"{re.escape(label)}:\s*([^\n]+)", re.IGNORECASE)
    match = pattern.search(text)
    return strip_special_chars(match.group(1)) if match else None


def extract_journal(text: str) -> str | None:
    """
    Extracts the journal from the text.
    Input:
        text: The text of the document.
    Returns:
        The journal. If no journal is found, returns None.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) > 3 and stripped.isupper() and "DOI" not in stripped:
            if stripped not in {"OPEN ACCESS", "RESEARCH ARTICLE"}:
                return stripped.title()
        if re.fullmatch(r"[A-Z][A-Z\s&.]+", stripped) and "https://" not in stripped:
            return stripped.title()
    return None


def extract_article_type(data: dict[str, Any], text: str) -> str | None:
    """
    Extracts the article type from the data and text.

    Input:
        data: The data from the JSON file.
        text: The text of the document.
    Returns:
        The article type. If no article type is found, returns None.
    """
    for page in data.get("pages", [])[:1]:
        for box in page.get("boxes", []):
            box_text = extract_box_text(box)
            if not box_text:
                continue
            if box_text.isupper() and (
                "article" in box_text.lower()
                or "review" in box_text.lower()
                or "report" in box_text.lower()
            ):
                return box_text.title()

    for line in text.splitlines()[:10]:
        stripped = line.strip()
        if not stripped.isupper():
            continue
        if "article" in stripped.lower() or "review" in stripped.lower() or "report" in stripped.lower():
            return stripped.title()
    return None

def split_authors(author_text: str) -> list[str]:
    """
    Splits the authors from the author text.
    Removes the ID tag from the authors.

    Input:
        author_text: The text containing the authors.
    Returns:
        A list of authors. If no authors are found, returns an empty list.
    """
    cleaned = strip_special_chars(author_text)
    if not cleaned:
        return []
    authors = []
    for chunk in cleaned.split(","):
        # Removes multiple spaces and also removes the ID tag
        candidate = re.sub(r"\s+", " ", chunk).strip()
        candidate = re.sub(r"\bID\b", "", candidate).strip(" *")
        if candidate:
            authors.append(candidate)
    return authors


def extract_authors_from_front_matter(front_matter: str, title: str) -> list[str]:
    """
    Extracts the authors from the front matter of the document.
    The front matter would typically be the first 2 pages of the document.
    This would assume that the authors are typically listed after the title.

    Input:
        front_matter: The front matter of the document.
        title: The title of the document.
    Returns:
        A list of authors. If no authors are found, returns an empty list.
    """
    lines = [line.strip() for line in front_matter.splitlines() if line.strip()]
    if not lines:
        return []

    # Finds the index of the title in the front matter
    title_index = -1
    title_norm = normalize_text(title)
    for index, line in enumerate(lines):
        if title_norm and normalize_text(line) in title_norm:
            title_index = index
            break

    if title_index == -1:
        return []

    author_lines = []
    for line in lines[title_index + 1 :]:
        lower = line.lower()
        if lower.startswith("abstract") or re.match(r"^\d+\s", line):
            break
        author_lines.append(line)
    return split_authors(" ".join(author_lines))


# =======================================================
# Section Extraction
# =======================================================

def compute_layout_stats(data: dict[str, Any]) -> LayoutStats:
    """
    Computes the layout statistics from the data.
    This is used to determine the minimum body font size and the body font size (most common font size).

    Input:
        data: The data from the JSON file.
    Returns:
        A LayoutStats object.
    """
    font_sizes = Counter()

    for _, _, box in iterate_boxes(data):
        boxclass = box.get("boxclass", "")
        if boxclass not in {"text", "list-item"}:
            continue
        for span in iterate_spans(box):
            size = span.get("size", 0.0)
            if size:
                font_sizes[round(float(size), 1)] += 1

    body_font_size = font_sizes.most_common(1)[0][0] if font_sizes else 10.0
    min_body_font_size = max(body_font_size - 1.0, body_font_size * 0.9)
    return LayoutStats(body_font_size=body_font_size, min_body_font_size=min_body_font_size)


def build_sections(
    data: dict[str, Any],
    heading_candidates: dict[tuple[int, int], HeadingCandidate],
    layout_stats: LayoutStats,
) -> list[Section]:
    """
    Builds the sections of the document from the data.
    This is used to group the text into sections based on the headings.

    Input:
        data: The data from the JSON file.
        heading_candidates: The heading candidates from the data.
        layout_stats: The layout statistics from the data.
    Returns:
        A list of sections.
    """

    # Initializes the list of sections and the current section
    sections: list[Section] = []
    current_section: Section | None = None
    section_stack: list[Section] = []

    for page_number, box_index, box in iterate_boxes(data):
        # Gets the heading candidate for the current box.
        candidate = heading_candidates.get((page_number, box_index))
        if candidate:
            # If the candidate is the title of the document, skip it
            if candidate.is_title:
                continue
            effective_level = resolve_section_level(candidate, section_stack)
            if effective_level is None:
                continue

            # Removes the sections from the stack that are at a higher level than the current section
            while section_stack and section_stack[-1].level >= effective_level:
                section_stack.pop()

            # If the section text is under a subheading, add the parent heading to the section path
            parent_heading = section_stack[-1].path if section_stack else None
            section_path = (
                f"{parent_heading} > {candidate.text}" if parent_heading else candidate.text
            )
            current_section = Section(
                heading=candidate.text,
                text="",
                level=effective_level,
                parent_heading=section_stack[-1].heading if section_stack else None,
                path=section_path,
                page_numbers=[page_number],
            )
            sections.append(current_section)
            section_stack.append(current_section)
            continue

        if current_section is None:
            continue

        # If the section is the reference list, skip it.
        if get_preferred_heading(current_section.heading) == "references":
            continue

        # If the box is not a text box, skip it.
        boxclass = box.get("boxclass", "")
        if boxclass != "text":
            if boxclass == "links":
                box_text = extract_box_text(box, min_size=layout_stats.min_body_font_size)
                # If the text matches the pattern of a citation, add it to the text
                if not any(pattern.search(box_text) for pattern in [CITATION_PATTERN, AUTHOR_YEAR_PATTERN, FALLBACK_CITATION_PATTERN]):
                    continue
            else:
                continue

        # Extracts the text from the box and filters out unwanted text.
        box_text = extract_box_text(box, min_size=layout_stats.min_body_font_size)
        if not box_text or is_unwanted_text(box_text):
            continue

        # Merges the text from the box into the current section
        current_section.text = merge_text_chunks(current_section.text, box_text)
        if page_number not in current_section.page_numbers:
            current_section.page_numbers.append(page_number)
    
    # Finds all acronyms in the document
    all_acronyms = LearnedAcronyms()
    for section in sections:
        all_acronyms = find_all_acronyms(section.text, all_acronyms)

    # Remove sections with no text or non-English text
    cleaned_sections = []
    for section in sections:
        if not section.text.strip() or len(section.text) < 20 or detector.detect_language_of(section.text) is None:
            continue

        # Replace the acronyms in the text with the full form
        section.text = all_acronyms.replace_acronyms(section.text)
        cleaned_sections.append(section)
    return cleaned_sections


def filter_title_candidates(
    heading_candidates: dict[tuple[int, int], HeadingCandidate],
    metadata: DocumentMetadata | None,
) -> None:
    """
    Updates the is_title flag on existing heading candidates once
    the document title has been normalized.

    When the metadata title matches a candidate we flag it as the authoritative
    title and strip the is_title flag from any font-size fallback candidate that the
    initial detection pass may have flagged.

    Input:
        heading_candidates: The heading candidates from the data.
        metadata: The metadata from the document if available.
    """
    if not metadata or not metadata.title:
        return
    normalized_title = normalize_text(metadata.title)
    if not normalized_title:
        return

    # Finds all heading candidates that match the normalized title
    matches = [
        candidate
        for candidate in heading_candidates.values()
        if normalize_text(candidate.text) == normalized_title
    ]
    if not matches:
        return

    # Sets the is_title flag to False for all heading candidates
    for candidate in heading_candidates.values():
        candidate.is_title = False

    # Sets the is_title flag to True for the heading candidates that match the normalized title
    for candidate in matches:
        candidate.is_title = True
        candidate.level = 0


def detect_heading_candidates(
    data: dict[str, Any],
    layout_stats: LayoutStats,
    metadata: DocumentMetadata | None = None,
) -> dict[tuple[int, int], HeadingCandidate]:
    """
    Detects the heading candidates from the data.

    Input:
        data: The data from the JSON file.
        layout_stats: The layout statistics from the data.
        metadata: The metadata from the document if available.
    Returns:
        A dictionary of heading candidates.
    """

    # Initializes the list of heading candidates
    candidates: list[HeadingCandidate] = []

    # Normalizes the title of the document if available
    normalized_title = normalize_text(metadata.title) if metadata and metadata.title else ""

    for page_number, box_index, box in iterate_boxes(data):
        # If the box is not a section header, skip it
        if box.get("boxclass") != "section-header":
            continue

        # Extracts the heading and filters out filler headings
        text = extract_box_text(box)
        if not text:
            continue
        if is_filler_heading(text):
            continue

        # If the heading size is smaller than the minimum body font size, skip it
        spans = list(iterate_spans(box))
        font_size = max((float(span.get("size", 0.0)) for span in spans), default=0.0)
        if font_size and font_size < layout_stats.min_body_font_size:
            continue

        candidate = HeadingCandidate(
            page_number=page_number,
            box_index=box_index,
            text=get_preferred_heading(text),
            font_size=font_size or layout_stats.body_font_size,
        )

        # If the heading is the title of the document, set the is_title flag to True
        if normalized_title and normalize_text(candidate.text) == normalized_title:
            candidate.is_title = True
        candidates.append(candidate)

    # Return an empty dictionary if no candidates are found
    if not candidates:
        return {}

    # Search for the title candidate in the first page if no title candidate is found
    if not any(candidate.is_title for candidate in candidates):
        title_candidate = max(
            candidates,
            key=lambda candidate: (
                candidate.page_number == 1,
                candidate.font_size,
                len(candidate.text.split()),
            ),
        )
        if title_candidate.page_number == 1 and title_candidate.font_size >= layout_stats.body_font_size:
            title_candidate.is_title = True

    # Filters out the title candidates and sorts the remaining candidates by font size
    non_title_sizes = sorted(
        {candidate.font_size for candidate in candidates if not candidate.is_title},
        reverse=True,
    )
    if not non_title_sizes:
        non_title_sizes = sorted({candidate.font_size for candidate in candidates}, reverse=True)

    # Sets the level of the candidates based on the font size (essentially, groups headings by font size)
    for candidate in candidates:
        if candidate.is_title:
            candidate.level = 0
            continue
        closest_size = min(non_title_sizes, key=lambda value: abs(value - candidate.font_size))
        candidate.level = non_title_sizes.index(closest_size) + 1

    return {candidate.key: candidate for candidate in candidates}


def resolve_section_level(
    candidate: HeadingCandidate,
    section_stack: list[Section],
) -> int | None:
    """
    Resolve the level of a section based on the candidate heading and the section stack.
    This allows for the extraction of subheadings from the document.
    """
    heading_key = get_preferred_heading(candidate.text)

    # If the candidate heading is a subheading of the abstract, return 2
    if any(section.heading == "Abstract" for section in section_stack) and heading_key in ABSTRACT_SUBHEADINGS:
        return 2
    # If the candidate heading is a top-level heading, return 1
    if heading_key in TOP_LEVEL_HEADINGS:
        return 1
    # If the candidate heading is not a top-level heading, return the maximum of 1 and the candidate level
    if not section_stack:
        return max(1, candidate.level)
    if any(section.heading == "Abstract" for section in section_stack):
        return 2
    return max(2, candidate.level)

def extract_reference_block(
    data: dict[str, Any],
    heading_candidates: dict[tuple[int, int], HeadingCandidate],
    ) -> list[dict[str, Any]]:
    """
    Extracts the reference boxes from the data.
    It uses the heading candidates to find the reference start and end boxes.

    Input:
        data: The data from the JSON file.
        heading_candidates: The heading candidates from the data.
    Returns:
        A list of boxes that contain the reference entries.
    """

    # Sorts the heading candidates by page number and box index
    ordered_candidates = sorted(
        heading_candidates.values(),
        key=lambda candidate: (candidate.page_number, candidate.box_index),
    )

    # Finds the reference start box
    reference_start: tuple[int, int] | None = None
    for candidate in ordered_candidates:
        if get_preferred_heading(candidate.text) == "references":
            reference_start = (candidate.page_number, candidate.box_index)
            break

    # Extracts the reference boxes from the data
    reference_boxes: list[dict[str, Any]] = []
    if reference_start is not None:
        start_page, start_box_index = reference_start
        for page_number, box_index, box in iterate_boxes(data):
            if page_number < start_page:
                continue
            if page_number == start_page and box_index <= start_box_index:
                continue
            if box.get("boxclass") in {"list-item", "table", "text"}:
                reference_boxes.append(box)
        return reference_boxes

    # Fallback to extracting any list-item or table boxes in the last 3 pages if the reference start box is not found
    pages = data.get("pages", [])
    for page in pages[-3:]:
        candidate_boxes = [box for box in page.get("boxes", []) if box.get("boxclass") in {"list-item", "table"}]
        if candidate_boxes:
            reference_boxes.extend(candidate_boxes)
    return reference_boxes


# =======================================================
# Reference Extraction Helper Functions
# =======================================================
def parse_references(reference_boxes: list[dict[str, Any]]) -> list[Reference]:
    """
    Parses the reference boxes into Reference objects.
    
    Input:
        reference_boxes: A list of boxes that contain the reference entries.
    Returns:
        A list of Reference objects.
    """
    references: list[Reference] = []
    current_index: int | None = None
    current_text = ""

    # Flushes the current reference and starts a new one
    def flush_reference() -> None:
        nonlocal current_index, current_text
        cleaned = strip_special_chars(current_text)
        if not cleaned:
            current_index = None
            current_text = ""
            return
        references.append(build_reference(current_index, cleaned))
        current_index = None
        current_text = ""

    for box in reference_boxes:
        for entry_text in extract_reference_entries(box):
            # If the reference text is empty, skip the entry
            if not entry_text:
                continue

            # Parses the reference number and content from the reference text
            # If the reference number is found, flush the current reference and start a new one
            number, content = split_reference_number(entry_text)
            if number is not None:
                flush_reference()
                current_index = number
                current_text = content or ""
                continue

            # If the reference is a list-item and the current text is not empty, flush the current reference and start a new one
            if box.get("boxclass") == "list-item" and current_text:
                flush_reference()
                current_index = None
                current_text = entry_text
                continue

            current_text = merge_text_chunks(current_text, entry_text)

    flush_reference()
    return references


def extract_reference_entries(box: dict[str, Any]) -> list[str]:
    """
    Extract reference entries whether it was parsed as a table or list-item
    These are the entries usually found in the bibliography or reference list at the end of the document.
    """
    boxclass = box.get("boxclass", "")
    if boxclass in {"list-item", "text"}:
        text = extract_box_text(box)
        return [text] if text else []

    # If the box is a table, extract the reference entries from the cells in the table
    if boxclass == "table":
        entries = []
        for row in box.get("table", {}).get("extract", []):
            row_text = strip_special_chars(" ".join(cell for cell in row if cell))
            if row_text:
                entries.append(row_text)
        return entries

    return []


def citation_litmus(sections: list[Section]) -> re.Pattern | None:
    """
    Checks all sections for citation patterns.
    If text does not have square bracket formatted citations, return False.
    CITATION_PATTERN: [number], [number-number], [number,number] - e.g. [1], [1-3], [1,3]
    AUTHOR_YEAR_PATTERN: (author, year) - e.g. (Author, 2026)
    FALLBACK_CITATION_PATTERN: (number), (number-number), (number,number) - e.g. (1), (1-3), (1,3)

    Returns the citation pattern with the highest count if it meets the following thresholds:
        - at least 3 citation patterns
        - at least 3 author year patterns
        - at least 7 fallback citation patterns

    Otherwise, returns None.
    """
    citation_count = 0
    author_year_count = 0
    fallback_citation_count = 0

    for section in sections:
        for _ in CITATION_PATTERN.finditer(section.text):
            citation_count += 1
        for _ in AUTHOR_YEAR_PATTERN.finditer(section.text):
            author_year_count += 1
        for _ in FALLBACK_CITATION_PATTERN.finditer(section.text):
            fallback_citation_count += 1
    
    if max(citation_count, author_year_count, fallback_citation_count) == citation_count and citation_count >= 3:
        return CITATION_PATTERN
    elif max(citation_count, author_year_count, fallback_citation_count) == author_year_count and author_year_count >= 3:
        return AUTHOR_YEAR_PATTERN
    elif max(citation_count, author_year_count, fallback_citation_count) == fallback_citation_count and fallback_citation_count >= 7:
        return FALLBACK_CITATION_PATTERN
    else:
        return None

def parse_citation_block(citation_block: str) -> list[int]:
    """
    Expand a single bracketed citation block into citation numbers.

    Examples:
        - [1] -> [1]
        - [1, 3] -> [1, 3]
        - [1-3, 5] -> [1, 2, 3, 5]
        - (1) -> [1]
        - (1-3) -> [1, 2, 3]
        - (1-3, 5) -> [1, 2, 3, 5]
    """
    numbers = citation_block.strip()[1:-1].replace("–", "-")
    citation_numbers: list[int] = []

    for chunk in numbers.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue

        if "-" not in chunk:
            citation_numbers.append(int(chunk))
            continue

        start_text, end_text = [part.strip() for part in chunk.split("-", 1)]
        start = int(start_text)
        end = int(end_text)
        citation_numbers.extend(range(start, end + 1))

    return citation_numbers

def associate_citations(sections: list[Section], citation_pattern: re.Pattern) -> list[Section]:
    """
    Associates bracketed numeric citations with each section text block.
    Citation pattern: CITATION_PATTERN, AUTHOR_YEAR_PATTERN, FALLBACK_CITATION_PATTERN

    Returns:
        A list of sections with the citations associated with each section.
    """
    for section in sections:
        if section.citations:
            continue
        
        if citation_pattern == AUTHOR_YEAR_PATTERN:
            # Don't asscociate citations numbers if in-text citations (Harvard style) pattern is found
            section.text = citation_pattern.sub("", section.text)
        else:
            citation_numbers: list[int] = []
            for match in citation_pattern.finditer(section.text):
                citation_numbers.extend(parse_citation_block(match.group(0).strip()))
            section.text = citation_pattern.sub("", section.text)
            section.text = section.text.replace("[,]", "").replace("[–]","")
            section.text = section.text.replace("(,)", "").replace("(–)", "")
            section.citations = citation_numbers

    return sections

def enrich_document_references(doi: str, enricher: MetadataEnricher | None = None) -> list[Reference]:
    """
    Obtains the references in the document using the DOI.
    Uses the Crossref API by default to enrich the references.

    Input:
        doi: The DOI of the document.
    Returns:
        A list of references.
    """
    enricher = enricher or CrossrefEnricher()
    try:
        enriched = enricher.enrich(doi or "")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return []
    except Exception:
        return []

    raw_references = enriched.get("references")
    if raw_references is None:
        raw_references = enriched.get("message", {}).get("reference", [])
    if not isinstance(raw_references, list):
        return []

    # Extract the value(s) from the reference objects using the keys given
    def get_reference_value(reference_payload: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = reference_payload.get(key)
            if isinstance(value, list):
                value = " ".join(str(part).strip() for part in value if str(part).strip())
            if value is None:
                continue
            cleaned = strip_special_chars(str(value))
            if cleaned:
                return cleaned
        return ""

    references: list[Reference] = []
    for index, raw_reference in enumerate(raw_references, start=1):
        if not isinstance(raw_reference, dict):
            continue

        doi_value = normalize_doi(get_reference_value(raw_reference, "DOI", "doi"))         # Normalize the DOI
        pmid_value = get_reference_value(raw_reference, "PMID", "pmid") or None             # Extract the PMID
        url_value = get_reference_value(raw_reference, "URL", "url") or None                # Extract the URL
        unstructured = get_reference_value(raw_reference, "unstructured")                   # Extract the unstructured text

        author = get_reference_value(raw_reference, "author")                               # Extract the author
        title = get_reference_value(                                                        # Extract the title from the reference object
            raw_reference,
            "article-title",
            "chapter-title",
            "series-title",
            "volume-title",
        )
        journal = get_reference_value(raw_reference, "journal-title", "container-title")    # Extract the journal
        volume = get_reference_value(raw_reference, "volume")                               # Extract the volume
        issue = get_reference_value(raw_reference, "issue")                                 # Extract the issue
        first_page = get_reference_value(raw_reference, "first-page", "page")               # Extract the first page
        year = get_reference_value(raw_reference, "year")                                   # Extract the year

        # Rebuild the reference text from the extracted values
        # Build the source parts of the reference text
        source_parts: list[str] = []
        if journal:
            source_parts.append(journal)
        if volume and issue:
            source_parts.append(f"{volume}({issue})")
        elif volume:
            source_parts.append(volume)
        elif issue:
            source_parts.append(f"issue {issue}")
        if first_page:
            source_parts.append(f"p. {first_page}")
        if year:
            source_parts.append(year)

        # Build the text parts of the reference text
        text_parts: list[str] = []
        if author:
            text_parts.append(author)
        if title:
            text_parts.append(title)
        if source_parts:
            text_parts.append(", ".join(source_parts))
        if doi_value:
            text_parts.append(f"DOI: {doi_value}")
        elif url_value:
            text_parts.append(url_value)
        if pmid_value:
            text_parts.append(f"PMID: {pmid_value}")

        text = strip_special_chars(unstructured or ". ".join(text_parts))
        if not text:
            fallback_parts = [part for part in [doi_value, url_value, pmid_value] if part]
            if not fallback_parts:
                continue
            text = " ".join(fallback_parts)

        # Build the Reference object.
        reference = build_reference(index, text)
        reference.doi = reference.doi or doi_value
        reference.url = reference.url or url_value or (f"https://doi.org/{doi_value}" if doi_value else None)
        reference.pmid = reference.pmid or pmid_value
        references.append(reference)

    return references

def count_reference_citations(sections: list[Section], references: list[Reference], metadata_enricher: MetadataEnricher | None = None) -> int:
    """
    Gets the total "is-referenced-by-count" of the references in the document.

    Input:
        references: The references of the document.
        metadata_enricher: The metadata enricher to use.
    Returns:
        The total "is-referenced-by-count" of the citations in the sections.
    """
    metadata_enricher = metadata_enricher or CrossrefEnricher()

    reference_by_index = {reference.index: reference for reference in references if reference.doi}

    # Fetch the citations count for the cited references
    def fetch_citations_count(reference: Reference) -> tuple[int, int]:
        try:
            enriched = metadata_enricher.enrich(reference.doi or "")
            citations_count = enriched.get("citations_count") or 0
            return reference.index, citations_count
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return reference.index, 0
        except Exception:
            return reference.index, 0
            
    if reference_by_index:
        max_workers = min(8, len(reference_by_index))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_citations_count, reference): reference.index
                for reference in reference_by_index.values()
            }
            for future in as_completed(futures):
                reference_index, citations_count = future.result()
                reference_by_index[reference_index].citations_count = citations_count
    
    # Count the number of citations and the citations reference count for each section
    for section in sections:
        if section.citations:
            section.number_of_citations = len(section.citations)
            section.citations_reference_count = sum(
                (reference_by_index.get(citation).citations_count or 0)
                if reference_by_index.get(citation)
                else 0
                for citation in section.citations
            )

# =======================================================
# Text Extraction Helper Functions
# =======================================================
def iterate_boxes(data: dict[str, Any]):
    """
    Iterates over all boxes in the document JSON data.
    """
    for page_number, page in enumerate(data.get("pages", []), start=1):
        for box_index, box in enumerate(page.get("boxes", [])):
            yield page_number, box_index, box


def iterate_spans(box: dict[str, Any]):
    """
    Iterates over all spans in the textlines of a box.
    """
    if not box.get("textlines"):
        return
    for textline in box.get("textlines", []):
        for span in textline.get("spans", []):
            yield span

def get_preferred_heading(text: str) -> str:
    """
    Gets the preferred heading from the text.
    """
    cleaned = strip_special_chars(text)                              # Strip special characters from the text
    cleaned = cleaned.lower()                                        # Convert the text to lowercase
    cleaned = HEADING_ALIASES.get(cleaned, cleaned)                  # Get the preferred heading from the heading aliases
    return cleaned

def find_primary_doi(data: dict[str, Any], text: str) -> str | None:
    """
    Finds the primary DOI in the data and text.
    Identifies the primary DOI by returning the most common DOI in the links extracted from the first 3 pages.
    """
    link_candidates: list[str] = []
    text_candidates: list[str] = []

    # Finds all DOIs in the links (of the JSON data) of the first 3 pages
    for page in data.get("pages", [])[:3]:
        for box in page.get("boxes", []):
            for link in box.get("links", []):
                uri = link.get("uri", "")
                link_candidates.extend(match.group(1) for match in DOI_REGEX.finditer(uri))

    # Finds all DOIs in the text
    text_candidates.extend(match.group(1) for match in DOI_REGEX.finditer(text))
    if not link_candidates and not text_candidates:
        return None

    # Normalizes the DOIs and returns the most common DOI
    cleaned_link_candidates = [normalize_doi(candidate) for candidate in link_candidates if normalize_doi(candidate)]
    if cleaned_link_candidates:
        counts = Counter(cleaned_link_candidates)
        return counts.most_common(1)[0][0]

    # If no DOIs are found in the links, normalize the DOIs in the text and return the most common DOI
    cleaned_text_candidates = [normalize_doi(candidate) for candidate in text_candidates if normalize_doi(candidate)]
    if not cleaned_text_candidates:
        return None

    counts = Counter(cleaned_text_candidates)
    return counts.most_common(1)[0][0]


def normalize_doi(text: str) -> str | None:
    """
    Finds the DOI in the text, removes the URL prefix, and removes any month text if it is present.
    """
    match = DOI_REGEX.search(text)
    if not match:
        return None

    doi = match.group(1).rstrip(").,;")
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    doi = re.sub(
        r"(?<=\d)(January|February|March|April|May|June|July|August|September|October|November|December)$",
        "",
        doi,
        flags=re.IGNORECASE,
    )
    return doi


def split_reference_number(text: str) -> tuple[int | None, str]:
    """
    Splits the reference number from the text of the reference.
    Expected format: [number] or number.
    """
    match = re.match(r"^\s*(?:\[(\d+)\]|(\d+)[\].)])\s*(.*)$", text)
    if not match:
        return None, text
    number = match.group(1) or match.group(2)
    remainder = match.group(3).strip()
    return int(number), remainder


def build_reference(index: int | None, text: str) -> Reference:
    """
    Builds a Reference object from the text.
    """
    doi = normalize_doi(text)                                               # Normalize the DOI
    urls = URL_REGEX.findall(text)                                          # Find all URLs in the text
    url = urls[0].rstrip(").,;") if urls else None
    pmid_match = PMID_REGEX.search(text)                                    # Find the PMID in the text
    pmid = pmid_match.group(1) if pmid_match else None
    return Reference(index=index, text=text, doi=doi, url=url, pmid=pmid)   # Return the Reference object


def extract_box_text(box: dict[str, Any], min_size: float | None = None) -> str:
    """
    Extracts useful text from a box in the document.
    """
    text = ""
    for span in iterate_spans(box):
        size = float(span.get("size", 0.0))
        # If the size of the span is less than the minimum size, skip the span
        if min_size is not None and size and size < min_size:
            # If the text matches the pattern of a citation, add it to the text
            if CITATION_PATTERN.search(span.get("text", "")):
                text = merge_text_chunks(text, span.get("text", ""))
            continue
        # Merge the text across all spans in the box
        text = merge_text_chunks(text, span.get("text", ""))
    # Strip special characters from the text
    return strip_special_chars(text)

def merge_text_chunks(existing: str, new_text: str) -> str:
    """
    Merges text new_text into existing text with defined rules.
    """
    new_text = strip_special_chars(new_text)
    # If the new text is empty, return the existing text
    if not new_text:
        return existing
    # If the existing text is empty, return the new text
    if not existing:
        return new_text
    # If the existing text ends with a hyphen and the new text starts with an alphanumeric character, remove the hyphen and add the new text
    if existing.endswith("-") and new_text[:1].isalnum():
        return existing[:-1] + new_text
    # If the existing text ends with a URL continuation and the new text starts with a URL continuation, add the new text to the existing text
    if check_url_characters(existing[-15:]) or new_text.startswith(("/", ".", "?", "&", "=")):
        return existing + new_text
    return f"{existing} {new_text}"


def strip_special_chars(text: str) -> str:
    """
    Strips special characters from the text.
    Replaces multiple consecutive spaces with a single space.
    Strips leading and trailing whitespace.
    """
    if not text:
        return ""
    for char in SPECIAL_CHARS:
        text = text.replace(char, "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    """
    Normalize the text to a lowercase string with only alphanumeric characters.
    """
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def check_url_characters(text: str) -> bool:
    """
    Checks if the last 10 characters contain at least two of the following characters: /, ., :, ?, =
    Returns True if the text looks like a URL continuation.
    """
    count = 0
    for char in text:
        if char in ["/", ".", ":", "?", "="]:
            count += 1
    return count >= 2

def is_unwanted_text(text: str) -> bool:
    """
    Determines if the text is unwanted.
    Unwanted text is text that is not relevant to the content of the document.
    """
    lower = text.lower()
    # Ignore selected text if it starts with a prefix in the IGNORE_PREFIXES list
    if any(lower.startswith(prefix) for prefix in IGNORE_PREFIXES):
        return True
    # Ignore selected text if it matches the pattern of a page number (e.g. "1 of 10")
    if re.fullmatch(r"-{1,3}\s*\d+\s+of\s+\d+\s*-{1,3}", lower):
        return True
    # Ignore selected text if it matches the pattern of a DOI.
    if re.search(r"\b\d+\s*/\s*\d+\b", lower) and "doi.org/" in lower:
        return True
    # Ignore selected text if it starts with a1111111111 (sometimes used to represent an interactive element)
    if lower.startswith("a1111111111"):
        return True
    return False


def extract_date(payload: dict[str, Any] | None) -> str | None:
    """
    Extracts the date from the payload from the Crossref API response.
    The date-parts array has the following format: [[year, month, day]]
    For example, the payload {"date-parts": [[2026, 3, 16]]} will return "2026-03-16".
    """
    if not payload:
        return None
    date_parts = payload.get("date-parts", [])
    if not date_parts or not date_parts[0]:
        return None
    # Return the date in the format YYYY-MM-DD
    return "-".join(str(part) for part in date_parts[0])


def is_filler_heading(text: str) -> bool:
    """
    Determines if a heading is a filler heading.
    Filler headings are headings that are not relevant to the content of the document.
    """
    lowered = get_preferred_heading(text)
    if lowered in FILLER_HEADINGS:
        return True
    # Ignore selected text if it contains a lot of commas, brackets, or at symbols
    if text.count(",") >= 3 or "[" in text or "@" in text:
        return True
    # Ignore selected text if it is too long (it is likely a sentence instead of a heading)
    if len(text.split()) > 10:
        return True
    return False


# =======================================================
# Acronym Matching Helper Functions
# =======================================================

def acronym_matches_full_form(full_form: str, acronym: str) -> Optional[str]:
    """
    Checks if the acronym matches the full form.
    Returns the trimmed full form if matched, or None if no match.
    """
    words = re.findall(r"[A-Za-z]+", full_form)
    significant_words = [w for w in words if w.lower() not in STOPWORDS]
    clean_acronym = acronym.replace("-", "")

    # Strict matching: walk through acronym and significant words and track which word indices matched
    acronym_idx = 0
    matched_indices = []
    for i, word in enumerate(significant_words):
        if acronym_idx < len(clean_acronym) and word[0].lower() == clean_acronym[acronym_idx].lower():
            # Ensure that the first significant word starts with a capital letter
            if len(matched_indices) < 1 and not word[0].isupper():
                continue
            matched_indices.append(i)
            acronym_idx += 1

    if acronym_idx == len(clean_acronym) and matched_indices:
        # Include all words between the first and last matched word and preserve intermediate words
        # Example: "TMTB" -> "Trail-Making Test Part B" ("Part" is preserved)
        start = matched_indices[0]
        end = matched_indices[-1]
        return " ".join(significant_words[start:end + 1])

    # Fallback: threshold matching for stylised acronyms (if the acronym is not mixed case, return None)
    has_mixed_case = any(c.islower() for c in clean_acronym) and any(c.isupper() for c in clean_acronym)
    if not has_mixed_case:
        return None

    # Ensure at least 2 upper case letters are present in the acronym (otherwise do not apply fallback matching)
    upper_letters = [c for c in clean_acronym if c.isupper()]
    if len(upper_letters) < 2:
        return None

    # Find which significant words contain matched capital letters and track the first and last word that contributed
    first_matched_word = None
    last_matched_word = None
    match_count = 0
    for i, word in enumerate(words):
        # Ensure that the first significant word starts with a capital letter
        if match_count == 0 and not word[0].isupper():
            continue
        for letter in upper_letters[match_count:]:
            pos = word.find(letter)
            if pos != -1:
                match_count += 1
                if first_matched_word is None:
                    first_matched_word = i
                last_matched_word = i
            else:
                break

    # Use the ratio of matched letters to the total number of letters in the acronym to determine if the match is strong enough
    # If the match is strong enough, return the full form
    if match_count / len(upper_letters) >= 0.5 and first_matched_word is not None:
        return " ".join(words[first_matched_word:last_matched_word + 1])

    return None

def find_all_acronyms(text: str, acronyms: LearnedAcronyms) -> str:
    """
    Finds and replaces acronyms in the text with the full form.
    """
    matches = ACRONYM_REGEX.findall(text)
    for match in matches:
        full_form = acronym_matches_full_form(match[0], match[1])
        if full_form is not None:
            acronyms.add_acronym(match[1], full_form)

    return acronyms