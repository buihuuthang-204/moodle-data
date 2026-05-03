# 🎓 EWS Pro — Hệ thống Cảnh báo Sớm Sinh viên có Nguy cơ Bỏ học

> **Đề tài Tốt nghiệp:** Xây dựng hệ thống cảnh báo sớm (Early Warning System) phát hiện sinh viên có nguy cơ bỏ học dựa trên phân tích hành vi học tập trên LMS Moodle, kết hợp Machine Learning và Trí tuệ nhân tạo Gemini AI.

## 📋 Tổng quan

| Thành phần | Công nghệ |
|---|---|
| **Dữ liệu** | 200 SV × 13 features × 4 tuần × 2 khóa học (8 nhóm hành vi G1–G8) |
| **Backend** | Python Flask + MongoDB Atlas |
| **AI** | Google Gemini API (tự soạn Email/SMS cảnh báo) |
| **Bot** | Playwright (mô phỏng hành vi SV trên Moodle) |
| **Data Sync** | Google Sheets API + MongoDB Atlas |

## 🏗️ Kiến trúc hệ thống

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  data_pipeline.py │───>│  AUTO_HOC_BAI.py  │───>│  Moodle MySQL     │
│  Sinh kịch bản    │    │  Bot Playwright   │    │  Log + Grades     │
│  → JSON + Sheets  │    │  → Hành vi SV     │    │  → 49,000+ events │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
┌──────────────────┐    ┌──────────────────┐             │
│  api_server.py    │    │ sync_*_to_mongo  │             │
│  Flask API        │<───│  Sheets/JSON →   │<────────────┘
│  ← Gemini AI      │    │  MongoDB Atlas   │
└──────────────────┘    └──────────────────┘
```

## 🚀 Hướng dẫn Cài đặt

### 1. Cài đặt thư viện
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Cấu hình biến môi trường
Tạo file `.env` trong thư mục gốc:
```env
MONGO_URI=mongodb+srv://...
GEMINI_API_KEY=AIza...
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 3. Đặt file `credentials.json`
Tải Service Account Key từ Google Cloud Console, đặt vào thư mục gốc để kết nối Google Sheets.

## 📦 Thứ tự chạy

| Bước | Lệnh | Mô tả |
|------|-------|-------|
| 1 | `python data_pipeline.py` | Sinh dữ liệu mô phỏng → JSON + Google Sheets |
| 2 | `python AUTO_HOC_BAI.py` | Bot mô phỏng hành vi SV trên Moodle |
| 3 | `python sync_sheet_to_mongo.py` | Đồng bộ Google Sheets → MongoDB Atlas |
| 4 | `python api_server.py` | Khởi chạy API Server tại `http://localhost:5000` |

> 💡 **Demo mode:** `python AUTO_HOC_BAI.py --demo` — mở trình duyệt hiển thị để giáo viên quan sát Bot thao tác.

## 📁 Cấu trúc thư mục

```
auto/
├── api_server.py              # Flask API Server (Backend chính)
├── AUTO_HOC_BAI.py            # Bot mô phỏng hành vi SV trên Moodle
├── data_pipeline.py           # Pipeline sinh dữ liệu mô phỏng (200 SV × 8 nhóm)
├── sync_sheet_to_mongo.py     # ETL: Google Sheets → MongoDB Atlas
├── sync_json_to_mongo.py      # ETL: JSON file → MongoDB Atlas
├── etl_moodle_warehouse.py    # ETL: Moodle MySQL → SQLite Warehouse (Production)
├── students_data.json         # Dữ liệu 400 records (200 SV × 2 khóa)
├── moodle_config.json         # Cấu hình nhóm hành vi cho Bot
├── requirements.txt           # Danh sách thư viện Python
├── bot_modules/               # Modules Bot Playwright
│   ├── bot_login.py           #   Xử lý đăng nhập/đăng xuất
│   ├── bot_quiz.py            #   Làm bài quiz
│   ├── bot_forum.py           #   Thảo luận forum
│   └── bot_assign.py          #   Nộp bài tập
├── tests/                     # Unit tests
│   └── test_ews.py            #   Test cases
├── .github/workflows/         # CI/CD
│   └── ci.yml                 #   GitHub Actions workflow
├── credentials.json           # (Không đẩy lên Git) Google Service Account
├── .env                       # (Không đẩy lên Git) Biến môi trường bí mật
└── .gitignore                 # Danh sách file không track
```

## 🔬 Dữ liệu & Phương pháp

### 8 Nhóm hành vi sinh viên (G1–G8)

| Nhóm | Tên | Cơ sở khoa học | Đặc trưng |
|------|-----|----------------|-----------|
| G1 | Chăm chỉ toàn diện | Kizilcec (2013) — Completing | Login cao, điểm cao |
| G2 | Trì hoãn tích cực | You (2016) — Active Procrastination | Nộp sát deadline, điểm khá |
| G3 | Gian lận | Baker (2004) — Gaming the System | Điểm cao, session ngắn |
| G4 | Yếu — ít đăng nhập | Kizilcec (2013) — Sampling | Login 0–3 |
| G5 | Yếu — không đọc TL | Kizilcec (2013) — Auditing | document_reads = 0 |
| G6 | Thụ động — không thảo luận | Romero (2013) — Passive Lurkers | discussion = 0 |
| G7 | Bỏ cuộc giữa chừng | Kizilcec (2013) — Disengaging | Giảm dần theo tuần |
| G8 | Gián đoạn do ngoại cảnh | Quan sát thực tế | V-shape tuần 3 |

### 13 Features hành vi (mỗi tuần)
`login_count`, `active_days`, `session_duration`, `video_views`, `document_reads`, `discussion`, `total_assignments`, `assignment_attempt`, `assignment_duration_mins`, `weekly_score`, `ontime_margin`, `days_since_last_login`, `deadline_proximity`

## 👨‍💻 Tác giả

Đồ án tốt nghiệp — Đại học

---

## 🏭 Hướng dẫn Triển khai Thực tế (Production)

*Chuyển đổi từ Data Mô phỏng sang chạy thực tế trên Moodle của trường.*

### Bước 1: Thay đổi Nguồn Dữ liệu
Kết nối `etl_moodle_warehouse.py` trực tiếp vào MySQL của Moodle:
```python
# Truy vấn SQL vào các bảng Moodle:
# - mdl_logstore_standard_log (login, view, submit events)
# - mdl_grade_grades (điểm quiz + assign)
# - mdl_assign_submission (bài nộp)
```

### Bước 2: Lên lịch Tự động (Cron Job)
```bash
# Tự động ETL mỗi đêm lúc 01:00
0 1 * * * /usr/bin/python3 /path/to/etl_moodle_warehouse.py
```

### Bước 3: Tích hợp Frontend
Phát triển giao diện Dashboard riêng hoặc đóng gói thành **Moodle Block Plugin** (PHP/JS) để giáo viên xem trực tiếp trên Moodle.

### 🗑️ Các file loại bỏ khi lên Production
- `AUTO_HOC_BAI.py`, `bot_modules/` — Bot mô phỏng
- `data_pipeline.py` — Script sinh data
- `moodle_config.json` — Cấu hình Bot
