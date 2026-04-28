"""
Potential Risk Factor Evaluation

This module is used to evaluate the potential risk factors for the UKG Generator.
It graphs the subject distribution of the potential risk factors.
"""

from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

annotated_triples_file = Path("src/evaluation/triples/potential_rf.csv")
EVALUATION_DIR = Path(__file__).resolve().parent / "triples"

# Labels for the potential risk factors.
SUBJECT_LABELS = {
    "1": "Diet",
    "2": "Sleep / sleep apnea",
    "3": "Psychosocial factors",
    "4": "Socioeconomic factors",
    "5": "Racial biases/disparities",
    "6": "Medication",
    "7": "Chronic conditions",
    "8": "Mobility",
    "9": "Diagnosis time",
    "10": "Geopolitics/social structure",   
    "11": "Culture",
    "12": "Menopause",
    "13": "Mentally stimulating activities"
}

def load_annotated_triples() -> list[tuple[str, str, str, float, str]]:
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

def plot_subject_counts(annotated_triples: list[tuple]) -> Path:
    """
    Plot a bar chart of the subject counts of the potential RF triples.
    """
    chart_path = EVALUATION_DIR / "potential_rf_subject_counts.png"
    plt.style.use("default")

    df = pd.DataFrame(
        annotated_triples,
        columns=["subject", "predicate", "object", "confidence", "category"],
    )
    df["category_label"] = df["category"].map(SUBJECT_LABELS)

    counts = (
        df.dropna(subset=["category_label"])
        .groupby("category_label")
        .size()
        .sort_values(ascending=False)
    )

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(
        counts.index,
        counts.values,
        color="#007d69",
        edgecolor="#003c3c",
    )

    ax.set_title("Potential Risk Factor Subject Distribution", fontsize=16)
    ax.set_xlabel("Subject", fontsize=14)
    ax.set_ylabel("Count", fontsize=14)
    ax.tick_params(axis="x", rotation=45, labelsize=12)
    ax.tick_params(axis="y", labelsize=12)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    max_count = int(counts.max()) if len(counts) else 0
    ax.set_ylim(0, max_count * 1.1 if max_count else 1)

    for bar, value in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_count * 0.01,
            f"{int(value)}",
            ha="center",
            va="bottom",
            fontsize=12,
        )

    for label in ax.get_xticklabels():
        label.set_ha("right")

    fig.tight_layout()
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return chart_path

def main() -> None:
    annotated_triples = load_annotated_triples()
    subject_counts_chart_path = plot_subject_counts(annotated_triples)
    print(f"Saved subject counts chart to: {subject_counts_chart_path}")
if __name__ == "__main__":
    main()