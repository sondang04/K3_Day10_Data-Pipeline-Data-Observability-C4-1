from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption."""
    corruption_log: list[dict[str, Any]] = []
    df = df.copy()
    
    initial_count = len(df)
    
    if len(df) > 5:
        n_drop = max(1, len(df) // 8)
        drop_indices = random.sample(list(df.index), n_drop)
        dropped_ids = df.loc[drop_indices, "paper_id"].tolist()
        df = df.drop(index=drop_indices).reset_index(drop=True)
        
        corruption_log.append({
            "type": "drop_latest_records",
            "count": n_drop,
            "paper_ids": dropped_ids,
            "description": f"Dropped {n_drop} latest records"
        })
    
    if len(df) > 3:
        n_blank = max(1, len(df) // 6)
        blank_indices = random.sample(list(df.index), min(n_blank, len(df)))
        
        for idx in blank_indices:
            df.at[idx, "summary"] = ""
            df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(df.loc[idx])
        
        corruption_log.append({
            "type": "blank_summary",
            "count": len(blank_indices),
            "indices": blank_indices,
            "description": f"Blanked summary in {len(blank_indices)} records"
        })
    
    noise_words = [
        "XXX", "ZZZ", "NOISE", "TEST", "[CORRUPTED]", "<<<>>>", 
        "[UNVERIFIED]", "???", "***", "###", "[DUBIOUS]"
    ]
    
    if len(df) > 3:
        n_noise = max(1, len(df) // 6)
        noise_indices = random.sample(list(df.index), min(n_noise, len(df)))
        
        for idx in noise_indices:
            noise = " " + random.choice(noise_words) + " "
            summary = df.loc[idx, "summary"]
            if summary and len(summary) > 20:
                insert_pos = random.randint(len(summary) // 4, 3 * len(summary) // 4)
                df.at[idx, "summary"] = summary[:insert_pos] + noise + summary[insert_pos:]
                df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(df.loc[idx])
        
        corruption_log.append({
            "type": "inject_noise",
            "count": len(noise_indices),
            "indices": noise_indices,
            "description": f"Injected noise in {len(noise_indices)} records"
        })
    
    if len(df) > 3:
        n_truncate = max(1, len(df) // 6)
        truncate_indices = random.sample(list(df.index), min(n_truncate, len(df)))
        
        for idx in truncate_indices:
            title = df.loc[idx, "title"]
            if title and len(title) > 15:
                new_len = random.randint(10, len(title) // 2)
                df.at[idx, "title"] = title[:new_len] + "..."
                df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(df.loc[idx])
        
        corruption_log.append({
            "type": "truncate_title",
            "count": len(truncate_indices),
            "indices": truncate_indices,
            "description": f"Truncated titles in {len(truncate_indices)} records"
        })
    
    if len(df) > 3:
        n_old_date = max(1, len(df) // 6)
        old_date_indices = random.sample(list(df.index), min(n_old_date, len(df)))
        
        old_years = ["1999", "2000", "2001", "2002", "2003", "2004", "2005"]
        
        for idx in old_date_indices:
            old_year = random.choice(old_years)
            new_date = f"{old_year}-01-01"
            df.at[idx, "published"] = new_date
            df.at[idx, "updated"] = new_date
            if pd.notna(df.loc[idx, "age_days"]):
                reference_date = pd.Timestamp("2026-08-06")
                pub_date = pd.Timestamp(new_date)
                df.at[idx, "age_days"] = (reference_date - pub_date).days
        
        corruption_log.append({
            "type": "stale_date",
            "count": len(old_date_indices),
            "indices": old_date_indices,
            "description": f"Set old publication dates in {len(old_date_indices)} records"
        })
    
    if len(df) > 5:
        n_duplicates = max(1, len(df) // 8)
        dup_indices = random.sample(list(df.index), min(n_duplicates, len(df)))
        
        duplicates = df.loc[dup_indices].copy()
        new_ids = []
        for i, idx in enumerate(dup_indices):
            old_id = df.at[idx, "paper_id"]
            new_id = f"{old_id}_dup_{i}"
            new_ids.append(new_id)
            df.at[idx, "paper_id"] = new_id
        
        corruption_log.append({
            "type": "duplicate_ids",
            "count": len(dup_indices),
            "original_ids": df.loc[dup_indices, "paper_id"].tolist(),
            "new_ids": new_ids,
            "description": f"Created duplicate IDs for {len(dup_indices)} records"
        })
    
    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump({
            "corruption_log": corruption_log,
            "initial_count": initial_count,
            "final_count": len(df),
            "corrupted_count": initial_count - len(df),
            "corruption_types": [c["type"] for c in corruption_log]
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Corrupted dataset: {initial_count} -> {len(df)} records")
    print(f"Applied {len(corruption_log)} corruption types")
    for log in corruption_log:
        print(f"  - {log['description']}")
    
    return df


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    """Rebuild text_for_embedding for a corrupted row."""
    parts = []
    
    title = row.get("title", "")
    if title:
        parts.append(f"Title: {title}")
    
    summary = row.get("summary", "")
    if summary:
        parts.append(f"Abstract: {summary}")
    
    authors_joined = row.get("authors_joined", "")
    if authors_joined and not pd.isna(authors_joined):
        parts.append(f"Authors: {authors_joined}")
    
    categories_joined = row.get("categories_joined", "")
    if categories_joined and not pd.isna(categories_joined):
        parts.append(f"Categories: {categories_joined}")
    
    return " | ".join(parts)


def save_corrupted_data(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Save corrupted dataframe to CSV and JSON."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    
    print(f"Saved {len(df)} corrupted records to {csv_path} and {json_path}")
