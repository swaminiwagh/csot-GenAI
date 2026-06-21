import os
import requests
from markdownify import markdownify
import trafilatura

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def web_search(query):
    url = "https://google.serper.dev/search"
    res = requests.post(url, headers={
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }, json={"q": query})

    if res.status_code != 200:
        return {"error": f"Serper returned {res.status_code}"}

    data = res.json()

    results = []
    for r in data.get("organic", [])[:5]:
        results.append({
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "snippet": r.get("snippet", "")
        })

    return {"results": results}

def web_fetch(url):
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded)

    if not text:
        return {"error": "Failed to extract content"}

    return {
        "content": markdownify(text)[:12000]
    }