"""Download Kaggle datasets required for the pipeline."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.preprocessing.config_loader import resolve_path

FOOD_COM = "shuyangli94/food-com-recipes-and-user-interactions"
EXPIRY = "prekshad2166/food-expiry-tracker"


def _has_food_com(raw_dir: Path) -> bool:
    return (raw_dir / "RAW_recipes.csv").exists() and (raw_dir / "RAW_interactions.csv").exists()


def _has_expiry(raw_dir: Path) -> bool:
    return any("expiry" in f.name.lower() for f in raw_dir.glob("*.csv"))


def _extract_zip(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)


def _kaggle_download(dataset: str, raw_dir: Path) -> None:
    cmd = [sys.executable, "-m", "kaggle", "datasets", "download", "-d", dataset, "-p", str(raw_dir), "--unzip"]
    subprocess.run(cmd, check=True)


def download_all(raw_dir: Path | None = None) -> None:
    raw_dir = raw_dir or resolve_path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("kaggle") and not _module_available("kaggle"):
        print(
            "Kaggle CLI not configured.\n"
            "Manual download:\n"
            f"  1. Food.com: https://www.kaggle.com/datasets/{FOOD_COM}\n"
            f"  2. Expiry:   https://www.kaggle.com/datasets/{EXPIRY}\n"
            f"Place RAW_recipes.csv, RAW_interactions.csv, and the expiry CSV in:\n  {raw_dir}\n"
        )
        if not _has_food_com(raw_dir):
            raise FileNotFoundError("Food.com raw files missing. Download manually or configure Kaggle API.")
        return

    if not _has_food_com(raw_dir):
        print("Downloading Food.com dataset...")
        _kaggle_download(FOOD_COM, raw_dir)

    if not _has_expiry(raw_dir):
        print("Downloading Food Expiry Tracker dataset...")
        _kaggle_download(EXPIRY, raw_dir)

    print("Raw datasets ready in", raw_dir)


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    download_all()
