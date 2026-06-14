"""Train recommenders and run offline evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.evaluate import main as evaluate


def main() -> None:
    print("Running offline evaluation (Content-Based, CF, Hybrid)...")
    results = evaluate()
    print("\nResults saved. Summary:")
    for model, metrics in results["models"].items():
        print(f"\n{model}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
    print(f"\nRMSE (CF): {results['rmse_collaborative_filtering']:.4f}")


if __name__ == "__main__":
    main()
