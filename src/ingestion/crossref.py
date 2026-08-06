from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

import requests

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        doi = item.get("DOI", "")
        if not doi:
            continue
        
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            continue
        
        abstracts = item.get("abstract", "")
        summary = _clean_html_tags(str(abstracts)) if abstracts else ""
        
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)
        
        categories = item.get("subject", [])
        if not categories:
            categories = item.get("categories", [])
        
        primary_category = categories[0] if categories else ""
        
        published_info = item.get("published-print", item.get("published-online", {}))
        published_date = published_info.get("date-parts", [[]])
        if published_date and published_date[0]:
            parts = published_date[0]
            if len(parts) >= 3:
                published = f"{parts[0]}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) == 2:
                published = f"{parts[0]}-{parts[1]:02d}-01"
            elif len(parts) == 1:
                published = f"{parts[0]}-01-01"
            else:
                published = ""
        else:
            published = ""
        
        updated_date = item.get("updated", {}).get("date-parts", [[]])
        if updated_date and updated_date[0]:
            parts = updated_date[0]
            if len(parts) >= 3:
                updated = f"{parts[0]}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) == 2:
                updated = f"{parts[0]}-{parts[1]:02d}-01"
            elif len(parts) == 1:
                updated = f"{parts[0]}-01-01"
            else:
                updated = published
        else:
            updated = published
        
        url = item.get("URL", "")
        abs_url = url if url else f"https://doi.org/{doi}"
        
        pdf_url = ""
        links = item.get("link", [])
        for link in links:
            if link.get("content-type", "").startswith("application/pdf"):
                pdf_url = link.get("URL", "")
                break
        
        comment = item.get("comment", "")
        
        paper_id = doi.replace("/", "_").replace(".", "_")
        
        record = PaperRecord(
            paper_id=paper_id,
            title=title.strip(),
            summary=summary.strip(),
            authors=authors,
            categories=categories if isinstance(categories, list) else [],
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)
    
    return records


def _clean_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records."""
    base_url = "https://api.crossref.org/works"
    
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "mailto": "lab@example.com",
    }
    
    url = f"{base_url}?{urlencode(params)}"
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 429:
                wait_time = int(response.headers.get("Retry-After", retry_delay))
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            if response.status_code == 503:
                print(f"Service unavailable. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            response.raise_for_status()
            break
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request failed: {e}. Retrying...")
                time.sleep(retry_delay)
            else:
                raise RuntimeError(f"Failed to fetch from Crossref after {max_retries} attempts") from e
    
    payload = response.json()
    
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    records = parse_crossref_payload(payload)
    
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    records_dict = [asdict(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)
    
    print(f"Fetched {len(records)} records from Crossref")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records not found at {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        records_dict = json.load(f)
    
    records = []
    for rd in records_dict:
        record = PaperRecord(
            paper_id=rd["paper_id"],
            title=rd["title"],
            summary=rd["summary"],
            authors=rd["authors"],
            categories=rd["categories"],
            primary_category=rd["primary_category"],
            published=rd["published"],
            updated=rd["updated"],
            abs_url=rd["abs_url"],
            pdf_url=rd["pdf_url"],
            comment=rd["comment"],
        )
        records.append(record)
    
    return records
