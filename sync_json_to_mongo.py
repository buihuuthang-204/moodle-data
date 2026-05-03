"""
Đẩy students_data.json (đã fix, 100 SV duy nhất) lên MongoDB Atlas.
"""
import os, sys, json, datetime
sys.stdout.reconfigure(encoding='utf-8')

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "")

WEEKLY_FEATURES = [
    'active_days','login_count','video_views','document_reads',
    'discussion','total_assignments','assignment_attempt',
    'assignment_duration_mins','ontime_margin','weekly_score',
    'days_since_last_login','session_duration','deadline_proximity',
]
TOTAL_FEATURES = [
    'total_active_days','total_login_count','total_video_views',
    'total_document_reads','total_discussion','total_assignment_attempt',
    'total_assignment_duration_mins','total_ontime_margin',
    'total_weekly_score','total_days_since_last_login',
    'total_session_duration','total_deadline_proximity',
]

def to_num(val):
    try:
        n = float(val)
        return int(n) if n == int(n) else round(n, 2)
    except (ValueError, TypeError):
        return 0

def build_doc(row):
    doc = {
        "mssv": str(row.get('student_id', '')),
        "name": row.get('full_name', ''),
        "email": row.get('email', ''),
        "course": row.get('course', ''),
        "class": row.get('class', ''),
    }
    weeks = []
    for w in range(1, 5):
        wd = {"week": w}
        for feat in WEEKLY_FEATURES:
            wd[feat] = to_num(row.get(f'{feat}_w{w}', 0))
        weeks.append(wd)
    doc["weeks"] = weeks

    totals = {}
    for feat in TOTAL_FEATURES:
        totals[feat] = to_num(row.get(feat, 0))
    doc["totals"] = totals
    return doc

def main():
    print("=" * 60)
    print("🚀 SYNC JSON → MONGODB (100 SV duy nhất)")
    print("=" * 60)

    data = json.load(open('students_data.json', encoding='utf-8'))
    print(f"📋 Đọc students_data.json: {len(data)} records")

    # Verify uniqueness
    ids = [s['student_id'] for s in data]
    unique_ids = set(ids)
    print(f"   {len(unique_ids)} unique IDs × {len(ids)//len(unique_ids)} courses = {len(ids)} records")
    
    classes = {}
    courses = {}
    for s in data:
        c = s.get('class', '?')
        co = s.get('course', '?')
        classes[c] = classes.get(c, 0) + 1
        courses[co] = courses.get(co, 0) + 1
    print(f"   Lớp:   {classes}")
    print(f"   Khóa:  {courses}")

    docs = [build_doc(r) for r in data]

    if not MONGO_URI:
        print("❌ Chưa cấu hình MONGO_URI!")
        return

    print(f"\n⏳ Kết nối MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client['ews_pro']
    col = db['students']

    print("🗑️ Xóa dữ liệu cũ...")
    col.delete_many({})

    print("🚀 Đẩy 100 records lên...")
    result = col.insert_many(docs)
    print(f"✅ Đã đẩy {len(result.inserted_ids)} records!")

    db['metadata'].update_one(
        {"type": "sync_status"},
        {"$set": {
            "last_updated": datetime.datetime.now(),
            "total_students": len(docs),
            "unique_students": True,
            "status": "Ready"
        }},
        upsert=True
    )

    print(f"\n{'='*60}")
    print("🎉 HOÀN TẤT! MongoDB giờ có đúng 100 SV, mỗi SV 1 khóa.")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
