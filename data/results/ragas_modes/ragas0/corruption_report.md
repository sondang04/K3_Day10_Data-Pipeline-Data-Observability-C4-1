# Corruption Flow - Comparison Report

Generated at: 2026-08-06T05:33:54.085709+00:00

This report compares three pipeline states to demonstrate the impact of data corruption
on RAG agent quality and the effectiveness of recovery from raw source data.

## 1. Comparison Summary

| Metric | Baseline | Corrupted | Repaired | Corrupted Δ | Repaired Δ |
| --- | --- | --- | --- | --- | --- |
| retrieval_hit_rate | 1.000 | 0.800 | 1.000 | -0.200 | +0.000 |
| mean_token_f1 | 0.834 | 0.639 | 0.834 | -0.195 | +0.000 |
| judge_accuracy | 0.920 | 0.640 | 0.880 | -0.280 | -0.040 |
| mean_judge_score | 4.640 | 3.880 | 4.640 | -0.760 | +0.000 |

## 2. Record Counts

- Baseline records: 24
- Corrupted records: 21
- Repaired records: 24

## 3. Quality Status

- Baseline: PASSED
- Corrupted: FAILED
- Repaired: PASSED

## 4. Freshness Status

- Baseline: FRESH
- Corrupted: STALE
- Repaired: FRESH

## 5. Corruption Applied

- Initial records: 24
- Final records: 21
- Corruption types applied: drop_latest_records, blank_summary, inject_noise, truncate_title, stale_date, duplicate_ids

  - Dropped 3 latest records: 3 records
  - Blanked summary in 3 records: 3 records
  - Injected noise in 3 records: 3 records
  - Truncated titles in 3 records: 3 records
  - Set old publication dates in 3 records: 3 records
  - Created duplicate IDs for 2 records: 2 records

## 6. Key Findings

- **Retrieval performance degraded** after corruption, demonstrating data quality impact.
- **Recovery successful**: Repaired metrics approximately match baseline.

## 7. Reproduce

```bash
# First run baseline
uv run python script/run_phase1.py

# Then run corruption flow
uv run python script/run_corruption_flow.py
```
