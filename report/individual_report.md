# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Đặng Thái Nam Sơn |
| MSSV | 2A202601431 |
| Khóa/Lớp | K3 |
| Tên nhóm | C4-1 |
| Vai trò chính | Pipeline integration & orchestration owner |
| Repository | https://github.com/sondang04/K3_Day10_Data-Pipeline-Data-Observability-C4-1.git |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline orchestration | `src/pipelines/phase1.py` — `main()`, `_load_records()`, `_load_test_set()`, `_source_summary()`, `_run_agent_demo()` | Raw records hoặc snapshot, settings từ `core/config.py` | 8 bước chạy tuần tự và toàn bộ artifact pha 1 | Hoàn thành |
| Bản dựng Phase-1 đầu tiên trên nhánh `p1_lead` | `crossref.py`, `cleaning.py`, `testset.py`, `quality.py`, `reporting.py` (commit `f6b26fb`) | Starter có `TODO(student)` | Baseline chạy được end-to-end để các thành viên khác tiếp tục mở rộng | Hoàn thành, sau đó được Đăng và Phong viết lại/mở rộng theo phần việc của họ |
| Trace và so sánh 3 trạng thái | `script/run_ragas_comparison.py` | Baseline + corrupted + repaired artifacts | `data/reports/ragas_mode_comparison.md`, `data/results/ragas_modes/comparison.json`, `data/quality/pipeline_trace.jsonl` | Hoàn thành |
| Chạy và xác minh tích hợp | Cả hai flow | Code của cả nhóm sau merge | Bảng metrics 3 trạng thái khớp với artifact | Hoàn thành |
| Sửa đường Ragas | `src/evaluation/metrics.py`, `src/retrieval/embeddings.py` | Lỗi khi bật `RUN_RAGAS=1` | 3 lỗi chặn đã sửa | Một phần — sửa (1)(2) đã kiểm chứng, sửa (3) chưa chạy qua kết quả Ragas thật |

Tôi chỉ nhận ownership cho `phase1.py`, script trace/so sánh và phần chạy–xác minh tích hợp. Nội dung hiện tại của `crossref.py`, `cleaning.py`, `corruption.py`, `corruption_flow.py` là của Trần Đình Đăng; `quality.py`, `reporting.py`, `testset.py` sau CP0–CP2 là của Dương Mạnh Phong; `index.py`, `embeddings.py`, `llm.py`, `agent.py` là của Chu Thành Dũng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Khôi phục `generate_corruption_report` bị mất khi merge | Dương Mạnh Phong / `src/observability/reporting.py` | `run_corruption_flow.py` chạy lại được hết 9/9 bước, sinh `data/reports/corruption_report.md` |
| Báo cáo 2 lỗi logic trong corruption | Trần Đình Đăng / `src/ingestion/corruption.py` | Xác định `duplicate_ids` không tạo dòng trùng và `drop_latest_records` xóa ngẫu nhiên; có bằng chứng số liệu kèm theo |
| Sửa thuộc tính `model` của embeddings | Chu Thành Dũng / `src/retrieval/embeddings.py` | Ragas không còn ném `ValidationError` ở mọi job embedding |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Ghép 8 bước của baseline flow và in log từng bước | `src/pipelines/phase1.py` | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` | `python script/run_phase1.py`, đọc log `[phase1] 1/8 … 8/8` |
| Cho phép tái dùng snapshot raw và test set | `_load_records()`, `_load_test_set()` | Chạy lại không cần gọi Crossref, test set giữ nguyên qua 3 trạng thái | Chạy lần hai in `raw-snapshot` và `25 questions (cached)` |
| Cố định RNG corruption để so sánh có kiểm soát | `script/run_ragas_comparison.py` (`CORRUPTION_SEED = 20260806`) | Hai lần chạy corrupt đúng cùng 14 record | `data/results/corruption_log.json` giống nhau giữa hai lần chạy |
| Dựng trace theo từng record và từng câu hỏi | `_dataset_trace()`, `_quality_trace()`, `_answer_trace()` | 33 event trong `data/quality/pipeline_trace.jsonl` | `python script/run_ragas_comparison.py 0` |
| Chạy agent demo với provider thật | `_run_agent_demo()` | `data/results/agent_demo_answers.json` với `status: ok` | Đọc file, provider `openrouter`, model `openai/gpt-4o-mini` |

Nêu một output cụ thể mà phần việc của tôi tạo ra hoặc giúp xác minh:

`data/results/ragas_modes/comparison.json` là output tôi thấy có giá trị nhất. Nó không chỉ chép lại metric mà so từng record giữa baseline, corrupted và repaired rồi gắn nhãn corruption cho từng `paper_id` (`record_dropped`, `summary_blanked`, `summary_noise_injected[[UNVERIFIED]]`, `title_truncated`, `published_backdated[2026-07-03->2001-01-01]`, `paper_id_mutated`), đồng thời theo dõi từng câu hỏi chuyển trạng thái hit/F1 ra sao. Nhờ file này nhóm mới chỉ ra được chính xác vì sao `retrieval_hit_rate` rớt 0.200: 5 câu `02-*` cùng hỏi về `10.3390/buildings16132637`, paper này bị xóa nên retrieval trả về `10.63646/kpqm1958` — một paper **không** bị corrupt nhưng gần về ngữ nghĩa.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Mỗi module trong `src/` chạy riêng thì đúng, nhưng bài lab chỉ có ý nghĩa khi chúng chạy đúng thứ tự, dùng đúng artifact của nhau và tạo ra bằng chứng đối chiếu được. Phần của tôi là biến các hàm rời rạc thành một pipeline lặp lại được, và tạo ra dữ liệu đủ chi tiết để kết luận "corruption làm giảm chất lượng agent" không phải là phỏng đoán.

### Cách triển khai

`phase1.py` chạy 8 bước: (1) nạp raw records — gọi Crossref nếu chưa có snapshot hoặc khi `REFRESH_SOURCE=1`, ngược lại đọc `data/raw/crossref_records.json`; (2) clean; (3) ghi CSV + JSON; (4) build ChromaDB index; (5) sinh hoặc nạp lại test set; (6) evaluate; (7) quality checks + freshness; (8) xuất báo cáo Markdown, rồi chạy thêm agent demo. Mỗi bước in một dòng log có số thứ tự và một dòng số liệu tóm tắt, để khi hỏng thì biết ngay hỏng ở đâu.

Hai quyết định về khả năng tái hiện: mặc định **không** gọi lại API và **không** sinh lại test set, vì Crossref là nguồn sống — nếu mỗi lần chạy lại lấy dữ liệu mới thì baseline và corrupted không còn so sánh được với nhau. Agent demo được bọc `try/except` vì nó là phần duy nhất bắt buộc phải có LLM provider; thiếu credential thì demo ghi `status: skipped` chứ không làm hỏng cả pipeline.

`script/run_ragas_comparison.py` chạy `phase1.main()` rồi `corruption_flow.main()` trong cùng tiến trình, seed `random` ngay trước bước corruption, chụp lại artifact vào `data/results/ragas_modes/`, sau đó suy ra trace bằng cách so sánh các file CSV/JSON thay vì chèn code đo đạc vào module của người khác — cách này không đụng vào file các bạn đang sửa.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `Settings` từ `core/config.py`; `data/raw/crossref_records.json`; biến môi trường `REFRESH_SOURCE`, `REFRESH_TEST_SET`, `RUN_RAGAS` |
| Output | `data/clean/`, `data/embeddings/`, `data/eval/test_set.json`, `data/results/baseline_metrics.json` + `baseline_answers.json`, `data/quality/`, `data/reports/phase1_report.md` |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting`, `retrieval.index`, `retrieval.agent` |
| Module sử dụng output | `pipelines.corruption_flow` đọc `papers_clean.csv`, `baseline_metrics.json` và `test_set.json` |
| Điều kiện lỗi cần xử lý | Cleaning trả về dataframe rỗng → dừng sớm kèm hướng dẫn chạy `REFRESH_SOURCE=1`; thiếu LLM credential → agent demo ghi lý do vào artifact thay vì ném exception; thiếu snapshot raw → tự gọi API |

### Cách xác minh

```bash
python script/run_ragas_comparison.py 0
```

- **Kết quả mong đợi:** cả hai flow chạy hết, baseline PASS toàn bộ quality checks và FRESH; corrupted phải fail một số checks và STALE; repaired quay lại bằng baseline.
- **Kết quả thực tế:** baseline 25/25 PASS, FRESH, `retrieval_hit_rate` 1.000, `mean_token_f1` 0.834; corrupted 20/25, STALE, 0.800 và 0.639; repaired 25/25 PASS, FRESH, 1.000 và 0.834. Trace ghi `restored: 24`, `unrestored: []`.
- **Artifact/log:** `data/reports/ragas_mode_comparison.md`, `data/results/ragas_modes/comparison.json`, `data/quality/pipeline_trace.jsonl` (33 event, sinh lúc 2026-08-06T05:35Z).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lần chạy baseline đầu tiên cho `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` đều bằng đúng 1.000. Nhìn thì đẹp nhưng vô dụng: nếu baseline đã kịch trần thì không đo được gì, và mọi sụt giảm sau corruption sẽ không phân biệt được là do retrieval hỏng hay do câu hỏi quá dễ.
- **Các phương án đã cân nhắc:** (a) giữ nguyên — mọi câu hỏi đều trích nguyên tiêu đề trong dấu nháy đơn, nên `qa.answer_question` luôn đi nhánh lookup chính xác và ground truth luôn nằm trong kết quả; (b) bỏ hẳn nhánh lookup để ép mọi câu đi qua embedding search; (c) giữ 4 nhóm câu hỏi cũ và thêm một nhóm `semantic` không trích tiêu đề.
- **Phương án đã chọn:** (c).
- **Lý do:** Phương án (a) khiến metric không có khả năng phân biệt. Phương án (b) phải sửa `qa.py` — file của thành viên khác — và làm mất luôn khả năng kiểm thử nhánh lookup vốn cũng là một tính năng. Phương án (c) chỉ thêm dữ liệu vào test set, không đụng code người khác, mà vẫn tạo được 5 câu chỉ có thể trả lời đúng nếu ChromaDB trả về đúng document.
- **Bằng chứng quyết định phù hợp:** Ngay trong lần chạy thêm nhóm `semantic`, baseline `mean_token_f1` rời khỏi mức kịch trần, giảm từ 1.000 xuống 0.965; trên bản code cuối cùng của nhóm baseline là 0.834 và khi corrupt thì rớt tiếp xuống 0.639 — tức là metric đã có "khoảng trống" để phản ánh thiệt hại. Bảng theo `question_type` trong `ragas_mode_comparison.md` cho thấy nhóm `semantic` có 1/5 câu regress, đúng như kỳ vọng rằng nhóm này nhạy với chất lượng embedding.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Bật `RUN_RAGAS=1` thì cả 3 trạng thái đều ghi `{"error": "Ragas evaluation failed: 0"}` vào `*_metrics.json`. Thông báo chỉ có đúng một ký tự `0` nên ban đầu nhóm tưởng là lỗi thiếu API key.
- **Lệnh hoặc bước tái hiện:** `RUN_RAGAS=1 python script/run_phase1.py`, sau đó đọc trường `ragas` trong `data/results/baseline_metrics.json`.
- **Nguyên nhân gốc:** Có ba nguyên nhân chồng lên nhau, và `except Exception` trong `_run_ragas` gộp tất cả thành một dòng khó đọc.
  1. `MiniLMEmbeddings` lưu đối tượng `SentenceTransformer` vào thuộc tính `model`. Wrapper của Ragas đọc `getattr(embeddings, "model", None)` rồi đưa vào một event pydantic khai báo `Optional[str]` → mọi job dùng embedding chết vì `ValidationError`.
  2. Timeout mặc định 180s của Ragas ngắn hơn thời gian thực tế: mỗi job qua provider hosted mất 40–60s và có retry, nên nhiều job ném `TimeoutError`.
  3. Nguyên nhân của chính chuỗi `0`: `_run_ragas` kết thúc bằng `return dict(result)` — cách này chỉ đúng với Ragas 0.1. Ở phiên bản 0.4.3 đang cài, `evaluate()` trả về `EvaluationResult` không có `keys()`, nên `dict()` rơi về giao thức lặp cũ và gọi `__getitem__(0)`; hàm này tra `self._scores_dict[0]` và ném `KeyError: 0`. Chuỗi `0` trong thông báo lỗi chính là key bị thiếu.
- **Cách xử lý:** Đổi `MiniLMEmbeddings.model` thành tên model dạng chuỗi và chuyển encoder sang thuộc tính `encoder`; truyền `RunConfig(timeout=600, max_workers=8)` vào `evaluate()`; thay `dict(result)` bằng tổng hợp trung bình từng metric trên `result.to_pandas()`, kèm số dòng thực sự chấm được.
- **Cách xác minh sau khi sửa:** Chạy `_run_ragas` trên 2 sample thật với `openai/gpt-4o-mini`: trước khi sửa mọi job đều ném `ValidationError`/`TimeoutError`; sau khi sửa cả 8/8 job chạy xong không exception.
- **Điều học được:** Không nên để `except Exception` nuốt lỗi rồi chỉ in `str(exc)` — với `KeyError` thì `str(exc)` chỉ còn tên key, mất hoàn toàn ngữ cảnh. Nếu log kèm `type(exc).__name__` và traceback thì nhóm đã tiết kiệm được nhiều giờ. Bài học thứ hai: khi thư viện lên major version, những chỗ "tưởng vô hại" như `dict(result)` mới là chỗ vỡ.

Phần chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** trường `ragas` trong `data/results/*_metrics.json` vẫn là `skipped`.
- **Những gì đã loại trừ:** đã loại trừ nguyên nhân thiếu credential (LLM judge chạy được với cùng provider), loại trừ lỗi schema dataset (Ragas 0.4.3 vẫn nhận tên cột cũ `question/answer/ground_truth/contexts`), loại trừ lỗi embedding và timeout.
- **Bước tiếp theo:** chạy `RUN_RAGAS=1` trọn vẹn để kiểm chứng nốt phần tổng hợp `to_pandas()`. Ước tính cần khoảng 3,5 giờ với `gpt-4o-mini` ở mức 8 job song song (đo được ~1,4 job/phút, 100 job cho mỗi trạng thái).

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** `crossref.py` gọi `/works` với query và filter trong `config.py`, lưu nguyên văn response vào `data/raw/crossref_response.json` để còn truy vết, rồi parse thành `PaperRecord` và lưu `crossref_records.json`. `cleaning.py` chuẩn hóa text, parse ngày, tính `age_days`, loại record thiếu trường bắt buộc, khử trùng lặp và ghép `text_for_embedding`. `index.py` mã hóa cột đó bằng `all-MiniLM-L6-v2` và nạp vào collection ChromaDB kèm metadata; mỗi document giữ `paper_id` là DOI nên truy ngược được về record gốc.

2. **Evaluation set và ground-truth document IDs:** test set sinh từ cleaned dataset, mỗi sample có `question`, `ground_truth` và `ground_truth_doc_ids` (chính là DOI của paper sinh ra câu hỏi). Khi đánh giá, `retrieval_hit` đúng nếu có ít nhất một `paper_id` trong top-4 nằm trong `ground_truth_doc_ids` — đây là thước đo retrieval. Còn `token_f1` và LLM judge so nội dung câu trả lời với `ground_truth` — đây là thước đo answer quality. Tách hai tầng như vậy mới biết lỗi nằm ở khâu tìm tài liệu hay khâu trả lời.

3. **Quality checks khác freshness monitoring:** quality checks trả lời "dữ liệu có đúng hợp đồng không" — không rỗng, không trùng, đúng định dạng, đủ độ dài; kết quả là PASS/FAIL trên từng expectation. Freshness trả lời "dữ liệu có còn mới không" — so `published`/`age_days` với ngưỡng 180 ngày, và báo cáo mốc mới nhất/cũ nhất. Một dataset có thể PASS toàn bộ quality checks mà vẫn STALE, và ngược lại. Trong bài này backdating làm hỏng cả hai, nhưng blank summary thì chỉ làm hỏng quality chứ không đụng freshness.

4. **Vì sao dùng cùng test set:** vì test set đại diện cho câu hỏi của người dùng, mà người dùng thì không đổi câu hỏi chỉ vì dữ liệu của ta bị hỏng. Nếu sinh lại test set từ corrupted dataset thì những câu hỏi về paper đã bị xóa sẽ tự biến mất và ground truth của summary rỗng sẽ trở thành chuỗi rỗng — metric có thể vẫn đẹp trong khi hệ thống đã hỏng. Giữ cố định test set là cách duy nhất để chênh lệch metric quy về đúng một biến số là chất lượng dữ liệu.

5. **Repair thành công dựa trên artifact nào:** ba lớp bằng chứng. Lớp dữ liệu — trace so từng record cho `restored: 24`, `unrestored: []`. Lớp observability — `data/quality/repaired-quality.json` PASS 25/25 và `repaired_freshness.json` trả `is_fresh: true`, `stale_rows: 0`. Lớp agent — `repaired_metrics.json` cho `retrieval_hit_rate` 1.000, `mean_token_f1` 0.834 và `mean_judge_score` 4.640, trùng khớp baseline. Chỉ khi cả ba lớp cùng về trạng thái baseline thì mới gọi là repair thành công.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.800 | 1.000 | Mất đúng 5/25 câu, bằng đúng số câu hỏi về paper bị xóa — quan hệ 1:1 chứ không phải trùng hợp |
| `mean_token_f1` | 0.834 | 0.639 | 0.834 | Repaired trùng baseline đến từng chữ số, cho thấy repair dựng lại đúng dữ liệu chứ không xấp xỉ |
| `judge_accuracy` | 0.920 | 0.640 | 0.880 | Chênh 0.04 ở repaired là nhiễu judge, không phải mất mát dữ liệu |
| `mean_judge_score` | 4.640 | 3.880 | 4.640 | Trùng baseline, củng cố kết luận trên |
| Quality checks | 25/25 PASS | 20/25 FAIL | 25/25 PASS | 5 check fail thuộc 3 nhóm: độ dài title, độ dài/rỗng summary, ngưỡng `age_days` |
| Freshness status | FRESH (0/24 stale) | STALE (3/21 stale) | FRESH (0/24 stale) | `oldest_published` nhảy về 2001-01-01 rồi quay lại 2026-02-12 |

### Kết luận từ số liệu

1. **Xóa 3 record khỏi cleaned dataset** → row count 24 → 21, quality vẫn không bắt được vì check row count chỉ yêu cầu ≥ 10, nhưng ground truth của 5 câu hỏi biến mất → `retrieval_hit` của cả 5 câu `02-*` chuyển sang `false`, top-1 chuyển sang `10.63646/kpqm1958`, kéo `retrieval_hit_rate` 1.000 → 0.800 và `mean_token_f1` 0.834 → 0.639.
2. **Repair bằng cách clean lại từ `data/raw/crossref_records.json`** → 24/24 record khôi phục nguyên trạng, quality 25/25 PASS và freshness FRESH trở lại → `retrieval_hit_rate` về 1.000, `mean_token_f1` và `mean_judge_score` về đúng giá trị baseline; `judge_accuracy` còn lệch 0.04 do dao động của judge chứ không phải do dữ liệu.

Corruption nào ảnh hưởng rõ nhất và vì sao?

**Xóa record**, cách biệt so với các loại còn lại. Lý do là nó phá ở tầng không thể bù đắp: khi document không còn trong corpus thì không có kỹ thuật retrieval nào cứu được, top-4 dù xếp hạng tốt đến đâu cũng chỉ trả về paper khác. Các corruption còn lại chỉ làm *giảm chất lượng* của document vẫn đang tồn tại — blank summary vẫn để lại title và metadata nên câu hỏi về tác giả hay ngày xuất bản vẫn trả lời đúng, noise chỉ làm lệch embedding một chút. Điều đáng chú ý là xóa record lại là loại corruption mà quality checks **không** bắt được, vì ngưỡng row count đặt ở mức ≥ 10 quá lỏng so với dataset 24 dòng.

Kết quả nào khác với kỳ vọng ban đầu?

Ba điểm.

Thứ nhất, tôi kỳ vọng backdating ngày xuất bản sẽ kéo metric của agent xuống, nhưng nó chỉ làm freshness chuyển STALE mà không đổi `retrieval_hit_rate`. Kiểm tra lại `corrupted_answers.json` thì hiểu: không câu hỏi nào trong test set phụ thuộc vào độ mới của paper, còn nhóm câu `date` thì hỏi 5 paper khác. Đây là ví dụ tốt cho thấy observability bắt được lỗi *trước* khi người dùng thấy hậu quả.

Thứ hai, `judge_accuracy` của repaired không về đúng baseline (0.880 so với 0.920). Giả thuyết ban đầu là repair chưa hoàn chỉnh. Tôi kiểm tra bằng cách so từng record giữa baseline và repaired (giống hệt) và so từng câu trả lời (cả 25 câu giống hệt), rồi tìm ra đúng một câu `04-summary` mà LLM judge cho cùng điểm 3 nhưng lật cờ `correct`. Kết luận: đây là nhiễu của judge, và với 25 sample thì một câu lật cờ đã đổi metric 0.04.

Thứ ba, corruption `duplicate_ids` không tạo ra tín hiệu nào. Kiểm tra corrupted CSV thấy 21 dòng với 21 ID duy nhất và 0 dòng trùng nội dung. Đọc lại code thì thấy biến `duplicates` được copy ra nhưng không bao giờ được `concat` lại vào dataframe — thực tế code chỉ đổi tên 2 ID thành `<doi>_dup_<i>`. Vì vậy nhóm check uniqueness chưa từng được kiểm chứng trong bài này.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** khả năng tái hiện phải được thiết kế từ đầu chứ không thêm vào sau. Việc lưu snapshot raw ngay sau lần gọi API đầu tiên, mặc định đọc lại snapshot thay vì gọi API, và cố định seed cho bước corruption là ba quyết định nhỏ nhưng chính chúng làm cho phép so sánh baseline/corrupted/repaired có ý nghĩa — nếu không thì mỗi lần chạy sẽ lấy dữ liệu Crossref khác nhau và mọi chênh lệch metric đều vô nghĩa.
2. **Về data quality/observability:** một bộ check chỉ phát hiện được những gì nó được viết ra để phát hiện. Bộ 25 check của nhóm bắt rất tốt blank summary, title cụt và ngày cũ, nhưng để lọt hoàn toàn việc mất 3 record — thứ gây thiệt hại lớn nhất cho agent — chỉ vì ngưỡng row count đặt ở ≥ 10. Quality check cần được thiết kế theo kịch bản hỏng thực tế, không phải theo những gì dễ viết.
3. **Về ảnh hưởng của data tới RAG agent:** thiệt hại không phân bố đều. Xóa một document làm hỏng toàn bộ câu hỏi liên quan tới nó, trong khi làm nhiễu abstract gần như không đổi kết quả. Và triệu chứng ở phía người dùng rất khó nhận ra: agent không báo lỗi, nó vẫn tự tin trả lời — chỉ có điều trả lời về một paper khác.

### Nếu có thêm thời gian

Tôi sẽ siết check row count từ "≥ 10 dòng" thành "không giảm quá 5% so với lần chạy trước", bằng cách lưu row count của lần chạy gần nhất vào `data/quality/` và so sánh. Đo cải thiện rất trực tiếp: chạy lại corruption flow với đúng seed `20260806`, kỳ vọng check mới FAIL ở trạng thái corrupted (24 → 21 là giảm 12,5%) và PASS ở baseline lẫn repaired. Như vậy loại corruption gây thiệt hại nặng nhất mới có tín hiệu cảnh báo tương xứng, thay vì chỉ lộ ra khi metric của agent đã rớt.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (đường Ragas được ghi rõ là chưa xác minh trọn vẹn).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đặng Thái Nam Sơn
**Ngày xác nhận:** 2026-08-06
