"""Refresh Open Food Facts product cache."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.preprocessing.fetch_open_food_facts import main as fetch_products


def main() -> None:
    df = fetch_products()
    print(f"Refreshed {len(df)} products → data/processed/clean_open_food_products.csv")


if __name__ == "__main__":
    main()
