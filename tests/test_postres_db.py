import pandas as pd
from src.Postres.postres import engine

# 1. View the raw Apify data
df_raw = pd.read_sql("SELECT * FROM jobs_raw;", engine)
print("--- Raw Jobs Table ---")
print(df_raw.head())

# 2. View the processed features & extracted Ollama skills
df_features = pd.read_sql("SELECT * FROM job_features;", engine)
print("\n--- Job Features Table ---")
print(df_features[['id', 'title', 'company_name', 'skills']].head())
