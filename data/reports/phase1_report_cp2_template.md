# Phase 1 — Baseline Report (CP2 template)

Prepared at: 2026-08-06T04:10:27.537773+00:00

This template contains only verified CP2 facts. Evaluation metrics remain pending until CP3; no values are fabricated.

## 1. Locked evaluation set

- Samples: 25
- Types: authors, categories, date, semantic, summary
- SHA-256: `63a0d6fe3acd44d28fc5ef949ade9529b4f1889bed101459674fb49d46a968c3`

## 2. Baseline index

- Backend: chroma
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Collection: papers-baseline
- Documents: 24
- Dimension: 384

## 3. Evaluation metrics — fill at CP3

| Metric | Value |
| --- | --- |
| Evaluation samples | PENDING_CP3 |
| Retrieval hit rate | PENDING_CP3 |
| Mean token F1 | PENDING_CP3 |
| Judge accuracy | PENDING_CP3 |
| Mean judge score (1–5) | PENDING_CP3 |
| Ragas | PENDING_CP3 |

## 4. Data quality

- Status: PASS
- Rows: 24
- Checks passed: 15/15

## 5. Freshness

- Status: FRESH
- Fresh/stale rows: 24/0
- Threshold: 180 days
- Latest publication: 2026-08-01
- Source timestamp: updated = 2026-08-05T00:00:00+00:00

## 6. CP3 evidence to attach

- `data/results/baseline_answers.json`
- `data/results/baseline_metrics.json`
- Agent smoke-test output with cited sources
