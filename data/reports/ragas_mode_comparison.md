# Baseline / corrupted / repaired comparison and trace (RUN_RAGAS=0)

Generated at: 2026-08-06T05:35:24.135823+00:00

Every mode runs `phase1.main()` then `corruption_flow.main()` in-process with the corruption RNG seeded to `20260806`, so repeated runs corrupt identical rows.

## 1. Metrics per pipeline state

| Metric | State | RUN_RAGAS=0 |
| --- | --- | --- |
| samples | baseline | 25 |
| samples | corrupted | 25 |
| samples | repaired | 25 |
| retrieval_hit_rate | baseline | 1.000 |
| retrieval_hit_rate | corrupted | 0.800 |
| retrieval_hit_rate | repaired | 1.000 |
| mean_token_f1 | baseline | 0.834 |
| mean_token_f1 | corrupted | 0.639 |
| mean_token_f1 | repaired | 0.834 |
| judge_accuracy | baseline | 0.920 |
| judge_accuracy | corrupted | 0.640 |
| judge_accuracy | repaired | 0.880 |
| mean_judge_score | baseline | 4.640 |
| mean_judge_score | corrupted | 3.880 |
| mean_judge_score | repaired | 4.640 |


### Ragas payload per mode

| Mode | State | Ragas result |
| --- | --- | --- |
| RUN_RAGAS=0 | baseline | `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}` |
| RUN_RAGAS=0 | corrupted | `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}` |
| RUN_RAGAS=0 | repaired | `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}` |

## 2. What corruption did to the dataset

Rows: baseline 24 -> corrupted 21 -> repaired 24

| Corruption | Records |
| --- | --- |
| embedding_text_rewritten | 9 |
| paper_id_mutated | 2 |
| published_backdated | 3 |
| record_dropped | 3 |
| summary_blanked | 3 |
| summary_noise_injected | 3 |
| title_truncated | 3 |
| unchanged | 10 |

Untouched records: 10 | restored by repair: 24 | not restored: 0

## 3. How observability reacted

| State | Quality | Checks passed | Freshness | Stale rows |
| --- | --- | --- | --- | --- |
| baseline | PASS | 25/25 | FRESH | 0 |
| corrupted | FAIL | 20/25 | STALE | 3 |
| repaired | PASS | 25/25 | FRESH | 0 |

Checks that flipped to FAIL on corrupted data:

- `expect_column_value_lengths_to_be_between` (title): 3 unexpected rows -> recovered after repair
- `expect_column_values_to_be_between` (age_days): 3 unexpected rows -> recovered after repair
- `cp1_summary_not_blank` (summary): 3 unexpected rows -> recovered after repair
- `cp1_summary_min_length` (summary): 3 unexpected rows -> recovered after repair
- `cp1_age_days_within_freshness_threshold` (age_days): 3 unexpected rows -> recovered after repair

## 4. How the agent's answers moved

| Question type | Samples | Regressed on corruption | Recovered after repair |
| --- | --- | --- | --- |
| authors | 5 | 1 | 1 |
| categories | 5 | 1 | 1 |
| date | 5 | 2 | 2 |
| semantic | 5 | 1 | 1 |
| summary | 5 | 1 | 1 |

Per-question regressions:

- `02-summary` (summary): hit True->False->True, F1 1.000->0.128->1.000, top doc corrupted=`10.63646/kpqm1958`
- `02-authors` (authors): hit True->False->True, F1 0.800->0.000->0.800, top doc corrupted=`10.63646/kpqm1958`
- `02-date` (date): hit True->False->True, F1 1.000->0.000->1.000, top doc corrupted=`10.63646/kpqm1958`
- `02-categories` (categories): hit True->False->True, F1 0.500->0.222->0.500, top doc corrupted=`10.63646/kpqm1958`
- `02-semantic` (semantic): hit True->False->True, F1 1.000->0.078->1.000, top doc corrupted=`10.21203/rs.3.rs-10012178/v1`
- `05-date` (date): hit True->True->True, F1 1.000->0.000->1.000, top doc corrupted=`10.1093/sleep/zsag091.0346`

## 5. Reproduce

```bash
uv run python script/run_ragas_comparison.py
```

Per-mode artifact snapshots live in `data/results/ragas_modes/ragas<mode>/`, the structured event log in `data/quality/pipeline_trace.jsonl`.

A Ragas pass needs a reachable LLM provider: `LLM_PROVIDER`/`LLM_MODEL` plus the matching API key in `.env`. Without credentials the pass is recorded as an error and the core metrics are unaffected.
