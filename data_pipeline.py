"""
=== DATA PIPELINE: Student Behavioral Data ===
ETL pipeline — xử lý và đồng bộ data lên Google Sheets + JSON.

Cấu trúc:
  200 SV (122000000-199), cả 200 đều học CẢ 2 khóa:
    - 22CT111: SV 000-049 (50 SV)
    - 22CT112: SV 050-099 (50 SV)
    - 22CT113: SV 100-149 (50 SV)
    - 22CT114: SV 150-199 (50 SV)
  
  8 nhóm hành vi (chia đều ~25 SV/nhóm, trộn trong mỗi lớp):
    G1: Chăm chỉ toàn diện
    G2: Trì hoãn nhưng khá
    G3: Gian lận (điểm cao, session ngắn)
    G4: Yếu - ít đăng nhập
    G5: Yếu - không đọc tài liệu
    G6: Yếu - không thảo luận
    G7: Bỏ cuộc giữa chừng
    G8: Ốm tuần 3 (tuần 3 sụt, tuần 4 hồi phục)

  Mỗi khóa có sheet riêng: Data_EnglishIT (200 dòng), Data_C++ (200 dòng)
"""

import sys, random, time, json
sys.stdout.reconfigure(encoding='utf-8')

import gspread
from oauth2client.service_account import ServiceAccountCredentials

random.seed(42)

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1zZ8QxLurma5j_J9YUTSm6vL5JFHujWFmScYZ44RizEs/edit'
JSON_KEY  = 'credentials.json'

# ═══ HỌ TÊN VIỆT NAM ═══
HO = ['Nguyễn','Trần','Lê','Phạm','Hoàng','Huỳnh','Phan','Vũ','Võ','Đặng',
      'Bùi','Đỗ','Hồ','Ngô','Dương','Lý','Lương','Đinh','Tô','Mai']
DEM = ['Văn','Thị','Hoàng','Minh','Thanh','Đức','Quốc','Bảo','Tuấn','Hữu',
       'Ngọc','Kim','Phương','Anh','Xuân','Thu','Hồng','Trung','Hải','Tấn']
TEN = ['An','Bình','Chi','Dũng','Em','Phúc','Giang','Hùng','Khang','Linh',
       'Minh','Ngọc','Phong','Quang','Sơn','Thảo','Uyên','Vinh','Yến','Hà',
       'Đạt','Long','Nhật','Tâm','Khánh','Duy','Trâm','Hưng','Huy','Thắng',
       'Hiếu','Tú','Lâm','Nam','Bách','Vân','Thy','Nhung','Tiến','Kiệt',
       'Khôi','Thịnh','Cường','Toàn','Hoài','Trinh','Như','Phát','Thành','Tùng']

# ═══ CẤU TRÚC BÀI TẬP TRÊN MOODLE ═══
MOODLE_STRUCTURE = {
    'English for Information Technology': {
        'w1': {'quiz': 1, 'assign': 1, 'total': 2},
        'w2': {'quiz': 1, 'assign': 1, 'total': 2},
        'w3': {'quiz': 1, 'assign': 1, 'total': 2},
        'w4': {'quiz': 1, 'assign': 1, 'total': 2},
    },
    'Nhập môn Lập trình C++': {
        'w1': {'quiz': 1, 'assign': 1, 'total': 2},
        'w2': {'quiz': 1, 'assign': 1, 'total': 2},
        'w3': {'quiz': 1, 'assign': 1, 'total': 2},
        'w4': {'quiz': 1, 'assign': 1, 'total': 2},
    }
}

# ═══ HÀNH VI THEO 8 NHÓM — ĐẦY ĐỦ FEATURES ═══
# Mỗi nhóm: (min, max) cho từng feature cơ bản
BEHAVIOR = {
    1: {  # Chăm chỉ toàn diện
        'active_days': (5, 7), 'login_count': (8, 15), 'video_views': (3, 8),
        'document_reads': (2, 6), 'discussion': (2, 5),
        'assign_grade': (7.0, 10.0), 'quiz_grade': (7.5, 10.0),
        'assign_prob': 0.95, 'quiz_prob': 0.95,
        'assign_duration': (20, 55), 'session_duration': (40, 90),
        'ontime_margin': (60, 600), 'days_since_login': (0, 2),
        'deadline_proximity': (1, 3),
    },
    2: {  # Trì hoãn nhưng khá
        'active_days': (3, 5), 'login_count': (4, 10), 'video_views': (2, 5),
        'document_reads': (1, 4), 'discussion': (1, 3),
        'assign_grade': (5.5, 8.5), 'quiz_grade': (5.0, 8.0),
        'assign_prob': 0.80, 'quiz_prob': 0.80,
        'assign_duration': (15, 40), 'session_duration': (25, 60),
        'ontime_margin': (-200, 100), 'days_since_login': (1, 4),
        'deadline_proximity': (0, 2),
    },
    3: {  # Gian lận (điểm cao, session ngắn bất thường)
        'active_days': (2, 4), 'login_count': (3, 7), 'video_views': (0, 2),
        'document_reads': (0, 1), 'discussion': (0, 1),
        'assign_grade': (8.0, 10.0), 'quiz_grade': (9.0, 10.0),
        'assign_prob': 0.90, 'quiz_prob': 0.90,
        'assign_duration': (2, 8), 'session_duration': (5, 15),
        'ontime_margin': (-50, 200), 'days_since_login': (2, 5),
        'deadline_proximity': (0, 1),
    },
    4: {  # Yếu - ít đăng nhập
        'active_days': (0, 2), 'login_count': (0, 3), 'video_views': (0, 2),
        'document_reads': (0, 2), 'discussion': (0, 1),
        'assign_grade': (2.0, 5.0), 'quiz_grade': (1.5, 4.5),
        'assign_prob': 0.30, 'quiz_prob': 0.30,
        'assign_duration': (5, 15), 'session_duration': (5, 20),
        'ontime_margin': (-800, -100), 'days_since_login': (3, 7),
        'deadline_proximity': (0, 1),
    },
    5: {  # Yếu - không đọc tài liệu
        'active_days': (1, 3), 'login_count': (2, 5), 'video_views': (0, 1),
        'document_reads': (0, 0), 'discussion': (0, 2),
        'assign_grade': (1.0, 4.0), 'quiz_grade': (1.0, 3.5),
        'assign_prob': 0.35, 'quiz_prob': 0.35,
        'assign_duration': (5, 20), 'session_duration': (10, 30),
        'ontime_margin': (-600, -50), 'days_since_login': (2, 6),
        'deadline_proximity': (0, 1),
    },
    6: {  # Yếu - không thảo luận
        'active_days': (2, 4), 'login_count': (3, 6), 'video_views': (1, 3),
        'document_reads': (1, 3), 'discussion': (0, 0),
        'assign_grade': (3.0, 6.0), 'quiz_grade': (2.5, 5.5),
        'assign_prob': 0.50, 'quiz_prob': 0.55,
        'assign_duration': (10, 30), 'session_duration': (15, 40),
        'ontime_margin': (-400, 50), 'days_since_login': (1, 5),
        'deadline_proximity': (0, 2),
    },
    7: {  # Bỏ cuộc giữa chừng (tuần 1-2 còn, tuần 3-4 bỏ)
        'active_days': (1, 3), 'login_count': (1, 4), 'video_views': (0, 2),
        'document_reads': (0, 1), 'discussion': (0, 1),
        'assign_grade': (3.0, 6.0), 'quiz_grade': (2.0, 5.0),
        'assign_prob': 0.0, 'quiz_prob': 0.0,
        'assign_duration': (5, 15), 'session_duration': (5, 25),
        'ontime_margin': (-500, -50), 'days_since_login': (4, 7),
        'deadline_proximity': (0, 1),
    },
    8: {  # Ốm tuần 3 (tuần 1,2,4 khá; tuần 3 sụt)
        'active_days': (4, 6), 'login_count': (5, 12), 'video_views': (2, 5),
        'document_reads': (1, 4), 'discussion': (1, 3),
        'assign_grade': (6.5, 9.5), 'quiz_grade': (6.0, 9.0),
        'assign_prob': 0.85, 'quiz_prob': 0.85,
        'assign_duration': (15, 40), 'session_duration': (30, 70),
        'ontime_margin': (0, 300), 'days_since_login': (0, 3),
        'deadline_proximity': (1, 3),
    },
}

# G7: bỏ dần theo tuần
G7_PROB = {'w1': 0.60, 'w2': 0.40, 'w3': 0.10, 'w4': 0.05}
G7_ACTIVITY = {'w1': 1.0, 'w2': 0.6, 'w3': 0.15, 'w4': 0.05}
# G8: ốm tuần 3
G8_ACTIVITY = {'w1': 1.0, 'w2': 1.0, 'w3': 0.15, 'w4': 0.90}


def rr(lo, hi):
    """Random range (int)."""
    return random.randint(int(lo), int(hi))

def rf(lo, hi, dp=1):
    """Random float."""
    return round(random.uniform(lo, hi), dp)


def assign_groups(n=200):
    """Chia 200 SV thành 8 nhóm, trộn đều trong mỗi lớp 50."""
    # Mỗi lớp 50 SV → chia 8 nhóm: ~6-7 SV/nhóm/lớp
    groups = {}
    for cls_start in range(0, 200, 50):
        ids_in_class = list(range(cls_start, cls_start + 50))
        random.shuffle(ids_in_class)
        # Chia 8 nhóm: [7,7,6,6,6,6,6,6] = 50
        sizes = [7, 7, 6, 6, 6, 6, 6, 6]
        idx = 0
        for g, sz in enumerate(sizes, 1):
            for _ in range(sz):
                groups[ids_in_class[idx]] = g
                idx += 1
    return groups


def get_class(i):
    if i < 50: return '22CT111'
    if i < 100: return '22CT112'
    if i < 150: return '22CT113'
    return '22CT114'


def gen_weekly_data(group, week_num):
    """Sinh data 1 tuần cho 1 SV dựa theo nhóm hành vi."""
    b = BEHAVIOR[group]
    wk = f'w{week_num}'
    
    # Activity multiplier cho G7 và G8
    mult = 1.0
    if group == 7:
        mult = G7_ACTIVITY[wk]
    elif group == 8:
        mult = G8_ACTIVITY[wk]
    
    row = {}
    row['login_count'] = max(0, round(rr(*b['login_count']) * mult))
    row['active_days'] = max(0, round(rr(*b['active_days']) * mult))
    row['video_views'] = max(0, round(rr(*b['video_views']) * mult))
    row['document_reads'] = max(0, round(rr(*b['document_reads']) * mult))
    row['discussion'] = max(0, round(rr(*b['discussion']) * mult))
    row['session_duration'] = max(0, round(rr(*b['session_duration']) * mult))
    row['days_since_last_login'] = rr(*b['days_since_login'])
    row['ontime_margin'] = rr(*b['ontime_margin'])
    row['deadline_proximity'] = rr(*b['deadline_proximity'])
    
    # ═══ RÀNG BUỘC LOGIC: không login → không có activity ═══
    if row['login_count'] == 0:
        row['session_duration'] = 0
        row['active_days'] = 0
        row['video_views'] = 0
        row['document_reads'] = 0
        row['discussion'] = 0
    
    # active_days không thể vượt quá login_count
    row['active_days'] = min(row['active_days'], row['login_count'])
    
    # Điểm bài tập
    total_available = 2  # 1 quiz + 1 assign
    grades = []
    done = 0
    duration = 0
    
    # Xác suất làm bài (login=0 → không thể làm bài)
    a_prob = b['assign_prob']
    q_prob = b['quiz_prob']
    if row['login_count'] == 0:
        a_prob = 0.0
        q_prob = 0.0
    elif group == 7:
        a_prob = G7_PROB[wk]
        q_prob = G7_PROB[wk]
    elif group == 8 and week_num == 3:
        a_prob = 0.10
        q_prob = 0.10
    
    # Assignment
    if random.random() < a_prob:
        grade = rf(*b['assign_grade'])
        grades.append(grade)
        done += 1
        duration = rf(*b['assign_duration'])
    
    # Quiz
    if random.random() < q_prob:
        grade = rf(*b['quiz_grade'])
        grades.append(grade)
        done += 1
    
    row['total_assignments'] = total_available
    row['assignment_attempt'] = done
    row['assignment_duration_mins'] = round(duration, 2)
    
    # weekly_score = tổng điểm / tổng bài (không làm = 0)
    row['weekly_score'] = round(sum(grades) / total_available, 1) if total_available > 0 else 0
    
    return row


def gen_student(idx, group, course_name):
    """Sinh toàn bộ data cho 1 SV × 1 khóa."""
    mssv = f'122{idx:06d}'
    full_name = f'{HO[idx % len(HO)]} {DEM[idx % len(DEM)]} {TEN[idx % len(TEN)]}'
    email = f'{mssv}@student.edu.vn'
    cls = get_class(idx)
    
    row = {
        'student_id': int(mssv),
        'full_name': full_name,
        'email': email,
        'course': course_name,
        'class': cls,
    }
    
    weekly_scores = []
    totals = {k: 0 for k in ['active_days','login_count','video_views','document_reads',
              'discussion','assignment_attempt','assignment_duration_mins','ontime_margin',
              'weekly_score','days_since_last_login','session_duration','deadline_proximity']}
    
    for w in range(1, 5):
        wd = gen_weekly_data(group, w)
        for key, val in wd.items():
            row[f'{key}_w{w}'] = val
            if key in totals:
                totals[key] += val
        weekly_scores.append(wd['weekly_score'])
    
    # Totals
    for key, val in totals.items():
        if key == 'weekly_score':
            row['total_weekly_score'] = round(sum(weekly_scores) / len(weekly_scores), 1)
        elif key in ['days_since_last_login', 'session_duration']:
            row[f'total_{key}'] = round(val / 4)  # Average
        else:
            row[f'total_{key}'] = round(val, 2) if isinstance(val, float) else val
    
    row['Last_Updated'] = time.strftime('%H:%M:%S %d/%m')
    return row


def build_headers():
    headers = ['student_id', 'full_name', 'email', 'course', 'class']
    weekly = [
        'active_days', 'login_count', 'video_views', 'document_reads',
        'discussion', 'total_assignments', 'assignment_attempt',
        'assignment_duration_mins', 'ontime_margin', 'weekly_score',
        'days_since_last_login', 'session_duration', 'deadline_proximity'
    ]
    for w in range(1, 5):
        for feat in weekly:
            headers.append(f'{feat}_w{w}')
    totals = [
        'total_active_days', 'total_login_count', 'total_video_views',
        'total_document_reads', 'total_discussion', 'total_assignment_attempt',
        'total_assignment_duration_mins', 'total_ontime_margin',
        'total_weekly_score', 'total_days_since_last_login',
        'total_session_duration', 'total_deadline_proximity'
    ]
    headers.extend(totals)
    headers.append('Last_Updated')
    return headers


def row_to_list(row, headers):
    result = []
    for h in headers:
        val = row.get(h, 0)
        try:
            val = float(val)
            val = int(val) if val == int(val) else round(val, 2)
        except (ValueError, TypeError):
            pass
        result.append(val)
    return result


def main():
    print("=" * 60)
    print("🚀 DATA PIPELINE: Processing student data")
    print("=" * 60)
    
    # ── 1. Assign groups ──
    groups = assign_groups(200)
    print(f"\n📊 8 nhóm hành vi (trộn đều trong 4 lớp):")
    for g in range(1, 9):
        count = sum(1 for v in groups.values() if v == g)
        print(f"   G{g}: {count} SV")
    
    # ── 2. Generate data ──
    print(f"\n🔧 Sinh data...")
    eng_rows = []
    cpp_rows = []
    for i in range(200):
        g = groups[i]
        eng_rows.append(gen_student(i, g, 'English for Information Technology'))
        cpp_rows.append(gen_student(i, g, 'Nhập môn Lập trình C++'))
    
    headers = build_headers()
    eng_data = [row_to_list(r, headers) for r in eng_rows]
    cpp_data = [row_to_list(r, headers) for r in cpp_rows]
    
    # Preview
    h_idx = {h: i for i, h in enumerate(headers)}
    print(f"\n📊 Mẫu (3 SV đầu, English):")
    for r in eng_data[:3]:
        sid = r[h_idx['student_id']]
        name = r[h_idx['full_name']]
        cls = r[h_idx['class']]
        ts = r[h_idx['total_weekly_score']]
        print(f"   {sid} | {name} | {cls} | G{groups[eng_data.index(r)]} | TB={ts}")
    
    # Stats
    print(f"\n📊 Điểm TB theo nhóm (English):")
    for g in range(1, 9):
        scores = [r[h_idx['total_weekly_score']] for i, r in enumerate(eng_data) if groups[i] == g]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"   G{g}: avg={avg:.1f}, min={min(scores)}, max={max(scores)}, n={len(scores)}")
    
    # ── 3. Upload Google Sheets ──
    print(f"\n☁️ Kết nối Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY, scope)
    gc = gspread.authorize(creds)
    ss = gc.open_by_url(SHEET_URL)
    
    # 3a. Cập nhật sheet Cấu Hình
    print("   📋 Cập nhật 'Cấu Hình'...")
    try:
        cfg_ws = ss.worksheet('Cấu Hình')
    except:
        cfg_ws = ss.add_worksheet('Cấu Hình', 210, 5)
    
    cfg_headers = ['MSSV', 'Group', 'Class', 'Full_Name', 'Email']
    cfg_data = []
    for i in range(200):
        mssv = f'122{i:06d}'
        name = f'{HO[i % len(HO)]} {DEM[i % len(DEM)]} {TEN[i % len(TEN)]}'
        cfg_data.append([mssv, groups[i], get_class(i), name, f'{mssv}@student.edu.vn'])
    
    cfg_ws.clear()
    time.sleep(1)
    cfg_all = [cfg_headers] + cfg_data
    cfg_ws.resize(rows=len(cfg_all), cols=len(cfg_headers))
    time.sleep(1)
    cfg_ws.update(f'A1:{gspread.utils.rowcol_to_a1(len(cfg_all), len(cfg_headers))}',
                  cfg_all, value_input_option='RAW')
    print(f"      ✅ {len(cfg_data)} SV × 8 nhóm × 4 lớp")
    time.sleep(2)
    
    # 3b. Upload Data_EnglishIT
    print("   📋 Cập nhật 'Data_EnglishIT'...")
    eng_ws = ss.worksheet('Data_EnglishIT')
    eng_ws.clear()
    time.sleep(1)
    eng_all = [headers] + eng_data
    eng_ws.resize(rows=len(eng_all), cols=len(headers))
    time.sleep(1)
    eng_ws.update(f'A1:{gspread.utils.rowcol_to_a1(len(eng_all), len(headers))}',
                  eng_all, value_input_option='RAW')
    print(f"      ✅ {len(eng_data)} × {len(headers)} cột")
    time.sleep(2)
    
    # 3c. Upload Data_C++
    print("   📋 Cập nhật 'Data_C++'...")
    cpp_ws = ss.worksheet('Data_C++')
    cpp_ws.clear()
    time.sleep(1)
    cpp_all = [headers] + cpp_data
    cpp_ws.resize(rows=len(cpp_all), cols=len(headers))
    time.sleep(1)
    cpp_ws.update(f'A1:{gspread.utils.rowcol_to_a1(len(cpp_all), len(headers))}',
                  cpp_all, value_input_option='RAW')
    print(f"      ✅ {len(cpp_data)} × {len(headers)} cột")
    
    # ── 4. Save JSON ──
    print(f"\n💾 Lưu students_data.json...")
    all_records = [{h: v for h, v in zip(headers, r)} for r in eng_data + cpp_data]
    with open('students_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"   ✅ {len(all_records)} records (200 Eng + 200 C++)")
    
    # ── 5. Save config for Moodle sync ──
    print(f"\n💾 Lưu moodle_config.json...")
    config = []
    for i in range(200):
        config.append({
            'MSSV': f'122{i:06d}',
            'Group': groups[i],
            'Class': get_class(i),
        })
    with open('moodle_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"🎉 HOÀN TẤT!")
    print(f"{'='*60}")
    print(f"  ✅ Google Sheets: Cấu Hình + Data_EnglishIT + Data_C++")
    print(f"  ✅ students_data.json: {len(all_records)} records")
    print(f"  ✅ moodle_config.json: 200 SV × nhóm hành vi")
    print(f"\n  📌 Phân bổ:")
    for cls in ['22CT111','22CT112','22CT113','22CT114']:
        count = sum(1 for c in config if c['Class'] == cls)
        ids = [c['MSSV'] for c in config if c['Class'] == cls]
        print(f"     {cls}: {count} SV ({ids[0]}-{ids[-1]})")
    print(f"\n  📌 Tiếp theo: Chạy sync_json_to_mongo.py để đồng bộ MongoDB")


if __name__ == '__main__':
    main()
