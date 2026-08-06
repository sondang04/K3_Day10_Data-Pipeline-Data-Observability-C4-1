# Vai trò 4 — Checkpoint 2

Generated at: 2026-08-06T04:10:27.537490+00:00

Trạng thái: **PASS**

## 1. Test set đã khóa

- Artifact: `data/eval/test_set.json`
- SHA-256: `63a0d6fe3acd44d28fc5ef949ade9529b4f1889bed101459674fb49d46a968c3`
- Samples: **25**
- Question types: **authors, categories, date, semantic, summary**
- Validation với clean data: **PASS**
- Validation với baseline index: **PASS**
- Document IDs được tham chiếu: **5**

### Preview

| ID | Type | Question | Ground-truth document |
| --- | --- | --- | --- |
| 01-summary | summary | What is the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation' about? | 10.2118/234689-pa |
| 01-authors | authors | Who authored the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'? | 10.2118/234689-pa |
| 01-date | date | When was the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation' published? | 10.2118/234689-pa |
| 01-categories | categories | What categories are assigned to the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'? | 10.2118/234689-pa |
| 01-semantic | semantic | Which indexed paper studies A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation? | 10.2118/234689-pa |

## 2. Baseline embedding/index audit

- Audit status: **PASS**
- Backend/model: **chroma / sentence-transformers/all-MiniLM-L6-v2**
- Collection: **papers-baseline**
- Embedding dimension: **384**
- Clean / manifest / collection counts: **24 / 24 / 24**
- Runtime persist path: `data/chroma`
- Chroma database: `data/chroma/chroma.sqlite3`
- Failed checks: **none**

### Audit checks

| Check | Result | Observed | Expected |
| --- | --- | --- | --- |
| manifest_exists | pass | data/embeddings/papers_embeddings.json | - |
| manifest_required_fields | pass | - | - |
| backend_is_chroma | pass | chroma | chroma |
| embedding_model_matches_settings | pass | sentence-transformers/all-MiniLM-L6-v2 | sentence-transformers/all-MiniLM-L6-v2 |
| collection_name_is_baseline | pass | papers-baseline | papers-baseline |
| manifest_document_count_matches_clean | pass | 24 | 24 |
| manifest_paper_ids_are_unique | pass | - | - |
| manifest_paper_ids_match_clean | pass | - | - |
| chroma_database_exists | pass | data/chroma/chroma.sqlite3 | - |
| baseline_collection_exists | pass | - | - |
| collection_document_count_matches_clean | pass | 24 | 24 |
| collection_paper_ids_are_unique | pass | - | - |
| collection_paper_ids_match_clean | pass | - | - |
| embedding_dimension_is_minilm | pass | 384 | 384 |

Warnings:

- Manifest persist_path was created on another machine; runtime uses settings.paths.chroma_dir. This does not affect LocalEmbeddingIndex.load because it resolves the configured project path.

## 3. Baseline observability snapshot

- Quality: **PASS**, 15/15 checks passed.
- Freshness: **FRESH**, fresh/stale rows = 24/0.
- Latest/oldest publication: **2026-08-01 / 2026-02-12**.
- Source timestamp column: **updated**; latest timestamp: **2026-08-05T00:00:00+00:00**.

## 4. Handoff sang CP3

- Không tạo lại test set; SHA-256 ở trên là mốc đối chiếu cho baseline, corrupted và repaired.
- Role 3 có thể chạy semantic search, exact lookup và agent smoke test trên `papers-baseline`.
- Role 4 chỉ điền metric thật vào phase1 report sau khi baseline evaluation hoàn tất.

## Chạy lại

```bash
uv run python script/run_role4_cp2.py
```
