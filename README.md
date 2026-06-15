# FridgeWise AI

A hybrid recipe recommendation system that helps reduce household food waste by suggesting recipes based on what is in your fridge, which ingredients expire soon, user taste preferences, and nutrition data from packaged products.

FridgeWise combines **collaborative filtering**, **content-based ingredient matching**, **expiry-aware re-ranking**, and **nutrition scoring** into a single hybrid recommender, exposed through a **FastAPI backend** and a **Flutter mobile app**.

**Project status:** Core pipeline, models, evaluation, API, mobile app, tests, Docker, and CI are complete and ready for demo.

---

## Features

- **Fridge-aware recommendations** — ranks recipes by how well they match ingredients you already have
- **Expiry prioritisation** — boosts recipes that use items close to their use-by date
- **Personalised suggestions** — item-based KNN collaborative filtering on Food.com ratings
- **Nutrition & allergen awareness** — Open Food Facts barcode lookup for packaged products
- **Cold-start support** — fallback ranking for new users and unfamiliar ingredients (`src/cold_start/`)
- **Offline evaluation** — MAP@K, NDCG@K, Precision@K, Recall@K, and RMSE across three model variants
- **Mobile app** — Flutter prototype with fridge CRUD, barcode camera scan, configurable API URL for physical devices

---

## Architecture

```mermaid
flowchart TB
    subgraph Data["Data Layer"]
        FC[Food.com Recipes & Interactions]
        EX[Food Expiry Tracker]
        OFF[Open Food Facts]
        FC --> Clean[Cleaning & Normalisation]
        EX --> Clean
        OFF --> Clean
        Clean --> CSV[Processed CSVs]
        Clean --> DB[(fridge_recommender.db)]
    end

    subgraph Models["Recommendation Engine"]
        CB[Content-Based TF-IDF]
        CF[Collaborative Filtering KNN]
        HY[Hybrid Recommender]
        CB --> HY
        CF --> HY
    end

    subgraph Eval["Evaluation"]
        HY --> Metrics[MAP NDCG P@K R@K RMSE]
        CB --> Metrics
        CF --> Metrics
    end

    subgraph App["Application Layer"]
        API[FastAPI Backend]
        FL[Flutter App]
        HY --> API --> FL
    end

    DB --> Models
    Metrics --> API
```

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Data processing | Python, Pandas, NumPy |
| Machine learning | scikit-learn, Surprise (KNN + SVD) |
| Storage | SQLite, CSV |
| API | FastAPI, Uvicorn |
| Mobile | Flutter, Dart, mobile_scanner, shared_preferences |
| DevOps | Docker, GitHub Actions, pytest |
| External data | Kaggle datasets, [Open Food Facts API](https://openfoodfacts.github.io/openfoodfacts-server/api/tutorial-off-api/) |

---

## Repository Structure

```
FridgeWise-AI/
├── api/
│   ├── main.py                      # FastAPI recommendation service
│   └── fridge_store.py              # In-memory fridge CRUD for the app
├── config/
│   ├── config.yaml                  # Paths, model weights, evaluation settings
│   └── cf_best.json                 # Tuned CF hyperparameters (KNN k=40)
├── data/
│   ├── raw/                         # Raw Kaggle downloads (gitignored)
│   ├── processed/                   # Cleaned CSVs, charts, evaluation results
│   └── cache/                       # Cached API responses (gitignored)
├── flutter_app/
│   ├── android/                     # Android platform (HTTP + camera permissions)
│   ├── ios/                         # iOS platform
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/                 # Home, fridge, recommendations, barcode, recipe
│   │   ├── services/                # api_service.dart, api_config.dart
│   │   └── widgets/                 # ApiScope, error handling, settings sheet
│   └── pubspec.yaml
├── notebooks/
│   ├── data_exploration.ipynb
│   └── evaluation_results.ipynb
├── scripts/
│   ├── build_dataset.py             # End-to-end data pipeline
│   ├── train_and_evaluate.py        # Tune CF + run offline evaluation
│   ├── plot_evaluation_results.py   # Export metric charts as PNG
│   ├── setup_flutter.ps1            # Generate platform folders
│   ├── run_demo.ps1                 # Start API for physical device testing
│   ├── log_unmatched_ingredients.py
│   ├── refresh_open_food_facts.py
│   ├── download_data.py
│   └── verify_database.py
├── src/
│   ├── preprocessing/               # Cleaning, normalisation, dataset builders
│   ├── models/                      # Content-based, CF, hybrid, tune_cf
│   ├── cold_start/                  # Cold-start mappings & resolver
│   └── evaluation/                  # metrics.py, evaluate.py
├── tests/                           # pytest unit tests
├── .github/workflows/ci.yml         # CI: pytest + API import check
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Datasets

| Source | Purpose |
|--------|---------|
| [Food.com Recipes & Interactions](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions) | Recipe catalogue, user ratings, collaborative filtering, offline evaluation |
| [Food Expiry Tracker](https://www.kaggle.com/datasets/prekshad2166/food-expiry-tracker) | Expiry prioritisation and food-waste reduction signals |
| [Open Food Facts](https://world.openfoodfacts.org/data) | Barcode lookup, nutrition values, allergens, Nutri-Score |

**Integration:** The three sources do not share a common ID. FridgeWise links them through **ingredient-level matching** — names are cleaned, lowercased, normalised, and mapped to canonical forms before joining (see `src/preprocessing/ingredient_utils.py` and `src/cold_start/`).

**Example normalisations:**

| Raw | Normalised |
|-----|------------|
| tomatoes | tomato |
| cheddar cheese | cheese |
| Greek yogurt | yogurt |
| whole wheat pasta | pasta |
| boneless chicken breasts | chicken |

---

## Data Outputs

Running the pipeline produces processed CSV files, evaluation artefacts, and one SQLite database.

### CSV files (`data/processed/`)

| File | Description |
|------|-------------|
| `clean_recipes.csv` | Parsed ingredients, dietary/cuisine tags, difficulty |
| `clean_interactions.csv` | Filtered Food.com ratings (1–5) |
| `clean_interactions_train.csv` | Training split for CF |
| `clean_interactions_validation.csv` | Validation split for hyperparameter tuning |
| `clean_interactions_test.csv` | Test split for final metrics |
| `clean_expiry_items.csv` | Expiry items with priority scores |
| `clean_open_food_products.csv` | Cached Open Food Facts products |
| `user_fridge_inventory.csv` | Synthetic fridge inventories (demo users) |
| `recipe_ingredient_features.csv` | Recipe–ingredient bridge with expiry/nutrition features |
| `final_recommendation_dataset.csv` | User–recipe modelling dataset with hybrid scores |
| `evaluation_results.json` | Offline metric results for all three models |
| `unmatched_ingredients_report.csv` | Ingredient matching diagnostics |
| `charts/` | PNG charts from `plot_evaluation_results.py` |

### SQLite database (`data/fridge_recommender.db`)

Tables: `recipes`, `interactions`, `expiry_items`, `open_food_products`, `user_fridge_inventory`, `recipe_ingredient_features`, `final_recommendation_dataset`

---

## Quick Start

Minimal path to a working demo (assumes processed data is already in the repo):

```bash
pip install -r requirements.txt
python api/main.py
```

In a second terminal:

```powershell
cd flutter_app
flutter pub get
flutter run
```

For a **physical phone**, use `.\scripts\run_demo.ps1` instead of `python api/main.py`, then set your PC LAN IP in the app Settings screen.

---

## Getting Started (full setup)

### Prerequisites

- Python 3.10+
- [Kaggle API credentials](https://www.kaggle.com/docs/api) (for dataset download)
- [Flutter SDK](https://docs.flutter.dev/get-started/install) 3.10+ (for mobile app)
- Docker (optional, for containerised API)

### Installation

```bash
git clone https://github.com/nadeeshaJ/FridgeWise-AI.git
cd FridgeWise-AI
pip install -r requirements.txt
```

### 1. Download raw data

```bash
python scripts/download_data.py
```

Place manually if needed:
- `data/raw/RAW_recipes.csv`
- `data/raw/RAW_interactions.csv`
- `data/raw/interactions_train.csv`, `interactions_validation.csv`, `interactions_test.csv`
- `data/raw/food_expiry_tracker.csv`

### 2. Build the integrated dataset

```bash
python scripts/build_dataset.py
python scripts/verify_database.py
```

### 3. Train and evaluate recommenders

```bash
python scripts/train_and_evaluate.py
```

Results are written to `data/processed/evaluation_results.json`.

Generate report charts:

```bash
python scripts/plot_evaluation_results.py
```

Charts are saved to `data/processed/charts/`. For interactive exploration, open `notebooks/evaluation_results.ipynb`.

Run unit tests:

```bash
python -m pytest tests/ -q
```

CI runs the same tests on every push to `main` (see `.github/workflows/ci.yml`).

### 4. Run the API

```bash
python api/main.py
```

For physical device testing (binds to all network interfaces):

```powershell
.\scripts\run_demo.ps1
```

API runs at `http://localhost:8000`. Endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/demo-users` | List available demo user IDs |
| GET | `/users/{id}/fridge` | Fridge inventory for a user |
| POST | `/users/{id}/fridge/items` | Add a fridge item |
| PUT | `/users/{id}/fridge/items/{inventory_id}` | Update a fridge item |
| DELETE | `/users/{id}/fridge/items/{inventory_id}` | Remove a fridge item |
| POST | `/users/{id}/fridge/from-barcode` | Add item from Open Food Facts barcode |
| GET | `/users/{id}/recommendations?top_k=10` | Hybrid recipe recommendations |
| GET | `/recipes/{id}` | Full recipe details |
| GET | `/products/{barcode}` | Open Food Facts product lookup |

Fridge edits are stored in memory for the running API session and immediately affect hybrid recommendations.

### 5. Run the Flutter app

Platform folders (`android/`, `ios/`, etc.) are included in the repo. If you need to regenerate them:

```powershell
.\scripts\setup_flutter.ps1
```

Run the app:

```bash
cd flutter_app
flutter pub get
flutter run
```

**Physical device on the same Wi‑Fi:**

1. Start the API: `.\scripts\run_demo.ps1`
2. Find your PC IPv4 address: `ipconfig` (e.g. `192.168.1.42`)
3. In the app, tap the **Settings** gear → choose **Physical device (LAN)** → enter `http://192.168.1.42:8000` → **Test connection** → **Save**
4. Allow Python through Windows Firewall if prompted

| Environment | Default API URL |
|-------------|-----------------|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator / desktop | `http://127.0.0.1:8000` |
| Physical phone | `http://<your-pc-lan-ip>:8000` |

The app auto-selects the platform default on first launch; saved URLs persist via `shared_preferences`.

Demo users: `10001`–`10040` (synthetic fridges with mixed expiry dates and cold-start ingredients). These users use **cold-start mode** in the app — recommendations are based on fridge contents, expiry, and nutrition rather than Food.com rating history.

See also: [`flutter_app/README.md`](flutter_app/README.md)

### 6. Docker (optional)

Run the API in a container (requires `data/processed/` CSVs present):

```bash
docker compose up --build
```

API available at `http://localhost:8000`. Processed data is mounted read-only from `data/processed/`.

### Utility scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_flutter.ps1` | Generate/repair Flutter platform folders + dev permissions |
| `scripts/run_demo.ps1` | Start API on `0.0.0.0:8000` for phone testing |
| `scripts/log_unmatched_ingredients.py` | Report fridge ingredients with weak recipe/product matches |
| `scripts/refresh_open_food_facts.py` | Re-fetch Open Food Facts product cache |
| `scripts/plot_evaluation_results.py` | Export evaluation charts as PNG |
| `scripts/test_api_fridge.py` | Smoke-test fridge CRUD endpoints |

---

## Data Pipeline

The pipeline is orchestrated by `scripts/build_dataset.py` in nine stages:

| Stage | Script / module | Output |
|-------|-----------------|--------|
| 1 | `download_data.py` | Raw files in `data/raw/` |
| 2 | `clean_recipes.py` | `clean_recipes.csv` |
| 3 | `clean_interactions.py` | `clean_interactions.csv` |
| 3b | `clean_interaction_splits.py` | `clean_interactions_{train,val,test}.csv` |
| 4 | `clean_expiry.py` | `clean_expiry_items.csv` |
| 5 | `fetch_open_food_facts.py` | `clean_open_food_products.csv` |
| 6 | `build_fridge_inventory.py` | `user_fridge_inventory.csv` |
| 7 | `build_integrated_dataset.py` | `recipe_ingredient_features.csv`, `final_recommendation_dataset.csv` |
| 8 | `build_database.py` | `fridge_recommender.db` |

Adjust subset sizes and weights in `config/config.yaml`.

---

## Preprocessing Details

### Recipes (`clean_recipes.csv`)

- Parse Food.com ingredient lists (stringified Python lists)
- Normalise ingredient names via `ingredient_utils.py`
- Extract `dietary_tags`, `cuisine_tags`, `difficulty_level` from recipe tags
- Columns: `recipe_id`, `recipe_name`, `minutes`, `cleaned_ingredients`, `tags`, etc.

### Interactions

- Keep ratings 1–5; drop rows with missing `user_id`, `recipe_id`, or `rating`
- Inner join on valid `recipe_id` from the recipes table
- Preserve official train / validation / test splits from Food.com

### Expiry items (`clean_expiry_items.csv`)

The Food Expiry Tracker uses a **one-hot schema** (`item_dairy`, `item_vegetable`, `storage_fridge`, `days_until_expiry`, etc.). The cleaner:

1. Derives category and representative ingredient from one-hot flags
2. Maps storage flags to `fridge`, `freezer`, or `pantry`
3. Converts normalised `days_until_expiry` (0–1) to calendar days using category shelf-life
4. Computes `expiry_priority_score`:

| days_to_expiry | expiry_priority_score |
|----------------|----------------------|
| ≤ 0 | 1.0 |
| ≤ 2 | 0.9 |
| ≤ 5 | 0.7 |
| ≤ 10 | 0.5 |
| otherwise | 0.2 |

### Open Food Facts products

- Fetches products by category search and known barcodes
- Caches responses in `data/cache/open_food_facts_cache.json`
- Maps product names to `generic_ingredient_name` (e.g. Cheddar → cheese)
- Computes `nutrition_score` (penalises high sugar/sat fat/salt; rewards protein/fibre)

### Fridge inventory

- Generates 40 synthetic users (`10001`–`10040`)
- Samples common Food.com ingredients plus cold-start items (`miso`, `tempeh`, `kimchi`, `plantain`, etc.)
- Links ~30% of items to Open Food Facts barcodes

### Ingredient normalisation

Foundation for all matching (`ingredient_utils.py` + `src/cold_start/`):

- Lowercase, strip punctuation, remove quantity prefixes
- 100+ synonym mappings (`cheddar cheese` → `cheese`, `olive oil` → `oil`)
- Simple plural handling (`tomatoes` → `tomato`)
- Cold-start substitute expansion (`tempeh` → `tofu`, `quinoa` → `rice`)

---

## Recommender Models

### Model 1 — Content-Based Filtering (Baseline)

**Method:** TF-IDF vectorisation on `cleaned_ingredients` combined with ingredient overlap score.

**Use cases:**
- Rank recipes against a user's fridge contents (app)
- Rank against a taste profile built from highly rated recipes (offline evaluation)
- Strong when no interaction history exists (new recipes, cold-start users)

**Implementation:** `src/models/content_based.py`

---

### Model 2 — Collaborative Filtering

**Method:** Item-based KNN (cosine similarity on the user–item matrix), selected after validation tuning. SVD is also supported as an alternative.

**Output:** Predicted rating per user–recipe pair.

**Tuning:** `src/models/tune_cf.py` compares KNN and SVD on the validation split, optimising hit-rate@10 (ranking) alongside RMSE. Best config is saved to `config/cf_best.json` and loaded by the API.

**Selected model:** item-based KNN with `k=40` (validation hit@10 = 0.60, validation RMSE ≈ 0.90).

**Implementation:** `src/models/collaborative_filtering.py`, `src/models/tune_cf.py`

---

### Model 3 — Hybrid Recommender

Combines all signals into a single ranking score. This is the **production model** used by the API and Flutter app.

**Standard formula:**

```
final_hybrid_score =
  0.35 × ingredient_match_score
+ 0.30 × predicted_rating_normalised
+ 0.20 × expiry_priority_score
+ 0.15 × nutrition_score
```

**Cold-start formula** (user with no rating history — all demo app users):

```
final_hybrid_score =
  0.50 × ingredient_match_score
+ 0.30 × expiry_priority_score
+ 0.20 × nutrition_score
```

Weights are configurable in `config/config.yaml`.

**Implementation:** `src/models/hybrid_recommender.py`

---

## Evaluation

### Splits

| Split | File | Use |
|-------|------|-----|
| Train | `clean_interactions_train.csv` | Fit CF and build content profiles |
| Validation | `clean_interactions_validation.csv` | Tune hyperparameters |
| Test | `clean_interactions_test.csv` | Report final metrics |

### Metrics

| Metric | Description |
|--------|-------------|
| **MAP@K** | Mean Average Precision at K |
| **NDCG@K** | Normalised Discounted Cumulative Gain at K |
| **Precision@K** | Fraction of top-K recommendations that are relevant |
| **Recall@K** | Fraction of relevant items found in top-K |
| **RMSE** | Root Mean Square Error for CF rating prediction |

Evaluated at **K = 5** and **K = 10** for all three models. Positive interactions defined as rating ≥ 4.

### Protocol

1. Train CF on the train split; tune KNN vs SVD on validation (`scripts/train_and_evaluate.py` step 1)
2. For each test user, rank held-out positive recipes against sampled negatives
3. Compare content-based, CF, and hybrid recommendation lists
4. Save results to `data/processed/evaluation_results.json`

**Hybrid offline protocol:** CF-first rank fusion — CF top-K list merged with content-based hits so collaborative signal is preserved while content can surface additional relevant recipes.

```bash
python scripts/train_and_evaluate.py
```

### Latest results (test split, 30 users, LOO)

| Model | P@5 | R@5 | MAP@5 | NDCG@5 | P@10 | R@10 |
|-------|-----|-----|-------|--------|------|------|
| Content-based | 0.007 | 0.033 | 0.033 | 0.033 | 0.003 | 0.033 |
| Collaborative filtering | 0.113 | 0.567 | 0.517 | 0.530 | 0.057 | 0.567 |
| **Hybrid** | **0.120** | **0.600** | **0.550** | **0.563** | **0.060** | **0.600** |

CF rating prediction: test RMSE ≈ **0.93** (KNN, k=40).

Leave-one-out evaluation produces conservative absolute scores; compare models relatively. Content-based acts as a cold-start baseline; hybrid improves on CF by blending content signals without degrading collaborative ranking.

---

## Cold-Start Handling

| Scenario | Detection | Strategy |
|----------|-----------|----------|
| **New user** | No interaction history | Cold-start hybrid formula (fridge + expiry + nutrition only) |
| **New recipe** | No ratings in training data | Content-based features (ingredients, tags, cook time) |
| **New barcode product** | Unknown barcode | Map via Open Food Facts → generic ingredient |
| **Unfamiliar ingredient** | Not in training vocabulary | Synonym / substitute mapping in `src/cold_start/` |

**Example cold-start ingredient mappings** (`src/cold_start/mappings.py`):

| Ingredient | Mapped to |
|------------|-----------|
| tempeh | tofu |
| cassava | potato |
| miso | soy sauce |
| kimchi | cabbage |
| plantain | banana / potato |
| quinoa | rice / cereal |

---

## Mobile App

The Flutter app (`flutter_app/`) is a functional prototype connected to the FastAPI backend. Android and iOS platform folders are included; HTTP cleartext and camera permissions are pre-configured for local development.

| Screen | Description |
|--------|-------------|
| **Home** | Select demo user; API settings (gear icon); cold-start info banner |
| **Fridge Inventory** | View, add, edit, and delete items; pull-to-refresh; colour-coded expiry urgency |
| **Recommendations** | Top hybrid-ranked recipes with match % and scores; pull-to-refresh |
| **Recipe Detail** | Ingredients, steps, cook time, explanation of why it was recommended |
| **Barcode / Nutrition** | Camera scan or manual barcode entry; nutrition/allergens; add to fridge |
| **API Settings** | Presets for emulator/desktop/LAN; test connection; persisted URL |

---

## Configuration

Key settings in `config/config.yaml`:

```yaml
food_com:
  max_recipes: 50000          # Subset for faster prototyping; set null for full dataset

fridge_inventory:
  num_users: 40
  reference_date: "2026-06-14"

collaborative_filtering:
  default:
    algorithm: knn_item
    params:
      k: 40

hybrid_weights:
  ingredient_match: 0.35
  predicted_rating: 0.30
  expiry_priority: 0.20
  nutrition: 0.15

evaluation:
  k_values: [5, 10]
  max_eval_users: 30
  min_rating_for_positive: 4
```

---

## Project Status

| Area | Status |
|------|--------|
| Data pipeline | Complete |
| Expiry integration | Complete |
| Content-based model | Complete |
| Collaborative filtering (KNN k=40) | Complete |
| Hybrid model | Complete |
| Offline evaluation | Complete — hybrid MAP@5 0.55, NDCG@5 0.56 |
| FastAPI backend + fridge CRUD | Complete |
| Flutter app (emulator + physical device) | Complete |
| Ingredient matching + cold-start module | Complete |
| Unit tests + CI | Complete |
| Evaluation charts + notebooks | Complete |
| Docker | Complete |

**Optional future work:** full Food.com dataset, user authentication, persistent fridge storage, production HTTPS deployment.

---

## Known Limitations

- **Ingredient matching** — fuzzy normalisation reduces but does not eliminate mismatch errors between datasets
- **Synthetic fridges** — demo users (`10001`–`10040`) are generated; not linked to real Food.com user IDs
- **In-memory fridge edits** — API fridge CRUD resets when the server restarts
- **Open Food Facts API** — subject to rate limits and outages; products are cached locally
- **Evaluation difficulty** — leave-one-out test set makes absolute MAP/NDCG scores conservative; compare models relatively
- **Nutrition score** — simplified heuristic; not a substitute for dietary or medical advice

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with clear commit messages
4. Run `python -m pytest tests/ -q` and `python scripts/train_and_evaluate.py` to verify
5. Open a pull request

---

## License

This project is provided for educational and research purposes. Dataset licenses apply to Food.com, Food Expiry Tracker, and Open Food Facts data respectively.
