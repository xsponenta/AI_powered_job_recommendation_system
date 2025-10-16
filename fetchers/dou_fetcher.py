import requests
from bs4 import BeautifulSoup
import pandas as pd
from fetchers.headers import get_headers

def fetch_dou_jobs(query: str, count: int = 30):
    base_url = "https://jobs.dou.ua/vacancies/"
    params = {"search": query}
    
    try:
        response = requests.get(base_url, params=params, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"[dou.ua] Fetch error: {e}")
        return pd.DataFrame()

    jobs = []
    for div in soup.select("li.l-vacancy")[:count]:
        title_tag = div.select_one("div.title > a")
        company_tag = div.select_one("div.title > strong > a")
        desc_tag = div.select_one("div.sh-info")

        title = title_tag.text.strip() if title_tag else ""
        company = company_tag.text.strip() if company_tag else ""
        desc = desc_tag.text.strip() if desc_tag else ""
        url = title_tag["href"] if title_tag else ""

        jobs.append({
            "title": title,
            "company": company,
            "location": None,
            "description": desc,
            "url": url,
            "source": "dou.ua"
        })

    return pd.DataFrame(jobs)
