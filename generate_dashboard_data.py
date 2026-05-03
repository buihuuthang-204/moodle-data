"""
Tạo students_data.json từ 2 Sheets (Data_EnglishIT + Data_C++).
Dùng làm fallback khi không kết nối được MongoDB.
"""
import sys, json

sys.stdout.reconfigure(encoding='utf-8')

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1zZ8QxLurma5j_J9YUTSm6vL5JFHujWFmScYZ44RizEs/edit'
JSON_KEY = 'credentials.json'

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(SHEET_URL)

students = []

for sheet_name in ['Data_EnglishIT', 'Data_C++']:
    ws = spreadsheet.worksheet(sheet_name)
    rows = ws.get_all_records()
    print(f"Sheet '{sheet_name}': {len(rows)} rows")

    for row in rows:
        s = {
            "mssv": str(row.get('student_id', '')),
            "name": row.get('full_name', ''),
            "course": row.get('course', ''),
            "class": row.get('class', ''),
            "score": round(float(row.get('total_weekly_score', 0)), 1),
            "login": int(float(row.get('total_login_count', 0))),
            "video": int(float(row.get('total_video_views', 0))),
            "doc": int(float(row.get('total_document_reads', 0))),
            "disc": int(float(row.get('total_discussion', 0))),
            "session": round(float(row.get('total_session_duration', 0)), 1),
            "duration": round(float(row.get('total_assignment_duration_mins', 0)), 1),
            "w": [
                round(float(row.get('weekly_score_w1', 0)), 1),
                round(float(row.get('weekly_score_w2', 0)), 1),
                round(float(row.get('weekly_score_w3', 0)), 1),
                round(float(row.get('weekly_score_w4', 0)), 1),
            ],
            "total_assignments": [
                int(float(row.get('total_assignments_w1', 0))),
                int(float(row.get('total_assignments_w2', 0))),
                int(float(row.get('total_assignments_w3', 0))),
                int(float(row.get('total_assignments_w4', 0))),
            ],
            "assignment_attempt": [
                int(float(row.get('assignment_attempt_w1', 0))),
                int(float(row.get('assignment_attempt_w2', 0))),
                int(float(row.get('assignment_attempt_w3', 0))),
                int(float(row.get('assignment_attempt_w4', 0))),
            ],
        }
        students.append(s)

with open('students_data.json', 'w', encoding='utf-8') as f:
    json.dump(students, f, ensure_ascii=False, indent=2)

# Stats
courses = {}
classes = {}
for s in students:
    courses[s['course']] = courses.get(s['course'], 0) + 1
    classes[s['class']] = classes.get(s['class'], 0) + 1

print(f"\nGenerated students_data.json with {len(students)} records")
for c, cnt in courses.items():
    print(f"  📚 {c}: {cnt} SV")
for c, cnt in sorted(classes.items()):
    print(f"  🏫 {c}: {cnt} SV")
