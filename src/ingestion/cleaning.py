from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.crossref import PaperRecord

MIN_TITLE_CHARS = 5
MIN_SUMMARY_CHARS = 50
PUBLISHED_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    data = []
    
    for record in records:
        title = _normalize_title(record.title)
        summary = _normalize_summary(record.summary)
        authors = _normalize_authors(record.authors)
        categories = _normalize_categories(record.categories)
        
        published = _parse_date(record.published)
        updated = _parse_date(record.updated)
        
        age_days = (run_date - published).days if published else None
        
        authors_joined = "; ".join(authors) if authors else ""
        categories_joined = "; ".join(categories) if categories else ""
        summary_chars = len(summary) if summary else 0
        
        text_for_embedding = _build_text_for_embedding(title, summary, authors, categories)
        
        data.append({
            "paper_id": record.paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "authors_joined": authors_joined,
            "categories": categories,
            "categories_joined": categories_joined,
            "primary_category": record.primary_category,
            "published": published.strftime("%Y-%m-%d") if published else "",
            "updated": updated.strftime("%Y-%m-%d") if updated else "",
            "age_days": age_days,
            "abs_url": record.abs_url,
            "pdf_url": record.pdf_url,
            "comment": record.comment,
            "summary_chars": summary_chars,
            "text_for_embedding": text_for_embedding,
        })
    
    df = pd.DataFrame(data)
    
    df = _filter_invalid_records(df)
    
    df = _deduplicate(df)
    
    df = df.sort_values("paper_id").reset_index(drop=True)
    
    return df


def _normalize_title(title: str) -> str:
    """Normalize title text."""
    if not title:
        return ""
    title = title.strip()
    title = re.sub(r'\s+', ' ', title)
    return title


def _normalize_summary(summary: str) -> str:
    """Normalize summary/abstract text."""
    if not summary:
        return ""
    summary = summary.strip()
    summary = re.sub(r'\s+', ' ', summary)
    return summary


def _normalize_authors(authors: list[str]) -> list[str]:
    """Normalize author names."""
    if not authors:
        return []
    normalized = []
    for author in authors:
        author = author.strip()
        author = re.sub(r'\s+', ' ', author)
        if author and len(author) > 1:
            normalized.append(author)
    return normalized


def _normalize_categories(categories: list[str]) -> list[str]:
    """Normalize category/subject list."""
    if not categories:
        return []
    normalized = []
    for cat in categories:
        cat = cat.strip()
        if cat:
            normalized.append(cat)
    return list(set(normalized))


def _parse_date(date_str: str) -> datetime | None:
    """Parse date string to datetime object."""
    if not date_str:
        return None
    try:
        naive = datetime.strptime(date_str, "%Y-%m-%d")
        return naive.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            naive = datetime.strptime(date_str, "%Y-%m")
            return naive.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                naive = datetime.strptime(date_str, "%Y")
                return naive.replace(tzinfo=timezone.utc)
            except ValueError:
                return None


def _build_text_for_embedding(
    title: str, summary: str, authors: list[str], categories: list[str]
) -> str:
    """Build combined text for embedding."""
    parts = []
    
    if title:
        parts.append(f"Title: {title}")
    
    if summary:
        parts.append(f"Abstract: {summary}")
    
    if authors:
        authors_text = ", ".join(authors[:5])
        if len(authors) > 5:
            authors_text += f" and {len(authors) - 5} more"
        parts.append(f"Authors: {authors_text}")
    
    if categories:
        parts.append(f"Categories: {', '.join(categories[:5])}")
    
    return " | ".join(parts)


def _filter_invalid_records(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out invalid records based on quality rules."""
    initial_count = len(df)
    
    mask = df["title"].notna() & (df["title"] != "")
    df = df[mask].copy()
    
    mask = df["paper_id"].notna() & (df["paper_id"] != "")
    df = df[mask].copy()
    
    filtered_count = initial_count - len(df)
    if filtered_count > 0:
        print(f"Filtered {filtered_count} invalid records (no title or paper_id)")
    
    return df


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate records based on paper_id."""
    initial_count = len(df)
    
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    
    dup_count = initial_count - len(df)
    if dup_count > 0:
        print(f"Removed {dup_count} duplicate records")
    
    return df


def save_clean_data(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Save cleaned dataframe to CSV and JSON."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    
    print(f"Saved {len(df)} cleaned records to {csv_path} and {json_path}")


def get_cleaning_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Get statistics about cleaned data."""
    stats = {
        "total_records": len(df),
        "unique_papers": df["paper_id"].nunique(),
        "records_with_summary": int(df["summary"].str.len().gt(0).sum()),
        "records_with_authors": int(df["authors_joined"].str.len().gt(0).sum()),
        "records_with_categories": int(df["categories_joined"].str.len().gt(0).sum()),
        "mean_age_days": float(df["age_days"].mean()) if "age_days" in df.columns else None,
        "median_age_days": float(df["age_days"].median()) if "age_days" in df.columns else None,
        "title_null_count": int(df["title"].isna().sum()),
        "summary_null_count": int(df["summary"].isna().sum()),
        "authors_null_count": int(df["authors_joined"].isna().sum()),
        "published_null_count": int(df["published"].isna().sum()),
    }
    return stats
