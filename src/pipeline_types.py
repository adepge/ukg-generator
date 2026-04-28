"""
Lightweight, dependency-free dataclasses shared by the UKG pipeline stages.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    title: str = ""                                     # The title of the document
    authors: list[str] = field(default_factory=list)    # The authors of the document
    citations_count: int = 0                            # Count of the number of other articles that cite this document
    doi: Optional[str] = None                           # The DOI of the document
    journal: Optional[str] = None                       # The journal of the document
    article_type: Optional[str] = None                  # The type of the document
    received_date: Optional[str] = None                 # The received date of the document
    accepted_date: Optional[str] = None                 # The accepted date of the document
    published_date: Optional[str] = None                # The published date of the document
    raw: dict[str, Any] = field(default_factory=dict)   # The raw metadata of the document as extracted from the JSON file


@dataclass
class Section:
    """A section of a document."""
    heading: str                                              # The heading of the section
    text: str                                                 # The text of the section (the content of the section)
    level: int                                                # The level of the section (how deeply nested the section is in the document)
    parent_heading: Optional[str] = None                      # The parent heading of the section
    citations: Optional[list[int]] = None                     # The list of section IDs that are cited by this section
    number_of_citations: int = 0                              # Count of the number of citations in the section
    citations_reference_count: int = 0                        # Total citation count of all the references cited in the section
    path: list[str] = field(default_factory=list)             # The path of the section (e.g Introduction > Background > Methods)
    page_numbers: list[int] = field(default_factory=list)     # The page numbers of the section


@dataclass
class Reference:
    """A reference to a document."""
    index: int                                                # The index of the reference
    text: str                                                 # The text of the reference
    doi: Optional[str] = None                                 # The DOI of the reference
    url: Optional[str] = None                                 # The URL of the reference
    pmid: Optional[str] = None                                # The PMID of the reference
    citations_count: Optional[int] = None                     # The number of citations of the reference

    def as_legacy_tuple(self) -> tuple[int | None, str | None, str]:
        main_url = self.url
        if self.doi and not main_url:
            main_url = f"https://doi.org/{self.doi}"
        return (self.index, main_url, self.text)


@dataclass
class ExtractionResult:
    """
    Stores the extraction result.

    Contains the following:
    - metadata: The metadata of the document
    - sections: The sections of the document
    - references: The references of the document
    """
    metadata: DocumentMetadata
    sections: list[Section]
    references: list[Reference]

    def to_tuples(self) -> list[tuple[str, str]]:
        return [
            (section.path or section.heading, section.text, section.citations)
            for section in self.sections
            if section.text.strip()
        ]


@dataclass
class LearnedAcronyms:
    """
    Stores the learned acronyms.
    This allows the replacement of acronyms found within the text across all sections of the document.
    """
    acronyms: dict[str, str] = field(default_factory=dict)

    def add_acronym(self, acronym: str, full_form: str):
        if acronym in self.acronyms:
            return
        self.acronyms[acronym] = full_form

    def replace_acronyms(self, string: str) -> str:
        for acronym in self.acronyms:
            if acronym in string:
                string = string.replace(acronym, self.acronyms[acronym])
        return string.strip()
