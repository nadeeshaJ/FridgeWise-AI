import sqlite3

import pandas as pd

conn = sqlite3.connect("data/fridge_recommender.db")
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
print("Tables:", tables["name"].tolist())
for t in tables["name"]:
    n = pd.read_sql(f"SELECT COUNT(*) as n FROM {t}", conn).iloc[0]["n"]
    print(f"  {t}: {n} rows")

sample = pd.read_sql(
    """
    SELECT user_id, recipe_name, ingredient_match_score, expiry_priority_score,
           nutrition_score, final_hybrid_score, cold_start_flag
    FROM final_recommendation_dataset
    ORDER BY final_hybrid_score DESC
    LIMIT 5
    """,
    conn,
)
print("\nTop 5 hybrid scores:")
print(sample.to_string(index=False))
conn.close()
