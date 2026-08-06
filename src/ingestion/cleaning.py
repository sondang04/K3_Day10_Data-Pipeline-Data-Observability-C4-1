from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

MIN_TITLE_CHARS = 12
MIN_SUMMARY_CHARS = 80
PUBLISHED_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "author_count",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
    "ingested_at",
]


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(normalize_whitespace(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = normalize_whitespace(value)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            unique.append(normalized)
    return unique


def _text_for_embedding(row: dict) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Published: {row['published']}\n"
        f"Summary: {row['summary']}"
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    run_day = run_date.date()
    rows: list[dict] = []

    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        published = _parse_date(record.published)

        if not paper_id or not published:
            continue
        if len(title) < MIN_TITLE_CHARS or len(summary) < MIN_SUMMARY_CHARS:
            continue

        authors = _dedupe(record.authors)
        categories = _dedupe(record.categories)
        updated = _parse_date(record.updated) or published
        row = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": compact_join(authors),
            "author_count": len(authors),
            "categories_joined": compact_join(categories),
            "primary_category": normalize_whitespace(record.primary_category) or (categories[0] if categories else ""),
            "published": published.isoformat(),
            "updated": updated.isoformat(),
            # Crossref sometimes carries future publication dates, so clamp to keep age non-negative.
            "age_days": max((run_day - published).days, 0),
            "summary_chars": len(summary),
            "abs_url": normalize_whitespace(record.abs_url),
            "pdf_url": normalize_whitespace(record.pdf_url),
            "comment": normalize_whitespace(record.comment),
            "ingested_at": run_date.isoformat(),
        }
        row["text_for_embedding"] = _text_for_embedding(row)
        rows.append(row)

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if df.empty:
        return df

    df = df[~df["paper_id"].duplicated(keep="first")]
    df = df[~df["title"].str.lower().duplicated(keep="first")]
    return df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
