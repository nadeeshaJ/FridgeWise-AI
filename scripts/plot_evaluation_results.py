"""Plot offline evaluation metrics from evaluation_results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.preprocessing.config_loader import load_config, resolve_path


def load_results(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def plot_model_comparison(results: dict, output_dir: Path) -> None:
    models = results["models"]
    metrics = ["precision", "recall", "map", "ndcg"]
    k_values = [5, 10]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    model_names = list(models.keys())
    x = np.arange(len(model_names))
    width = 0.18
    colors = ["#2ecc71", "#3498db", "#e67e22", "#9b59b6"]

    for ax, k in zip(axes, k_values):
        for i, metric in enumerate(metrics):
            values = [models[m].get(f"{metric}@{k}", 0.0) for m in model_names]
            offset = (i - 1.5) * width
            ax.bar(x + offset, values, width, label=metric.upper(), color=colors[i])
        ax.set_title(f"Ranking metrics @ K={k}")
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace("_", "\n") for m in model_names], fontsize=9)
        ax.set_ylim(0, max(0.65, ax.get_ylim()[1]))
        ax.grid(axis="y", alpha=0.3)

    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("FridgeWise-AI — Offline model comparison (test split)", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_dir / "model_comparison.png", dpi=150)
    plt.close(fig)


def plot_hybrid_vs_cf(results: dict, output_dir: Path) -> None:
    models = results["models"]
    cf = models["collaborative_filtering"]
    hy = models["hybrid"]
    keys = ["map@5", "ndcg@5", "recall@5", "map@10", "ndcg@10", "recall@10"]
    labels = ["MAP@5", "NDCG@5", "R@5", "MAP@10", "NDCG@10", "R@10"]
    cf_vals = [cf[k] for k in keys]
    hy_vals = [hy[k] for k in keys]

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, cf_vals, width, label="Collaborative filtering", color="#3498db")
    ax.bar(x + width / 2, hy_vals, width, label="Hybrid", color="#2ecc71")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Score")
    ax.set_title("Hybrid vs collaborative filtering")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "hybrid_vs_cf.png", dpi=150)
    plt.close(fig)


def plot_cf_summary(results: dict, output_dir: Path) -> None:
    cf_info = results.get("collaborative_filtering", {})
    if not cf_info:
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Validation RMSE", "Test RMSE"]
    values = [cf_info.get("validation_rmse", 0), cf_info.get("test_rmse", 0)]
    ax.bar(labels, values, color=["#f39c12", "#e74c3c"])
    ax.set_ylim(0, max(values) * 1.2)
    ax.set_title(f"CF rating prediction ({cf_info.get('algorithm', 'cf')})")
    for i, v in enumerate(values):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center")
    fig.tight_layout()
    fig.savefig(output_dir / "cf_rmse.png", dpi=150)
    plt.close(fig)


def main() -> None:
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])
    results_path = processed / "evaluation_results.json"
    output_dir = processed / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not results_path.exists():
        raise FileNotFoundError(
            f"{results_path} not found. Run: python scripts/train_and_evaluate.py"
        )

    results = load_results(results_path)
    plot_model_comparison(results, output_dir)
    plot_hybrid_vs_cf(results, output_dir)
    plot_cf_summary(results, output_dir)
    print(f"Saved charts to {output_dir}/")
    for name in ("model_comparison.png", "hybrid_vs_cf.png", "cf_rmse.png"):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
