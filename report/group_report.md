# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Khóa/Lớp | K3 |
| Tên nhóm | C4-1 |
| Repository | https://github.com/sondang04/K3_Day10_Data-Pipeline-Data-Observability-C4-1.git |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đặng Thái Nam Sơn | 2A202601431 | Pipeline integration & orchestration owner | `src/pipelines/phase1.py`, `script/run_ragas_comparison.py`, chạy và đối chiếu baseline/corrupted/repaired |
| 2 | Trần Đình Đăng | 2A202601998 | Ingestion, cleaning & corruption owner | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` |
| 3 | Dương Mạnh Phong | 2A202601557 | Observability & evaluation owner | `src/observability/quality.py`, `src/observability/reporting.py`, `src/evaluation/testset.py`, `script/run_role4_cp0_cp1.py`, `script/run_role4_cp2.py` |
| 4 | Chu Thành Dũng | 2A2020601405 | Retrieval, embedding & LLM/agent owner | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/llm.py`, `src/retrieval/agent.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành cả hai pha của bài lab. Pha 1 dựng baseline pipeline chạy end-to-end: lấy dữ liệu từ Crossref REST API, làm sạch thành 24 record, tạo embedding bằng `all-MiniLM-L6-v2` và index vào ChromaDB, sinh evaluation set 25 câu hỏi thuộc 5 nhóm, đánh giá agent, chạy 25 data quality checks và freshness monitoring, cuối cùng xuất báo cáo Markdown. Toàn bộ artifact có trong `data/raw/`, `data/clean/`, `data/embeddings/`, `data/eval/`, `data/results/`, `data/quality/` và `data/reports/`.

Pha 2 tạo corrupted dataset (24 → 21 record) với 6 loại corruption, rebuild index, đánh giá lại trên **cùng** test set, repair từ raw records rồi đánh giá lần nữa. Corruption ảnh hưởng rõ nhất là **xóa record**: 3 record bị loại bỏ, trong đó `10.3390/buildings16132637` là ground truth của 5 câu hỏi `02-*`; retrieval chuyển sang trả về paper lân cận `10.63646/kpqm1958` khiến cả 5 câu mất hit. Backdating ngày xuất bản về 2001–2005 làm freshness chuyển từ FRESH sang STALE, còn blank summary và truncate title làm 5/25 quality checks fail.

Repair từ `data/raw/crossref_records.json` phục hồi đủ 24/24 record, đưa `retrieval_hit_rate` về 1.000, `mean_token_f1` về 0.834 và `mean_judge_score` về 4.640, quality trở lại 25/25 PASS và freshness về FRESH.

Giới hạn quan trọng nhất: Ragas chưa chạy được trọn vẹn (chi phí thời gian, xem mục 12), corruption "add duplicate rows" trên thực tế chưa tạo dòng trùng, và `judge_accuracy` có nhiễu ±0.04 do LLM judge không hoàn toàn deterministic.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (/works)
    -> data/raw/crossref_response.json, data/raw/crossref_records.json
    -> cleaning và data modeling -> data/clean/papers_clean.csv|json
    -> embedding MiniLM + ChromaDB -> data/embeddings/, data/chroma/
    -> evaluation baseline -> data/results/baseline_metrics.json, baseline_answers.json
    -> quality/freshness -> data/quality/baseline-quality.json, freshness_report.json
    -> corruption -> data/clean/papers_clean_corrupted.csv, data/results/corruption_log.json
    -> re-index và re-evaluate -> data/results/corrupted_metrics.json
    -> repair từ raw records -> data/clean/papers_clean_repaired.csv
    -> comparison report -> data/reports/corruption_report.md, ragas_mode_comparison.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref `/works` | Fetch có retry/backoff cho 429/503, parse JATS abstract, chuẩn hóa DOI | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Trần Đình Đăng |
| Cleaning | Raw records | Chuẩn hóa text, parse date, tính `age_days`, tạo `text_for_embedding`, dedupe | `data/clean/papers_clean.csv|json` | Trần Đình Đăng |
| Embedding/index | Cleaned dataframe | `all-MiniLM-L6-v2`, ChromaDB PersistentClient, cosine space | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Chu Thành Dũng |
| Evaluation | Cleaned dataframe | Sinh 25 câu hỏi 5 loại, token F1, LLM judge | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Dương Mạnh Phong |
| Observability | Cleaned/corrupted/repaired dataframe | 10 expectation GX + 15 CP1 contract checks, freshness | `data/quality/*.json` | Dương Mạnh Phong |
| Corruption/repair | Baseline clean CSV + raw records | 6 kịch bản corruption, repair bằng cách clean lại từ raw | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted|repaired.*` | Trần Đình Đăng |
| Orchestration | Toàn bộ module trên | Thứ tự chạy, logging từng bước, trace và so sánh 3 trạng thái | `data/reports/phase1_report.md`, `corruption_report.md`, `ragas_mode_comparison.md`, `data/quality/pipeline_trace.jsonl` | Đặng Thái Nam Sơn |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `openrouter` (truyền qua biến môi trường khi chạy; file `.env` trong repo vẫn để `gemini`) |
| `LLM_MODEL` | `openai/gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 record sạch (raw response chứa 48 item) |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed, nếu có | `20260806` — seed cho RNG corruption, đặt trong `script/run_ragas_comparison.py` |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

Chạy cả vòng đời trong một tiến trình kèm trace và so sánh (seed cố định):

```bash
python script/run_ragas_comparison.py 0
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06T05:32:00Z | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption flow | Thành công | 2026-08-06T05:33:54Z | `data/reports/corruption_report.md`, `data/results/corrupted_metrics.json`, `repaired_metrics.json` |
| Trace + so sánh 3 trạng thái | Thành công | 2026-08-06T05:35Z | `data/reports/ragas_mode_comparison.md`, `data/quality/pipeline_trace.jsonl` (33 event) |

Lần chạy gần nhất được thực hiện qua `script/run_ragas_comparison.py 0`; script này gọi trực tiếp `phase1.main()` rồi `corruption_flow.main()` trong cùng tiến trình nên artifact sinh ra giống hệt khi chạy hai script riêng lẻ.

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter | `query.bibliographic=agentic retrieval augmented generation large language model`, `filter=from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 (snapshot trong `data/raw/`) |
| Số record nhận được | 48 item trong raw response, parse và giữ lại 24 record (`total-results` của Crossref: 99.740) |
| Cơ chế retry/backoff | Retry tối đa 3–4 lần cho 429/503, tôn trọng header `Retry-After`, backoff giữa các lần thử |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string | Có | DOI dùng làm document ID ổn định | Bỏ record nếu thiếu DOI |
| `title` | string | Có | Tiêu đề bài báo | Bỏ record nếu rỗng hoặc ngắn hơn ngưỡng |
| `summary` | string | Có | Abstract đã bỏ thẻ JATS | Bỏ record nếu rỗng/quá ngắn (826–2601 ký tự trong dataset thực tế) |
| `authors`, `authors_joined` | list / string | Không | Danh sách tác giả và bản nối chuỗi cho metadata | Để rỗng nếu Crossref không trả `author` |
| `categories`, `categories_joined`, `primary_category` | list / string | Không | Chủ đề; Crossref thường thiếu `subject` nên fallback sang tên tạp chí và `type` | Fallback container-title/type |
| `published`, `updated` | string `YYYY-MM-DD` | Có | Ngày xuất bản và ngày cập nhật | Bỏ record nếu không parse được ngày |
| `age_days` | int | Có | Tuổi dữ liệu tính từ ngày chạy (thực tế 5–175 ngày) | Chặn dưới ở 0 vì Crossref có ngày tương lai |
| `summary_chars` | int | Có | Độ dài abstract, phục vụ quality check | Tính lại từ `summary` |
| `text_for_embedding` | string | Có | Chuỗi đưa vào embedding | Bỏ record nếu rỗng |
| `abs_url`, `pdf_url`, `comment` | string | Không | Link và metadata phụ | Để rỗng |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ record thiếu DOI/title/abstract/ngày | Completeness / Validity | 0 trên snapshot hiện tại (24 raw → 24 clean) | `data/clean/papers_clean.csv` và log `[phase1] 2/8` |
| Chuẩn hóa whitespace, bỏ thẻ JATS và nhãn "Abstract"/"Summary" đầu abstract | Consistency | Toàn bộ 24 record | So sánh `summary` trong `data/raw/crossref_records.json` và `data/clean/papers_clean.csv` |
| Deduplicate theo `paper_id` và theo title đã chuẩn hóa | Uniqueness | 0 trùng còn lại | Check `cp1_paper_id_unique_normalized`, `cp1_title_unique_normalized` PASS |
| Chặn `age_days` không âm | Validity | Áp dụng cho mọi record | Check `cp1_age_days_non_negative` PASS |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- `text_for_embedding` ghép các trường có ngữ nghĩa theo dạng có nhãn: `Title: ... / Authors: ... / Categories: ... / Published: ... / Summary: ...`. Ghép cả tiêu đề và abstract giúp câu hỏi dạng semantic vẫn khớp được khi người dùng chỉ mô tả chủ đề chứ không trích nguyên tiêu đề.
- Document ID dùng chính DOI (`paper_id`) vì DOI là khóa ổn định của Crossref, cho phép đối chiếu ground truth giữa baseline, corrupted và repaired mà không phụ thuộc thứ tự dòng.
- `age_days` = số ngày giữa ngày chạy pipeline và `published`, chặn dưới ở 0 vì Crossref có record ghi ngày xuất bản ở tương lai. `age_days` là tín hiệu chính cho freshness và cho check `cp1_age_days_within_freshness_threshold`.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 25 |
| Các `question_type` | `summary`, `authors`, `date`, `categories`, `semantic` — mỗi loại 5 câu, trên 5 paper đại diện |
| Ground-truth document ID | `ground_truth_doc_ids` lấy trực tiếp từ `paper_id` (DOI) của paper sinh ra câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB PersistentClient tại `data/chroma/`, collection `papers-baseline` / `papers-corrupted` / `papers-repaired`, cosine space |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenRouter, `openai/gpt-4o-mini` (dùng cho LLM judge và agent demo) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`, 25 sample, chỉ sinh lại khi đặt `REFRESH_TEST_SET=1` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Nếu sinh lại test set từ corrupted dataset thì câu hỏi và ground truth sẽ được tạo từ chính dữ liệu đã hỏng — ví dụ ground truth của một câu summary sẽ là abstract rỗng, hoặc câu hỏi về paper đã bị xóa sẽ biến mất khỏi bộ đo. Khi đó metric có thể vẫn cao dù dữ liệu đã hỏng, và phép so sánh mất ý nghĩa. Giữ nguyên test set nghĩa là giữ nguyên "kỳ vọng của người dùng": cùng 25 câu hỏi, cùng ground truth, chỉ có corpus thay đổi, nên mọi chênh lệch metric đều quy được về chất lượng dữ liệu. Điều này cũng là lý do 5 trong 25 câu hỏi vẫn hỏi về paper đã bị xóa — và chính chúng để lộ ra thiệt hại.

Có một chi tiết cần lưu ý khi đọc số: câu hỏi thuộc nhóm `summary`, `authors`, `date`, `categories` đều trích nguyên tiêu đề trong dấu nháy đơn nên `qa.answer_question` sẽ đi qua nhánh lookup chính xác; nhóm `semantic` cố ý không trích tiêu đề nên chỉ có thể trả lời được qua embedding search. Nhờ vậy `retrieval_hit_rate` mới thực sự đo retrieval thay vì luôn bằng 1.0.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 48 item raw, 24 record đã parse |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | Có | 24 dòng, 16 cột |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection `papers-baseline`, 24 document |
| Evaluation set | `data/eval/test_set.json` | Có | 25 câu, 5 question_type |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` chi tiết từng câu |
| Quality/freshness | `data/quality/baseline-quality.json`, `data/quality/freshness_report.json` | Có | 25 check, freshness FRESH |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh lúc 2026-08-06T05:32:00Z |
| Agent demo | `data/results/agent_demo_answers.json` | Có | `status: ok`, provider `openrouter`, model `openai/gpt-4o-mini` |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.000 | Cả 25 câu đều có ground-truth document nằm trong top-4, kể cả 5 câu semantic không trích tiêu đề |
| `mean_token_f1` | 0.834 | Câu trả lời trùng phần lớn token với ground truth; phần hụt chủ yếu ở nhóm `categories` vì Crossref thiếu `subject` nên fallback sang tên tạp chí |
| `judge_accuracy` | 0.920 | 23/25 câu được `gpt-4o-mini` chấm là đúng về bản chất |
| `mean_judge_score` | 4.640 | Thang 1–5 |
| Ragas, nếu có | N/A | Chưa chạy — xem mục 12 |

## 8. Data quality và freshness

### Quality checks

Tổng cộng 25 check: 10 expectation của Great Expectations 1.19.1 và 15 contract check tự viết (tiền tố `cp1_`). Baseline PASS 25/25.

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `expect_table_row_count_to_be_between` | Completeness | ≥ 10 dòng | Pass — 24 dòng | `data/quality/baseline-quality.json` |
| `expect_column_values_to_be_unique` (`paper_id`) | Uniqueness | Không trùng DOI | Pass — 0 vi phạm | như trên |
| `expect_column_value_lengths_to_be_between` (`summary`) | Validity | ≥ 80 ký tự | Pass — ngắn nhất 826 ký tự | như trên |
| `expect_column_value_lengths_to_be_between` (`title`) | Validity | ≥ 12 ký tự | Pass — 0 vi phạm | như trên |
| `expect_column_values_to_match_regex` (`published`) | Validity | `^\d{4}-\d{2}-\d{2}$` | Pass — 0 vi phạm | như trên |
| `expect_column_values_to_be_between` (`age_days`) | Timeliness | 0 ≤ age ≤ 180 | Pass — max 175 ngày | như trên |
| `cp1_summary_not_blank`, `cp1_summary_min_length` | Completeness / Validity | Không rỗng, ≥ 80 ký tự | Pass | như trên |
| `cp1_paper_id_unique_normalized`, `cp1_title_unique_normalized` | Uniqueness | Không trùng sau chuẩn hóa | Pass | như trên |
| `cp1_age_days_matches_published` | Consistency | Lệch ≤ 1 ngày so với ngày tính lại | Pass — 0 dòng lệch | như trên |
| `cp1_source_timestamp_present` | Timeliness | Có cột timestamp nguồn hợp lệ | Pass — dùng cột `updated` | như trên |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned dataset (`data/clean/papers_clean.csv`), báo cáo tại `data/quality/freshness_report.json` |
| Timestamp mới nhất | `published` mới nhất: 2026-08-01; cũ nhất: 2026-02-12 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | Fresh |
| Lý do | 0/24 dòng có `age_days` vượt ngưỡng (max 175 ngày), và ngày xuất bản mới nhất chỉ cách thời điểm chạy 5 ngày. Freshness được tính lại từ `published` chứ không tin tuyệt đối vào `age_days` đã lưu, nên nếu ai đó sửa ngày mà quên cập nhật `age_days` thì báo cáo vẫn phát hiện được |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Xóa record | `random.sample` rồi drop khỏi dataframe | 3 | Row count giảm, mất document | 24 → 21 dòng; 5 câu hỏi `02-*` mất ground truth, hit chuyển False | Clean lại từ `data/raw/crossref_records.json` |
| Blank summary | Gán `summary = ""` và dựng lại `text_for_embedding` | 3 | `summary` rỗng, độ dài dưới ngưỡng | `cp1_summary_not_blank` và `cp1_summary_min_length` FAIL, mỗi check 3 dòng vi phạm | như trên |
| Inject noise | Chèn token nhiễu (`XXX`, `[CORRUPTED]`, …) vào giữa abstract | 3 | Giảm chất lượng embedding | Không làm fail check nào; ảnh hưởng gián tiếp qua embedding | như trên |
| Truncate title | Cắt tiêu đề còn 10–50% rồi thêm `...` | 3 | Độ dài title dưới ngưỡng | `expect_column_value_lengths_to_be_between` (title) FAIL, 3 dòng | như trên |
| Stale publication date | Đặt `published`/`updated` về 1999–2005 và tính lại `age_days` | 3 | Freshness STALE, `age_days` vượt ngưỡng | `expect_column_values_to_be_between` (age_days) và `cp1_age_days_within_freshness_threshold` FAIL; freshness STALE, oldest_published = 2001-01-01 | như trên |
| Duplicate IDs | Đổi `paper_id` thành `<doi>_dup_<i>` | 2 | Trùng lặp `paper_id` | **Không tạo được tín hiệu**: dataframe vẫn 21 dòng với 21 ID duy nhất nên các check uniqueness vẫn PASS (xem mục 12) | như trên |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 loại corruption, số record bị tác động và `initial_count`/`final_count` (24 → 21). Hai điểm cần sửa: (1) mục `duplicate_ids` ghi `original_ids` **sau** khi đã đổi ID nên `original_ids` trùng hệt `new_ids`, không dùng để hoàn tác được; (2) mục `drop_latest_records` mô tả là "latest" nhưng thực tế chọn ngẫu nhiên.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair **không** đụng vào corrupted dataset. `corruption_flow.py` đọc lại `data/raw/crossref_records.json` — snapshot raw được lưu ngay sau lần gọi Crossref đầu tiên, trước mọi bước biến đổi — rồi chạy lại đúng hàm `build_clean_dataframe` mà baseline đã dùng, build index mới vào collection `papers-repaired` và đánh giá lại. Nghĩa là repaired dataset được dựng lại từ đầu theo cùng một contract, không phải vá từng ô dữ liệu hỏng. Bằng chứng: trace trong `data/results/ragas_modes/comparison.json` so từng record giữa baseline và repaired trên các cột `title`, `summary`, `published`, `text_for_embedding` và cho kết quả `restored: 24`, `unrestored: []`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | 1.000 | 0.800 | 1.000 | −0.200 | 100% | 5 câu mất hit đúng bằng số câu hỏi về paper bị xóa |
| `mean_token_f1` | 0.834 | 0.639 | 0.834 | −0.195 | 100% | Trùng khớp tuyệt đối với baseline |
| `judge_accuracy` | 0.920 | 0.640 | 0.880 | −0.280 | ~86% | Chênh 0.04 là nhiễu của judge, không phải mất mát dữ liệu — xem ghi chú dưới |
| `mean_judge_score` | 4.640 | 3.880 | 4.640 | −0.760 | 100% | Trùng khớp tuyệt đối với baseline |
| Quality checks pass/fail | 25/25 PASS | 20/25 FAIL | 25/25 PASS | 5 check chuyển FAIL | 100% | 5 check fail đều recover |
| Freshness status | FRESH (0/24 stale) | STALE (3/21 stale) | FRESH (0/24 stale) | STALE | 100% | `oldest_published` 2026-02-12 → 2001-01-01 → 2026-02-12 |

Ghi chú về `judge_accuracy` của repaired: repaired dataset **giống hệt** baseline theo từng record, và cả 25 câu trả lời của agent cũng giống hệt baseline. Chênh lệch 0.920 → 0.880 đến từ đúng một câu (`04-summary`): cả hai lần LLM judge đều cho điểm 3 nhưng cờ `correct` lật từ `true` sang `false`. Đây là dao động của judge chứ không phải tín hiệu về dữ liệu; với 25 sample thì mỗi câu lật cờ đã làm metric đổi 0.04.

Hai chuỗi nhân quả có artifact hỗ trợ:

1. **Xóa 3 record** (`corruption_log.json`, `drop_latest_records`) → row count 24 → 21 và paper `10.3390/buildings16132637` biến mất khỏi corpus → 5 câu hỏi `02-*` chuyển `retrieval_hit` từ `true` sang `false`, top-1 chuyển sang paper lân cận `10.63646/kpqm1958`, `retrieval_hit_rate` 1.000 → 0.800 và `mean_token_f1` 0.834 → 0.639 (`data/results/corrupted_answers.json`, mục 4 của `data/reports/ragas_mode_comparison.md`).
2. **Repair từ raw records** (`corruption_flow.py` bước 8) → 24/24 record khôi phục đúng nội dung, quality trở lại 25/25 PASS và freshness trở lại FRESH → `retrieval_hit_rate`, `mean_token_f1`, `mean_judge_score` về đúng giá trị baseline; riêng `judge_accuracy` lệch 0.04 vì lý do nhiễu judge nêu trên.

Ngoài ra, backdating ngày xuất bản → `cp1_age_days_within_freshness_threshold` FAIL và freshness STALE, nhưng **không** làm giảm retrieval trên test set này, vì không có câu hỏi nào phụ thuộc vào việc paper còn mới hay không. Đây là ví dụ cho thấy quality signal và agent metric không phải lúc nào cũng đổi cùng nhau: quality check bắt được lỗi sớm hơn cả trước khi người dùng thấy câu trả lời sai.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Sau khi merge nhánh của các thành viên, chạy `python script/run_corruption_flow.py` dừng ở bước 9/9 với `NotImplementedError: Student task: implement corruption comparison report.`, không sinh được `data/reports/corruption_report.md`.
- **Nguyên nhân:** `generate_corruption_report` đã được hoàn thiện ở commit `5d17475` với chữ ký `(report_path, baseline_metrics, corrupted_metrics, repaired_metrics, comparison, corruption_log_path)`. Các commit sau đó (`cbac14d`, `fb8e939`) ghi đè lại toàn bộ `src/observability/reporting.py` và vô tình đưa hàm này về trạng thái stub của starter, trong khi `corruption_flow.py` vẫn gọi theo chữ ký mới.
- **Cách xử lý:** Khôi phục phần thân hàm từ commit `5d17475` vào `reporting.py` hiện tại, giữ nguyên các hàm `generate_role4_*` mà thành viên khác đã thêm; bổ sung guard cho `corruption_log_path` khi giá trị là `None` và dùng `read_json` thay cho `import json` cục bộ.
- **Cách xác minh:** Chạy lại toàn bộ flow; bước 9/9 in ra `report: data/reports/corruption_report.md` và file được sinh lúc 2026-08-06T05:33:54Z với đầy đủ 7 mục.

Bài học của nhóm: khi nhiều người cùng sửa một file, cần merge theo hàm chứ không ghi đè cả file, và mỗi lần merge xong phải chạy lại cả hai flow trước khi commit.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Ragas chưa chạy trọn vẹn | Cột Ragas trong metrics là `skipped`; thiếu các chỉ số faithfulness/context precision | Đã sửa 3 lỗi chặn (xem dưới). Chạy `RUN_RAGAS=1` với provider có sẵn và đo lại; cần khoảng 3,5 giờ với `gpt-4o-mini` ở mức song song 8 job |
| Corruption "duplicate rows" chưa tạo dòng trùng | Không kiểm chứng được nhóm check uniqueness; kịch bản trong Guide chưa được phủ | Sửa `corrupt_clean_dataframe` để `pd.concat` phần `duplicates` đã copy vào dataframe; kỳ vọng `cp1_paper_id_unique_normalized` FAIL và row count tăng |
| `drop_latest_records` xóa ngẫu nhiên | Không chứng minh được kịch bản "mất dữ liệu mới nhất" ảnh hưởng freshness | Sắp xếp theo `published` giảm dần rồi drop N dòng đầu; kỳ vọng `latest_published` lùi lại và `days_since_latest_publication` tăng |
| `judge_accuracy` nhiễu ±0.04 | Khó kết luận chênh lệch nhỏ giữa các trạng thái | Tăng số sample, hoặc chạy judge nhiều lần lấy trung bình, hoặc chỉ kết luận khi chênh lệch > 0.08 |
| Corpus nhỏ (24 document, 25 câu hỏi) | Mỗi record chiếm ~4% dataset nên metric nhảy bậc lớn | Tăng `max_results` và số câu hỏi; kiểm chứng bằng độ rộng khoảng biến động của metric giữa các lần chạy |
| `qa.py` trích xuất bằng heuristic, chưa sinh câu trả lời bằng LLM | `mean_token_f1` phản ánh khả năng khớp metadata hơn là khả năng diễn đạt | Thay bằng LLM sinh câu trả lời từ context và so sánh lại cùng test set |

Ba lỗi đã chặn Ragas và đã được sửa trong `src/retrieval/embeddings.py` và `src/evaluation/metrics.py`:

1. `MiniLMEmbeddings.model` giữ đối tượng `SentenceTransformer`, trong khi wrapper của Ragas đọc thuộc tính `model` và ép kiểu `Optional[str]` → mọi job embedding hỏng vì `ValidationError`. Đã đổi `model` thành tên model dạng chuỗi, đối tượng encoder chuyển sang thuộc tính `encoder`.
2. Timeout mặc định 180s của Ragas quá ngắn so với độ trễ thực tế 40–60s mỗi job qua provider hosted → nhiều job `TimeoutError`. Đã truyền `RunConfig(timeout=600, max_workers=8)`.
3. `return dict(result)` là API của Ragas 0.1; ở 0.4.3 `evaluate()` trả về `EvaluationResult` không có `keys()` nên `dict()` rơi vào truy cập theo chỉ số và ném `KeyError: 0`, hiển thị ra ngoài thành thông báo gây hiểu nhầm `Ragas evaluation failed: 0`. Đã đổi sang tổng hợp từ `result.to_pandas()`.

Cần nói rõ: sửa (1) và (2) đã được kiểm chứng (toàn bộ job chạy xong, không còn exception), nhưng sửa (3) **chưa** chạy qua một `EvaluationResult` thật, nên vẫn phải coi đường Ragas là chưa được xác minh end-to-end.

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, 25 sample).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
