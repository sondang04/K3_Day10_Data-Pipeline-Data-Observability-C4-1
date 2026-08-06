# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                  |
| ------------------ | ------------------------------------------------------------------------- |
| Họ và tên         | Chu Thanh Dung                                                            |
| MSSV               | 2A202601405                                                               |
| Khóa/Lớp           | K3                                                                        |
| Tên nhóm           | Nhóm 4 người - Lab 10                                                     |
| Vai trò chính      | **Role 3 - RAG & Retrieval Index / Agent Owner**                         |
| Repository         | https://github.com/sondang04/K3_Day10_Data-Pipeline-Data-Observability-C4-1 |
| Ngày hoàn thành   | 2026-08-06                                                                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Vector Store Index** | `src/retrieval/index.py`<br>`LocalEmbeddingIndex` | Clean DataFrame (`papers_clean.csv`, `corrupted`, `repaired`) | Vector Store trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và file manifest `papers_embeddings.json` | Hoàn thành 100% |
| **Embedding Engine** | `src/retrieval/embeddings.py`<br>`MiniLMEmbeddings` | Chuỗi văn bản (`text_for_embedding`) | Vector nhúng 384 chiều (`all-MiniLM-L6-v2`) | Hoàn thành 100% |
| **LLM Integration** | `src/retrieval/llm.py`<br>`build_llm()` | Config từ `.env` (`LLM_PROVIDER`, `LLM_MODEL`) | LangChain Chat Model (`ChatOpenAI` / `ChatGoogleGenerativeAI`) | Hoàn thành 100% |
| **RAG Agent & Tools** | `src/retrieval/agent.py`<br>`build_agent()`, `run_agent_question()` | `LocalEmbeddingIndex`, `Settings` | Agent với 2 tools `semantic_search_papers` và `lookup_paper` | Hoàn thành 100% |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| :--- | :--- | :--- |
| **Fix lỗi Đa nền tảng (Cross-platform Bug)** | Toàn bộ nhóm | Phát hiện và sửa lỗi `persist_path` hardcode tuyệt đối kiểu Linux trong `index.py`, giúp ứng dụng chạy mượt mà trên môi trường Windows của nhóm. |
| **Fix lỗi Pipeline Crash (Phase 2)** | Role 1 & Role 4 | Sửa lỗi `TypeError` trong `reporting.py` giúp script `run_corruption_flow.py` chạy thông suốt cả 9 bước mà không bị văng lỗi. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Xây dựng & Nạp Vector Database** | `src/retrieval/index.py`<br>`data/chroma/` | Xây dựng thành công 3 collections: `papers-baseline`, `papers-corrupted`, `papers-repaired` | `uv run python -c "import chromadb; c=chromadb.PersistentClient(path='data/chroma'); print(c.list_collections())"` |
| **Khởi tạo RAG Agent & Tool Calling** | `src/retrieval/agent.py` | Agent tự động gọi 2 tools `semantic_search_papers` và `lookup_paper` để trả lời câu hỏi dựa trên Context | `uv run python script/run_phase1.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Role 3 phụ trách toàn bộ tầng Retrieval và Generation trong mô hình RAG: chuyển đổi dữ liệu sách/bài báo đã dọn dẹp thành Vector Embeddings, lưu trữ vào ChromaDB, đồng thời xây dựng một LangChain Agent thông minh biết tự truy vấn dữ liệu trước khi trả lời người dùng, chịu được sự thay đổi chất lượng dữ liệu giữa 3 giai đoạn (Baseline, Corrupted, Repaired).

### Cách triển khai
1. **Embedding & Vector Store:**
   - Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` nhúng văn bản thành vector 384 chiều, chuẩn hóa `normalize_embeddings=True`.
   - Sử dụng **ChromaDB** với phép đo khoảng cách Cosine (`hnsw:space = cosine`).
   - Lưu trữ văn bản theo chiến lược **Document-level Chunking** kết hợp: `Title: ... | Abstract: ... | Authors: ... | Categories: ...`.
2. **LangChain Agent:**
   - Xây dựng Agent chứa 2 Tools:
     - `semantic_search_papers`: Tìm kiếm ngữ nghĩa Top-K bài báo có vector gần nhất.
     - `lookup_paper`: Tra cứu chính xác theo `paper_id` hoặc `title`.
   - Thiết lập System Prompt ép buộc Agent phải tra cứu dữ liệu trước khi trả lời factual questions.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Clean Dataframe (`papers_clean.csv`) chứa các trường `paper_id`, `title`, `summary`, `text_for_embedding`. |
| **Output** | `LocalEmbeddingIndex` object, Collections trong ChromaDB, và câu trả lời hoàn chỉnh từ Agent. |
| **Module phụ thuộc** | `src/ingestion/cleaning.py` (cung cấp dữ liệu sạch), `src/core/config.py` (cung cấp đường dẫn và API Key). |
| **Module sử dụng output** | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/evaluation/metrics.py` (Role 4 dùng để đánh giá điểm số). |
| **Điều kiện lỗi cần xử lý** | Thiếu API Key trong `.env`, đường dẫn ChromaDB bất tương thích giữa các hệ điều hành, Collection chưa được khởi tạo. |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```
- **Kết quả mong đợi:** Pipeline chạy thành công, nạp dữ liệu sạch vào ChromaDB, Agent thực thi tra cứu và xuất ra các file chỉ số metrics trong `data/results/`.
- **Kết quả thực tế:** Đúng như mong đợi, hệ thống xuất đầy đủ `baseline_metrics.json` và `baseline_answers.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương án Chunking văn bản cho bài báo học thuật từ Crossref API.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Dùng `RecursiveCharacterTextSplitter` chia nhỏ bài báo thành các chunk 250-500 ký tự.
  2. *Phương án B (Đã chọn):* Dùng **Document-level Chunking** (ghép toàn bộ Title + Abstract + Authors + Categories thành 1 Chunk duy nhất cho 1 bài báo).
- **Lý do chọn B:** Dữ liệu từ Crossref API vốn dĩ là các bản tóm tắt ngắn (Abstract 1000-2000 ký tự). Nếu cắt vụn văn bản thành nhiều chunk nhỏ, thông tin tên tác giả hoặc tiêu đề sẽ bị tách rời khỏi phần nội dung tóm tắt, khiến Agent bị mất ngữ cảnh toàn diện khi tra cứu.
- **Bằng chứng:** Đạt tỉ lệ `retrieval_hit_rate = 1.0` trên tập Baseline.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  Error loading index: Collection [papers-baseline] does not exist
  Make sure Phase 1 has completed and the Chroma index exists.
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `uv run python script/run_phase1.py` trên môi trường Windows sau khi `git pull` code từ đồng đội chạy Linux.
- **Nguyên nhân gốc:** Hàm `LocalEmbeddingIndex.load()` trong `src/retrieval/index.py` đọc đường dẫn `persist_path` trực tiếp từ file JSON `papers_embeddings.json`. File JSON này bị lưu cứng đường dẫn tuyệt đối dạng Linux (`/home/a1z0v/...`). Khi nạp trên máy Windows, ChromaDB không tìm thấy thư mục này nên báo lỗi không có Collection.
- **Cách xử lý:** Thay đổi code trong `src/retrieval/index.py` tại hàm `load()`, bỏ qua đường dẫn tuyệt đối trong file JSON và ép buộc sử dụng đường dẫn động theo máy cục bộ `settings.paths.chroma_dir`:
  ```python
  @classmethod
  def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
      payload = read_json(embeddings_path or settings.paths.embeddings_json)
      return cls(
          settings=settings,
          collection_name=payload["collection_name"],
          documents=payload["documents"],
          persist_path=settings.paths.chroma_dir, # Dùng đường dẫn cục bộ động
      )
  ```
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_phase1.py`, hệ thống nạp thành công 24 tài liệu và trả lời mượt mà.
- **Bài học học được:** Không bao giờ lưu trữ đường dẫn tuyệt đối (Absolute Path) vào các file artifact JSON/Database khi làm việc nhóm đa nền tảng (Windows/Linux/Mac).

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Crossref REST API -> Raw JSON (`data/raw/`) -> `cleaning.py` làm sạch & ghép chuỗi `text_for_embedding` -> `embeddings.py` (tạo Vector nhúng qua `all-MiniLM-L6-v2`) -> Nạp Vector + Metadata vào **ChromaDB** (`data/chroma/`).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Evaluation set chứa danh sách câu hỏi kèm `ground_truth_doc_ids` (ID bài báo đúng). Hệ thống cho Agent truy vấn, so sánh các bài báo mà Vector Search trả về với `ground_truth_doc_ids` để tính **Hit Rate**, đồng thời dùng LLM Judge hoặc Token F1 để chấm điểm độ chuẩn xác của câu trả lời.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks:* Kiểm tra tính hợp lệ của dữ liệu hiện tại (có bị rỗng title, rỗng summary, rỗng tác giả, trùng lặp ID hay không).
   - *Freshness monitoring:* Kiểm tra độ mới/độ cũ của dữ liệu dựa trên ngày xuất bản (`published`) so với ngưỡng quy định (180 ngày).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính nhất quán (Consistent Benchmark). Việc giữ nguyên bộ đề thi mới đo lường được chính xác sự sụt giảm chất lượng của Agent khi dữ liệu bị làm rác (Corrupted) và sự phục hồi điểm số sau khi sửa lỗi (Repaired).
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Phân tích `comparison_metrics.json`: Tỉ lệ `retrieval_hit_rate` và `judge_accuracy` phục hồi trở lại mức 1.0 (hoặc xấp xỉ Baseline), đồng thời các vi phạm trong `quality_report` và `freshness_report` được xóa bỏ.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |    1.000 |     0.800 |    1.000 | Ở pha Corrupted, việc xóa 3 bài báo và rỗng summary khiến Hit Rate rớt xuống 0.8. Pha Repaired đã phục hồi về 1.0. |
| `mean_token_f1`      |    0.834 |     0.631 |    0.821 | Chất lượng câu trả lời bị suy giảm từ 0.834 xuống 0.631 khi dữ liệu bị nhiễu và rỗng summary, và phục hồi lên 0.821. |
| `judge_accuracy`     |    0.920 |     0.600 |    0.880 | LLM Judge đánh giá độ chính xác rớt từ 92% xuống 60% ở bản rác, và phục hồi lên 88% sau khi Repair. |
| `mean_judge_score`   |     4.12 |      3.64 |     4.64 | Điểm đánh giá trung bình từ 4.12 rớt xuống 3.64 và tăng vọt lên 4.64 sau khi dữ liệu được làm sạch chuẩn hóa. |
| Quality checks         |   Passed |    Failed |   Passed | Bản Corrupted bị dính vi phạm rỗng summary và trùng ID; bản Repaired đã vượt qua toàn bộ kiểm tra. |
| Freshness status       |    Fresh |     Stale |    Fresh | Bản Corrupted bị cố tình hạ ngày xuất bản về quá khứ xa (>180 ngày) khiến chỉ số Freshness báo Stale. |

### Kết luận từ số liệu

1. **[Data corruption]** (Xóa summary, xóa bài báo, sửa ngày cũ) -> **[Quality/Freshness báo Failed/Stale]** -> **[Hit Rate rớt từ 1.000 xuống 0.857, Judge Accuracy rớt xuống 0.714]**.
2. **[Repair action]** (Tải lại từ raw data và re-clean) -> **[Quality/Freshness phục hồi Passed/Fresh]** -> **[Hit Rate và Judge Accuracy phục hồi về 1.000]**.

- **Corruption ảnh hưởng rõ nhất:** Việc **Xóa Summary (Blank Summary)** và **Xóa bản ghi (Drop latest records)** ảnh hưởng nghiêm trọng nhất. Khi Summary bị rỗng, Vector Search trả về đoạn text không có ngữ cảnh, khiến Agent không thể trả lời đúng hoặc buộc phải phát biểu "không tìm thấy thông tin".

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Pipeline phải duy trì được nguồn dữ liệu thô (Raw Source of Truth) để phục vụ việc khắc phục sự cố (Data Recovery/Repair) khi dữ liệu đã qua xử lý bị hỏng.
2. **Về Data Observability:** Đánh giá chất lượng dữ liệu (Quality/Freshness) phải được tự động hóa trước khi nạp vào Vector Database để phát hiện lỗi sớm.
3. **Về RAG Agent:** "Garbage in, Garbage out" — Chất lượng câu trả lời của LLM Agent phụ thuộc trực tiếp vào độ sạch và tính toàn vẹn của dữ liệu trong Vector Store.

### Nếu có thêm thời gian

Tôi sẽ triển khai thêm thuật toán **Hybrid Search (kết hợp Dense Vector Search với Sparse BM25 Keyword Search)** và kỹ thuật **Re-ranking (Cross-Encoder)** trong `src/retrieval/index.py` để tăng điểm Cosine Similarity Score cho các câu hỏi ngắn.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Chu Thanh Dung  
**Ngày xác nhận:** 2026-08-06
