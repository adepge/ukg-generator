import re


def normalize_term(value: str) -> str:
    """
    Normalizes a term by removing non-alphanumeric characters and converting to lowercase.
    Input:
        value: The term to normalize.
    Returns:
        The normalized term.
    """
    cleaned = (value or "").strip().lower().replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def triple_key(subject: str, predicate: str, obj: str) -> str:
    """
    Creates a key for a triple by concatenating the normalized subject, predicate, and object.
    Input:
        subject: The subject of the triple.
        predicate: The predicate of the triple.
        obj: The object of the triple.
    Returns:
        The key for the triple.
    """
    return f"{subject}|{predicate}|{obj}"


def edge_opacity(confidence: float) -> float:
    """
    Calculates the opacity for an edge based on the confidence score.
    Input:
        confidence: The confidence score of the edge.
    Returns:
        The opacity for the edge.
    """
    bounded = max(0.0, min(1.0, confidence))
    return round(0.3 + 0.7 * bounded, 4)
