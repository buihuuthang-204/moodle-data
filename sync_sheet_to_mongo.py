import os
import sys
import json
import datetime

sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

import gspread  # type: ignore
from oauth2client.service_account import ServiceAccountCredentials  # type: ignore
from pymongo import MongoClient  # type: ignore
from dotenv import load_dotenv  # type: ignore

# 1. Load cấu hình
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "")

# 2. Cấu hình Google Sheets
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1zZ8QxLurma5j_J9YUTSm6vL5JFHujWFmScYZ44RizEs/edit'
JSON_KEY = 'credentials.json'

# Tên 2 sheet riêng biệt (mỗi môn 1 sheet)
SHEET_ENGLISH = 'Data_EnglishIT'
SHEET_CPP     = 'Data_C++'

# Các features theo tuần (tên gốc từ Sheet, bỏ hậu tố _w1/_w2/...)
WEEKLY_FEATURES = [
    'active_days',
    'login_count',
    'video_views',
    'document_reads',
    'discussion',
    'total_assignments',
    'assignment_attempt',
    'assignment_duration_mins',
    'ontime_margin',
    'weekly_score',
    'days_since_last_login',
    'session_duration',
    'deadline_proximity',
]

# Các features tổng hợp (total_)
TOTAL_FEATURES = [
    'total_active_days',
    'total_login_count',
    'total_video_views',
    'total_document_reads',
    'total_discussion',
    'total_assignment_attempt',
    'total_assignment_duration_mins',
    'total_ontime_margin',
    'total_weekly_score',
    'total_days_since_last_login',
    'total_session_duration',
    'total_deadline_proximity',
]

NUM_WEEKS = 4


def get_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY, scope)
    return gspread.authorize(creds)


def get_data_from_sheets():
    """Đọc dữ liệu từ cả 2 sheet (English IT + C++)."""
    print("⏳ Đang kết nối Google Sheets...")
    client = get_sheet_client()
    spreadsheet = client.open_by_url(SHEET_URL)

    all_rows = []
    for sheet_name in [SHEET_ENGLISH, SHEET_CPP]:
        ws = spreadsheet.worksheet(sheet_name)
        rows = ws.get_all_records()
        print(f"   ✅ Sheet '{sheet_name}': {len(rows)} sinh viên")
        all_rows.extend(rows)

    print(f"✅ Tổng: {len(all_rows)} records từ 2 sheets!")
    return all_rows


def to_num(val):
    """Chuyển giá trị về số, trả về 0 nếu lỗi"""
    try:
        n = float(val)
        return int(n) if n == int(n) else round(n, 2)  # type: ignore
    except (ValueError, TypeError):
        return 0


def build_student_doc(row):
    """Chuyển 1 dòng Sheet thành 1 document MongoDB (mỗi dòng = 1 SV + 1 khóa)."""
    # Header mới: student_id, full_name, email, course, class
    mssv = str(row.get('student_id', ''))

    doc = {
        "mssv": mssv,
        "name": row.get('full_name', ''),
        "email": row.get('email', ''),
        "course": row.get('course', ''),
        "class": row.get('class', ''),
    }

    # === Weekly Data — Nested Array ===
    weeks = []
    for w in range(1, NUM_WEEKS + 1):
        week_data = {"week": w}
        for feat in WEEKLY_FEATURES:
            col_name = f"{feat}_w{w}"
            week_data[feat] = to_num(row.get(col_name, 0))
        weeks.append(week_data)
    doc["weeks"] = weeks

    # === Tổng hợp (total) ===
    totals = {}
    for feat in TOTAL_FEATURES:
        totals[feat] = to_num(row.get(feat, 0))
    doc["totals"] = totals

    return doc


def sync_data_to_mongodb_array():
    print(f"\n{'='*60}")
    print("🚀 ETL PIPELINE: GOOGLE SHEETS → MONGODB (Nested Array)")
    print(f"{'='*60}")

    # 1. Tải data từ cả 2 Sheet
    raw_data = get_data_from_sheets()

    # 2. Chuyển đổi sang format Nested Array
    print("⏳ Đang chuyển đổi sang cấu trúc Nested Array...")
    data_to_upload = []
    for row in raw_data:
        try:
            doc = build_student_doc(row)
            data_to_upload.append(doc)
        except Exception as e:
            print(f"⚠️ Lỗi SV {row.get('student_id', '?')}: {e}")

    total_records = len(data_to_upload)
    print(f"✅ Đã chuyển đổi {total_records} records!")

    # 3. Hiển thị mẫu
    if data_to_upload:
        sample = data_to_upload[0]
        print(f"\n📋 Mẫu dữ liệu — {sample['mssv']} ({sample['name']}):")
        print(f"   course: {sample['course']}")
        print(f"   class:  {sample['class']}")
        print(f"   weeks:  {len(sample['weeks'])} tuần")
        for w in sample['weeks']:  # type: ignore
            print(f"      Tuần {w['week']}: login={w['login_count']}, score={w['weekly_score']}, "
                  f"total_tasks={w['total_assignments']}, attempt={w['assignment_attempt']}")
        print(f"   totals: score={sample['totals']['total_weekly_score']}, "
              f"login={sample['totals']['total_login_count']}")

    # 4. Đẩy lên MongoDB
    if not MONGO_URI:
        print("\n❌ Chưa cấu hình MONGO_URI trong .env!")
        print("💡 Tạm lưu ra students_data.json...")
        with open('students_data.json', 'w', encoding='utf-8') as f:
            json.dump(data_to_upload, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu {total_records} SV vào students_data.json!")
        return

    try:
        print("\n⏳ Đang kết nối MongoDB Atlas...")
        client = MongoClient(MONGO_URI)
        db = client['ews_pro']
        collection = db['students']
        meta_col = db['metadata']

        print("🗑️ Đang làm sạch dữ liệu cũ...")
        collection.delete_many({})

        print("🚀 Đang đẩy dữ liệu cấu trúc Array lên Cloud...")
        result = collection.insert_many(data_to_upload)
        print(f"✅ Đã đẩy thành công {len(result.inserted_ids)} records.")

        # 5. Cập nhật Metadata
        meta_col.update_one(
            {"type": "sync_status"},
            {"$set": {
                "last_updated": datetime.datetime.now(),
                "week_processed": NUM_WEEKS,
                "total_students": total_records,
                "data_format": "Nested Array",
                "status": "Ready"
            }},
            upsert=True
        )

        print("\n" + "=" * 30)
        print("✨ HOÀN TẤT ĐỒNG BỘ DẠNG MẢNG ✨")
        print("=" * 30)

    except Exception as e:
        print(f"❌ Lỗi xảy ra: {e}")


# Chạy hàm
sync_data_to_mongodb_array()
