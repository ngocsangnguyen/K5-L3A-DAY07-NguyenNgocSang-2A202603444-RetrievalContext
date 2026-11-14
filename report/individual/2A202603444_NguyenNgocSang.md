# Báo cáo Day 7

## Dữ liệu và benchmark

- **Nguồn:** OpenStax, *Introduction to Computer Science*. PDF gốc nằm trong thư mục `data/corpus/` của repo Day 6 (`$DAY6_ROOT`), không được copy vào repo Day 7. PDF có 939 trang; trang bản quyền ghi Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0). Phiên bản/ấn bản không được lưu trong artifacts; cần ghi lại khi chốt nguồn nộp.
- **Phạm vi index:** PostgreSQL 16 + pgvector 0.8.7 chạy local theo Docker Compose Day 6. Database hiện có 251 chunks cho strategy A và 317 chunks cho mỗi strategy B/C (paragraph, tối đa 500 ký tự). Các benchmark trong báo cáo chỉ dùng A: fixed-size 500 ký tự, overlap 50 ký tự, trên 34 giá trị trang nguồn (19–60). Vì vậy đây chưa phải index toàn bộ PDF 939 trang.
- **Dense embedding:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 chiều; embedding được normalize và truy vấn pgvector bằng cosine distance. Không có version/hash của model được lưu. TF-IDF dùng lowercase, unigram/bigram, English stop words và cosine similarity.
- **Agent:** OpenRouter, model `openai/gpt-4o-mini` (theo lần chạy demo thành công); không ghi API key vào báo cáo. Hybrid dùng Reciprocal Rank Fusion (RRF), `rrf_k=60`, lấy tối đa 20 ứng viên từ mỗi retriever rồi trả top-3. Không có reranker riêng.
- **Benchmark retrieval:** [questions.json](../../benchmark/questions.json) có 20 câu có gold evidence: 15 dev và 5 test. Bốn câu có filter: q03/q09 dùng `chapter_1` ở dev; q17/q19 dùng `chapter_2` ở test. Evaluator đã được sửa để đọc trường `filter` đơn trong benchmark (trước đó chỉ đọc `filters`/`metadata_filter`), rồi chạy lại các kết quả trong báo cáo.
- **Benchmark agent:** [agent_cases.json](../../benchmark/agent_cases.json) có 24 câu: dev 17 (15 answerable, 2 unanswerable), test 7 (5 answerable, 2 unanswerable). Agent được kỳ vọng trả lời câu có evidence và abstain khi thiếu evidence.
- **Tiêu chí retrieval:** so khớp toàn bộ `evidence_quote` sau khi chuẩn hóa whitespace, đồng thời yêu cầu đúng `source_id` và trang. `Hit@1` là evidence ở hạng 1; `Evidence Hit@3` là có evidence ở top-3; `Context Evidence Rate` là evidence có mặt trong context gửi cho agent.
- **Review agent:** Đã đối chiếu câu trả lời với citation chunk cho từng trace và chấm theo [rubric benchmark](../../BENCHMARK.md). Các file review và metric được lưu cùng trace. Đây là evidence audit trong lần làm báo cáo, không phải đánh giá độc lập/blind. Các câu unanswerable đã được rà soát trên text toàn PDF; riêng u03/u04 không có số liệu điện của máy tác giả hoặc email cá nhân của Ada Lovelace.
- **Giới hạn đo lường:** Test retrieval và test agent đã chạy. Trace không lưu token hoặc chi phí OpenRouter, vì vậy chi phí là **không được ghi nhận**, không phải 0. Chỉ số agent phản ánh những lần chạy đã lưu; model/API có thể không deterministic.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, filter, context budget | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Latency retrieval/context |
|---|---|---|---:|---:|---:|---:|
| Baseline TF-IDF | Strategy A; unigram/bigram cosine; top-3; budget 800 | dev, n=15 | 9/15 (60.0%) | 10/15 (66.7%) | 9/15 (60.0%) | 3.37 ms/query |
| Dense | Strategy A; MiniLM + pgvector cosine; top-3; budget 800 | dev, n=15 | 7/15 (46.7%) | 11/15 (73.3%) | 7/15 (46.7%) | 141.61 ms/query |
| Hybrid (800) | Dense + TF-IDF; RRF k=60; tối đa 20 candidate/retriever; fused top-3; budget 800 | dev, n=15 | 9/15 (60.0%) | 12/15 (80.0%) | 9/15 (60.0%) | 186.20 ms/query |
| Hybrid (1600) | Như trên; budget 1600 | dev, n=15 | 9/15 (60.0%) | 12/15 (80.0%) | 10/15 (66.7%) | 159.46 ms/query |
| Hybrid (3200) | Như trên; budget 3200 | dev, n=15 | 9/15 (60.0%) | 12/15 (80.0%) | 12/15 (80.0%) | 369.66 ms/query |
| Baseline TF-IDF | Strategy A; top-3; budget 800 | test, n=5 | 2/5 (40.0%) | 3/5 (60.0%) | 2/5 (40.0%) | 3.28 ms/query |
| Dense | Strategy A; MiniLM + pgvector cosine; top-3; budget 800 | test, n=5 | 3/5 (60.0%) | 3/5 (60.0%) | 3/5 (60.0%) | 165.65 ms/query |
| Cấu hình Hybrid đã chạy | RRF k=60; top-3; budget 800 | test, n=5 | 3/5 (60.0%) | 3/5 (60.0%) | 3/5 (60.0%) | 205.74 ms/query |

Filter được truyền cho mọi retriever theo benchmark: q03/q09 dùng `chapter_1` ở dev; q17/q19 dùng `chapter_2` ở test; các câu còn lại không lọc. Latency là thời gian retrieval và đóng gói context trong evaluator, không gồm khởi tạo model/embedding hoặc lượt gọi LLM. Budget 800 là mặc định của evaluator và cũng là budget của các lần agent test. Dịch vụ/API cost không được lưu. Các con số giữa lần chạy có thể dao động; không diễn giải chênh lệch latency nhỏ như cải thiện ổn định.

**Lỗi dev và phân tích**

1. **q01 — “What does computer science study?”**: hybrid tìm được gold ở top-3 nhưng không đưa vào context ở budget 800 hoặc 1600; budget 3200 đưa được vào. Đây là lỗi đóng gói context, không phải thay đổi ranking. Kết quả 3200 tốt nhất về Context Evidence Rate trong các cấu hình retrieval đã lưu, nhưng chưa được kiểm chứng bằng agent end-to-end ở budget đó.
2. **q02/q03 — algorithm và binary search:** gold quote dài lần lượt khoảng 210/205 ký tự nhưng không có chunk strategy A nào trên trang gold chứa nguyên quote sau khi chuẩn hóa whitespace. Cả ba retriever vì vậy bị chấm miss top-3. Đây là vấn đề gold span/chunk boundary hoặc chuẩn hóa dữ liệu; cần sửa quote cho khớp một chunk hoặc định nghĩa rõ evidence nhiều chunk trước khi dùng các miss này để kết luận về ranking.

**Lựa chọn:** Hybrid được dùng làm cấu hình retrieval cho agent vì Evidence Hit@3 trên dev là 12/15, so với TF-IDF 10/15 và Dense 11/15. Trong thử nghiệm retrieval-only, budget 3200 đạt Context Evidence Rate 12/15, cao nhất, nhưng agent được đánh giá với budget 800; không suy rộng kết quả agent sang budget 3200. Test Hybrid 800 đạt 3/5 ở cả ba retrieval/context metric, ngang Dense và cao hơn TF-IDF về Hit@3/context trên mẫu test nhỏ này.

Artifacts: [TF-IDF dev](../retrieval/tfidf_dev.json), [Dense dev](../retrieval/dense_dev.json), [Hybrid dev 800](../retrieval/hybrid_dev_800.json), [Hybrid dev 1600](../retrieval/hybrid_dev_1600.json), [Hybrid dev 3200](../retrieval/hybrid_dev_3200.json), [TF-IDF test](../retrieval/tfidf_test.json), [Dense test](../retrieval/dense_test.json), [Hybrid test 800](../retrieval/hybrid_test_800.json).

## Agent và đánh giá

- **Luồng:** một search tool dùng Hybrid RRF; top-3 mỗi lượt, tối đa 4 search, context budget 800 ký tự. Context expansion tìm overlap từ 25 ký tự trở lên giữa chunks cùng nguồn/trang và lấy cửa sổ quanh điểm nối (tối đa khoảng 250 ký tự mỗi phía). Agent chỉ giữ context trong budget.
- **Dừng và citation:** dừng khi model trả answer; blank answer/citations, citation ID không có trong context hoặc thiếu `[chunk-id]` trong answer dẫn tới abstain; đạt giới hạn search cũng abstain. Kiểm tra này chỉ xác nhận citation ID/format, không xác nhận evidence có hỗ trợ nội dung. Lỗi API/retriever cần được báo riêng, không dùng kết quả giả.

| Cấu hình / split | Tool use | Search calls | Grounded answer (0/1/2; mean /2) | Citation support | Answer có citation | Abstention đúng; từ chối nhầm |
|---|---:|---:|---|---|---:|---|
| Hybrid trước context expansion, dev | 17/17 | 22 tổng; 1.29/query | 2/1/12; 1.67 | 13/13 | 13/13 | 2/2; 2/15 |
| Hybrid sau context expansion, dev | 17/17 | 26 tổng; 1.53/query | 8/0/7; 0.93 | 7/11 | 11/11 | 2/2; 4/15 |
| Baseline TF-IDF, test | 7/7 | 14 tổng; 2.00/query | 2/1/2; 1.00 | 3/3 | 3/3 | 2/2; 2/5 |
| Hybrid, test | 7/7 | 14 tổng; 2.00/query | 2/0/3; 1.20 | 3/3 | 3/3 | 2/2; 2/5 |

Citation support là review ngữ nghĩa của passage, không phải chỉ kiểm tra ID/format. Mọi lần chạy có 0 provider error. Wall-clock trung bình: Hybrid dev trước 2.811 giây/query (median 2.419), sau 2.815 (median 2.575), TF-IDF test 3.250 và Hybrid test 3.399 giây/query. Token/API cost không được lưu. Sau expansion, câu answerable có trạng thái answered giảm 13/15 xuống 11/15; q08/q10/q13 chuyển từ answered sang abstain, q14 từ abstain sang answered; q06 chạm search limit sau 4 lượt. Chất lượng grounded cũng giảm trong các trace này: citation support từ 13/13 xuống 7/11, chủ yếu do q04/q05/q09/q12 có citation không hỗ trợ phần cốt lõi của answer. Đây là đánh giá các trace đã lưu, không khẳng định nhân quả; model/API có thể không deterministic.

**Trace từng câu sau context expansion** (answer đầy đủ trong [hybrid_dev_after.json](../agent/hybrid_dev_after.json); review chi tiết tại [hybrid_dev_after_reviews.json](../agent/hybrid_dev_after_reviews.json)):

| Query ID | Kết quả | Grade / citation | Nhận xét |
|---|---|---|---|
| q01 | answered; 1 search | 2 / supported | Định nghĩa và ví dụ được passage hỗ trợ. |
| q02 | answered; 1 search | 2 / supported | Định nghĩa algorithm có trong chunk; retrieval gold span vẫn có giới hạn căn chỉnh chunk. |
| q03 | answered; 1 search | 2 / supported | Giải thích đúng cách chia đôi interval. |
| q04 | answered; 1 search | 0 / unsupported | Citation là passage recipe/abacus, không hỗ trợ John Napier. |
| q05 | answered; 1 search | 0 / unsupported | Citation nói về Napier/logarithms, không hỗ trợ mục đích Difference Engine. |
| q06 | abstain; 4 searches | 0 / không có citation | Từ chối nhầm câu có evidence sau khi chạm search limit. |
| q07 | answered; 1 search | 2 / supported | Bellman và năm 1953 được passage hỗ trợ. |
| q08 | abstain; 3 searches | 0 / không có citation | Từ chối nhầm câu có evidence. |
| q09 | answered; 1 search | 0 / unsupported | Citation không nêu/không hỗ trợ bốn hardware components. |
| q10 | abstain; 2 searches | 0 / không có citation | Từ chối nhầm câu có evidence. |
| q11 | answered; 1 search | 2 / supported | Citation hỗ trợ định nghĩa Turing-complete. |
| q12 | answered; 1 search | 0 / unsupported | Citation hỗ trợ mục đích giáo dục của LOGO, không hỗ trợ turtle graphics trong answer. |
| q13 | abstain; 2 searches | 0 / không có citation | Từ chối nhầm câu có evidence. |
| q14 | answered; 1 search | 2 / supported | Passage xác nhận Mark Dean và công việc với Industry Standard Architecture. |
| q15 | answered; 1 search | 2 / supported | Quan hệ giữa lượng dữ liệu/người dùng và rủi ro spreadsheet được hỗ trợ. |
| u01 | abstain; 2 searches | Đúng | Không tìm thấy Python 3.15/ngày phát hành trong text PDF. |
| u02 | abstain; 2 searches | Đúng | Không có số liệu thị phần Việt Nam; chỗ nhắc Windows 11 là danh sách phần mềm. |

**Test agent:** TF-IDF baseline và Hybrid chạy cùng 7 câu test; mỗi cấu hình gọi search 14 lần, trả lời q17–q19 và abstain q16/q20 cùng hai câu ngoài phạm vi u03/u04. Trong cả hai trace, 3 câu trả lời có citation đều được passage hỗ trợ; 2/2 câu unanswerable abstain đúng. q16/q20 là từ chối nhầm trên câu answerable. [Trace TF-IDF](../agent/tfidf_test_traces.json), [review TF-IDF](../agent/tfidf_test_reviews.json), [metrics TF-IDF](../agent/tfidf_test_metrics.json), [trace Hybrid](../agent/hybrid_test_traces.json), [review Hybrid](../agent/hybrid_test_reviews.json), [metrics Hybrid](../agent/hybrid_test_metrics.json).

- **Trace/review dev:** [Hybrid trước expansion](../agent/hybrid_dev_before.json), [review trước](../agent/hybrid_dev_before_reviews.json), [metrics trước](../agent/hybrid_dev_before_metrics.json), [Hybrid sau expansion](../agent/hybrid_dev_after.json), [review sau](../agent/hybrid_dev_after_reviews.json), [metrics sau](../agent/hybrid_dev_after_metrics.json), [agent_cases.json](../../benchmark/agent_cases.json).
- **Hạn chế:** evidence review là một lượt chấm, không có inter-rater agreement. Context expansion chưa cải thiện chất lượng end-to-end trong trace dev đã lưu; đặc biệt có citation không hỗ trợ answer ở q04/q05/q09/q12.

## Thử thách nâng cao

Tài liệu gốc dài hơn 100 trang (939 trang) và có giấy phép CC BY-NC-SA 4.0, nhưng artifacts hiện có chỉ chứng minh index text trên 34 giá trị trang nguồn (19–60). Không có bằng chứng index toàn bộ tài liệu, trích xuất/kiểm chứng bảng, ảnh hoặc biểu đồ; cũng không có benchmark nhóm nâng cao, test traces 30 câu, nhãn từng câu hoặc kết quả đạt ngưỡng 90%. Vì vậy **thử thách nâng cao chưa hoàn thành; không tuyên bố đạt bonus**.

| Nhóm test | Kết quả hiện có | Tỷ lệ | Giới hạn |
|---|---|---|---|
| Bảng | 0 câu có nhãn | — | Không có bộ câu hỏi/trace riêng |
| Ảnh, sơ đồ | 0 câu có nhãn | — | Không có pipeline visual/OCR được xác minh |
| Biểu đồ | 0 câu có nhãn | — | Không có bộ câu hỏi/trace riêng |
| Multi-hop | 0 câu có nhãn | — | Không có nhãn evidence nhiều bước |
| Text nâng cao | 0 câu thuộc benchmark nâng cao | — | Test text hiện tại chỉ là benchmark cơ bản |
| Câu ngoài phạm vi nguồn (test cơ bản) | Agent abstain đúng 2/2 ở cả hai cấu hình | 100% | Không phải benchmark nâng cao riêng |
| **Toàn bộ thử thách nâng cao** | **Không chạy** | **—** | **Không có benchmark 30 câu; không thể kết luận đạt ngưỡng 90%** |

- **Lệnh tái lập retrieval dev** (chạy từ root Day 7; đặt `DAY6_ROOT` tới repo Day 6 trước):

  ```powershell
  python starter/evaluate_retrievers.py --split dev --strategy tfidf --chunk-strategy A --budget 800
  python starter/evaluate_retrievers.py --split dev --strategy dense --chunk-strategy A --budget 800
  python starter/evaluate_retrievers.py --split dev --strategy hybrid --chunk-strategy A --budget 800
  python starter/evaluate_retrievers.py --split test --strategy tfidf --chunk-strategy A --budget 800
  python starter/evaluate_retrievers.py --split test --strategy dense --chunk-strategy A --budget 800
  python starter/evaluate_retrievers.py --split test --strategy hybrid --chunk-strategy A --budget 800
  python starter/evaluate_agent.py --split dev --retriever hybrid --max-searches 4 --budget 800
  python starter/evaluate_agent.py --split test --retriever tfidf --max-searches 4 --budget 800
  python starter/evaluate_agent.py --split test --retriever hybrid --max-searches 4 --budget 800
  ```

  Evaluator ghi đè file cùng tên khi chạy lại; giữ bản sao từng budget với hậu tố `_800`, `_1600`, `_3200`. Demo smoke test: `python starter/demo_agent.py --question "What is an algorithm?" --retriever hybrid`. Không đưa `.env`/API key vào báo cáo hoặc Git.
- Các đường dẫn lệnh/code: [evaluate_retrievers.py](../../starter/evaluate_retrievers.py), [evaluate_agent.py](../../starter/evaluate_agent.py), [demo_agent.py](../../starter/demo_agent.py), [định dạng benchmark](../../data/README.md).
- Warning còn lại: Day 6 gọi `get_sentence_embedding_dimension()` và hiện FutureWarning đổi tên API; không làm hỏng lần chạy. Cần cập nhật ở repo Day 6 riêng nếu muốn loại warning.
