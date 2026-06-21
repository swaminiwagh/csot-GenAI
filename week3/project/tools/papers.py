import requests

BASE = "https://huggingface.co"

def paper_search(query, limit=5):
    url = f"{BASE}/api/papers/search?q={query}"
    res = requests.get(url)
    data = res.json()

    if isinstance(data, list):
        items = data
    else:
        items = data.get("papers", [])

    papers = []
    for p in items[:limit]:
        # arxiv_id is nested inside p["paper"]["id"]
        paper_meta = p.get("paper") or {}
        arxiv_id = (
            paper_meta.get("id")
            or paper_meta.get("arxiv_id")
            or p.get("arxiv_id", "")
        ).strip()

        abstract = (
            p.get("summary")           # top-level summary field
            or paper_meta.get("abstract", "")
        )

        papers.append({
            "arxiv_id": arxiv_id,
            "title": p.get("title", ""),
            "abstract": abstract,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
        })

    return {"papers": papers}


def read_paper(arxiv_id):
    arxiv_id = arxiv_id.replace("https://arxiv.org/abs/", "").replace("v1", "").strip()

    meta_res = requests.get(f"{BASE}/api/papers/{arxiv_id}")
    meta = meta_res.json() if meta_res.ok else {}

    md = requests.get(f"{BASE}/papers/{arxiv_id}.md")

    if md.status_code != 200:
        return {
            "arxiv_id": arxiv_id,
            "title": meta.get("title", ""),
            "abstract": meta.get("abstract", ""),
            "content": meta.get("abstract", ""),
            "url": f"https://arxiv.org/abs/{arxiv_id}"
        }

    return {
        "arxiv_id": arxiv_id,
        "title": meta.get("title", ""),
        "abstract": meta.get("abstract", ""),
        "content": md.text[:12000],
        "url": f"https://arxiv.org/abs/{arxiv_id}"
    }