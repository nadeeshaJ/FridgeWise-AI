"""Unit tests for in-memory fridge inventory store."""

import pandas as pd

from api.fridge_store import FridgeStore


def _empty_store() -> FridgeStore:
    cols = [
        "inventory_id",
        "user_id",
        "ingredient_name",
        "cleaned_ingredient_name",
        "quantity",
        "unit",
        "storage_type",
        "purchase_date",
        "expiry_date",
        "days_to_expiry",
        "barcode",
        "expiry_priority_score",
    ]
    return FridgeStore(pd.DataFrame(columns=cols), "2026-06-14")


def test_add_and_get_item():
    store = _empty_store()
    item = store.add_item(10001, "Cherry Tomatoes", quantity=2, days_to_expiry=3)
    assert item["cleaned_ingredient_name"] == "tomato"
    assert len(store.get_user_items(10001)) == 1


def test_update_item():
    store = _empty_store()
    item = store.add_item(10001, "Milk", quantity=1, days_to_expiry=7)
    updated = store.update_item(
        10001,
        item["inventory_id"],
        {"quantity": 2, "days_to_expiry": 1},
    )
    assert updated is not None
    assert updated["quantity"] == 2
    assert updated["days_to_expiry"] == 1
    assert updated["expiry_priority_score"] == 0.9


def test_delete_item():
    store = _empty_store()
    item = store.add_item(10001, "Eggs")
    assert store.delete_item(10001, item["inventory_id"]) is True
    assert store.get_user_items(10001) == []
    assert store.delete_item(10001, item["inventory_id"]) is False
