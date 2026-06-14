"""Train/tune CF and run offline evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.evaluate import main as evaluate
from src.models.tune_cf import main as tune_cf


def main() -> None:
    print("Step 1/2: Tuning collaborative filtering on validation split...")
    tuning = tune_cf()
    best = tuning["best"]
    print(
        f"  Best: {best['algorithm']} {best.get('params', {})} | "
        f"val RMSE={best.get('validation_rmse')} | "
        f"hit@{10}={best.get('validation_hit_rate@10', best.get('validation_hit_rate@10'))}"
    )

    print("\nStep 2/2: Evaluating content-based, CF, and hybrid on test split...")
    results = evaluate()

    print("\n=== Test Results ===")
    cf_info = results.get("collaborative_filtering", {})
    print(f"CF algorithm: {cf_info.get('algorithm')} {cf_info.get('params')}")
    print(f"Validation RMSE: {cf_info.get('validation_rmse')}")
    print(f"Test RMSE: {cf_info.get('test_rmse')}")
    for model, metrics in results["models"].items():
        print(f"\n{model}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")


if __name__ == "__main__":
    main()
