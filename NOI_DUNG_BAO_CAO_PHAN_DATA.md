# CHƯƠNG 4: XÂY DỰNG TẬP DỮ LIỆU MÔ PHỎNG VÀ QUY TRÌNH SINH DỮ LIỆU

*(Định dạng: Font Times New Roman, cỡ 13, giãn dòng 1.5, lề trái 3.5cm, lề phải 2cm)*

---

## 4.1. Tổng quan về dữ liệu mô phỏng (Synthetic Data)

### 4.1.1. Lý do sử dụng dữ liệu mô phỏng

Trong quá trình phát triển Hệ thống Cảnh báo Sớm (EWS), nhóm đã đưa ra quyết định chiến lược sử dụng dữ liệu mô phỏng (Synthetic Data) thay vì dữ liệu thực từ hệ thống LMS Moodle của trường. Quyết định này dựa trên bốn cơ sở chính:

**Thứ nhất, vấn đề đạo đức nghiên cứu và bảo mật dữ liệu cá nhân (Data Privacy & Research Ethics).** Theo quy định chung về bảo vệ dữ liệu cá nhân, việc thu thập và xử lý lịch sử truy cập chi tiết của sinh viên — bao gồm thời gian đăng nhập, thời lượng phiên học tập, điểm số bài kiểm tra — đòi hỏi sự đồng ý rõ ràng (informed consent) của từng sinh viên và sự phê duyệt của Hội đồng Đạo đức Nghiên cứu (Institutional Review Board — IRB). Trong khuôn khổ đồ án tốt nghiệp với timeline giới hạn, nhóm không có đủ thời gian và thẩm quyền pháp lý để hoàn tất quy trình này. Nghiên cứu của Jordon và cộng sự (2022) [1] đã chỉ ra rằng synthetic data là giải pháp được khuyến khích trong nghiên cứu giáo dục khi dữ liệu thực gặp rào cản về quyền riêng tư, cho phép nhà nghiên cứu phát triển và kiểm thử mô hình mà không xâm phạm quyền riêng tư của người học.

**Thứ hai, vấn đề mất cân bằng dữ liệu (Class Imbalance).** Trong thực tế, dữ liệu hành vi học tập thường có sự mất cân bằng nghiêm trọng: sinh viên hoàn thành khóa học chiếm đại đa số (thường trên 85–90%), trong khi các trường hợp sinh viên bỏ học giữa chừng, gian lận, hoặc gián đoạn học tập do ngoại cảnh chỉ chiếm tỷ lệ rất nhỏ (dưới 5%). Sự mất cân bằng này gây khó khăn lớn cho việc huấn luyện mô hình Machine Learning, vì mô hình có xu hướng thiên về lớp đa số (majority class) và bỏ qua các trường hợp thiểu số — chính là những trường hợp mà hệ thống EWS cần phát hiện. Nghiên cứu của Fernández và cộng sự (2018) [6] đã chỉ ra rằng class imbalance là một trong những thách thức lớn nhất trong Educational Data Mining, và kỹ thuật oversampling/synthetic generation là phương pháp phổ biến để khắc phục.

**Thứ ba, khả năng kiểm soát kịch bản biên (Edge Cases) và xác lập Ground Truth.** Dữ liệu mô phỏng cho phép nhóm chủ động thiết kế đầy đủ các kịch bản hành vi đặc biệt: gian lận bài thi (Gaming the System), bỏ cuộc giữa chừng (Disengaging), gián đoạn do bệnh tật (External Disruption), trì hoãn học tập (Procrastination). Những kịch bản này trong thực tế rất hiếm gặp nhưng lại là đối tượng chính mà hệ thống EWS cần nhận diện. Quan trọng hơn, dữ liệu mô phỏng cho phép nhóm biết chính xác nhãn thực (ground truth) — nghĩa là biết chắc sinh viên nào thuộc nhóm hành vi nào — để đánh giá chính xác hiệu quả của mô hình phân loại.

**Thứ tư, tính tái tạo kết quả nghiên cứu (Reproducibility).** Bằng cách sử dụng hạt giống ngẫu nhiên cố định (`random.seed(42)`) trong script sinh dữ liệu, toàn bộ tập dữ liệu có thể được tái tạo chính xác 100% bất kỳ lúc nào, đảm bảo tính minh bạch và khả năng kiểm chứng của kết quả nghiên cứu — một yêu cầu quan trọng trong khoa học dữ liệu.

> **Lưu ý quan trọng:** Mục đích của hệ thống EWS Pro là *proof-of-concept* — chứng minh tính khả thi của kiến trúc hệ thống và pipeline xử lý dữ liệu. Trong triển khai thực tế (production), mô hình Machine Learning sẽ được huấn luyện lại (retrain) trên dữ liệu hành vi thực từ Moodle của trường thông qua module ETL (`etl_moodle_warehouse.py`) kết nối trực tiếp vào MySQL database.

---

### 4.1.2. Cơ sở khoa học thiết kế 8 nhóm hành vi sinh viên (G1–G8)

Tập dữ liệu mô phỏng được thiết kế dựa trên **8 nhóm hành vi sinh viên (behavioral archetypes)**, mỗi nhóm mô tả một mẫu hành vi học tập đặc trưng trên hệ thống LMS. Các nhóm này được xây dựng từ tổng hợp và ánh xạ kết quả của **5 công trình nghiên cứu tiêu biểu** trong lĩnh vực Learning Analytics và Educational Data Mining:

#### a) Nghiên cứu nền tảng: Phân loại mức độ tương tác của sinh viên

**Kizilcec, Piech & Schneider (2013) [2]** — *"Deconstructing Disengagement: Analyzing Learner Subpopulations in Massive Open Online Courses"*, Hội nghị Learning Analytics and Knowledge (LAK '13), ACM.

Nghiên cứu này phân tích dữ liệu từ 3 khóa MOOC trên Coursera với hơn 100,000 người học, sử dụng kỹ thuật phân cụm (clustering) để xác định **4 nhóm hành vi chính** dựa trên mức độ tương tác với nội dung khóa học:

| Nhóm Kizilcec | Mô tả | Ánh xạ G | Đặc điểm trong EWS Pro |
|---|---|---|---|
| **Completing** | Hoàn thành hầu hết bài tập và video | → **G1** (Chăm chỉ toàn diện) | Login 8–15 lần/tuần, xem 3–8 video, đọc 2–6 tài liệu, hoàn thành 95% bài tập, điểm 7.5–10.0 |
| **Auditing** | Xem video nhưng không nộp bài | → **G5** (Yếu — không đọc tài liệu) | Login 2–5 lần nhưng document_reads = 0, ít nộp bài (35%), điểm 1.0–4.0 |
| **Disengaging** | Bắt đầu tích cực rồi bỏ dần | → **G7** (Bỏ cuộc giữa chừng) | Tuần 1: login 1–4 (prob 60%), Tuần 4: gần như bỏ hẳn (prob 5%) |
| **Sampling** | Chỉ "nếm thử" vài bài | → **G4** (Yếu — ít đăng nhập) | Login 0–3 lần/tuần, active_days 0–2, điểm 1.5–4.5 |

#### b) Nghiên cứu về hành vi trì hoãn (Procrastination)

**You, J. W. (2016) [3]** — *"Identifying Significant Indicators Using LMS Data to Predict Course Achievement in Online Learning"*, The Internet and Higher Education, Vol. 29.

Nghiên cứu phân tích log data từ LMS của 530 sinh viên đại học, phát hiện rằng **thời điểm nộp bài** (submission timing) là một trong những chỉ báo mạnh nhất cho kết quả học tập. You phân biệt hai loại trì hoãn:

| Loại trì hoãn | Mô tả | Ánh xạ G | Đặc điểm trong EWS Pro |
|---|---|---|---|
| **Active Procrastination** | Nộp sát deadline nhưng chất lượng tốt | → **G2** (Trì hoãn tích cực) | ontime_margin: -200 đến +100 phút, nhưng điểm 5.5–8.5, login 4–10 lần/tuần |
| **Passive Procrastination** | Nộp trễ, chất lượng thấp | → **G4** (Yếu — ít đăng nhập) | ontime_margin: -800 đến -100 phút, điểm 2.0–5.0, login 0–3 lần/tuần |

Feature `ontime_margin` trong tập dữ liệu được thiết kế để phản ánh chính xác phát hiện này: giá trị dương biểu thị nộp trước deadline, giá trị âm biểu thị nộp trễ.

#### c) Nghiên cứu về mẫu tương tác trên diễn đàn

**Romero, López & Luna (2013) [4]** — *"Predicting Students' Final Performance from Participation in On-line Discussion Forums"*, Computers & Education, Vol. 68.

Nghiên cứu sử dụng dữ liệu từ Moodle forum của 438 sinh viên, phát hiện rằng mức độ tham gia thảo luận (discussion participation) là một biến dự báo mạnh cho kết quả học tập cuối khóa. Nghiên cứu phân biệt giữa:

| Mẫu hành vi | Mô tả | Ánh xạ G | Đặc điểm trong EWS Pro |
|---|---|---|---|
| **Active Participants** | Đọc và đăng bài thường xuyên | → **G1** (discussion: 2–5/tuần), **G2** (1–3/tuần) | Tương quan dương với điểm cuối khóa |
| **Passive Lurkers** | Đọc nhưng không đăng bài | → **G6** (Thụ động — không thảo luận) | discussion = 0 bài/tuần, nhưng vẫn login xem tài liệu (doc_reads 1–3, video 1–3) |

Feature `discussion` được thiết kế với giá trị = 0 tuyệt đối cho nhóm G6, phản ánh chính xác hành vi "passive lurking" mà Romero và cộng sự đã mô tả.

#### d) Nghiên cứu về gian lận học thuật (Gaming the System)

**Baker, Corbett, Koedinger & Wagner (2004) [5]** — *"Off-Task Behavior in the Cognitive Tutor Classroom: When Students 'Game the System'"*, Proceedings of SIGCHI Conference on Human Factors in Computing Systems, ACM.

Baker và cộng sự định nghĩa "gaming the system" là hành vi cố tình khai thác lỗ hổng của hệ thống để đạt điểm cao mà không thực sự học tập. Dấu hiệu đặc trưng:
- Thời gian làm bài rất ngắn so với mặt bằng chung (attempt duration thấp bất thường)
- Điểm số cao bất thường so với mức độ tương tác (high score, low engagement)
- Ít xem tài liệu/video nhưng vẫn đạt kết quả tốt

| Mẫu hành vi | Ánh xạ G | Đặc điểm trong EWS Pro |
|---|---|---|
| **Gaming the System** | → **G3** (Gian lận) | quiz_grade: 9.0–10.0, assign_grade: 8.0–10.0 NHƯNG session_duration chỉ 5–15 phút/tuần (vs G1 là 40–90 phút), assign_duration: 2–8 phút (vs G1 là 20–55 phút), video_views: 0–2, document_reads: 0–1 |

Nhóm G3 được thiết kế để mô phỏng chính xác mẫu này: **điểm cao bất thường kết hợp với thời gian tương tác thấp bất thường** — tạo ra tín hiệu anomaly mà mô hình ML cần nhận diện.

#### e) Kịch bản ngoại lệ: Gián đoạn do ngoại cảnh

**Nhóm G8 (Ốm tuần 3)** được thiết kế dựa trên quan sát thực tế về ảnh hưởng của các sự kiện ngoại cảnh (bệnh tật, gia đình, công việc) đến hành vi học tập. Đây là một kịch bản quan trọng mà hệ thống EWS cần phân biệt với hành vi "bỏ cuộc" (G7):

| Feature | Tuần 1 | Tuần 2 | Tuần 3 (ốm) | Tuần 4 (hồi phục) |
|---|---|---|---|---|
| Activity multiplier | 1.0 | 1.0 | **0.15** | 0.90 |
| Login count | 5–12 | 5–12 | **1–2** | 5–11 |
| Session duration | 30–70 | 30–70 | **5–11** | 27–63 |
| Prob làm bài | 85% | 85% | **10%** | 85% |

Điểm khác biệt then chốt so với G7 (Bỏ cuộc): G8 có mẫu "V-shape" — sụt giảm mạnh ở tuần 3 nhưng **hồi phục** ở tuần 4, trong khi G7 có xu hướng suy giảm liên tục không hồi phục (60% → 40% → 10% → 5%).

#### Tổng hợp: Bảng ánh xạ 8 nhóm hành vi

| Nhóm | Tên | Cơ sở khoa học | Đặc trưng nổi bật | Số SV |
|------|-----|----------------|---------------------|-------|
| **G1** | Chăm chỉ toàn diện | Kizilcec (2013) — Completing | Login cao, điểm cao, session dài | 28 |
| **G2** | Trì hoãn tích cực | You (2016) — Active Procrastination | Nộp sát deadline, điểm khá | 28 |
| **G3** | Gian lận | Baker (2004) — Gaming the System | Điểm cao, session ngắn bất thường | 24 |
| **G4** | Yếu — ít đăng nhập | Kizilcec (2013) — Sampling | Login 0–3, điểm thấp | 24 |
| **G5** | Yếu — không đọc TL | Kizilcec (2013) — Auditing | document_reads = 0 | 24 |
| **G6** | Thụ động — không thảo luận | Romero (2013) — Passive Lurkers | discussion = 0 | 24 |
| **G7** | Bỏ cuộc giữa chừng | Kizilcec (2013) — Disengaging | Giảm dần 60%→5% theo tuần | 24 |
| **G8** | Gián đoạn do ngoại cảnh | Quan sát thực tế | V-shape: sụt tuần 3, phục hồi tuần 4 | 24 |

**Tổng: 200 sinh viên**, phân bổ đều trong 4 lớp (22CT111–22CT114), mỗi lớp 50 sinh viên chứa đầy đủ 8 nhóm hành vi (~6–7 SV/nhóm/lớp) để đảm bảo tính đại diện.

---

### 4.1.3. Bảng mô tả 13 features hành vi học tập

Mỗi sinh viên có 13 features được thu thập theo tuần (w1–w4), tổng cộng 52 features theo tuần cộng thêm 12 features tổng hợp (totals/averages) và 5 trường thông tin cá nhân:

#### a) Features đo lường mức độ tương tác (Engagement Metrics)

| # | Feature | Kiểu | Đơn vị | Mô tả | Nguồn trên Moodle |
|---|---------|-------|--------|-------|---------------------|
| 1 | `login_count` | int | lần/tuần | Số lần đăng nhập vào hệ thống LMS | `mdl_logstore_standard_log` (event: `\core\event\user_loggedin`) |
| 2 | `active_days` | int | ngày/tuần | Số ngày có ít nhất 1 lần đăng nhập | Tính từ `DISTINCT DATE(FROM_UNIXTIME(timecreated))` trong log |
| 3 | `session_duration` | int | phút/tuần | Tổng thời lượng phiên học tập trung bình | Tính từ khoảng cách giữa 2 event liên tiếp của cùng 1 user |
| 4 | `video_views` | int | lượt/tuần | Số lượt xem tài nguyên video (mod_url) | `mdl_logstore_standard_log` (component: `mod_url`, action: `viewed`) |
| 5 | `document_reads` | int | lượt/tuần | Số lượt đọc tài liệu học tập (mod_page) | `mdl_logstore_standard_log` (component: `mod_page`, action: `viewed`) |
| 6 | `discussion` | int | bài/tuần | Số lượt tham gia thảo luận trên forum | `mdl_logstore_standard_log` (component: `mod_forum`, action: `created`) |

#### b) Features đo lường kết quả học tập (Performance Metrics)

| # | Feature | Kiểu | Đơn vị | Mô tả | Nguồn trên Moodle |
|---|---------|-------|--------|-------|---------------------|
| 7 | `total_assignments` | int | bài/tuần | Tổng số bài tập được giao trong tuần | `mdl_assign` (filtered by course section) |
| 8 | `assignment_attempt` | int | bài/tuần | Số bài tập sinh viên đã nộp | `mdl_assign_submission` (status: 'submitted') |
| 9 | `assignment_duration_mins` | float | phút | Thời gian hoàn thành bài tập (tính từ lúc mở đến lúc nộp) | Hiệu giữa `timemodified` và `timecreated` trong `mdl_assign_submission` |
| 10 | `weekly_score` | float | điểm (0–10) | Điểm trung bình tuần = tổng điểm quiz + assign chia tổng số bài | `mdl_grade_grades.finalgrade` / `mdl_grade_items.grademax` × 10 |

#### c) Features đo lường hành vi thời gian (Temporal Behavior Metrics)

| # | Feature | Kiểu | Đơn vị | Mô tả | Nguồn trên Moodle |
|---|---------|-------|--------|-------|---------------------|
| 11 | `ontime_margin` | int | phút | Khoảng cách thời gian nộp bài so với deadline. Dương = trước hạn, Âm = trễ hạn | `mdl_assign.duedate - mdl_assign_submission.timemodified` |
| 12 | `days_since_last_login` | int | ngày | Số ngày kể từ lần đăng nhập gần nhất | `(NOW - MAX(timecreated)) / 86400` trong log |
| 13 | `deadline_proximity` | int | ngày | Số ngày còn lại trước deadline gần nhất | `(MIN(duedate) - NOW) / 86400` |

#### d) Công thức tính các trường tổng hợp (Totals)

Các trường tổng hợp được tính từ 4 tuần dữ liệu theo công thức:

| Trường tổng hợp | Công thức | Ý nghĩa |
|---|---|---|
| `total_login_count` | `Σ(login_count_w1..w4)` | Tổng lần đăng nhập 4 tuần |
| `total_active_days` | `Σ(active_days_w1..w4)` | Tổng ngày hoạt động |
| `total_video_views` | `Σ(video_views_w1..w4)` | Tổng lượt xem video |
| `total_document_reads` | `Σ(document_reads_w1..w4)` | Tổng lượt đọc tài liệu |
| `total_discussion` | `Σ(discussion_w1..w4)` | Tổng lượt thảo luận |
| `total_assignment_attempt` | `Σ(attempt_w1..w4)` | Tổng bài đã nộp |
| `total_assignment_duration` | `Σ(duration_w1..w4)` | Tổng thời gian làm bài |
| `total_ontime_margin` | `Σ(ontime_margin_w1..w4)` | Tổng cộng biên thời gian |
| `total_weekly_score` | `AVG(score_w1..w4)` | **Trung bình** điểm 4 tuần |
| `total_days_since_last_login` | `AVG(days_since_w1..w4)` | **Trung bình** khoảng cách login |
| `total_session_duration` | `AVG(session_w1..w4)` | **Trung bình** session |
| `total_deadline_proximity` | `Σ(deadline_w1..w4)` | Tổng proximity |

> **Lưu ý thiết kế:** `total_weekly_score` và `total_session_duration` dùng phép **trung bình (AVG)** thay vì tổng (SUM), vì tổng điểm 4 tuần không có ý nghĩa thống kê bằng điểm trung bình, và thời lượng session trung bình phản ánh mức độ tương tác tốt hơn tổng.

#### e) Ví dụ cụ thể: 1 record dữ liệu mẫu

Dưới đây là dữ liệu thực tế của sinh viên **Nguyễn Văn An** (MSSV 122000000, Nhóm G1 — Chăm chỉ, Lớp 22CT111) ở khóa English IT:

| Tuần | login | active_days | video | doc | disc | attempt | duration | score | session | ontime | days_since | deadline |
|------|-------|-------------|-------|-----|------|---------|----------|-------|---------|--------|------------|----------|
| W1 | 11 | 6 | 5 | 4 | 3 | 2/2 | 42.3 | 8.5 | 72 | 245 | 1 | 2 |
| W2 | 9 | 5 | 4 | 3 | 2 | 2/2 | 38.1 | 7.8 | 58 | 180 | 1 | 3 |
| W3 | 13 | 7 | 6 | 5 | 4 | 2/2 | 51.7 | 9.2 | 85 | 420 | 0 | 1 |
| W4 | 10 | 6 | 3 | 2 | 3 | 2/2 | 35.6 | 8.1 | 63 | 310 | 1 | 2 |
| **Total** | **43** | **24** | **18** | **14** | **12** | **8** | **167.7** | **8.4** (avg) | **70** (avg) | **1155** | **1** (avg) | **8** |

**Nhận xét:** Dữ liệu phản ánh đúng hành vi G1 — login đều đặn (9–13 lần/tuần), hoàn thành 100% bài tập (8/8), điểm cao ổn định (7.8–9.2), session dài (58–85 phút), nộp bài trước deadline (ontime_margin luôn dương).

So sánh với SV nhóm **G7 (Bỏ cuộc)** — MSSV 122000045:

| Tuần | login | active_days | video | doc | disc | attempt | score | session |
|------|-------|-------------|-------|-----|------|---------|-------|--------|
| W1 | 3 | 2 | 1 | 1 | 1 | 1/2 | 4.2 | 18 |
| W2 | 2 | 1 | 0 | 0 | 0 | 1/2 | 2.8 | 8 |
| W3 | 0 | 0 | 0 | 0 | 0 | 0/2 | 0.0 | 0 |
| W4 | 0 | 0 | 0 | 0 | 0 | 0/2 | 0.0 | 0 |

**Nhận xét:** Xu hướng giảm rõ rệt — tuần 3–4 bỏ hẳn (login = 0, tất cả chỉ số = 0). Ràng buộc 1 được tuân thủ hoàn toàn.


---

### 4.1.4. Ràng buộc toàn vẹn dữ liệu (Data Integrity Constraints)

Để đảm bảo dữ liệu mô phỏng phản ánh đúng logic thực tế của hành vi học tập trên LMS, nhóm đã thiết kế **4 ràng buộc toàn vẹn** (integrity constraints) được kiểm tra tự động sau mỗi lần sinh dữ liệu. Các ràng buộc này ngăn chặn các trường hợp phi lý mà có thể xảy ra khi các feature được random độc lập:

#### Ràng buộc 1: Không đăng nhập → Không có hoạt động

```
NẾU login_count = 0
THÌ session_duration = 0
     active_days = 0
     video_views = 0
     document_reads = 0
     discussion = 0
     assignment_attempt_probability = 0
```

**Lý do:** Một sinh viên chưa đăng nhập vào hệ thống LMS thì không thể có thời gian học tập, không thể xem video hay đọc tài liệu. Đây là ràng buộc cơ bản nhất nhưng dễ bị vi phạm khi các feature được random độc lập — ví dụ, nhóm G4 có `login_count` range `(0,3)` có thể bằng 0, nhưng `session_duration` range `(5,20)` luôn ≥ 5 nếu không có ràng buộc.

**Triển khai trong `data_pipeline.py` (dòng 203–209):**

```python
# Constraint: no login → no activity
if row['login_count'] == 0:
    row['session_duration'] = 0
    row['active_days'] = 0
    row['video_views'] = 0
    row['document_reads'] = 0
    row['discussion'] = 0
```

#### Ràng buộc 2: Không làm bài → Không có điểm

```
NẾU assignment_attempt = 0
THÌ weekly_score = 0
     assignment_duration_mins = 0
```

**Lý do:** Nếu sinh viên không nộp bất kỳ bài tập hay quiz nào trong tuần, thì điểm tuần đó phải bằng 0 và thời gian làm bài cũng bằng 0.

**Triển khai:** Logic này được đảm bảo bởi cấu trúc vòng lặp sinh điểm — chỉ khi `random.random() < prob` thì mới tạo grade entry, ngược lại `grades = []` → `weekly_score = sum([]) / 2 = 0`.

#### Ràng buộc 3: Số ngày hoạt động ≤ Số lần đăng nhập

```
active_days ≤ login_count
```

**Lý do:** Trong một tuần, sinh viên có thể đăng nhập nhiều lần trong cùng một ngày (ví dụ: sáng và tối). Do đó, số ngày có hoạt động không thể lớn hơn tổng số lần đăng nhập.

**Triển khai trong `data_pipeline.py` (dòng 212):**

```python
row['active_days'] = min(row['active_days'], row['login_count'])
```

#### Ràng buộc 4: Tổng tuần khớp tuyệt đối với tổng kết

```
total_login_count = Σ(login_count_w1 + w2 + w3 + w4)
total_weekly_score = AVG(weekly_score_w1..w4)
total_session_duration = AVG(session_duration_w1..w4)
```

**Lý do:** Các trường tổng hợp phải nhất quán với dữ liệu chi tiết theo tuần. Bất kỳ sự sai lệch nào (dù chỉ 0.1 điểm do lỗi làm tròn) đều cho thấy lỗi trong pipeline tính toán.

**Triển khai trong `data_pipeline.py` (dòng 284–291):** Vòng lặp tính totals chạy song song với vòng lặp sinh weekly data, đảm bảo sử dụng cùng nguồn giá trị.

> **Tầm quan trọng:** Trước khi áp dụng các ràng buộc, nhóm đã phát hiện **128/1,600 weekly records** (~8%) vi phạm Ràng buộc 1 (login=0 nhưng session>0). Sau khi triển khai, tỷ lệ vi phạm giảm xuống **0/1,600** (0.00%).

---

### 4.1.5. Quy trình sinh dữ liệu End-to-End

Quy trình sinh và đồng bộ dữ liệu của hệ thống EWS Pro gồm **5 bước** chính, tạo thành một pipeline hoàn chỉnh từ sinh kịch bản đến phân tích:

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  BƯỚC 1           │    │  BƯỚC 2           │    │  BƯỚC 3           │
│  data_pipeline.py │───>│  AUTO_HOC_BAI.py  │───>│  Moodle MySQL     │
│  Sinh kịch bản    │    │  Bot Playwright   │    │  Log + Grades     │
│  → JSON + Sheets  │    │  → Hành vi SV     │    │  → 49,000+ events │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
┌──────────────────┐    ┌──────────────────┐             │
│  BƯỚC 5           │    │  BƯỚC 4           │             │
│  Kiểm định        │<───│  sync_to_mongo.py │<────────────┘
│  chất lượng       │    │  Sheets→MongoDB   │
└──────────────────┘    └──────────────────┘
```

#### Bước 1: Sinh kịch bản dữ liệu (`data_pipeline.py`)

**Input:** Cấu hình 8 nhóm hành vi (hardcoded), random seed = 42.

**Xử lý:**
1. Chia 200 SV thành 8 nhóm, trộn đều trong 4 lớp (hàm `assign_groups()`)
2. Với mỗi SV × mỗi khóa: sinh 4 tuần dữ liệu (hàm `gen_weekly_data()`)
3. Áp dụng activity multiplier cho G7 (giảm dần: 1.0→0.6→0.15→0.05) và G8 (V-shape: 1.0→1.0→0.15→0.90)
4. Kiểm tra 4 ràng buộc toàn vẹn sau mỗi record
5. Tính totals/averages cho 12 trường tổng hợp

**Output:**
- `students_data.json` — 400 records (200 SV × 2 khóa), mỗi record chứa 69 trường
- `moodle_config.json` — 200 entries (MSSV, Group, Class) cho Bot sử dụng
- Google Sheets — 3 worksheet: Cấu Hình, Data_EnglishIT, Data_C++

**Đặc điểm kỹ thuật:**
- Sử dụng Google Sheets API (gspread + oauth2client) để upload trực tiếp
- Random seed cố định → dữ liệu có thể tái tạo 100%
- Thời gian chạy: ~30 giây (bao gồm upload Sheets)

#### Bước 2: Bot mô phỏng hành vi trên Moodle (`AUTO_HOC_BAI.py`)

**Input:** `moodle_config.json` (danh sách 200 SV + nhóm hành vi).

**Tại sao dùng Bot Playwright thay vì ghi trực tiếp vào MySQL?**

Đây là quyết định thiết kế quan trọng. Nhóm có thể ghi dữ liệu trực tiếp vào bảng `mdl_logstore_standard_log` bằng SQL INSERT, nhưng chọn phương pháp Bot automation vì **3 lý do**:

| Tiêu chí | Ghi SQL trực tiếp | Bot Playwright |
|----------|-------------------|----------------|
| **Tính xác thực của log** | Log thiếu nhiều trường (contextid, sessionid, origin) → dễ phát hiện là data giả | Moodle tự sinh log đầy đủ với tất cả metadata tự nhiên |
| **Tương tác giữa các bảng** | Phải INSERT vào 8+ bảng đồng thời, dễ thiếu sót FK constraints | Moodle tự cập nhật tất cả bảng liên quan (log, grades, submissions, completions) |
| **Khả năng demo** | Không thể demo cho giáo viên xem | Chạy `--demo` → giáo viên thấy trực tiếp agent tự thao tác trên browser |

Nói cách khác, Bot tạo ra **hành vi thực** trên Moodle — Moodle xử lý hành vi đó và ghi log chính xác như thể sinh viên thật đang sử dụng. Điều này đảm bảo tính nhất quán 100% giữa giao diện hiển thị và database.

**Xử lý:** Bot sử dụng framework **Playwright** để điều khiển trình duyệt Chromium, thực hiện chuỗi hành vi cho từng sinh viên:

```
Login → Dashboard → Xem khóa học → Xem video (mod_url)
→ Đọc tài liệu (mod_page) → Xem thông báo (Forum)
→ Tham gia thảo luận → Làm Quiz → Nộp Assignment → Logout
```

Mỗi hành vi được điều chỉnh theo nhóm:

| Hành vi | G1 (Chăm chỉ) | G3 (Gian lận) | G6 (Thụ động) | G7 (Bỏ cuộc) |
|---------|----------------|---------------|---------------|---------------|
| Xem video | 3–8 lượt, xem 8–20s | 0–2 lượt, xem 1–3s | 1–3 lượt | Giảm theo tuần |
| Đọc tài liệu | 2–6 lượt | 0–1 lượt | 1–3 lượt | Giảm theo tuần |
| Thảo luận | 90% tham gia | 20% | **0%** (skip) | Giảm theo tuần |
| Làm quiz/assign | 95% | 90% | 50–55% | 60%→40%→10%→5% |

**Kiến trúc module:**

```
AUTO_HOC_BAI.py          # Điều phối chính
├── bot_modules/
│   ├── bot_login.py     # Xử lý đăng nhập/đăng xuất
│   ├── bot_quiz.py      # Làm bài quiz (multichoice)
│   ├── bot_forum.py     # Thảo luận forum
│   └── bot_assign.py    # Nộp bài tập (online text)
```

**Output:** Moodle tự động ghi log vào MySQL (`mdl_logstore_standard_log`):
- 8,360 events `user_loggedin` + 8,360 `user_loggedout`
- 8,360 events `dashboard_viewed`
- 16,770 events `course_viewed`
- 3,426 events `mod_url viewed` (xem video)
- 1,246 events `mod_page viewed` (đọc tài liệu)
- 1,178 events `quiz_attempt_started` + 1,177 `quiz_attempt_submitted`
- 727 events `assign_submission_created`
- 1,190 bài forum

**Tổng: ~49,000+ log events** phân bổ thực tế theo khung giờ 7–11h, 13–17h, 18–22h.

#### Bước 3: Moodle MySQL lưu trữ

Khi Bot thao tác trên Moodle, hệ thống LMS tự động ghi dữ liệu vào các bảng MySQL:

| Bảng MySQL | Dữ liệu | Mục đích |
|---|---|---|
| `mdl_logstore_standard_log` | Tất cả events (login, view, submit...) | Log hành vi chính |
| `mdl_quiz_attempts` | Chi tiết mỗi lần làm quiz | Kết quả quiz |
| `mdl_quiz_grades` | Điểm quiz cuối cùng | Gradebook |
| `mdl_assign_submission` | Bài nộp + nội dung text | Assignment |
| `mdl_assign_grades` | Điểm assignment | Gradebook |
| `mdl_grade_grades` | Điểm tổng hợp | Gradebook chung |
| `mdl_forum_posts` | Bài viết trên forum | Thảo luận |
| `mdl_user` | firstaccess, lastaccess, lastlogin | Hồ sơ SV |

Dữ liệu trong Moodle MySQL đóng vai trò **single source of truth** — giáo viên có thể mở Moodle Admin → Reports → Logs để kiểm tra trực tiếp, và kết quả sẽ khớp với dữ liệu trong JSON/MongoDB.

#### Bước 4: Đồng bộ lên MongoDB Atlas (`sync_sheet_to_mongo.py`)

**Input:** Google Sheets (Data_EnglishIT + Data_C++).

**Xử lý:**
1. Đọc toàn bộ dữ liệu từ 2 worksheet qua Google Sheets API
2. Chuyển đổi kiểu dữ liệu (string → int/float)
3. Upsert vào MongoDB Atlas collection `students` (key: `student_id` + `course`)

**Output:** 400 documents trong MongoDB Atlas, sẵn sàng cho API Server truy vấn.

**Lý do chọn MongoDB:** Dữ liệu sinh viên có cấu trúc bán cấu trúc (semi-structured) với nhiều trường lồng nhau (52 weekly features + 12 totals). MongoDB document model phù hợp hơn relational database cho trường hợp này, đồng thời MongoDB Atlas cung cấp hosting cloud miễn phí cho đồ án.

#### Bước 5: Kiểm định chất lượng (Automated Quality Audit)

Sau mỗi lần sinh dữ liệu, nhóm chạy script kiểm định tự động quét **400 records × 13 features × 4 tuần = 20,800 data points** qua 18 ràng buộc logic. Kết quả kiểm định được trình bày chi tiết trong mục 4.1.6.

---

### 4.1.6. Kết quả kiểm định chất lượng dữ liệu

#### a) Kiểm định ràng buộc logic — 0 vi phạm

| # | Quy tắc kiểm tra | Số records kiểm tra | Số vi phạm | Kết quả |
|---|---|---|---|---|
| 1 | `login_count = 0` → tất cả tương tác = 0 | 1,600 | 0 | ✅ Đạt |
| 2 | `active_days ≤ 7` (tối đa 7 ngày/tuần) | 1,600 | 0 | ✅ Đạt |
| 3 | `active_days ≤ login_count` | 1,600 | 0 | ✅ Đạt |
| 4 | `assignment_attempt ≤ total_assignments` | 1,600 | 0 | ✅ Đạt |
| 5 | `attempt = 0` → `weekly_score = 0` và `duration = 0` | 1,600 | 0 | ✅ Đạt |
| 6 | `weekly_score ≤ 10.0` | 1,600 | 0 | ✅ Đạt |
| 7 | Không có giá trị âm (trừ `ontime_margin`) | 1,600 | 0 | ✅ Đạt |
| 8 | Tổng tuần khớp tuyệt đối với tổng kết (11 trường) | 400 | 0 | ✅ Đạt |

**Tổng: 20,800 data points × 8 ràng buộc = 0 vi phạm (0.00%)**

#### b) Phân tích tương quan (Correlation Analysis)

Để chứng minh dữ liệu mô phỏng có mối quan hệ giữa các feature tương tự dữ liệu thực, nhóm tính hệ số tương quan Pearson (r) giữa các cặp feature chính:

| Cặp feature | Hệ số r | Đánh giá | Ý nghĩa thực tế |
|---|---|---|---|
| `login_count` ↔ `session_duration` | **0.906** | Rất mạnh | Đăng nhập nhiều → thời gian học dài hơn |
| `login_count` ↔ `active_days` | **0.953** | Rất mạnh | Số lần login tỷ lệ với số ngày hoạt động |
| `assignment_attempt` ↔ `weekly_score` | **0.932** | Rất mạnh | Làm bài → có điểm |
| `active_days` ↔ `weekly_score` | **0.788** | Mạnh | Hoạt động nhiều → điểm cao |
| `login_count` ↔ `weekly_score` | **0.776** | Mạnh | Tương tác nhiều → kết quả tốt |
| `video_views` ↔ `weekly_score` | **0.637** | Trung bình–mạnh | Xem video hỗ trợ học tập |
| `document_reads` ↔ `weekly_score` | **0.575** | Trung bình | Đọc tài liệu cải thiện kết quả |

Các hệ số tương quan này phù hợp với kết quả nghiên cứu thực tế. Nghiên cứu của You (2016) [3] báo cáo r = 0.71 giữa login frequency và course achievement, trong khi tập dữ liệu của nhóm đạt r = 0.776 — nằm trong khoảng hợp lý.

#### c) Phân phối thống kê

| Feature | Min | Max | Mean | Std | Zeros (%) |
|---------|-----|-----|------|-----|-----------|
| `total_login_count` | 2 | 54 | 21.1 | 13.3 | 0% |
| `total_session_duration` | 2 | 78 | 28.7 | 20.2 | 0% |
| `total_weekly_score` | 0.0 | 9.4 | 4.1 | 3.0 | 2% |
| `total_video_views` | 0 | 31 | 8.6 | 7.2 | 4% |
| `total_document_reads` | 0 | 21 | 6.2 | 5.5 | 16% |
| `total_discussion` | 0 | 18 | 4.8 | 4.7 | 18% |
| `total_assignment_attempt` | 0 | 8 | 4.8 | 2.3 | 2% |

**Nhận xét:**
- Phân phối không đồng đều (Std/Mean lớn) — phản ánh sự đa dạng giữa 8 nhóm hành vi
- `document_reads` có 16% zeros — đúng vì nhóm G5 (24 SV) có document_reads = 0
- `discussion` có 18% zeros — đúng vì nhóm G6 (24 SV) không tham gia thảo luận
- Không có giá trị bất thường (outlier) ngoài phạm vi thiết kế

#### d) Validation nhóm hành vi — Dữ liệu phản ánh đúng kịch bản thiết kế

| Nhóm | Điểm TB | Login TB | Session TB | Doc TB | Disc TB | Dấu hiệu đặc trưng |
|------|---------|----------|------------|--------|---------|---------------------|
| **G1** | **8.2** | 46.1 | 65.1 | 15.8 | 13.8 | Tất cả chỉ số cao nhất |
| **G2** | **5.5** | 28.1 | 43.8 | 9.9 | 7.5 | Điểm khá dù login trung bình |
| **G3** | **8.1** | 19.1 | **9.8** ⚡ | 1.9 | 1.9 | Điểm cao + session cực ngắn |
| **G4** | **0.7** | **6.2** | 10.0 | 3.0 | 1.6 | Login + điểm đều rất thấp |
| **G5** | **1.0** | 13.1 | 20.0 | **0.0** ⚡ | 3.6 | Document reads = 0 tuyệt đối |
| **G6** | **2.3** | 18.2 | 26.8 | 8.2 | **0.0** ⚡ | Discussion = 0 tuyệt đối |
| **G7** | **1.2** | **4.6** | 6.2 | 1.1 | 1.2 | Mọi chỉ số đều rất thấp (bỏ cuộc) |
| **G8** | **5.3** | 27.5 | 39.3 | 7.8 | 6.5 | Tương tự G2 nhưng tuần 3 sụt giảm |

*(⚡ = đặc trưng nổi bật, phản ánh đúng kịch bản thiết kế)*

**Phân tích đặc trưng nổi bật:**

- **G3 (Gian lận):** Điểm TB = 8.1 (gần bằng G1 = 8.2) nhưng session_duration chỉ 9.8 phút (G1 = 65.1 phút) → tín hiệu anomaly rõ ràng cho ML
- **G5 vs G6:** Cùng mức điểm yếu nhưng khác biệt ở document_reads (G5 = 0.0) và discussion (G6 = 0.0) → ML có thể phân biệt được hai nhóm
- **G7 vs G8:** Cùng sụt tuần 3 nhưng G8 hồi phục tuần 4 (V-shape), G7 tiếp tục giảm → EWS cần phân biệt "bỏ cuộc" với "gián đoạn tạm thời"

**Validation theo tuần — So sánh G7 (Bỏ cuộc) vs G8 (Gián đoạn):**

| Tuần | G7 Login TB | G7 Score TB | G7 Session TB | G8 Login TB | G8 Score TB | G8 Session TB |
|------|-------------|-------------|---------------|-------------|-------------|---------------|
| W1 | 2.4 | 2.1 | 12.5 | 8.2 | 7.1 | 52.3 |
| W2 | 1.5 | 1.0 | 6.8 | 7.8 | 6.5 | 48.7 |
| W3 | **0.3** | **0.1** | **1.2** | **1.4** | **0.8** | **7.8** |
| W4 | **0.2** | **0.0** | **0.5** | 7.1 | 6.2 | **45.1** |
| Xu hướng | ↘ Giảm liên tục | ↘ Giảm liên tục | ↘ Giảm liên tục | V-shape ✅ | V-shape ✅ | V-shape ✅ |

**Kết luận validation G7/G8:**
- G7 suy giảm liên tục 4 tuần liền (decay pattern: 100%→60%→15%→5%) → đúng mẫu "Disengaging" của Kizilcec (2013)
- G8 sụt mạnh tuần 3 rồi phục hồi gần mức ban đầu ở tuần 4 (V-shape) → đúng kịch bản "gián đoạn do ngoại cảnh"
- Hai nhóm này tạo challenge quan trọng cho mô hình ML: phải phân biệt được "bỏ hẳn" vs "nghỉ tạm" chỉ dựa trên dữ liệu 4 tuần

#### e) Tổng kết chất lượng dữ liệu

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| Ràng buộc logic (8 quy tắc) | 0/20,800 vi phạm | ✅ Đạt hoàn toàn |
| Tương quan features | r = 0.58–0.95 | ✅ Phù hợp nghiên cứu thực tế |
| Phân biệt 8 nhóm hành vi | Mỗi nhóm có ≥1 đặc trưng nổi bật | ✅ Rõ ràng |
| Nhất quán weekly ↔ totals | 0/400 mismatch | ✅ Chính xác tuyệt đối |
| Moodle log ↔ JSON data | 9 loại event, ~49,000 entries | ✅ Đồng bộ |

Kết quả kiểm định cho thấy tập dữ liệu mô phỏng đáp ứng đầy đủ các yêu cầu về chất lượng để phục vụ mục đích proof-of-concept của hệ thống EWS Pro. Dữ liệu có tương quan hợp lý giữa các features, tuân thủ nghiêm ngặt các ràng buộc logic, và phản ánh chính xác 8 kịch bản hành vi được thiết kế dựa trên cơ sở khoa học.

---

### 4.1.7. Hạn chế của dữ liệu mô phỏng và lộ trình chuyển đổi sang Production

#### a) Hạn chế được thừa nhận

Nhóm nhận thức rõ rằng dữ liệu mô phỏng, dù được thiết kế cẩn thận dựa trên cơ sở khoa học, vẫn tồn tại **3 hạn chế chính** so với dữ liệu thực:

**Hạn chế 1: Độ chính xác của mô hình ML có thể bị phóng đại (Inflated Accuracy).**

Vì 8 nhóm hành vi được thiết kế với boundary rõ ràng (ví dụ: G3 có session cực ngắn, G5 có document_reads = 0 tuyệt đối), mô hình ML có thể đạt accuracy rất cao (>95%) trên tập dữ liệu này. Trong thực tế, ranh giới giữa các nhóm hành vi mờ hơn — một sinh viên có thể vừa trì hoãn vừa gian lận, hoặc chuyển đổi nhóm giữa các tuần. Do đó, accuracy trên data thật có thể thấp hơn đáng kể.

**Biện pháp khắc phục:** Trong báo cáo kết quả ML, nhóm luôn ghi rõ: *"Kết quả đạt được trên tập dữ liệu mô phỏng, cần retrain và đánh giá lại trên dữ liệu thực."*

**Hạn chế 2: Thiếu nhiễu thực tế (Missing Real-world Noise).**

Dữ liệu thực có nhiều loại nhiễu mà dữ liệu mô phỏng không mô phỏng được:
- Sinh viên login rồi để tab mở cả ngày → session_duration rất lớn nhưng không thực sự học
- Trùng tài khoản (một SV đăng nhập cho bạn)
- Sự kiện bất thường (server down, maintenance window → mất log)
- Hành vi thay đổi theo mùa (giữa kỳ vs cuối kỳ)

**Biện pháp khắc phục:** Module ETL (`etl_moodle_warehouse.py`) trong hệ thống đã tích hợp bước lọc nhiễu cơ bản — ví dụ: session timeout sau 30 phút không có activity, loại bỏ log từ admin accounts.

**Hạn chế 3: Quy mô nhỏ (200 SV) so với thực tế.**

Một trường đại học có thể có 5,000–20,000 sinh viên. Quy mô 200 SV đủ để chứng minh concept nhưng chưa kiểm chứng được khả năng mở rộng (scalability) của pipeline.

**Biện pháp khắc phục:** Kiến trúc hệ thống (MongoDB Atlas + Flask API) được thiết kế stateless và horizontal-scalable, có thể xử lý hàng chục nghìn records mà không cần thay đổi code.

#### b) Lộ trình chuyển đổi sang triển khai thực tế (Production Roadmap)

Khi triển khai tại trường học thực tế, hệ thống EWS Pro chuyển đổi qua **4 bước**:

```
┌─────────────────────────────────────────────────────────┐
│                  MÔI TRƯỜNG HIỆN TẠI                     │
│  Bot → Moodle → Google Sheets → MongoDB → Dashboard     │
└───────────────────────┬─────────────────────────────────┘
                        │ Chuyển đổi
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  MÔI TRƯỜNG PRODUCTION                   │
│  Moodle MySQL ──ETL──→ MongoDB → API → Dashboard/Plugin  │
│                  (Cron Job mỗi đêm)                      │
└─────────────────────────────────────────────────────────┘
```

| Bước | Hành động | Chi tiết |
|------|-----------|----------|
| **1** | Thay đổi nguồn dữ liệu | Kết nối `etl_moodle_warehouse.py` trực tiếp vào MySQL của Moodle trường. Truy vấn SQL vào `mdl_logstore_standard_log`, `mdl_grade_grades`, `mdl_assign_submission` để rút trích 13 features thay vì đọc từ JSON |
| **2** | Retrain mô hình ML | Huấn luyện lại Random Forest/Gradient Boosting trên dữ liệu thực (ít nhất 1 học kỳ). Đánh giá lại accuracy, precision, recall trên tập test thực |
| **3** | Lên lịch tự động (Cron Job) | Cấu hình Cron Job chạy ETL pipeline mỗi đêm (`0 1 * * *`), đảm bảo dữ liệu Dashboard luôn cập nhật |
| **4** | Tích hợp vào Moodle (Plugin) | Đóng gói Dashboard thành Moodle Block Plugin (PHP/JS), giáo viên xem trực tiếp trên giao diện Moodle |

**Các file cần loại bỏ khi lên Production:**

| File | Lý do |
|------|-------|
| `AUTO_HOC_BAI.py` | Bot mô phỏng — không cần khi có data thật |
| `bot_modules/` | Các module của Bot |
| `data_pipeline.py` | Script sinh data mô phỏng |
| `moodle_config.json` | Cấu hình Bot |

**Các file giữ lại và điều chỉnh:**

| File | Vai trò Production |
|------|-------------------|
| `api_server.py` | Backend API — giữ nguyên |
| `etl_moodle_warehouse.py` | ETL pipeline — sửa connection string |
| `sync_sheet_to_mongo.py` | Đồng bộ — thay bằng ETL trực tiếp |
| `dashboard.html` | Frontend — giữ nguyên hoặc chuyển thành Plugin |

> **Kết luận:** Dữ liệu mô phỏng đóng vai trò **scaffolding** (giàn giáo) cho quá trình phát triển hệ thống. Khi hệ thống đã ổn định và được kiểm chứng trên dữ liệu mô phỏng, việc chuyển sang dữ liệu thực chỉ cần thay đổi ở tầng ETL (data source) mà không ảnh hưởng đến kiến trúc tổng thể — chứng tỏ tính module hóa và khả năng mở rộng của thiết kế hệ thống.

*(Hết Chương 4.1 — Xây dựng tập dữ liệu mô phỏng)*

---

## TÀI LIỆU THAM KHẢO (cho chương này)

[1] Jordon, J., Szpruch, L., Houssiau, F., Sheridan-Sheridan, M., & de Montjoye, Y.-A. (2022). "Synthetic Data – What, Why and How?" *arXiv preprint*, arXiv:2205.03257.

[2] Kizilcec, R. F., Piech, C., & Schneider, E. (2013). "Deconstructing Disengagement: Analyzing Learner Subpopulations in Massive Open Online Courses." *Proceedings of the Third International Conference on Learning Analytics and Knowledge (LAK '13)*, ACM, pp. 170–179. DOI: 10.1145/2460296.2460330.

[3] You, J. W. (2016). "Identifying Significant Indicators Using LMS Data to Predict Course Achievement in Online Learning." *The Internet and Higher Education*, Vol. 29, pp. 23–30. DOI: 10.1016/j.iheduc.2015.11.003.

[4] Romero, C., López, M.-I., Luna, J.-M., & Ventura, S. (2013). "Predicting Students' Final Performance from Participation in On-line Discussion Forums." *Computers & Education*, Vol. 68, pp. 458–472. DOI: 10.1016/j.compedu.2013.06.009.

[5] Baker, R. S., Corbett, A. T., Koedinger, K. R., & Wagner, A. Z. (2004). "Off-Task Behavior in the Cognitive Tutor Classroom: When Students 'Game the System'." *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems*, ACM, pp. 383–390. DOI: 10.1145/985692.985741.

[6] Fernández, A., García, S., Galar, M., Prati, R. C., Krawczyk, B., & Herrera, F. (2018). *Learning from Imbalanced Data Sets*. Springer. DOI: 10.1007/978-3-319-98074-4.
