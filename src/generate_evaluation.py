from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import matplotlib.font_manager as fm

BASE_DIR = Path(__file__).resolve().parent
EVALUATION_DIR = BASE_DIR / "evaluation"
API_URL = "http://localhost:8000/api/search"
CSV_COLUMNS = ["triple_id", "subject", "predicate", "object", "confidence"]

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


def fetch_risk_factor_data(risk_factor: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for entity in risk_factor:
        response = requests.get(
            API_URL,
            params={"q": entity, "type": "entity"},
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
    csv_path = EVALUATION_DIR / f"risk_factor_{risk_factor_name}.csv"
    return pd.read_csv(csv_path)


def summarise_risk_factor(risk_factor_name: str, df: pd.DataFrame) -> dict[str, float | int | str]:
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
    chart_path = EVALUATION_DIR / "risk_factor_confidence_summary.png"
    plt.style.use("default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Noto Sans Display"],
    })

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

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, float | int | str]] = []

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

        summary_rows.append(summarise_risk_factor(risk_factor_name, df))

    summary_df = pd.DataFrame(summary_rows)
    summary_csv_path = EVALUATION_DIR / "risk_factor_confidence_summary.csv"
    summary_df.to_csv(summary_csv_path, index=False)
    chart_path = plot_summary(summary_df)

    print(f"Saved summary statistics to: {summary_csv_path}")
    print(f"Saved bar chart to: {chart_path}")


if __name__ == "__main__":
    main()

