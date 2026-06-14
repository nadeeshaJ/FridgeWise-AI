# FridgeWise AI

A hybrid recipe recommendation system for food waste reduction using expiry dates, fridge ingredients, nutrition data, and personalized recipe suggestions.

**Course:** Recommender Systems group assignment  
**Goal:** Design, develop, and evaluate a hybrid recommender with baseline + improved models, offline evaluation (MAP, NDCG), cold-start handling, and Generative AI comparison.

---

## Project Overview

FridgeWise AI recommends recipes by considering:

1. Ingredients currently available in the user's fridge
2. Ingredients closest to expiry (food waste reduction)
3. User preferences and past recipe ratings
4. Nutrition information from barcode/product data (Open Food Facts)
5. Dietary and allergen constraints
6. Cold-start cases (new users, recipes, products, unfamiliar ingredients)

### Datasets

| Source | Purpose |
|--------|---------|
| [Food.com Recipes & Interactions](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions) | Recipe database, content-based + collaborative filtering, offline evaluation |
| [Food Expiry Tracker](https://www.kaggle.com/datasets/prekshad2166/food-expiry-tracker) | Expiry prioritisation, simulated fridge inventory |
| [Open Food Facts API](https://world.openfoodfacts.org/data) | Barcode lookup, nutrition, allergens, Nutri-Score |

**Integration note:** The three datasets do not share a common ID. Integration uses ingredient-level matching and product-to-ingredient mapping after cleaning, lowercasing, normalising, and standardising ingredient names.

---

## Architecture

```mermaid
flowchart TB
    subgraph Data["Phase 1–2: Data Layer"]
        FC[Food.com]
        EX[Expiry Tracker]
        OFF[Open Food Facts]
        FC --> Clean[Cleaning & Normalisation]
        EX --> Clean
        OFF --> Clean
        Clean --> DB[(fridge_recommender.db)]
        Clean --> CSV[7 CSV files]
    end

    subgraph Models["Phase 3–4: Models"]
        CB[Baseline: Content-Based]
        CF[Collaborative Filtering]
        HY[Hybrid Recommender]
        DB --> CB
        DB --> CF
        CB --> HY
        CF --> HY
    end

    subgraph Eval["Phase 5: Evaluation"]
        HY --> Metrics[P@K, R@K, MAP@K, NDCG@K, RMSE]
        CB --> Metrics
        CF --> Metrics
    end

    subgraph Report["Phase 6–7: Report & Demo"]
        Metrics --> ReportDoc[3,000-word report]
        HY --> Flutter[Optional Flutter app]
    end
```

---

## Repository Structure

```
FridgeWise-AI/
├── data/
│   ├── raw/              # Downloaded Kaggle datasets (gitignored)
│   ├── processed/        # 7 clean CSV files
│   └── fridge_recommender.db
├── src/
│   ├── preprocessing/
│   │   ├── ingredient_utils.py    # normalisation, synonym mapping
│   │   ├── clean_recipes.py
│   │   ├── clean_interactions.py
│   │   ├── clean_expiry.py
│   │   ├── fetch_open_food_facts.py
│   │   ├── build_fridge_inventory.py
│   │   └── build_integrated_dataset.py
│   ├── models/
│   │   ├── content_based.py
│   │   ├── collaborative_filtering.py
│   │   └── hybrid_recommender.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   └── evaluate.py
│   └── cold_start/
│       └── ingredient_mappings.py
├── notebooks/
│   ├── 01_exploration.ipynb
│   └── 02_evaluation_results.ipynb
├── config/
│   └── config.yaml
├── requirements.txt
├── README.md
└── report/               # Outline / figures (final report written in own words)
```

---

## Expected Data Outputs

### Clean CSV files

1. `clean_recipes.csv`
2. `clean_interactions.csv`
3. `clean_expiry_items.csv`
4. `clean_open_food_products.csv`
5. `user_fridge_inventory.csv`
6. `recipe_ingredient_features.csv`
7. `final_recommendation_dataset.csv`

### SQLite database: `fridge_recommender.db`

Tables: `recipes`, `interactions`, `expiry_items`, `open_food_products`, `user_fridge_inventory`, `recipe_ingredient_features`, `final_recommendation_dataset`

---

## Build Plan (Step by Step)

### Phase 0: Setup

| Step | Task | Output |
|------|------|--------|
| 0.1 | Create `requirements.txt` (pandas, numpy, scikit-learn, surprise, requests, etc.) | Dependencies |
| 0.2 | Download Food.com + Expiry Tracker from Kaggle | `data/raw/` |
| 0.3 | Set up project folders and `.gitignore` for raw data | Clean repo |
| 0.4 | Define `ingredient_utils.py` with normalisation rules | Shared utility |

Ingredient normalisation is the foundation — build this first:

- Lowercase, strip punctuation, remove extra spaces
- Lemmatisation (`tomatoes` → `tomato`)
- Synonym dictionary (`cheddar cheese` → `cheese`, `Greek yogurt` → `yogurt`)
- Cold-start mappings (`tempeh` → `tofu`, `cassava` → `potato`, etc.)

---

### Phase 1: Clean Individual Datasets

#### Step 1.1 — `clean_recipes.csv` → `recipes` table

- Load `RAW_recipes.csv`
- Parse ingredient lists (stringified Python lists)
- Apply normalisation → `cleaned_ingredients`
- Extract `dietary_tags`, `cuisine_tags`, `difficulty_level` from tags
- **Checkpoint:** spot-check 20 recipes manually

#### Step 1.2 — `clean_interactions.csv` → `interactions` table

- Filter valid ratings (1–5), drop nulls
- Inner join on valid `recipe_id`
- Generate `interaction_id`
- **Checkpoint:** interaction count before/after filtering

#### Step 1.3 — `clean_expiry_items.csv` → `expiry_items` table

- Clean ingredient names
- Compute `days_to_expiry` and `expiry_priority_score`:

  | days_to_expiry | expiry_priority_score |
  |----------------|----------------------|
  | ≤ 0 | 1.0 |
  | ≤ 2 | 0.9 |
  | ≤ 5 | 0.7 |
  | ≤ 10 | 0.5 |
  | otherwise | 0.2 |

#### Step 1.4 — `clean_open_food_products.csv` → `open_food_products` table

- Fetch ~50–100 products from Open Food Facts API (cache responses locally)
- Map to `generic_ingredient_name` (e.g. Cheddar Cheese → cheese)
- Compute `nutrition_score` (start 1.0; subtract for high sugar/sat fat/salt; add for protein/fibre; clamp 0–1)

#### Step 1.5 — `user_fridge_inventory.csv` → `user_fridge_inventory` table

- Synthetically generate 20–50 sample users
- Use common Food.com ingredients + cold-start items (miso, tempeh, kimchi, etc.)
- Link some rows to Open Food Facts barcodes

---

### Phase 2: Integration & Feature Engineering

#### Step 2.1 — `recipe_ingredient_features.csv`

- Explode recipes to one row per ingredient
- Match with expiry and nutrition data via `cleaned_ingredient_name`
- Add `is_expiry_matched`, `avg_expiry_priority_score`, `avg_nutrition_score`

#### Step 2.2 — `final_recommendation_dataset.csv`

For each `(user_id, recipe_id)` pair:

- `fridge_ingredients`, `matched_ingredients`, `missing_ingredients`
- `ingredient_match_score` = matched / total recipe ingredients
- Aggregated expiry + nutrition scores
- `predicted_rating`, `final_hybrid_score`, `cold_start_flag`

#### Step 2.3 — SQLite database

- Load all 7 tables into `fridge_recommender.db`
- Add indexes on `recipe_id`, `user_id`, `cleaned_ingredient_name`

**Prototype tip:** Use a subset of Food.com (e.g. top 10k recipes by interaction count) during development.

---

### Phase 3: Recommender Models

#### Model 1: Baseline Content-Based Filtering

- TF-IDF or CountVectorizer on `cleaned_ingredients` (+ optional tags)
- Cosine similarity between fridge ingredients and recipe ingredients
- Rank by `ingredient_match_score`

#### Model 2: Collaborative Filtering

- Train/test split on interactions (80/20)
- SVD / matrix factorisation (Surprise library)
- Output `predicted_rating`; evaluate RMSE

#### Model 3: Hybrid Recommender (Improved)

```
final_hybrid_score =
  0.35 * ingredient_match_score
+ 0.30 * predicted_rating_normalized
+ 0.20 * expiry_priority_score
+ 0.15 * nutrition_score
```

**Cold-start fallback** (new user, no CF prediction):

```
final_hybrid_score =
  0.50 * ingredient_match_score
+ 0.30 * expiry_priority_score
+ 0.20 * nutrition_score
```

---

### Phase 4: Evaluation

| Metric | Applies to |
|--------|------------|
| Precision@K, Recall@K | All three models |
| MAP@K, NDCG@K | All three models |
| RMSE | CF + Hybrid |

**Protocol:**

1. Split interactions → train / test
2. Train CF on train set
3. For each test user, generate top-N recommendations
4. Compare against held-out positive interactions (rating ≥ 4)
5. Evaluate at K = 5 and K = 10
6. Compare: Baseline vs CF vs Hybrid

---

### Phase 5: Cold-Start & Robustness

| Scenario | Detection | Fallback |
|----------|-----------|----------|
| New user | No interactions | Cold-start hybrid formula |
| New recipe | No interactions | Content-based only |
| New barcode product | Unknown barcode | Map via Open Food Facts → generic ingredient |
| Unfamiliar ingredient | Not in training vocab | Category/cuisine similarity + manual mapping |

**Scalability / robustness topics for report:**

- Reduce dataset size for prototype development
- Sparse matrices for user-item interactions
- Cache Open Food Facts API responses
- Normalise ingredient names to reduce mismatch errors
- Default/average scores for missing nutrition values

---

### Phase 6: Report & Presentation

Recommended report structure (~3,000 words):

1. Introduction
2. Problem Statement
3. Dataset Description
4. Data Preprocessing and Feature Engineering
5. System Design
6. Baseline Content-Based Recommender
7. Collaborative Filtering Recommender
8. Hybrid Recommender
9. Evaluation Methodology
10. Results and Comparison
11. Cold-Start Mitigation
12. Generative AI Analysis
13. Responsible AI and Limitations
14. Conclusion
15. References
16. Appendix

**Generative AI section** (discussion only — no implementation required):

- VAE-based recommender (latent taste preferences)
- GAN-based recipe generation (creative combinations from leftovers)
- LLM-based assistant (explanations, substitutions, dietary adaptation)
- GenAI for unfamiliar ingredients (cultural substitutions)

Compare traditional ranking vs generative approaches; note hallucination, nutrition inaccuracy, and safety risks.

**Responsible AI topics:** allergen safety, nutrition misinformation, cultural bias, privacy, over-personalisation, transparency.

---

### Phase 7: Optional Flutter Prototype

If time allows — demonstration layer only; recommender + evaluation + report remain priority.

| Screen | Features |
|--------|----------|
| Fridge Inventory | Add ingredient, expiry date, quantity, barcode |
| Barcode/Nutrition | Scan/enter barcode; show nutrition and allergens |
| Recipe Recommendations | Top recipes, match %, expiring ingredients used, nutrition score, missing ingredients |
| Recipe Detail | Ingredients, steps, cooking time, "Why this recipe was recommended" |

---

## Build Order Summary

| Order | Step | Why first |
|-------|------|-----------|
| 1 | Project setup + `requirements.txt` + folder structure | Foundation |
| 2 | `ingredient_utils.py` (normalisation + synonyms) | Everything depends on this |
| 3 | Clean recipes + interactions | Core Food.com data |
| 4 | Clean expiry + fetch Open Food Facts sample | Secondary sources |
| 5 | Synthetic fridge inventory | Enables end-to-end demo |
| 6 | Bridge + final dataset + SQLite | Single modelling source |
| 7 | Baseline content-based model | Quick win, baseline metrics |
| 8 | Collaborative filtering (SVD) | Personalisation layer |
| 9 | Hybrid model + cold-start logic | Main contribution |
| 10 | Evaluation notebook + results tables | Assignment requirement |
| 11 | Report sections + optional Flutter | Deliverables |

---

## Final Deliverables

1. Group report (max 3,000 words, written in own words)
2. Python notebook or GitHub repository with all code
3. Final cleaned CSV files and/or SQLite database
4. Group presentation (10–15 minutes)
5. Optional Flutter app prototype or screenshots

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Ingredient matching errors | Invest in synonym dictionary; log unmatched ingredients |
| Large dataset size | Use filtered subset for dev; full set for final eval if feasible |
| No shared IDs across datasets | Document as limitation; rely on normalised ingredient matching |
| Open Food Facts API limits | Cache responses locally |
| Report originality | Use this plan for structure; write final report in group's own words |

---

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Download datasets to `data/raw/`
4. Begin with **Phase 0** — project setup and `ingredient_utils.py`

---

## License

Academic project — see course guidelines for usage and attribution.
