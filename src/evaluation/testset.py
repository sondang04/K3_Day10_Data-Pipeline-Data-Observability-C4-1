from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json

MIN_DOCUMENTS = 4
MAX_PAPERS = 5
TOPIC_WORDS = 14
REQUIRED_CLEAN_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}
REQUIRED_SAMPLE_FIELDS = {
    "id",
    "question_type",
    "question",
    "ground_truth",
    "ground_truth_doc_ids",
}


def _as_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_CLEAN_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {missing_columns}")
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} cleaned documents to build a test set, got {len(df)}.")

    for column in REQUIRED_CLEAN_COLUMNS:
        blank_mask = df[column].map(_as_text).eq("")
        if blank_mask.any():
            raise ValueError(f"Clean dataframe contains blank values in {column}.")

    paper_ids = df["paper_id"].map(_as_text).str.lower()
    duplicated_ids = sorted(paper_ids[paper_ids.duplicated(keep=False)].unique().tolist())
    if duplicated_ids:
        raise ValueError(f"paper_id must be stable and unique before building the test set: {duplicated_ids[:5]}")


def _select_papers(df: pd.DataFrame) -> list[dict[str, Any]]:
    # `qa.answer_question` looks up the quoted title, so titles carrying an apostrophe
    # would break the exact-match path and are only used when nothing else is left.
    quotable = df[~df["title"].map(_as_text).str.contains("'", regex=False)]
    pool = quotable if len(quotable) >= MIN_DOCUMENTS else df

    count = min(MAX_PAPERS, len(pool))
    step = max(len(pool) // count, 1)
    positions = sorted({min(index * step, len(pool) - 1) for index in range(count)})
    return pool.iloc[positions].to_dict(orient="records")


def _topic_phrase(title: str) -> str:
    # Keep the descriptive half of "Acronym: long descriptive title" headings.
    chunk = max(title.split(":"), key=len)
    return " ".join(normalize_whitespace(chunk).split()[:TOPIC_WORDS])


def _samples_for_paper(row: dict[str, Any], index: int) -> list[dict[str, Any]]:
    title = _as_text(row["title"])
    paper_id = _as_text(row["paper_id"]).lower()
    doc_ids = [paper_id]
    summary_lead = first_sentence(_as_text(row["summary"]))
    candidates = [
        ("summary", f"What is the paper '{title}' about?", summary_lead),
        ("authors", f"Who authored the paper '{title}'?", row["authors_joined"]),
        ("date", f"When was the paper '{title}' published?", row["published"]),
        ("categories", f"What categories are assigned to the paper '{title}'?", row["categories_joined"]),
        # No quoted title, so this one can only be answered through embedding search.
        ("semantic", f"Which indexed paper studies {_topic_phrase(title)}?", summary_lead),
    ]

    samples: list[dict[str, Any]] = []
    for question_type, question, ground_truth in candidates:
        ground_truth_text = _as_text(ground_truth)
        if not ground_truth_text:
            continue
        samples.append(
            {
                "id": f"{index:02d}-{question_type}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth_text,
                "ground_truth_doc_ids": doc_ids,
            }
        )
    return samples


def validate_test_set(samples: list[dict[str, Any]], df: pd.DataFrame) -> dict[str, Any]:
    """Validate that every evaluation item is auditable against cleaned data.

    CP0-CP1 contract: document IDs must come from stable clean ``paper_id`` values;
    questions and ground truth cannot be blank; sample IDs must be unique.
    """

    _validate_clean_dataframe(df)
    clean_ids = set(df["paper_id"].map(_as_text).str.lower())
    sample_ids: list[str] = []
    invalid_samples: list[dict[str, Any]] = []

    for position, sample in enumerate(samples):
        missing_fields = sorted(REQUIRED_SAMPLE_FIELDS - set(sample))
        doc_ids = [normalize_whitespace(str(value)).lower() for value in sample.get("ground_truth_doc_ids", [])]
        unknown_doc_ids = sorted(set(doc_ids) - clean_ids)
        blank_fields = [
            field
            for field in ("id", "question_type", "question", "ground_truth")
            if not normalize_whitespace(str(sample.get(field, "")))
        ]
        if missing_fields or unknown_doc_ids or blank_fields or not doc_ids:
            invalid_samples.append(
                {
                    "position": position,
                    "id": sample.get("id"),
                    "missing_fields": missing_fields,
                    "blank_fields": blank_fields,
                    "unknown_doc_ids": unknown_doc_ids,
                    "has_ground_truth_doc_ids": bool(doc_ids),
                }
            )
        sample_ids.append(normalize_whitespace(str(sample.get("id", ""))))

    duplicate_sample_ids = sorted({value for value in sample_ids if value and sample_ids.count(value) > 1})
    if duplicate_sample_ids:
        invalid_samples.append({"duplicate_sample_ids": duplicate_sample_ids})

    result = {
        "success": not invalid_samples,
        "sample_count": len(samples),
        "question_types": sorted({str(item.get("question_type", "")) for item in samples}),
        "clean_document_count": len(clean_ids),
        "invalid_samples": invalid_samples,
    }
    if invalid_samples:
        raise ValueError(f"Invalid evaluation set: {invalid_samples[:3]}")
    return result


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    _validate_clean_dataframe(df)

    samples: list[dict[str, Any]] = []
    for index, row in enumerate(_select_papers(df), start=1):
        samples.extend(_samples_for_paper(row, index))

    validate_test_set(samples, df)
    write_json(output_path, samples)
    return samples
