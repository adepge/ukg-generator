"""
Generate Risk Factor Evaluation

This module is used to generate the risk factor evaluation for the UKG Generator.
It graphs the confidence distribution of the triples for each modifiable risk factor found in dementia research papers.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import matplotlib.font_manager as fm
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
EVALUATION_DIR = BASE_DIR / "risk_factors"
API_URL = "http://localhost:8000/api/search"
CSV_COLUMNS = ["triple_id", "subject", "predicate", "object", "confidence"]

# Search terms for dementia modifiable risk factors.
dementia_modifiable_risk_factors = [
    ["inactivity"],
    ["smoking"],
    ["alcohol"],
    ["pollution"],
    ["injury"],
    ["isolation"],
    ["education"],
    ["obesity"],
    ["hypertension"],
    ["diabetes"],
    ["depression"],
    ["hearing"],
    ["vision"],
    ["cholesterol"],
    ["poor_sleep", "sleep_apnea"],
    ["diet", "processed_food"],
]

# Fetch the risk factor data from the API.
def fetch_risk_factor_data(risk_factor: list[str]) -> pd.DataFrame:
    """
    Fetch the risk factor data from the API.

    Input:
        risk_factor: A list of risk factor search terms.
    Returns:
        A DataFrame containing the risk factor data.
    """
    frames: list[pd.DataFrame] = []
    for entity in risk_factor:
        response = requests.get(
            API_URL,
            params={"q": entity, "type": "entity", "limit": 5000},
            timeout=30,
        )
        response.raise_for_status()
        matches = response.json().get("matches", [])
        if matches:
            frames.append(pd.DataFrame(matches))

    if not frames:
        return pd.DataFrame(columns=CSV_COLUMNS)

    df = pd.concat(frames, ignore_index=True)
    df.columns = CSV_COLUMNS
    df = df.sort_values(by="confidence", ascending=False)
    df = df.drop_duplicates(subset=["subject", "predicate", "object"])
    return df


def load_risk_factor_data(risk_factor_name: str) -> pd.DataFrame:
    """
    Read the risk factor data from the CSV file.

    Input:
        risk_factor_name: The name of the risk factor.
    Returns:
        A DataFrame containing the risk factor data.
    """
    csv_path = EVALUATION_DIR / f"risk_factor_{risk_factor_name}.csv"
    return pd.read_csv(csv_path)

def summarise_risk_factor(risk_factor_name: str, df: pd.DataFrame) -> dict[str, float | int | str]:
    """
    Returns a summary of the risk factor data.
    The summary includes the risk factor name, the number of triples, the mean confidence, and the standard deviation of the confidence.

    Input:
        risk_factor_name: The name of the risk factor.
        df: The DataFrame containing the risk factor data.
    Returns:
        A dictionary containing the summary of the risk factor data.
    """
    confidence = pd.to_numeric(df["confidence"], errors="coerce").dropna()
    if confidence.empty:
        return {
            "risk_factor": risk_factor_name,
            "triple_count": 0,
            "mean_confidence": 0.0,
            "std_confidence": 0.0,
        }

    return {
        "risk_factor": risk_factor_name,
        "triple_count": int(confidence.count()),
        "mean_confidence": float(confidence.mean()),
        "std_confidence": float(confidence.std(ddof=0)),
    }


def plot_summary(summary_df: pd.DataFrame) -> Path:
    """
    Plot a bar chart of the mean confidence by dementia modifiable risk factor.

    Input:
        summary_df: A DataFrame containing the summary of the risk factor data.
    Returns:
        A path to the saved chart.
    """
    chart_path = EVALUATION_DIR / "risk_factor_confidence_summary.png"
    plt.style.use("default")

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.bar(
        summary_df["risk_factor"],
        summary_df["mean_confidence"],
        yerr=summary_df["std_confidence"],
        capsize=5,
        color="#007d69",
        edgecolor="#003c3c",
        error_kw={"alpha": 0.8, "ecolor": "#003c3c", "elinewidth": 2, "capsize": 5},
    )

    ax.set_title("Mean Confidence by Dementia Modifiable Risk Factor", fontsize=16)
    ax.set_xlabel("Modifiable Risk Factor", fontsize=14)
    ax.set_ylabel("Mean Confidence", fontsize=14)
    ax.set_ylim(0, max(1.0, (summary_df["mean_confidence"] + summary_df["std_confidence"]).max() + 0.05))
    ax.tick_params(axis="x", rotation=45, labelsize=12)
    ax.tick_params(axis="y", labelsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for bar, triple_count in zip(bars, summary_df["triple_count"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"n={triple_count}",
            ha="center",
            va="bottom",
            fontsize=12,
        )

    fig.tight_layout()
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return chart_path

def plot_confidence_distribution(df: pd.DataFrame) -> Path:
    """
    Plot a heatmap of the confidence distribution by risk factor.

    Input:
        df: A DataFrame containing the risk factor data.
    Returns:
        A path to the saved chart.
    """
    chart_path = EVALUATION_DIR / "risk_factor_confidence_distribution.png"
    plt.style.use("default")

    plot_df = df.copy()
    plot_df["confidence"] = pd.to_numeric(plot_df["confidence"], errors="coerce")
    plot_df = plot_df.dropna(subset=["risk_factor", "confidence"])
    plot_df = plot_df[(plot_df["confidence"] >= 0) & (plot_df["confidence"] <= 1)]

    risk_factors = sorted(plot_df["risk_factor"].unique())
    bins = np.linspace(0, 1, 21)
    bin_labels = [f"{bins[i]:.2f}-{bins[i + 1]:.2f}" for i in range(len(bins) - 1)]

    heatmap_data = []
    for risk_factor in risk_factors:
        rf_conf = plot_df.loc[plot_df["risk_factor"] == risk_factor, "confidence"]
        counts, _ = np.histogram(rf_conf, bins=bins)
        proportions = counts / counts.sum() if counts.sum() else counts
        heatmap_data.append(proportions)

    heatmap_df = pd.DataFrame(heatmap_data, index=risk_factors, columns=bin_labels)

    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(heatmap_df.values, aspect="auto", cmap="YlGnBu", interpolation="nearest")

    ax.set_title("Confidence Distribution by Risk Factor", fontsize=16)
    ax.set_xlabel("Confidence Bin", fontsize=14)
    ax.set_ylabel("Risk Factor", fontsize=14)
    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(risk_factors)))
    ax.set_yticklabels(risk_factors, fontsize=10)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Proportion of triples", fontsize=12)

    fig.tight_layout()
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return chart_path

def plot_triple_count_distribution(df: pd.DataFrame) -> Path:
    """
    Plot a bar chart of the triple count distribution by risk factor.
    """
    chart_path = EVALUATION_DIR / "risk_factor_triple_count_distribution.png"
    plt.style.use("default")

    counts = (
        df.dropna(subset=["risk_factor"])
        .groupby("risk_factor")
        .size()
        .sort_values(ascending=False)
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.bar(
        counts.index,
        counts.values,
        color="#007d69",
        edgecolor="#003c3c",
    )

    ax.set_title("Triple Count by Dementia Modifiable Risk Factor", fontsize=16)
    ax.set_xlabel("Modifiable Risk Factor", fontsize=14)
    ax.set_ylabel("Triple Count", fontsize=14)
    ax.tick_params(axis="x", rotation=45, labelsize=12)
    ax.tick_params(axis="y", labelsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    max_count = int(counts.max()) if len(counts) else 0
    ax.set_ylim(0, max_count * 1.1 if max_count else 1)

    for bar, triple_count in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_count * 0.01,
            f"{int(triple_count)}",
            ha="center",
            va="bottom",
            fontsize=12,
        )

    fig.tight_layout()
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return chart_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate evaluation CSVs and a confidence summary plot for each risk factor.",
    )
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Reuse existing CSVs in src/evaluation instead of refetching data from the API.",
    )
    args = parser.parse_args()

    # Make the evaluation directory if it doesn't exist.
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize the summary and distribution dataframes.
    summary_rows: list[dict[str, float | int | str]] = []
    distribution_frames: list[pd.DataFrame] = []

    # Fetch the risk factor data from the API and save the CSV file.
    for risk_factor in dementia_modifiable_risk_factors:
        risk_factor_name = risk_factor[0]

        if args.plot_only:
            df = load_risk_factor_data(risk_factor_name)
        else:
            df = fetch_risk_factor_data(risk_factor)
            df.to_csv(
                EVALUATION_DIR / f"risk_factor_{risk_factor_name}.csv",
                index=False,
                header=True,
            )

        df = df.copy()
        df["risk_factor"] = risk_factor_name

        summary_rows.append(summarise_risk_factor(risk_factor_name, df))
        distribution_frames.append(df[["risk_factor", "confidence"]])

    # Create the summary and distribution dataframes.
    summary_df = pd.DataFrame(summary_rows)
    distribution_df = pd.concat(distribution_frames, ignore_index=True)

    # Plot the summary and distribution charts.
    chart_path = plot_summary(summary_df)
    confidence_distribution_chart_path = plot_confidence_distribution(distribution_df)
    triple_count_distribution_chart_path = plot_triple_count_distribution(distribution_df)
    summary_csv_path = EVALUATION_DIR / "risk_factor_confidence_summary.csv"
    print(f"Saved summary statistics to: {summary_csv_path}")
    print(f"Saved bar chart to: {chart_path}")
    print(f"Saved confidence distribution chart to: {confidence_distribution_chart_path}")
    print(f"Saved triple count distribution chart to: {triple_count_distribution_chart_path}")

if __name__ == "__main__":
    main()

