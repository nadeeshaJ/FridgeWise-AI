"""In-memory fridge inventory store for the API prototype."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from src.preprocessing.ingredient_utils import clean_ingredient_name, compute_expiry_priority_score


class FridgeStore:
    def __init__(self, fridge_df: pd.DataFrame, reference_date: str):
        self._df = fridge_df.copy()
        self._reference_date = pd.to_datetime(reference_date).normalize()
        self._next_id = int(self._df["inventory_id"].max()) + 1 if not self._df.empty else 1

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._df

    def get_user_items(self, user_id: int) -> list[dict]:
        items = self._df[self._df["user_id"] == user_id]
        return items.to_dict(orient="records")

    def _refresh_expiry_fields(self, row: dict) -> dict:
        expiry = pd.to_datetime(row["expiry_date"]).normalize()
        days = int((expiry - self._reference_date).days)
        row["days_to_expiry"] = days
        row["expiry_priority_score"] = compute_expiry_priority_score(days)
        return row

    def add_item(
        self,
        user_id: int,
        ingredient_name: str,
        quantity: float = 1.0,
        unit: str = "piece",
        storage_type: str = "fridge",
        days_to_expiry: int = 7,
        barcode: str = "",
    ) -> dict:
        cleaned = clean_ingredient_name(ingredient_name)
        purchase = (self._reference_date - timedelta(days=1)).date()
        expiry = (self._reference_date + timedelta(days=days_to_expiry)).date()
        row = {
            "inventory_id": self._next_id,
            "user_id": user_id,
            "ingredient_name": ingredient_name.strip(),
            "cleaned_ingredient_name": cleaned,
            "quantity": float(quantity),
            "unit": unit,
            "storage_type": storage_type,
            "purchase_date": purchase,
            "expiry_date": expiry,
            "days_to_expiry": days_to_expiry,
            "barcode": barcode or "",
            "expiry_priority_score": compute_expiry_priority_score(days_to_expiry),
        }
        self._next_id += 1
        self._df = pd.concat([self._df, pd.DataFrame([row])], ignore_index=True)
        return row

    def update_item(self, user_id: int, inventory_id: int, updates: dict) -> dict | None:
        mask = (self._df["user_id"] == user_id) & (self._df["inventory_id"] == inventory_id)
        if not mask.any():
            return None

        idx = self._df.index[mask][0]
        row = self._df.loc[idx].to_dict()

        if "ingredient_name" in updates and updates["ingredient_name"]:
            row["ingredient_name"] = str(updates["ingredient_name"]).strip()
            row["cleaned_ingredient_name"] = clean_ingredient_name(row["ingredient_name"])
        if "quantity" in updates and updates["quantity"] is not None:
            row["quantity"] = float(updates["quantity"])
        if "unit" in updates and updates["unit"]:
            row["unit"] = str(updates["unit"])
        if "storage_type" in updates and updates["storage_type"]:
            row["storage_type"] = str(updates["storage_type"])
        if "days_to_expiry" in updates and updates["days_to_expiry"] is not None:
            days = int(updates["days_to_expiry"])
            row["expiry_date"] = (self._reference_date + timedelta(days=days)).date()
        if "expiry_date" in updates and updates["expiry_date"]:
            row["expiry_date"] = pd.to_datetime(updates["expiry_date"]).date()
        if "barcode" in updates:
            row["barcode"] = str(updates["barcode"] or "")

        row = self._refresh_expiry_fields(row)
        for key, value in row.items():
            if key in ("purchase_date", "expiry_date") and value is not None:
                if isinstance(value, pd.Timestamp):
                    value = value.date()
                elif isinstance(value, datetime):
                    value = value.date()
            self._df.at[idx, key] = value

        return self._df.loc[idx].to_dict()

    def delete_item(self, user_id: int, inventory_id: int) -> bool:
        mask = (self._df["user_id"] == user_id) & (self._df["inventory_id"] == inventory_id)
        if not mask.any():
            return False
        self._df = self._df[~mask].reset_index(drop=True)
        return True

    def sync_hybrid(self, hybrid) -> None:
        hybrid.fridge_df = self._df
