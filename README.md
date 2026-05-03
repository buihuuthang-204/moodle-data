# 🎓 EWS Pro — Hệ thống Phát hiện Sinh viên có Nguy cơ Bỏ học

> **Đề tài Tốt nghiệp:** Xây dựng hệ thống cảnh báo sớm (Early Warning System) phát hiện sinh viên có nguy cơ bỏ học dựa trên phân tích hành vi học tập trên LMS Moodle, kết hợp Machine Learning và Trí tuệ nhân tạo Gemini AI.

## 📋 Tổng quan

| Thành phần | Công nghệ |
|---|---|
| **Dữ liệu** | 200 SV × 60+ features × 4 tuần × 2 khóa học |
| **ML Pipeline** | K-Means, DBSCAN, Agglomerative, Random Forest, Gradient Boosting |
| **Backend** | Python Flask + MongoDB Atlas |
| **AI** | Google Gemini API (tự soạn Email/SMS cảnh báo) |
| **Frontend** | HTML/CSS/JS Dashboard (Chart.js) |
| **Bot** | Playwright (giả lập hành vi SV trên Moodle) |

## 🏗️ Kiến trúc hệ thống

```
[Moodle LMS] → [AUTO_HOC_BAI.py] → [Google Sheets]
                                         ↓
                               [sync_sheet_to_mongo.py]
                                         ↓
                                   [MongoDB Atlas]
                                         ↓
[Google Sheets] → [Train_Model_Colab.py] → [student_risk_model.pkl]
                                                    ↓
                                            [api_server.py] ← Gemini AI
                                                    ↓
                                            [dashboard.html]
```

## 🚀 Hướng dẫn Cài đặt

### 1. Cài đặt thư viện
```bash
pip install -r requirements.txt
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
| 1 | `python AUTO_HOC_BAI.py` | *(Tùy chọn)* Giả lập SV học trên Moodle |
| 2 | `python sync_sheet_to_mongo.py` | Đồng bộ dữ liệu Google Sheets → MongoDB |
| 3 | `python Train_Model_Colab.py` | Huấn luyện 5 thuật toán ML, xuất model `.pkl` |
| 4 | `python api_server.py` | Khởi chạy API Server tại `http://localhost:5000` |
| 5 | Mở `dashboard.html` | Xem giao diện Dashboard trên trình duyệt |

## 📁 Cấu trúc thư mục

```
auto/
├── api_server.py              # Flask API Server (Backend chính)
├── AUTO_HOC_BAI.py            # Bot giả lập hành vi SV trên Moodle
├── Train_Model_Colab.py       # Pipeline huấn luyện ML (5 thuật toán)
├── sync_sheet_to_mongo.py     # ETL: Google Sheets → MongoDB Atlas
├── generate_dashboard_data.py # Tạo JSON offline (fallback)
├── etl_moodle_warehouse.py    # ETL: Moodle MySQL → SQLite Warehouse
├── dashboard.html             # Giao diện Web Dashboard
├── requirements.txt           # Danh sách thư viện Python
├── credentials.json           # (Không đẩy lên Git) Google Service Account Key
├── .env                       # (Không đẩy lên Git) Biến môi trường bí mật
└── student_risk_model.pkl     # (Tự sinh) Model ML đã train
```

## 🔬 Phương pháp ML

### Unsupervised Learning
- **K-Means** (tìm K tối ưu bằng Silhouette Score)
- **DBSCAN** (eps tự động từ K-NN Distance)
- **Agglomerative Clustering**

### Supervised Learning
- **Random Forest** (200 trees, max_depth=10)
- **Gradient Boosting** (200 estimators, lr=0.1)

> ⚠️ **Chống Data Leakage:** Các cột `weekly_score` được loại bỏ khỏi tập features supervised vì nhãn Risk được tạo từ chính `total_weekly_score`.

## 👨‍💻 Tác giả

Đồ án tốt nghiệp — Đại học

---

## 🏭 Hướng dẫn Triển khai Thực tế (Production Deployment)

*Phần này hướng dẫn cách chuyển đổi từ môi trường Data Mô phỏng (Synthetic) sang chạy thực tế trên Moodle của Trường học.*

### Bước 1: Thay đổi Nguồn Dữ liệu (Data Source)
Khi chạy thực tế, không dùng Bot (`AUTO_HOC_BAI.py`) để giả lập nữa. Bạn cần kết nối thẳng vào Database thực của Moodle.
1. Mở file `api_server.py`.
2. Sửa chuỗi kết nối Database để trỏ vào MySQL/PostgreSQL của Moodle trường:
   ```python
   # Ví dụ:
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://db_user:db_pass@IP_MOODLE/moodle_db'
   ```

### Bước 2: Thay đổi Pipeline Trích xuất (ETL)
Thay vì đọc file `students_data.json` giả lập, bạn sẽ dùng các câu lệnh SQL để rút trích Log thực tế:
1. Mở file `data_pipeline.py` (hoặc `etl_moodle_warehouse.py`).
2. Viết câu SQL Query vào các bảng sau của Moodle:
   - **Đăng nhập & Tương tác:** `mdl_logstore_standard_log` (Đếm số lần view trang, xem video).
   - **Điểm số:** `mdl_grade_grades` và `mdl_quiz_grades`.
   - **Bài tập:** `mdl_assign_submission`.

### Bước 3: Lên lịch Tự động hóa (Cron Job)
Không chạy lệnh bằng tay. Hãy cấu hình một Cron Job trên máy chủ Linux để chạy Pipeline mỗi đêm:
```bash
# Mở crontab
crontab -e

# Thêm dòng sau để tự động lấy data Moodle và đồng bộ vào MongoDB lúc 01:00 sáng mỗi ngày:
0 1 * * * /usr/bin/python3 /path/to/sync_sheet_to_mongo.py
```

### Bước 4: Tích hợp Frontend (LMS Plugin)
Thay vì dùng Dashboard rời (`dashboard.html`), code Frontend này có thể được đóng gói thành một **Moodle Block Plugin (PHP/JS)**. 
Giáo viên chỉ cần cài Plugin này vào Moodle, Block sẽ gọi API (`http://your_api_server/api/get_students`) và hiển thị trực tiếp đồ thị cảnh báo trên màn hình Moodle của giáo viên.

### 🗑️ Các file cần xóa khi lên Production:
Khi đã gắn Moodle thật, toàn bộ bộ công cụ Sinh data mô phỏng sẽ bị loại bỏ:
- Xóa `AUTO_HOC_BAI.py`.
- Xóa toàn bộ thư mục `bot_modules/`.
- Xóa `moodle_config.json`.
