"""
Get triples with a specific relation and object key from the API.
"""

import requests
import csv
from pathlib import Path

API_URL = "http://localhost:8000/api/search"
EVALUATION_DIR = Path(__file__).resolve().parent / "risk_factors"

def fetch_triples_with_relation(relation: str, object_key: str) -> list[dict]:
    """
    Fetch triples with a specific relation and object key from the API.

    Input:
        relation: The relation to fetch the triples for.
        object_key: The object key to filter the triples by.
    Returns:
        A list of triples.
    """
    triples = []
    response = requests.get(
        API_URL,
        params={"q": relation, "type": "relation", "limit": 10000},
        timeout=30,
    )
    response.raise_for_status()
    matches = response.json().get("matches", [])
    for match in matches:
        if match["object"] == object_key:
            triples.append(match)
    return triples


def main() -> None:
    # Fetch the triples with the specific relation (risk_factor_of) and object key (dementia).
    triples = fetch_triples_with_relation("risk_factor_of", "dementia")
    sorted_triples = sorted(triples, key=lambda x: x["confidence"], reverse=True)

    # Save the triples to a CSV file
    with open( EVALUATION_DIR / "triples.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "predicate", "object", "confidence"])
        for triple in sorted_triples:
            writer.writerow([triple["subject"], triple["predicate"], triple["object"], round(triple["confidence"], 2)])

if __name__ == "__main__":
    main()