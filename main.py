from fetchers.workua_fetcher import fetch_workua_jobs
from fetchers.dou_fetcher import fetch_dou_jobs

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import pandas as pd
import re
import os

def clean_text(text):
    if not text:
        return ""
    
    text = str(text).lower().strip()

    allowed_chars_pattern = r"[^a-zA-Zа-яА-ЯіІїЇєЄ0-9\s]"
    text = re.sub(allowed_chars_pattern, "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()

def preprocess_jobs(df: pd.DataFrame):
    df["title_clean"] = df["title"].apply(clean_text)
    df["company_clean"] = df["company"].fillna("").apply(clean_text)
    df["description_clean"] = df["description"].fillna("").apply(clean_text)
    df["combined_text"] = (df["title_clean"] + " " + df["company_clean"] + " " + df["description_clean"]).str.strip()
    return df

def save_df(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)

def recommend_jobs(user_query: str, job_df: pd.DataFrame, top_k=10):
    vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
    job_vectors = vectorizer.fit_transform(job_df["combined_text"])
    user_vec = vectorizer.transform([user_query])
    sims = cosine_similarity(user_vec, job_vectors).flatten()
    job_df = job_df.copy()
    job_df["score"] = sims
    return job_df.sort_values("score", ascending=False).head(top_k)

def main():
    user_query = input("Enter job role / keywords: ").strip()
    if not user_query:
        
        print("Error: No query entered. Please provide job keywords to search for.")
        return

    print(f"Fetching jobs for query: {user_query}...")

    jobs_work = fetch_workua_jobs(user_query)
    jobs_dou = fetch_dou_jobs(user_query)

    jobs_all = pd.concat([jobs_work, jobs_dou], ignore_index=True)
    jobs_all.drop_duplicates(subset=["title", "company"], inplace=True)
    print(f"Total unique jobs fetched: {len(jobs_all)}")

    jobs_all = preprocess_jobs(jobs_all)

    recommended = recommend_jobs(user_query, jobs_all, top_k=50)

    print("\n=== Top recommended jobs ===")
    print(recommended[["title", "company", "source", "url", "score"]])

    os.makedirs("data", exist_ok=True)
    csv_path = f"data/recommended_jobs_{user_query.replace(' ', '_')}.csv"
    save_df(recommended, csv_path)
    print(f"Recommendations saved to {csv_path}")

if __name__ == "__main__":
    main()
