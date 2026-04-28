"""
Helpers for loading the pipeline's resource files.
"""

import csv
from functools import lru_cache


@lru_cache(maxsize=8)
def load_ontology_terms(ontology_list: tuple[str, ...]) -> frozenset[str]:
    """
    Load and cache ontology terms for a tuple of file paths.
    Each line in each file is expected to be a single term.
    """
    terms: set[str] = set()
    for ontology_file in ontology_list:
        with open(ontology_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                term = line.strip().lower()
                if term:
                    terms.add(term)
    return frozenset(terms)


def load_blacklist_files(
    filepaths: list[str],
) -> list[frozenset[tuple[str, str, str, str, str]]]:
    """
    Load blacklist CSVs into raw (term, category, rule, subject, object) frozensets.
    The header row of each CSV is skipped.
    """
    blacklists: list[frozenset[tuple[str, str, str, str, str]]] = []
    for filepath in filepaths:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader)
            blacklist = []
            for row in reader:
                term, category, rule, subject, object = row
                blacklist.append((term, category, rule, subject, object))
            blacklists.append(frozenset(blacklist))
    return blacklists


def build_blacklist_sets(
    blacklists: list[frozenset[tuple[str, str, str, str, str]]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Materialise raw blacklist rows into the
    (subject_excl_str, object_excl_str, subject_excl_word, object_excl_word)
    tuple consumed by generate_triples.

    Rules:
      - excl: substring match on the subject/object.
      - excl_only: exact match (case-insensitive, spaces → underscores).
    """
    subject_excl_str: list[str] = []
    object_excl_str: list[str] = []
    subject_excl_word: list[str] = []
    object_excl_word: list[str] = []
    for blacklist in blacklists:
        for term, _category, rule, subject, object in blacklist:
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
    return (
        list(set(subject_excl_str)),
        list(set(object_excl_str)),
        list(set(subject_excl_word)),
        list(set(object_excl_word)),
    )
