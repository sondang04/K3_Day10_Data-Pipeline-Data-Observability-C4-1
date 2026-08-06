from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
USER_AGENT = "day10-data-observability-lab/0.1 (baseline RAG pipeline; mailto:student@example.com)"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 2.0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_API_ROWS = 100
# Crossref items can be unusable (no title/abstract), so ask for more rows than needed
# and keep the first `max_results` records that survive parsing.
OVERFETCH_FACTOR = 2


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


def _strip_markup(value: str) -> str:
    return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", value)))


def _first_text(values: list | None) -> str:
    for value in values or []:
        text = _strip_markup(str(value))
        if text:
            return text
    return ""


def _iso_date(node: dict | None) -> str:
    date_parts = (node or {}).get("date-parts") or [[]]
    parts = [part for part in date_parts[0] if isinstance(part, int)]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _published_date(item: dict) -> str:
    for key in ("published", "published-online", "published-print", "issued", "created"):
        published = _iso_date(item.get(key))
        if published:
            return published
    return ""


def _updated_date(item: dict) -> str:
    for key in ("deposited", "indexed", "created"):
        updated = _iso_date(item.get(key))
        if updated:
            return updated
    return ""


def _authors(item: dict) -> list[str]:
    names: list[str] = []
    for author in item.get("author") or []:
        given = _strip_markup(str(author.get("given", "")))
        family = _strip_markup(str(author.get("family", "")))
        name = normalize_whitespace(f"{given} {family}") or _strip_markup(str(author.get("name", "")))
        if name:
            names.append(name)
    return names


def _categories(item: dict) -> list[str]:
    subjects = [_strip_markup(str(subject)) for subject in item.get("subject") or []]
    subjects = [subject for subject in subjects if subject]
    if subjects:
        return subjects
    # Most Crossref works carry no `subject`, so fall back to venue and work type.
    fallback = [_first_text(item.get("container-title")), _strip_markup(str(item.get("type", "")))]
    return [value for value in fallback if value]


def _abstract(item: dict) -> str:
    abstract = _strip_markup(str(item.get("abstract", "")))
    # JATS abstracts usually open with a section label such as <jats:title>Abstract</jats:title>.
    return re.sub(r"^(graphical\s+)?(abstract|summary)[:\s.-]*", "", abstract, flags=re.IGNORECASE).strip()


def _pdf_url(item: dict) -> str:
    links = item.get("link") or []
    for link in links:
        if str(link.get("content-type", "")).lower() == "application/pdf":
            return str(link.get("URL", ""))
    for link in links:
        url = str(link.get("URL", ""))
        if "pdf" in url.lower():
            return url
    return ""


def _comment(item: dict) -> str:
    return compact_join(
        [
            _strip_markup(str(item.get("type", ""))),
            _first_text(item.get("container-title")),
            _strip_markup(str(item.get("publisher", ""))),
        ],
        sep=" | ",
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = ((payload or {}).get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    for item in items:
        paper_id = normalize_whitespace(str(item.get("DOI", "")))
        title = _first_text(item.get("title"))
        summary = _abstract(item)
        published = _published_date(item)
        if not paper_id or not title or not summary or not published:
            continue

        categories = _categories(item)
        abs_url = normalize_whitespace(str(item.get("URL", ""))) or f"https://doi.org/{paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_updated_date(item) or published,
                abs_url=abs_url,
                pdf_url=_pdf_url(item),
                comment=_comment(item),
            )
        )
    return records


def _request_payload(params: dict) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
            last_error = RuntimeError(f"Crossref returned HTTP {response.status_code}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))

    raise RuntimeError(f"Crossref request failed after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    rows = min(settings.max_results * OVERFETCH_FACTOR, MAX_API_ROWS)
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": rows,
    }

    payload = _request_payload(params)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)[: settings.max_results]
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    payload = read_json(path)
    records: list[PaperRecord] = []
    for item in payload:
        categories = [str(value) for value in item.get("categories") or []]
        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                authors=[str(value) for value in item.get("authors") or []],
                categories=categories,
                primary_category=str(item.get("primary_category", "")) or (categories[0] if categories else ""),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
