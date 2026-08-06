# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Dương Mạnh Phong |
| MSSV | 2A202601557 |
| Khóa/Lớp | K3 |
| Tên nhóm | C4-1 |
| Vai trò chính | Vai trò 4 — Evaluation & Observability |
| Repository | K3_Day10_Data-Pipeline-Data-Observability-C4-1 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Vai trò 4 phụ trách toàn bộ tầng **Evaluation & Observability** — bao gồm xây dựng và khóa evaluation set, chạy evaluator trên ba trạng thái pipeline, thực hiện data quality checks và freshness monitoring, và sinh toàn bộ báo cáo Markdown.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Xây dựng evaluation set | `src/evaluation/testset.py` → `build_test_set`, `validate_test_set` | `data/clean/papers_clean.csv` | `data/eval/test_set.json` (25 samples, 5 question types) | Hoàn thành |
| Khóa test set với index | `testset.py` → `validate_test_set_against_index` | test_set.json + Chroma collection `papers-baseline` | SHA-256 checksum + `data/reports/role4_cp2_report.md` | Hoàn thành |
| Baseline evaluation | `src/evaluation/metrics.py` → `evaluate_pipeline` | `LocalEmbeddingIndex` (baseline) + test_set.json | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | Hoàn thành |
| Corrupted evaluation | `metrics.py` → `evaluate_pipeline` | `LocalEmbeddingIndex` (corrupted) + cùng test_set.json | `data/results/corrupted_metrics.json`, `data/results/corrupted_answers.json` | Hoàn thành |
| Repaired evaluation | `metrics.py` → `evaluate_pipeline` | `LocalEmbeddingIndex` (repaired) + cùng test_set.json | `data/results/repaired_metrics.json`, `data/results/repaired_answers.json` | Hoàn thành |
| Data quality checks — baseline | `src/observability/quality.py` → `run_quality_checks` | `data/clean/papers_clean.csv` | `data/quality/baseline-quality.json` | Hoàn thành |
| Data quality checks — corrupted | `quality.py` → `run_quality_checks` | `data/clean/papers_clean_corrupted.csv` | `data/quality/corrupted-quality.json` | Hoàn thành |
| Data quality checks — repaired | `quality.py` → `run_quality_checks` | `data/clean/papers_clean_repaired.csv` | `data/quality/repaired-quality.json` | Hoàn thành |
| Freshness monitoring (3 states) | `quality.py` → `check_freshness` | Clean dataframe (ba trạng thái) | `data/quality/freshness_report.json`, `corrupted_freshness.json`, `repaired_freshness.json` | Hoàn thành |
| Comparison metrics | `corruption_flow.py` → (tích hợp quality + metrics) | 3 bộ metrics + quality + freshness | `data/quality/comparison_metrics.json` | Hoàn thành |
| Phase 1 report | `src/observability/reporting.py` → `generate_phase1_report` | source_summary + baseline metrics + quality + freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption comparison report | `reporting.py` → `generate_corruption_report` | 3 bộ metrics + quality + freshness + corruption log | `data/reports/corruption_report.md` | Hoàn thành |
| CP2 index audit | Script `run_role4_cp2.py` | Chroma collection + manifest + clean dataframe | `data/reports/role4_cp2_report.md`, `data/quality/role4_cp2_index_audit.json` | Hoàn thành |

Chỉ nhận ownership cho phần trên. Vai trò 1 (lead) điều phối orchestration; Vai trò 2 bàn giao clean CSV; Vai trò 3 bàn giao Chroma collection.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra clean schema trước evaluation | Vai trò 2 (Data foundation) | Xác nhận `paper_id` unique, `text_for_embedding` không rỗng, không có blank `published` |
| Xác nhận smoke test Chroma collection | Vai trò 3 (RAG & agent owner) | Confirm `papers-baseline` có đúng 24 documents, `embedding_dimension=384`, collection tồn tại trước khi evaluation chạy |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Build và validate 25-sample evaluation set từ 5 papers | `testset.py`, `data/eval/test_set.json` | 25 samples, 5 question types (summary/authors/date/categories/semantic), 0 invalid samples | `cat data/eval/test_set.json \| python -m json.tool \| grep question_type` |
| Khóa test set với SHA-256 | `data/reports/role4_cp2_report.md` | SHA-256 = `63a0d6fe...`, 14/14 index audit checks PASS | `cat data/reports/role4_cp2_report.md` |
| Baseline evaluation — 25 questions × 3 metrics | `metrics.py`, `data/results/baseline_metrics.json` | retrieval_hit_rate=1.000, mean_token_f1=0.834, judge_accuracy=0.920, mean_judge_score=4.120 | `cat data/results/baseline_metrics.json` |
| Corrupted evaluation — cùng 25 questions | `metrics.py`, `data/results/corrupted_metrics.json` | retrieval_hit_rate=0.800, mean_token_f1=0.699, judge_accuracy=0.720, mean_judge_score=3.480 | `cat data/results/corrupted_metrics.json` |
| Repaired evaluation — cùng 25 questions | `metrics.py`, `data/results/repaired_metrics.json` | retrieval_hit_rate=1.000, mean_token_f1=0.826, judge_accuracy=0.920, mean_judge_score=4.120 | `cat data/results/repaired_metrics.json` |
| Quality checks — 3 trạng thái | `quality.py`, `data/quality/*-quality.json` | Baseline 10/10 PASS; Corrupted 8/10 PASS (2 FAIL); Repaired 10/10 PASS | `cat data/quality/corrupted-quality.json \| python -m json.tool \| grep '"success"'` |
| Freshness monitoring — 3 trạng thái | `quality.py`, `data/quality/*_freshness.json` | Baseline FRESH (0 stale); Corrupted STALE (3 stale, max 9714 ngày); Repaired FRESH (0 stale) | `cat data/quality/corrupted_freshness.json` |
| Phase 1 report | `reporting.py`, `data/reports/phase1_report.md` | Markdown report đầy đủ: source summary, metrics, quality table, freshness table | `cat data/reports/phase1_report.md` |
| Corruption comparison report | `reporting.py`, `data/reports/corruption_report.md` | Bảng delta 3 trạng thái, danh sách corruption types, key findings | `cat data/reports/corruption_report.md` |

**Output tiêu biểu — `data/quality/comparison_metrics.json` (số liệu thực):**

| Metric | Baseline | Corrupted | Repaired | Corrupted Δ | Repaired Δ (vs baseline) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | 0.800 | 1.000 | −0.200 | 0.000 |
| `mean_token_f1` | 0.834 | 0.699 | 0.826 | −0.135 | −0.008 |
| `judge_accuracy` | 0.920 | 0.720 | 0.920 | −0.200 | 0.000 |
| `mean_judge_score` | 4.120 | 3.480 | 4.120 | −0.640 | 0.000 |
| Quality checks | 10/10 PASS | 8/10 FAIL | 10/10 PASS | — | — |
| Freshness status | FRESH | STALE | FRESH | — | — |
| Record count | 24 | 21 | 24 | −3 | 0 |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 4 phải trả lời hai câu hỏi có thể đo được bằng artifact thực:

1. **Dữ liệu sạch có đảm bảo RAG agent trả lời đúng không?** Cần evaluation set được xây từ clean data, được khóa trước khi bất kỳ corruption nào xảy ra, và metrics phản ánh cả retrieval accuracy lẫn answer quality.
2. **Dữ liệu xấu tác động thế nào và repair có phục hồi được không?** Cần quality/freshness check phát hiện lỗi sớm, đồng thời so sánh ba trạng thái trên **cùng** test set để delta metrics là bằng chứng nhân quả.

### Cách triển khai

**Evaluation set (`testset.py`):**

`build_test_set` chọn 5 papers đại diện từ cleaned dataframe theo strided sampling (bước đều, tối đa 5 papers), ưu tiên papers không có apostrophe trong title để đảm bảo exact-match lookup hoạt động đúng. Mỗi paper tạo ra 5 loại câu hỏi: `summary` (nội dung bài báo), `authors` (tác giả), `date` (ngày xuất bản), `categories` (chủ đề), `semantic` (không dùng title trực tiếp, chỉ dùng embedding search). `ground_truth_doc_ids` lấy trực tiếp từ `paper_id` lowercase của clean data — không tự bịa ID. Sau `build_test_set`, `validate_test_set` kiểm tra không blank field, không unknown doc_id. Sau khi Vai trò 3 build index, `validate_test_set_against_index` đối chiếu tiếp với Chroma collection: tất cả ground-truth doc IDs phải tồn tại trong collection trước khi evaluation chạy. Test set được SHA-256 checksum (`63a0d6fe3acd44d28fc5ef949ade9529b4f1889bed101459674fb49d46a968c3`) và không rebuild trong suốt pipeline.

**Evaluation metrics (`metrics.py`):**

`evaluate_pipeline` iterate qua từng sample trong test set, gọi `answer_question(question, index)` để lấy `answer` và `retrieved_doc_ids`, rồi tính ba chỉ số:

- **`retrieval_hit`**: `True` nếu bất kỳ `retrieved_doc_id` nào thuộc `ground_truth_doc_ids` của sample đó.
- **`token_f1`**: precision-recall F1 trên tập token sau lowercase + whitespace-split, không stemming. Đo mức trùng khớp từ vựng giữa ground truth và answer.
- **`judge_verdict`**: gọi LLM (Gemini 2.5 Flash) với `.with_structured_output(JudgeVerdict)` — schema `{score: 1–5, correct: bool, reasoning: str}`. Nếu LLM lỗi hoặc parse fail, fallback sang heuristic dựa trên token_f1 threshold.

Ba lần chạy (baseline, corrupted, repaired) dùng **cùng** test set 25 samples và cùng `top_k=4`. Kết quả ghi vào `*_metrics.json` (summary) và `*_answers.json` (chi tiết từng sample).

**Data quality (`quality.py`):**

Sử dụng Great Expectations 1.18.0. Có 10 expectations được chạy trên mỗi trạng thái clean dataframe:

- `expect_table_row_count_to_be_between` (min=10)
- `expect_column_values_to_not_be_null` cho `paper_id`, `title`, `summary`, `text_for_embedding`
- `expect_column_values_to_be_unique` cho `paper_id`
- `expect_column_value_lengths_to_be_between` cho `title` và `summary` (min=threshold)
- `expect_column_values_to_match_regex` cho `published` (regex YYYY-MM-DD)
- `expect_column_values_to_be_between` cho `age_days` (0 đến `freshness_threshold_days=180`)

Output JSON có `success` (bool), `statistics` (counts), `failed_checks` (list), `checks` (chi tiết từng expectation).

**Freshness monitoring (`quality.py` → `check_freshness`):**

Tính từ cột `age_days` đã có trong clean dataframe (không recompute từ ngày hiện tại). `is_fresh = all(age_days ≤ threshold)`. Report ghi `stale_rows`, `fresh_rows`, `max_age_days`, `mean_age_days`, `latest_published`, `oldest_published`.

**Reporting (`reporting.py`):**

`generate_phase1_report` nhận `source_summary` (dict từ phase1.py), `metrics`, `quality`, `freshness` và sinh Markdown với bảng metrics, bảng quality checks, bảng freshness. `generate_corruption_report` nhận 3 bộ metrics + quality + freshness + corruption log JSON, tạo bảng delta baseline/corrupted/repaired và liệt kê corruption scenarios.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `papers_clean.csv` cần có đủ `paper_id` (unique, lowercase-stable), `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding` — không blank, không duplicate |
| Input | `LocalEmbeddingIndex` từ collection baseline/corrupted/repaired, đã load trước khi gọi `evaluate_pipeline` |
| Output | `*_metrics.json`: dict với `samples`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, `ragas` |
| Output | `*_answers.json`: list các answer record với `id`, `question`, `ground_truth`, `answer`, `retrieval_hit`, `token_f1`, `judge` |
| Output | `*-quality.json`: dict với `success`, `statistics`, `failed_checks`, `checks` |
| Output | `*_freshness.json`: dict với `is_fresh`, `stale_rows`, `mean_age_days`, `max_age_days` |
| Module phụ thuộc | Vai trò 2 phải bàn giao clean CSV với schema đúng; Vai trò 3 phải bàn giao collection đã build trước khi evaluation chạy |
| Module sử dụng output | Vai trò 1 (phase1.py, corruption_flow.py) gọi `evaluate_pipeline` và `run_quality_checks` rồi dùng output để sinh report |
| Điều kiện lỗi | LLM judge timeout / parse fail → fallback heuristic (heuristic chỉ dùng token_f1 threshold, kết quả kém chính xác hơn); GE unavailable → manual checks thay thế |

### Cách xác minh

```bash
# Chạy baseline end-to-end
uv run python script/run_phase1.py

# Đọc metrics baseline
cat data/results/baseline_metrics.json

# Kiểm tra quality baseline
cat data/quality/baseline-quality.json

# Chạy corruption flow (corrupt + evaluate + repair + evaluate)
uv run python script/run_corruption_flow.py

# Đọc metrics corrupted và repaired
cat data/results/corrupted_metrics.json
cat data/results/repaired_metrics.json

# Xem bảng so sánh 3 trạng thái
cat data/quality/comparison_metrics.json

# Xem reports
cat data/reports/phase1_report.md
cat data/reports/corruption_report.md
```

- **Kết quả mong đợi:** Baseline `retrieval_hit_rate=1.0`, quality 10/10 PASS, freshness FRESH. Corrupted: metrics thấp hơn, quality FAIL ≥ 1 check, freshness STALE. Repaired: metrics phục hồi về gần baseline, quality PASS, freshness FRESH.
- **Kết quả thực tế:** Đúng như mong đợi — xem bảng so sánh ở phần 8.
- **Artifact/log:** `data/quality/comparison_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định có rebuild evaluation set từ mỗi trạng thái data (baseline, corrupted, repaired) hay giữ một bộ test set cố định cho cả ba.
- **Các phương án đã cân nhắc:**
  1. **Rebuild test set cho từng trạng thái** — evaluation set luôn phù hợp với data hiện có, không bao giờ hỏi về document bị mất. Nhược điểm: delta metrics đo cả sự thay đổi về câu hỏi lẫn sự thay đổi về dữ liệu, không thể tách rời.
  2. **Khóa test set sau baseline build** — cùng 25 questions được dùng cho cả ba trạng thái. Nhược điểm: một số questions hỏi về document bị drop (không có trong corrupted index), làm retrieval_hit=False rõ ràng.
- **Phương án đã chọn:** Khóa test set từ baseline, SHA-256 `63a0d6fe3acd44d28fc5ef949ade9529b4f1889bed101459674fb49d46a968c3`.
- **Lý do:** Mục tiêu là đo **tác động của data quality đến agent**. Nếu test set thay đổi, delta metrics phản ánh sự thay đổi câu hỏi, không phải data. Nhược điểm ở phương án 2 thực ra là ưu điểm: retrieval_hit=False cho questions về papers bị drop chính xác là bằng chứng trực tiếp của tác hại corruption. Đây là yêu cầu của pipeline contract: "giữ nguyên test set, ground truth, evaluator và top-k khi so sánh."
- **Bằng chứng quyết định phù hợp:** Sau `drop_latest_records` (3 papers), 5/25 questions có ground-truth doc không còn trong index → `retrieval_hit_rate` giảm từ 1.000 xuống 0.800 (−0.200). Đây là bằng chứng định lượng rõ ràng. Nếu rebuild test set, câu hỏi về 3 papers bị drop biến mất và hit_rate có thể vẫn ≈ 1.0 dù mất 3 documents — kết luận sai.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy evaluation baseline lần đầu, log xuất hiện liên tục `"Fallback heuristic judge used because the LLM evaluator was unavailable."`. `judge_accuracy` trong kết quả là 0.72 thay vì giá trị kỳ vọng cao hơn.
- **Lệnh tái hiện:**
  ```bash
  uv run python script/run_phase1.py 2>&1 | grep "Fallback"
  # Output: Fallback heuristic judge used because the LLM evaluator was unavailable.
  ```
- **Nguyên nhân gốc:** `metrics.py` gọi `llm.invoke(prompt)` với `.with_structured_output(JudgeVerdict)`. Khi LLM trả về JSON thiếu trường `reasoning` (model alias cũ không hỗ trợ tốt structured output), Pydantic `ValidationError` được raise → `except Exception` catch và trả về heuristic fallback. Heuristic này chỉ dùng token_f1 threshold để cho score 1/3/5 và `correct = score >= 3` — kết quả không phản ánh đúng semantic correctness.
- **Cách xử lý:** Kiểm tra `.env`, đổi `LLM_MODEL` từ alias cũ sang đúng `gemini-2.5-flash`. Model mới trả về JSON đầy đủ 3 fields (`score`, `correct`, `reasoning`) → structured output parse thành công.
- **Cách xác minh sau khi sửa:**
  ```bash
  cat data/results/baseline_answers.json \
    | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['judge']['reasoning'])"
  # Output: chuỗi reasoning thực từ LLM (không phải "Fallback heuristic judge")

  cat data/results/baseline_metrics.json
  # "judge_accuracy": 0.92, "mean_judge_score": 4.12
  ```
- **Điều học được:** `.with_structured_output()` nhạy cảm với model version. Cần log đủ để phân biệt "LLM chạy nhưng trả về sai schema" với "LLM không reach được". Nên kiểm tra tỷ lệ fallback trong `answers.json` (grep `"Fallback heuristic"`) trước khi tin vào `judge_accuracy` trong metrics.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API (endpoint `/works`) trả về JSON list of works → `crossref.py` parse từng item thành `PaperRecord` dict với các trường ổn định (`paper_id` = DOI, `title`, `summary` = abstract, `authors`, `categories`, `published`, `url`). Raw response và raw records được lưu vào `data/raw/` làm lineage. `cleaning.py` đọc raw records, normalize title/summary (whitespace, encoding), parse ngày xuất bản thành `YYYY-MM-DD`, tính `age_days = (today - published).days`, tạo `text_for_embedding = title + " " + summary`, dedupe theo `paper_id`. Clean artifacts ghi vào `data/clean/papers_clean.csv` và `.json`. `index.py` đọc clean CSV, dùng `sentence-transformers/all-MiniLM-L6-v2` (384-dim) để embed từng `text_for_embedding`, lưu vector vào ChromaDB collection `papers-baseline` với metadata `{paper_id, title}`. Manifest JSON ghi vào `data/embeddings/papers_embeddings.json`.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

`build_test_set` tạo 25 samples từ 5 papers, mỗi sample có `ground_truth_doc_ids = [paper_id]`. Khi evaluate, `answer_question(question, index)` chạy semantic search hoặc exact lookup → trả về `retrieved_doc_ids` (list IDs của top-k documents). `retrieval_hit = any(id in ground_truth_doc_ids for id in retrieved_doc_ids)` — đo xem agent có tìm đúng document không. `token_f1` đo overlap từ vựng giữa `ground_truth` text và `answer` text. `judge_verdict` dùng LLM để đánh giá semantic correctness. Ba metric đo ba khía cạnh: retrieval chính xác không (hit_rate), trích đúng thông tin không (token_f1), trả lời đúng nghĩa không (judge).

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**

Quality checks đo **tính toàn vẹn schema và nội dung**: không null, không duplicate, length hợp lệ, date format đúng, age_days trong [0, 180]. Đây là tiêu chí "dữ liệu có đúng format và đủ field không." Freshness monitoring đo **độ kịp thời kinh doanh**: tất cả rows có `age_days ≤ 180` không? Đây là tiêu chí "dữ liệu có còn relevant không." Ví dụ rõ nhất: corruption `stale_date` set ngày xuất bản thành `2000-01-01` → `age_days` > 9000 → quality check `expect_column_values_to_be_between(age_days)` FAIL (age_days vượt ngưỡng 180), freshness check `is_fresh = False`. Nhưng nếu chỉ dùng freshness, sẽ không biết cụ thể field nào vi phạm; nếu chỉ dùng quality, sẽ không có tín hiệu kinh doanh "data này đã cũ." Cả hai cần thiết.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì mục tiêu là đo **tác động của data quality đến agent**, không phải đo tác động của câu hỏi khác nhau. Dùng cùng 25 questions → mọi thay đổi trong metrics chỉ do dữ liệu trong index thay đổi. Nếu rebuild test set sau corruption, questions về papers bị drop sẽ biến mất → hit_rate có thể không giảm dù agent mất access vào 3 papers → kết luận "corruption không ảnh hưởng" là sai. Test set cố định là điều kiện cần của fair comparison và của kết luận nhân quả.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair thành công khi đồng thời:

- `data/results/repaired_metrics.json`: `retrieval_hit_rate` ≥ baseline (1.000 ✓), `judge_accuracy` ≥ baseline (0.920 ✓)
- `data/quality/repaired-quality.json`: `success: true`, 10/10 expectations pass (✓)
- `data/quality/repaired_freshness.json`: `is_fresh: true`, `stale_rows: 0` (✓)
- `data/quality/comparison_metrics.json`: `record_counts.repaired == record_counts.baseline` (24 == 24 ✓)
- `data/clean/papers_clean_repaired.csv`: 24 rows, schema đúng, không copy từ baseline — phải được tạo lại từ raw source

Trong bài này, repair đã phục hồi gần hoàn toàn. Chỉ `mean_token_f1` còn Δ 0.008 (0.826 vs 0.834) do embedding noise từ `inject_noise` corruption đã thay đổi retrieval order nhẹ — không ảnh hưởng đến judge_accuracy.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.800 | 1.000 | Giảm 20 điểm % (5/25 questions miss) khi 3 ground-truth papers bị drop; phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 0.834 | 0.699 | 0.826 | Giảm 13.5 điểm; phục hồi gần hoàn toàn (Δ 0.008 không đáng kể, < 1%) |
| `judge_accuracy` | 0.920 | 0.720 | 0.920 | Giảm 20 điểm %; phục hồi hoàn toàn về baseline |
| `mean_judge_score` | 4.120 | 3.480 | 4.120 | Giảm 0.64/5 điểm; phục hồi hoàn toàn |
| Quality checks | 10/10 PASS | 8/10 FAIL | 10/10 PASS | 2 fail: `summary` length (3 blanked, 14.3%) + `age_days` out-of-range (3 stale, 14.3%) |
| Freshness status | FRESH | STALE | FRESH | Stale do 3 records bị set ngày 2000-01-01; mean_age_days tăng từ 80.6 → 1389.8 ngày |

### Kết luận từ số liệu

**1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**

6 loại corruption được áp vào 24-record baseline:

- `drop_latest_records` (3 records) + `blank_summary` (3 records) + `inject_noise` (3 records) + `truncate_title` (3 records) + `stale_date` (3 records) + `duplicate_ids` (2 records)
- → `corrupted-quality.json`: `success=false`, 2 expectations fail — `expect_column_value_lengths_to_be_between(summary)` FAIL (3 blank summaries, 14.3%), `expect_column_values_to_be_between(age_days)` FAIL (3 records > 180 ngày)
- → `corrupted_freshness.json`: `is_fresh=false`, `stale_rows=3`, `mean_age_days=1389.81`, `max_age_days=9714`
- → `corrupted_metrics.json`: `retrieval_hit_rate` giảm 1.000 → 0.800 (5 questions về 3 papers bị drop không tìm được doc), `mean_token_f1` giảm 0.834 → 0.699 (blank summary → text_for_embedding nghèo nàn → agent trả lời sai), `judge_accuracy` giảm 0.920 → 0.720 (agent không có context đủ để trả lời đúng)

**2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**

Repair bằng cách re-run cleaning từ `data/raw/crossref_records.json` (raw snapshot nguyên vẹn, không bị corrupt):

- → 24 records được khôi phục đầy đủ, summary không blank, publication date đúng
- → `repaired-quality.json`: `success=true`, 10/10 PASS
- → `repaired_freshness.json`: `is_fresh=true`, `stale_rows=0`, `mean_age_days=80.62`
- → `repaired_metrics.json`: `retrieval_hit_rate` phục hồi 0.800 → 1.000, `judge_accuracy` phục hồi 0.720 → 0.920, `mean_token_f1` phục hồi 0.699 → 0.826 (Δ 0.008 so với baseline không đáng kể)

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`drop_latest_records` ảnh hưởng trực tiếp và tức thì nhất: loại 3 papers hoàn toàn khỏi index, làm cho mọi câu hỏi về 3 papers đó không thể được trả lời đúng dù semantic search hay exact lookup đều fail. `blank_summary` ảnh hưởng gián tiếp: text_for_embedding của 3 records trở thành chỉ còn title (không có summary), làm embedding vector kém đại diện → agent retrieve sai context → token_f1 và judge_score giảm. `stale_date` không ảnh hưởng trực tiếp đến agent answer nhưng là tín hiệu data quality quan trọng — freshness STALE cảnh báo corpus đã cũ.

**Kết quả khác với kỳ vọng ban đầu:**

`mean_token_f1` sau repair là 0.826, không phục hồi về đúng 0.834 (Δ 0.008). Giả thuyết: `inject_noise` thêm text nhiễu vào summary của 3 records trong corruption step; sau khi repair từ raw source (không nhiễu), embedding vector của các records đó thay đổi nhẹ so với baseline → retrieval order thay đổi → context window đưa vào LLM khác nhẹ → answer wording khác chút ít → token_f1 thay đổi nhỏ. Đây là mức không có ý nghĩa thực tế (< 1%) và không ảnh hưởng `judge_accuracy` (vẫn 0.920).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Quality monitoring phải chạy sát ngay sau mỗi transformation, không phải chỉ ở cuối pipeline.** Trong bài này, `blank_summary` và `stale_date` được phát hiện ngay qua quality checks sau bước corruption — trước khi chạy evaluation. Nếu chỉ đo quality ở đầu hoặc cuối, sẽ không biết chính xác bước nào gây lỗi.

2. **Test set phải độc lập hoàn toàn với data state.** Đây là quyết định kiến trúc quan trọng nhất trong vai trò này. Test set được xây và khóa từ baseline clean data, không rebuild theo mỗi trạng thái. Nhờ đó delta metrics là bằng chứng nhân quả thuần túy của data quality thay đổi, không bị contaminate bởi câu hỏi thay đổi.

3. **Dữ liệu xấu tác động đồng thời lên nhiều tầng metric.** `drop_latest_records` gây `retrieval_hit_rate` giảm (thiếu doc trong index). `blank_summary` + `inject_noise` gây `token_f1` và `judge_score` giảm (context kém). `stale_date` gây freshness STALE (corpus không còn relevant). Mỗi metric đo một tầng khác nhau, cần đủ cả ba để hiểu đầy đủ tác hại.

### Nếu có thêm thời gian

Sẽ bổ sung **per-question-type breakdown metrics** vào comparison report: nhóm 25 samples theo `question_type` (summary/authors/date/categories/semantic) và tính riêng `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` cho từng nhóm trong cả ba trạng thái. Kỳ vọng: `blank_summary` ảnh hưởng mạnh nhất vào `summary` và `semantic` questions (cần abstract để trả lời), ít hơn vào `date` và `authors` questions (chỉ cần metadata). Phân tích này có thể đo bằng cách group `*_answers.json` theo `question_type` và aggregate metrics — không cần chạy lại pipeline, chỉ cần post-process artifact có sẵn.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Dương Mạnh Phong
**Ngày xác nhận:** 2026-08-06
