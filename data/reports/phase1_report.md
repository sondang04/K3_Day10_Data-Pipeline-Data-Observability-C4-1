# Phase 1 - Baseline Report

Generated at: 2026-08-06T03:37:50.615268+00:00

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
| raw_response_artifact | data\raw\crossref_response.json |
| raw_records_artifact | data\raw\crossref_records.json |
| clean_artifacts | data\clean\papers_clean.csv, data\clean\papers_clean.json |
| embeddings_artifact | data\embeddings\papers_embeddings.json |
| test_set_artifact | data\eval\test_set.json |
| metrics_artifact | data\results\baseline_metrics.json |

## 2. Evaluation metrics

| Metric | Value |
| --- | --- |
| Evaluation samples | 25 |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 0.834 |
| Judge accuracy | 0.920 |
| Mean judge score (1-5) | 4.120 |

Ragas:

| Ragas metric | Value |
| --- | --- |
| skipped | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## 3. Data quality

Overall status: **PASS** (10/10 expectations passed)

Engine: great_expectations 1.18.0 | rows checked: 24

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

## 4. Freshness

Status: **FRESH** (threshold 180 days)

| Field | Value |
| --- | --- |
| generated_at | 2026-08-06T03:37:50.611232+00:00 |
| threshold_days | 180 |
| total_rows | 24 |
| stale_rows | 0 |
| fresh_rows | 24 |
| latest_published | 2026-08-01 |
| oldest_published | 2026-02-12 |
| days_since_latest_publication | 5 |
| max_age_days | 175 |
| mean_age_days | 80.620 |
| is_fresh | yes |
| notes | Fresh means every row is younger than 180 days. |

## 5. Reproduce

```bash
uv run python script/run_phase1.py
```

Set `REFRESH_SOURCE=1` to re-fetch from Crossref and `REFRESH_TEST_SET=1` to rebuild the evaluation set.
