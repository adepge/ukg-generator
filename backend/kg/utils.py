import re


def normalize_term(value: str) -> str:
    cleaned = (value or "").strip().lower().replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def triple_key(subject: str, predicate: str, obj: str) -> str:
    return f"{subject}|{predicate}|{obj}"


def edge_opacity(confidence: float) -> float:
    bounded = max(0.0, min(1.0, confidence))
    return round(0.3 + 0.7 * bounded, 4)
