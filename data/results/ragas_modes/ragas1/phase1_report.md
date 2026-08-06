# Phase 1 - Baseline Report

Generated at: 2026-08-06T04:58:28.791014+00:00

Baseline run of the RAG data pipeline on clean Crossref data: ingestion -> cleaning -> embedding index -> evaluation -> data quality and freshness monitoring.

## 1. Source and dataset

| Field | Value |
| --- | --- |
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-02-07,has-abstract:true |
| records_source | raw-snapshot |
| raw_records | 24 |
| clean_rows | 24 |
| dropped_by_cleaning | 0 |
| clean_columns | 16 |
| published_range | 2026-02-12 .. 2026-08-01 |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| collection_name | papers-baseline |
| top_k | 4 |
| test_set_source | cached |
| test_set_size | 25 |
| raw_response_artifact | data/raw/crossref_response.json |
| raw_records_artifact | data/raw/crossref_records.json |
| clean_artifacts | data/clean/papers_clean.csv, data/clean/papers_clean.json |
| embeddings_artifact | data/embeddings/papers_embeddings.json |
| test_set_artifact | data/eval/test_set.json |
| metrics_artifact | data/results/baseline_metrics.json |

## 2. Evaluation metrics

| Metric | Value |
| --- | --- |
| Evaluation samples | 25 |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 0.813 |
| Judge accuracy | 0.880 |
| Mean judge score (1-5) | 4.040 |

Ragas:

| Ragas metric | Value |
| --- | --- |
| error | Ragas evaluation failed: GOOGLE_API_KEY is required when LLM_PROVIDER=gemini. |

## 3. Data quality

Overall status: **PASS** (25/25 expectations passed)

Engine: great_expectations 1.19.1 + CP1 contract checks | rows checked: 24

| Expectation | Column | Result | Unexpected | Observed |
| --- | --- | --- | --- | --- |
| expect_table_row_count_to_be_between | - | pass | - | 24 |
| expect_column_values_to_not_be_null | paper_id | pass | 0 | - |
| expect_column_values_to_be_unique | paper_id | pass | 0 | - |
| expect_column_values_to_not_be_null | title | pass | 0 | - |
| expect_column_value_lengths_to_be_between | title | pass | 0 | - |
| expect_column_values_to_not_be_null | summary | pass | 0 | - |
| expect_column_value_lengths_to_be_between | summary | pass | 0 | - |
| expect_column_values_to_not_be_null | text_for_embedding | pass | 0 | - |
| expect_column_values_to_match_regex | published | pass | 0 | - |
| expect_column_values_to_be_between | age_days | pass | 0 | - |
| cp1_table_row_count_minimum | - | pass | 0 | 24 |
| cp1_required_columns_present | - | pass | 0 | abs_url, age_days, authors, authors_joined, categories, categories_joined, comment, paper_id, pdf_url, primary_category, published, summary, summary_chars, text_for_embedding, title, updated |
| cp1_paper_id_not_blank | paper_id | pass | 0 | 0 |
| cp1_paper_id_unique_normalized | paper_id | pass | 0 | 0 |
| cp1_title_not_blank | title | pass | 0 | 0 |
| cp1_title_min_length | title | pass | 0 | 0 |
| cp1_title_unique_normalized | title | pass | 0 | 0 |
| cp1_summary_not_blank | summary | pass | 0 | 0 |
| cp1_summary_min_length | summary | pass | 0 | 0 |
| cp1_text_for_embedding_not_blank | text_for_embedding | pass | 0 | 0 |
| cp1_published_valid_date | published | pass | 0 | 0 |
| cp1_age_days_non_negative | age_days | pass | 0 | 0 |
| cp1_age_days_within_freshness_threshold | age_days | pass | 0 | 0 |
| cp1_age_days_matches_published | age_days,published | pass | 0 | 0 |
| cp1_source_timestamp_present | updated | pass | 0 | {'column': 'updated', 'invalid_rows': 0} |

## 4. Freshness

Status: **FRESH** (threshold 180 days)

| Field | Value |
| --- | --- |
| generated_at | 2026-08-06T04:58:28.788409+00:00 |
| threshold_days | 180 |
| total_rows | 24 |
| stale_rows | 0 |
| fresh_rows | 24 |
| invalid_published_rows | 0 |
| invalid_age_days_rows | 0 |
| age_mismatch_rows | 0 |
| latest_published | 2026-08-01 |
| oldest_published | 2026-02-12 |
| days_since_latest_publication | 5 |
| max_age_days | 175 |
| mean_age_days | 80.620 |
| source_timestamp_column | updated |
| latest_ingested_at | 2026-08-05T00:00:00+00:00 |
| source_lag_hours | 28.970 |
| is_fresh | yes |
| notes | Fresh means published/age_days are valid, consistent within 1 day, and no row is older than 180 days. |

## 5. Reproduce

```bash
uv run python script/run_phase1.py
```

Set `REFRESH_SOURCE=1` to re-fetch from Crossref and `REFRESH_TEST_SET=1` to rebuild the evaluation set.
