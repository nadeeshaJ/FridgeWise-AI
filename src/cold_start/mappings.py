"""Cold-start ingredient mappings for unfamiliar items."""

from __future__ import annotations

COLD_START_MAPPINGS: dict[str, list[str]] = {
    "cassava": ["potato", "yam"],
    "tempeh": ["tofu"],
    "jackfruit": ["mushroom", "vegetable"],
    "miso": ["soy sauce", "fermented seasoning"],
    "pandan": ["vanilla", "coconut"],
    "kimchi": ["cabbage", "fermented vegetable"],
    "plantain": ["banana", "potato"],
    "quinoa": ["rice", "cereal"],
    "couscous": ["pasta", "rice"],
    "halloumi": ["cheese"],
    "nutritional yeast": ["cheese", "seasoning"],
    "seitan": ["tofu", "protein"],
    "gochujang": ["chili", "soy sauce"],
    "harissa": ["chili", "spice"],
    "tahini": ["sesame", "oil"],
    "aquafaba": ["egg"],
    "zucchini": ["courgette", "vegetable"],
    "aubergine": ["eggplant", "vegetable"],
}
