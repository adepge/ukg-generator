"""
Get a sample of triples from the API.
"""

import requests
import csv
from pathlib import Path

API_URL = "http://localhost:8000/api/graph"
EVALUATION_DIR = Path(__file__).resolve().parent / "sample_triples"

document_ids="72,71,70,69,68,67,66,65,64,63,62,61,60,59,58,57,56,55,54,53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1"

def fetch_triples() -> list[dict]:
    """
    Fetch triples from the API.
    """
    response = requests.get(
        API_URL,
        params={"document_ids": document_ids, "min_confidence": 0.5, "limit": 1000},
        timeout=30,
    )
    response.raise_for_status()
    edges = response.json().get("edges", [])
    triples = [{"subject": edge["source"], "predicate": edge["label"], "object": edge["target"], "confidence": edge["confidence"]} for edge in edges]
    return triples


def main() -> None:
    # Fetch the triples.
    triples = fetch_triples()

    # Save the triples to a CSV file
    with open( EVALUATION_DIR / "triples.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "predicate", "object", "confidence"])
        for triple in triples:
            writer.writerow([triple["subject"], triple["predicate"], triple["object"], round(triple["confidence"], 2)])

if __name__ == "__main__":
    main()