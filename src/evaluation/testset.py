from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json

MIN_DOCUMENTS = 4
MAX_PAPERS = 5
TOPIC_WORDS = 14


def _select_papers(df: pd.DataFrame) -> list[dict[str, Any]]:
    # `qa.answer_question` looks up the quoted title, so titles carrying an apostrophe
    # would break the exact-match path and are only used when nothing else is left.
    quotable = df[~df["title"].str.contains("'", regex=False)]
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
    title = row["title"]
    doc_ids = [row["paper_id"]]
    summary_lead = first_sentence(row["summary"])
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
        if not ground_truth:
            continue
        samples.append(
            {
                "id": f"{index:02d}-{question_type}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": doc_ids,
            }
        )
    return samples


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} cleaned documents to build a test set, got {len(df)}.")

    samples: list[dict[str, Any]] = []
    for index, row in enumerate(_select_papers(df), start=1):
        samples.extend(_samples_for_paper(row, index))

    write_json(output_path, samples)
    return samples
