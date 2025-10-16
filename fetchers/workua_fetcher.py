import requests
from bs4 import BeautifulSoup
import pandas as pd
from fetchers.headers import get_headers


def fetch_workua_jobs(query: str, count: int = 30):
    base_url = "https://www.work.ua/jobs-"
    query_slug = query.lower().replace(" ", "-")
    url = f"{base_url}{query_slug}/"

    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"[work.ua] Fetch error: {e}")
        return pd.DataFrame()

    jobs = []
    for job_div in soup.select("div.job-link")[:count]:
        title_tag = job_div.select_one("h2 > a")
        company_tag = job_div.select_one("div.add-top-xs span")

        title = title_tag.text.strip() if title_tag else ""
        company = company_tag.text.strip() if company_tag else ""
        job_url = "https://www.work.ua" + title_tag["href"] if title_tag else ""

        description = fetch_workua_description(job_url)

        jobs.append({
            "title": title,
            "company": company,
            "location": None,
            "description": description,
            "url": job_url,
            "source": "work.ua"
        })

    return pd.DataFrame(jobs)


def fetch_workua_description(vacancy_url: str) -> str:
    try:
        resp = requests.get(vacancy_url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_tag = soup.select_one("div#job-description")
        return desc_tag.text.strip() if desc_tag else ""
    except Exception as e:
        print(f"[work.ua] Error fetching description: {e}")
        return ""
