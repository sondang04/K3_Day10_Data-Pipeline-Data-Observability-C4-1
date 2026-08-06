# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                |
| ----------------- | --------------------------------------- |
| Họ và tên         | Trần Đình Đăng                          |
| MSSV              | [MSSV]                                  |
| Khóa/Lớp          | K3                                      |
| Tên nhóm          | [Tên nhóm]                              |
| Vai trò chính     | Role 2 - Nền tảng dữ liệu & Recovery    |
| Repository        | K3_Day10_Data-Pipeline-Data-Observability-C4-1 |
| Ngày hoàn thành   | 2026-08-06                              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                    | File/hàm phụ trách                              | Input nhận vào              | Output bàn giao                                           | Trạng thái      |
| ------------------------------------- | ------------------------------------------------ | ---------------------------- | --------------------------------------------------------- | --------------- |
| Raw data ingestion từ Crossref       | `src/ingestion/crossref.py`                      | Crossref API response        | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Cleaning và data modeling             | `src/ingestion/cleaning.py`                      | Raw records JSON             | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Corruption simulation                  | `src/ingestion/corruption.py`                    | Clean records JSON           | Corrupted records, corruption log                         | Hoàn thành |
| Corruption orchestration flow         | `src/pipelines/corruption_flow.py`               | Baseline artifacts           | Corrupted artifacts, repaired artifacts, comparison report | Hoàn thành |
| Corruption reporting                  | `src/observability/reporting.py` (phần corruption) | Metrics JSON files           | `data/reports/corruption_report.md`                      | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| --------------------------------- | ------------------------------ | -------------------------- |
| Review code và feedback           | Các thành viên khác            | Code review comments       |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao                    | Cách xác minh                    |
| ---------------------- | ---------------------------- | ----------------------------------- | -------------------------------- |
| Parse Crossref API payload thành PaperRecord | `src/ingestion/crossref.py` | Raw records JSON với stable paper_id | `data/raw/crossref_records.json` |
| Normalize và clean dữ liệu | `src/ingestion/cleaning.py` | Clean CSV/JSON với text_for_embedding | `data/clean/papers_clean.csv` |
| Tính age_days từ published date | `src/ingestion/cleaning.py` | age_days field có timezone awareness | Kiểm tra trong JSON |
| Dedupe theo paper_id | `src/ingestion/cleaning.py` | 24 records duy nhất | Row count verification |
| Apply 6 loại corruption | `src/ingestion/corruption.py` | Corrupted dataset, log đầy đủ | `data/results/corruption_log.json` |
| Run corruption flow end-to-end | `src/pipelines/corruption_flow.py` | Baseline/Corrupted/Repaired comparison | `data/reports/corruption_report.md` |
| Repair từ raw source | `src/pipelines/corruption_flow.py` | Repaired dataset khôi phục quality | `data/clean/papers_clean_repaired.json` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 2 xây dựng nền tảng dữ liệu cho pipeline, phụ trách việc lấy dữ liệu từ Crossref API, clean và chuẩn hóa dữ liệu, sau đó simulate corruption để test khả năng repair. Mục tiêu là tạo ra một pipeline có thể detect data quality issues và recover từ raw source.

### Cách triển khai

**Crossref Ingestion:**
- Sử dụng `requests` để call Crossref API với rate limiting
- Parse response thành list of PaperRecord với dataclass
- Retry logic cho HTTP 429 (rate limit) và 503 (service unavailable)
- Lưu cả raw response và parsed records để có backup

**Data Cleaning:**
- Normalize title: lowercase, strip whitespace, remove extra spaces
- Parse date với timezone awareness (UTC), tính age_days từ ngày publish đến hiện tại
- Build `text_for_embedding` = f"{title}. {summary}" để RAG agent có consistent input
- Constants cho quality thresholds: MIN_TITLE_CHARS=5, MIN_SUMMARY_CHARS=50

**Corruption System:**
- 6 loại corruption được implement, mỗi loại có probability và config riêng
- Corruption được logged chi tiết với count và reason
- Repair flow dùng raw source data để rebuild clean dataset

### Input, output và contract

| Thành phần                   | Mô tả                                                   |
| ----------------------------- | ------------------------------------------------------- |
| Input                         | Crossref API payload (HTTP response JSON)              |
| Output                        | PaperRecord dataclass, CSV/JSON files, embedding index  |
| Module phụ thuộc             | None (crossref.py là entry point)                       |
| Module sử dụng output        | `src/evaluation/`, `src/retrieval/`, `src/observability/` |
| Điều kiện lỗi cần xử lý     | HTTP errors (429, 503), JSON parse errors, missing fields |

### Cách xác minh

```bash
# Chạy baseline pipeline
uv run python script/run_phase1.py

# Chạy corruption flow
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Baseline: 24 records, hit_rate=1.0; Corruption: hit_rate giảm; Repaired: khôi phục về ~1.0
- **Kết quả thực tế:** Baseline: 24 records, hit_rate=1.000; Corruption: hit_rate=0.600; Repaired: hit_rate=1.000
- **Artifact/log:** `data/reports/corruption_report.md`, `data/results/corruption_log.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Quyết định nên lưu raw response hay chỉ parsed records.
- **Các phương án đã cân nhắc:**
  1. Chỉ lưu parsed records (tiết kiệm storage, lossless)
  2. Lưu cả raw response và parsed records (backup cho repair)
- **Phương án đã chọn:** Lưu cả hai.
- **Lý do:** Raw response là nguồn để repair khi data bị corrupted. Nếu chỉ lưu parsed records, không có gì để recover về baseline.
- **Bằng chứng quyết định phù hợp:** Corruption flow sử dụng `data/raw/crossref_records.json` để repair, chứng minh raw data là cần thiết.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** HTTP 429 Too Many Requests khi gọi Crossref API.
- **Lệnh hoặc bước tái hiện:** `python -c "from src.ingestion.crossref import CrossrefClient; client = CrossrefClient(); client.fetch_all_works('10.1038/nature12373')"`
- **Nguyên nhân gốc:** Crossref API có rate limit, không có retry logic ban đầu.
- **Cách xử lý:** Thêm retry logic với exponential backoff cho HTTP 429 và 503 errors.
- **Cách xác minh sau khi sửa:** Chạy lại script, không còn HTTP 429 error.
- **Điều học được:** Luôn implement retry logic cho external API calls, đặc biệt khi có rate limiting.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API → Raw JSON → Parse thành PaperRecord → Clean/normalize → Build text_for_embedding → Generate embeddings → Store trong FAISS vector index.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Evaluation set chứa queries với expected document IDs. Retrieval đo hit_rate (có tìm đúng docs không). Judge đo F1 và quality score (câu trả lời có đúng không).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks xác minh schema và content hợp lệ (title length, summary length, required fields). Freshness monitoring theo dõi publication date và stale_rows count.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo comparison công bằng - nếu test set khác nhau, không thể so sánh performance được.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repaired metrics đạt/gần bằng baseline metrics, đặc biệt là retrieval_hit_rate quay về 1.0 và quality checks PASSED.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                    |
| ---------------------- | -------: | --------: | -------: | ---------------------------------------- |
| `retrieval_hit_rate`   |    1.000 |     0.600 |    1.000 | Corruption làm giảm 40%, repair phục hồi hoàn toàn |
| `mean_token_f1`        |    0.793 |     0.488 |    0.854 | Repair cải thiện F1 nhờ có đầy đủ data |
| `judge_accuracy`       |    0.840 |     0.520 |    0.960 | Repaired vượt baseline, cho thấy repair tốt hơn cả baseline |
| `mean_judge_score`     |    3.960 |     2.760 |    4.200 | Tương tự accuracy, repaired đạt score cao hơn |
| Quality checks         |    PASS  |     FAIL  |    PASS  | Corruption break quality rules, repair khôi phục |
| Freshness status       |    FRESH |     STALE |    FRESH | drop_latest_records gây stale data |

### Kết luận từ số liệu

1. **Data corruption** → quality/freshness signal thay đổi (FAIL, STALE) → agent metric thay đổi (hit_rate -40%, F1 -30%).
2. **Repair action** → quality/freshness signal phục hồi (PASS, FRESH) → agent metric phục hồi (hit_rate về 1.0, F1 tăng).

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
`drop_latest_records` ảnh hưởng rõ nhất vì nó trực tiếp làm mất data (3 records biến mất), dẫn đến retrieval không tìm được document cần thiết.

**Kết quả nào khác với kỳ vọng ban đầu?**
Repaired metrics vượt baseline (F1: 0.854 vs 0.793, judge_accuracy: 0.960 vs 0.840). Có thể do repair process loại bỏ một số noise và tạo ra dataset cleaner hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw data nên được lưu trữ riêng biệt để phục vụ recovery. Không nên overwrite raw data khi clean.
2. **Data quality/observability:** Data quality impacts trực tiếp đến model performance. Quality checks và freshness monitoring là cần thiết để detect issues sớm.
3. **Ảnh hưởng của data đến RAG agent:** Khi data bị corrupted, retrieval hit_rate giảm mạnh, dẫn đến answer quality kém. Repair khôi phục được performance.

### Nếu có thêm thời gian

Cải thiện corruption simulation để realistic hơn - ví dụ corrupt specific fields thay vì drop entire records, hoặc thêm more subtle corruptions như typos, date drift nhỏ.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Đình Đăng
**Ngày xác nhận:** 2026-08-06
