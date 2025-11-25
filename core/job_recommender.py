import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from fetchers.workua_fetcher import fetch_workua_jobs
from fetchers.dou_fetcher import fetch_dou_jobs


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9а-яіїє\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_skills(skills: str | None) -> list[str]:
    if not skills:
        return []
    return [s.strip().lower() for s in skills.split(",") if s.strip()]


def build_queries(title: str | None, skills: str | None):
    title = (title or "").strip()
    skills = (skills or "").strip()

    if not title and not skills:
        raise ValueError("Title or skills required")

    workua_query = title or skills.split(",")[0]
    workua_query = " ".join(workua_query.split()[:2])

    semantic_query = " ".join([title, skills]).strip()

    return workua_query, semantic_query


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    for col in ["title", "company", "description"]:
        if col not in df.columns:
            df[col] = ""

    df = df.copy()
    df["title_norm"] = df["title"].apply(normalize)
    df["desc_norm"] = df["description"].apply(normalize)
    return df


def title_score(job_title: str, target_title: str) -> float:
    if not target_title:
        return 0.0
    a = set(job_title.split())
    b = set(target_title.split())
    return len(a & b) / max(len(b), 1)


def skill_score(text: str, skills: list[str]) -> float:
    if not skills:
        return 0.0
    hits = sum(1 for s in skills if s in text)
    return hits / len(skills)


def semantic_scores(texts: list[str], query: str) -> list[float]:
    if not query.strip():
        return [0.0] * len(texts)

    vec = TfidfVectorizer(max_features=1200, stop_words="english")
    X = vec.fit_transform(texts)
    q = vec.transform([query])
    return cosine_similarity(q, X).flatten().tolist()

def recommend_jobs(
    title: str | None = None,
    skills: str | None = None,
    top_k: int = 30
) -> pd.DataFrame:

    workua_q, semantic_q = build_queries(title, skills)
    skills_list = parse_skills(skills)

    frames = []

    try:
        df = fetch_workua_jobs(workua_q)
        if not df.empty:
            frames.append(df)
    except Exception:
        pass

    try:
        df = fetch_dou_jobs(semantic_q)
        if not df.empty:
            frames.append(df)
    except Exception:
        pass

    if not frames:
        return pd.DataFrame()

    jobs = pd.concat(frames, ignore_index=True)
    jobs.drop_duplicates(subset=["title", "company"], inplace=True)
    jobs = preprocess(jobs)
    jobs = jobs.reset_index(drop=True)

    sem = semantic_scores(
        jobs["title_norm"] + " " + jobs["desc_norm"],
        semantic_q
    )

    raw_scores = []
    for i, row in jobs.iterrows():
        s = (
            0.45 * title_score(row["title_norm"], normalize(title or "")) +
            0.45 * skill_score(row["desc_norm"], skills_list) +
            0.10 * sem[i]
        )
        raw_scores.append(s)

    jobs["raw_score"] = raw_scores

    final_frames = []

    for source, group in jobs.groupby("source"):
        max_s = group["raw_score"].max()
        if max_s <= 0:
            group["score"] = 0.0
        else:
            group["score"] = (group["raw_score"] / max_s) * 100.0
        final_frames.append(group)

    jobs = pd.concat(final_frames)

    return (
        jobs
        .sort_values("score", ascending=False)
        .head(top_k)
        .drop(columns=["raw_score"])
    )
