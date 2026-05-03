# pyright: reportAll=false
# pylint: skip-file
# flake8: noqa
# type: ignore
# pyre-ignore-all-errors

"""
=== AUTO HỌC BÀI MOODLE ===
Agent tự động mô phỏng hành vi sinh viên trên Moodle LMS.
Sử dụng Playwright để điều khiển browser, thực hiện:
  - Đăng nhập → Xem dashboard → Xem khóa học
  - Xem video (URL), đọc tài liệu (Page)
  - Làm quiz, nộp bài tập (Assignment)
  - Tham gia thảo luận Forum
  - Đăng xuất

Hành vi được điều chỉnh theo 8 nhóm (G1-G8) từ cấu hình.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import random
import json
import os
import threading

from bot_modules.bot_login import dang_nhap_moodle
from bot_modules.bot_quiz import lam_bai_quiz
from bot_modules.bot_forum import xem_thong_bao, xem_thao_luan
from bot_modules.bot_assign import lam_bai_tap

# ================= CẤU HÌNH =================
BASE_URL   = "http://localhost:8080"
LOGIN_URL  = f"{BASE_URL}/login/index.php"
CONFIG_FILE = "moodle_config.json"

COURSES = [
    {"id": 3, "name": "English IT",  "url": f"{BASE_URL}/course/view.php?id=3", "announce_cmid": 6},
    {"id": 4, "name": "C++",         "url": f"{BASE_URL}/course/view.php?id=4", "announce_cmid": 25},
]

# ===== CẤU HÌNH TỐC ĐỘ =====
BATCH_SIZE   = 1
HEADLESS     = False
PAGE_TIMEOUT = 30000

# Danh sách User-Agents phổ biến
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

GEO_LOCATIONS = [
    {"longitude": 105.8342, "latitude": 21.0278},   # Hanoi
    {"longitude": 106.6297, "latitude": 10.8231},   # HCMC
    {"longitude": 108.2022, "latitude": 16.0544},   # Da Nang
    {"longitude": 106.6881, "latitude": 10.7626},   # Q1 HCMC
]

# --- HÀNH VI THEO 8 NHÓM ---
# Xác suất làm bài quiz/assign theo tuần (G7 giảm dần, G8 ốm tuần 3)
GROUP_PROB = {
    1: {"quiz": 0.95, "assign": 0.95, "forum": 0.90, "video": (3, 8), "doc": (2, 6)},
    2: {"quiz": 0.80, "assign": 0.80, "forum": 0.50, "video": (2, 5), "doc": (1, 4)},
    3: {"quiz": 0.90, "assign": 0.90, "forum": 0.20, "video": (0, 2), "doc": (0, 1)},
    4: {"quiz": 0.30, "assign": 0.30, "forum": 0.20, "video": (0, 2), "doc": (0, 2)},
    5: {"quiz": 0.35, "assign": 0.35, "forum": 0.30, "video": (0, 1), "doc": (0, 0)},
    6: {"quiz": 0.55, "assign": 0.50, "forum": 0.00, "video": (1, 3), "doc": (1, 3)},
    7: {"quiz": 0.60, "assign": 0.60, "forum": 0.20, "video": (0, 2), "doc": (0, 1)},
    8: {"quiz": 0.85, "assign": 0.85, "forum": 0.60, "video": (2, 5), "doc": (1, 4)},
}
# G7: xác suất giảm theo tuần (bỏ cuộc dần)
G7_PROB_WEEKLY = {"w1": 0.60, "w2": 0.40, "w3": 0.10, "w4": 0.05}
# G8: ốm tuần 3 → xác suất tuần 3 rất thấp
G8_PROB_WEEKLY = {"w1": 0.85, "w2": 0.85, "w3": 0.10, "w4": 0.85}


def doc_cau_hinh():
    """Đọc danh sách SV từ moodle_config.json (local)."""
    students = []
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        for sv in config:
            mssv = sv['MSSV']
            students.append({
                "user": mssv,
                "pass": "Sv@123456",
                "group": sv['Group'],
                "class": sv['Class'],
            })
        print(f"[CONFIG] Đã tải {len(students)} SV từ {CONFIG_FILE}")
    except Exception as e:
        print(f"[CONFIG] Lỗi: {e}")
    return students


def xem_video_va_tailieu(page, course_url, group):
    """Xem video (mod_url) và đọc tài liệu (mod_page) theo nhóm hành vi."""
    gp = GROUP_PROB[group]
    
    page.goto(course_url)
    time.sleep(2)

    # Xem video (URL resources)
    video_links = page.query_selector_all('a[href*="/mod/url/view.php"]')
    so_video = random.randint(*gp['video']) if gp['video'][1] > 0 else 0
    so_video = min(so_video, len(video_links))
    
    if so_video > 0:
        chosen = random.sample(list(range(len(video_links))), so_video)
        for i in chosen:
            try:
                href = video_links[i].get_attribute('href')
                if href:
                    page.goto(href)
                    if group == 1:   time.sleep(random.uniform(8, 20))
                    elif group == 3: time.sleep(random.uniform(1, 3))
                    elif group == 4: time.sleep(random.uniform(3, 8))
                    else:            time.sleep(random.uniform(5, 12))
                    print(f"   🎬 Đã xem video")
            except Exception:
                pass
    
    # Đọc tài liệu (Page resources)
    page.goto(course_url)
    time.sleep(1)
    doc_links = page.query_selector_all('a[href*="/mod/page/view.php"]')
    so_doc = random.randint(*gp['doc']) if gp['doc'][1] > 0 else 0
    so_doc = min(so_doc, len(doc_links))
    
    if so_doc > 0:
        chosen = random.sample(list(range(len(doc_links))), so_doc)
        for i in chosen:
            try:
                href = doc_links[i].get_attribute('href')
                if href:
                    page.goto(href)
                    if group == 1:   time.sleep(random.uniform(10, 25))
                    elif group == 3: time.sleep(random.uniform(1, 3))
                    else:            time.sleep(random.uniform(5, 15))
                    print(f"   📖 Đã đọc tài liệu")
            except Exception:
                pass


def nen_lam_bai(group, week_num=None):
    """Quyết định SV có nên làm bài không dựa trên nhóm + tuần."""
    if group == 7 and week_num:
        prob = G7_PROB_WEEKLY.get(f"w{week_num}", 0.05)
        return random.random() < prob
    elif group == 8 and week_num:
        prob = G8_PROB_WEEKLY.get(f"w{week_num}", 0.85)
        return random.random() < prob
    else:
        gp = GROUP_PROB[group]
        return random.random() < gp['quiz']


def xu_ly_sinh_vien(sv):
    """Xử lý 1 sinh viên: login → xem bài → quiz → forum → logout."""
    tag = f"[{sv['user']}]"
    group = sv['group']
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS, slow_mo=0)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                geolocation=random.choice(GEO_LOCATIONS),
                permissions=['geolocation'],
                viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)}
            )
            page = context.new_page()
            page.set_default_timeout(PAGE_TIMEOUT)

            print(f"🤖 {tag} Đăng nhập (Nhóm G{group})...")

            # === LOGIN ===
            if not dang_nhap_moodle(page, LOGIN_URL, sv["user"], sv["pass"]):
                print(f"   ❌ {tag} Login thất bại!")
                browser.close()
                return

            print(f"   ✅ {tag} Login OK!")

            # === DASHBOARD ===
            page.goto(f"{BASE_URL}/my/")
            time.sleep(random.uniform(1, 3))

            # === XỬ LÝ TỪNG KHÓA HỌC ===
            for course in COURSES:
                print(f"\n   📚 {tag} Khóa: {course['name']}")
                
                # Xem trang khóa học
                page.goto(course['url'])
                time.sleep(random.uniform(2, 4))

                # Xem video + tài liệu
                xem_video_va_tailieu(page, course['url'], group)

                # Xem thông báo (tất cả nhóm trừ G5 không đọc doc)
                xem_thong_bao(page, group, f"{BASE_URL}/mod/forum/view.php?id={course['announce_cmid']}")

                # Tham gia thảo luận (G6 không thảo luận)
                if group != 6:
                    xem_thao_luan(page, group, course['url'])

                # Quay lại trang khóa học để tìm quiz + assign
                page.goto(course['url'])
                time.sleep(2)

                # Thu thập tất cả quiz và assign
                quiz_links = page.query_selector_all('a[href*="/mod/quiz/view.php"]')
                assign_links = page.query_selector_all('a[href*="/mod/assign/view.php"]')

                activities = []
                for q in quiz_links:
                    href = q.get_attribute('href')
                    name = q.inner_text().strip()
                    if href:
                        activities.append(('quiz', href, name))
                for a in assign_links:
                    href = a.get_attribute('href')
                    name = a.inner_text().strip()
                    if href:
                        activities.append(('assign', href, name))

                # Làm bài theo xác suất nhóm hành vi
                for idx, (act_type, url, name) in enumerate(activities):
                    week_num = (idx % 4) + 1   # Map activity index → tuần
                    
                    if not nen_lam_bai(group, week_num):
                        print(f"   ⏭️ Bỏ qua {name} (xác suất nhóm G{group})")
                        continue
                    
                    try:
                        if act_type == 'quiz':
                            lam_bai_quiz(page, url, group, name, [])
                        else:
                            lam_bai_tap(page, url, group, name)
                    except Exception as e_act:
                        print(f"   ⚠️ Lỗi {name}: {str(e_act)[:60]}")
                    
                    # Quay lại trang khóa học sau mỗi activity
                    try:
                        page.goto(course['url'])
                        time.sleep(2)
                    except Exception:
                        pass

            # === LOGOUT ===
            print(f"\n   🔓 {tag} Đăng xuất...")
            page.goto(f"{BASE_URL}/login/logout.php")
            time.sleep(1)
            try:
                btn = page.query_selector('input[type="submit"], button[type="submit"]')
                if btn:
                    btn.click()
                    time.sleep(1)
            except Exception:
                pass

            browser.close()
            print(f"✅ {tag} Hoàn tất!")

    except Exception as e:
        print(f"❌ {tag} Lỗi: {e}")


def demo_mode():
    """
    CHẾ ĐỘ DEMO: Chạy 1 SV với browser hiển thị, chậm lại để thầy cô xem.
    Dùng khi bảo vệ đồ án: python AUTO_HOC_BAI.py --demo
    """
    global HEADLESS
    HEADLESS = False    # Hiện browser cho thầy cô xem

    print("=" * 60)
    print("🎓 CHẾ ĐỘ DEMO — Trình diễn Agent cho Giáo viên")
    print("   Browser hiển thị | Tốc độ chậm | 1 SV mẫu")
    print("=" * 60)

    students = doc_cau_hinh()
    if not students:
        print("❌ Không tải được cấu hình!")
        return

    # Chọn 1 SV nhóm G1 (chăm chỉ) để demo đẹp nhất
    sv_demo = None
    for s in students:
        if s['group'] == 1:
            sv_demo = s
            break
    if not sv_demo:
        sv_demo = students[0]

    print(f"\n🤖 Demo SV: {sv_demo['user']} (Nhóm G{sv_demo['group']})")
    print(f"   Hành vi: Chăm chỉ — xem video, đọc tài liệu, làm quiz, nộp bài, thảo luận")
    print(f"\n   ⏳ Browser sẽ mở ra, thầy/cô quan sát hành vi agent...\n")

    xu_ly_sinh_vien(sv_demo)

    print("\n" + "=" * 60)
    print("✅ DEMO HOÀN TẤT!")
    print("   Agent đã thực hiện đầy đủ flow:")
    print("   Login → Dashboard → Xem video → Đọc tài liệu")
    print("   → Làm Quiz → Nộp Assignment → Thảo luận → Logout")
    print("=" * 60)


def main():
    print("=" * 60)
    print("🚀 AUTO HỌC BÀI MOODLE — Agent mô phỏng hành vi SV")
    print("   200 SV × 2 khóa × 8 nhóm hành vi (G1-G8)")
    print("=" * 60)

    # Đọc cấu hình từ file local
    students = doc_cau_hinh()
    if not students:
        print("❌ Không tải được cấu hình SV!")
        return

    # Thống kê nhóm
    print(f"\n📊 Phân bổ nhóm:")
    for g in range(1, 9):
        count = sum(1 for s in students if s['group'] == g)
        print(f"   G{g}: {count} SV")

    # Chạy từng batch
    print(f"\n🔧 Batch size: {BATCH_SIZE} | Headless: {HEADLESS}")
    print(f"   Tổng: {len(students)} SV\n")

    threads = []
    for i, sv in enumerate(students):
        if len(threads) >= BATCH_SIZE:
            for t in threads:
                t.join()
            threads = []
            print(f"\n--- Batch tiếp theo ({i+1}/{len(students)}) ---\n")

        t = threading.Thread(target=xu_ly_sinh_vien, args=(sv,))
        t.start()
        threads.append(t)
        time.sleep(random.uniform(3, 8))    # Delay giữa các SV

    for t in threads:
        t.join()

    print("\n" + "=" * 60)
    print("🎉 HOÀN TẤT TẤT CẢ!")
    print("=" * 60)


if __name__ == '__main__':
    import sys
    if '--demo' in sys.argv:
        demo_mode()
    else:
        main()
