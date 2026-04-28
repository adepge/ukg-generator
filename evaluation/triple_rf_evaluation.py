"""
Triple Risk Factor Evaluation

This module is used to evaluate the triples for the UKG Generator.
It graphs the confidence distribution of the triples for each annotation category.
"""

from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

annotated_triples_file = Path("src/evaluation/triples/annotated_triples.csv")
EVALUATION_DIR = Path(__file__).resolve().parent / "triples"

# Labels for the annotation categories.
CATEGORY_LABELS = {
    "1": "Exact match",
    "2": "Synonymous",
    "3": "Compound",
    "4": "False positive",
    "5": "Identity",
    "6": "Potential MRF",
    "7": "Non-MRF",
}

def load_annotated_triples() -> list[dict]:
    """
    Load the annotated triples from the CSV file.

    Input:
        None
    Returns:
        A list of tuples containing the annotated triples.
    """
    annotated_triples = []
    with open(annotated_triples_file, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(tuple(row)) != 5:
                raise ValueError(f"Expected 5 columns in {annotated_triples_file}, got {len(tuple(row)) } for row {row}")
            annotated_triples.append(tuple(row))
    return annotated_triples

def count_annotated_triples(triples: tuple[str, str, str, float, int]) -> int:
    """
    Count the annotated triples for each annotation category.

    Input:
        triples: A list of tuples containing the annotated triples.
    Returns:
        A tuple containing the count of annotated triples for each annotation category.
    """
    exact_matches = 0
    synonymous = 0
    compound = 0
    false_positives = 0
    identity = 0
    potential_mrf = 0
    non_mrf = 0

    potential_mrf_triples = []

    for triple in triples:
        if triple[4] == "1":
            exact_matches += 1
        elif triple[4] == "2":
            synonymous += 1
        elif triple[4] == "3":
            compound += 1
        elif triple[4] == "4":
            false_positives += 1
        elif triple[4] == "5":
            identity += 1
        elif triple[4] == "6":
            potential_mrf += 1
            potential_mrf_triples.append(triple)
        elif triple[4] == "7":
            non_mrf += 1
        else:
            print(f"Unknown annotation: {triple[4]} for triple {triple}")
    return exact_matches, synonymous, compound, false_positives, identity, potential_mrf, non_mrf, potential_mrf_triples

def percentage_count(count: int, total: int) -> float:
    return round((count / total) * 100, 2)

def plot_confidence_distribution(annotated_triples: list[tuple]) -> Path:
    """
    Plot a heatmap of the confidence distribution of the annotated triples.

    Input:
        annotated_triples: A list of tuples containing the annotated triples.
    Returns:
        A path to the saved chart.
    """
    chart_path = EVALUATION_DIR / "triple_confidence_distribution.png"
    plt.style.use("default")

    df = pd.DataFrame(annotated_triples, columns=["subject", "predicate", "object", "confidence", "category"])
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df = df.dropna(subset=["confidence", "category"])
    df = df[(df["confidence"] >= 0.70) & (df["confidence"] <= 1.00)]

    # Create the bins for the confidence distribution (starting at 0.70 and ending at 1.00 with a step of 0.05).
    bins = np.round(np.arange(0.70, 1.00 + 1e-9, 0.05), 2)
    bin_labels = [f"{bins[i]:.2f}-{bins[i + 1]:.2f}" for i in range(len(bins) - 1)]

    categories = sorted(CATEGORY_LABELS.keys())
    category_display = [CATEGORY_LABELS[c] for c in categories]

    heatmap_data = []
    for category in categories:
        cat_conf = df.loc[df["category"] == category, "confidence"]
        counts, _ = np.histogram(cat_conf, bins=bins)
        proportions = counts / counts.sum() if counts.sum() else counts
        heatmap_data.append(proportions)

    heatmap_df = pd.DataFrame(heatmap_data, index=category_display, columns=bin_labels)

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(heatmap_df.values, aspect="auto", cmap="magma", interpolation="nearest")

    ax.set_title("Confidence Distribution by Annotation Category", fontsize=16)
    ax.set_xlabel("Confidence Bin", fontsize=14)
    ax.set_ylabel("Annotation Category", fontsize=14)
    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(range(len(category_display)))
    ax.set_yticklabels(category_display, fontsize=10)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Proportion of triples", fontsize=12)

    fig.tight_layout()
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return chart_path

def main() -> None:
    annotated_triples = load_annotated_triples()
    total_annotated_triples = len(annotated_triples)
    exact_matches, synonymous, compound, false_positives, identity, potential_mrf, non_mrf, potential_mrf_triples = count_annotated_triples(annotated_triples)

    # Print the counts of the annotated triples for each annotation category.
    print(f"Total annotated triples: {total_annotated_triples}")
    print(f"Exact matches: {exact_matches} ({percentage_count(exact_matches, total_annotated_triples)}%)")
    print(f"Synonymous: {synonymous} ({percentage_count(synonymous, total_annotated_triples)}%)")
    print(f"Compound: {compound} ({percentage_count(compound, total_annotated_triples)}%)")
    print(f"False positives: {false_positives} ({percentage_count(false_positives, total_annotated_triples)}%)")
    print(f"Identity: {identity} ({percentage_count(identity, total_annotated_triples)}%)")
    print(f"Potential MRF: {potential_mrf} ({percentage_count(potential_mrf, total_annotated_triples)}%)")
    print(f"Non MRF: {non_mrf} ({percentage_count(non_mrf, total_annotated_triples)}%)")

    # Print the potential MRF triples.
    print(f"Potential MRF triples:")
    for triple in potential_mrf_triples:
        print(f"{triple[0]},{triple[1]},{triple[2]},{triple[3]}")

    # Plot the confidence distribution chart.
    confidence_distribution_chart_path = plot_confidence_distribution(annotated_triples)
    print(f"Saved confidence distribution chart to: {confidence_distribution_chart_path}")
if __name__ == "__main__":
    main()