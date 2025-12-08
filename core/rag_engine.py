import pandas as pd
from sentence_transformers import SentenceTransformer, util
import torch

from fetchers.workua_fetcher import fetch_workua_jobs
from fetchers.dou_fetcher import fetch_dou_jobs


class RAGJobRecommender:
    def __init__(self):
        self.embedder = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.jobs_df = None
        self.embeddings = None

    def ingest(self, query: str, limit: int = 50):
        jobs = []

        try:
            jobs.append(fetch_workua_jobs(query, limit))
        except Exception as e:
            print("work.ua fetch error:", e)

        try:
            jobs.append(fetch_dou_jobs(query))
        except Exception as e:
            print("dou fetch error:", e)

        df = pd.concat(jobs, ignore_index=True)
        df.drop_duplicates(subset=["title", "company"], inplace=True)

        if df.empty:
            return False

        df["description"] = df["description"].fillna("")
        df = df[df["description"] != ""]

        df["text"] = (
            "Title: " + df["title"].astype(str) + "\n" +
            "Company: " + df["company"].astype(str) + "\n" +
            df["description"].astype(str)
        )

        self.jobs_df = df.reset_index(drop=True)
        self.embeddings = self.embedder.encode(
            self.jobs_df["text"].tolist(),
            convert_to_tensor=True
        )
        return True

    def search(self, semantic_query: str, top_k: int = 20):
        if self.embeddings is None:
            return pd.DataFrame()

        q_emb = self.embedder.encode(
            semantic_query, convert_to_tensor=True
        )

        scores = util.cos_sim(q_emb, self.embeddings)[0]
        k = min(top_k, len(scores))
        values, indices = torch.topk(scores, k)

        rows = []
        for score, idx in zip(values, indices):
            job = self.jobs_df.iloc[int(idx)]

            match_pct = (score.item() + 1) / 2 * 100

            rows.append({
                "title": job["title"],
                "company": job.get("company", ""),
                "source": job.get("source", ""),
                "url": job.get("url", ""),
                "score": round(match_pct, 1),
            })

        return pd.DataFrame(rows)

recommender = RAGJobRecommender()