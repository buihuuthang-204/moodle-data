# -*- coding: utf-8 -*-
"""
Module xử lý nộp bài tập (Assignment) trên Moodle.
Tách ra từ AUTO_HOC_BAI.py để dễ bảo trì.
"""
import time
import random
import os

# Nội dung bài nộp tự luận (đa dạng, tự nhiên)
NOI_DUNG_BAI_NOP = [
    "Bài làm đã hoàn thành. Em đã nghiên cứu kỹ nội dung bài giảng và áp dụng vào bài tập này.",
    "Em xin nộp bài tập. Trong quá trình làm bài, em đã tham khảo tài liệu từ sách giáo khoa.",
    "Dưới đây là bài làm của em. Em đã cố gắng trình bày rõ ràng từng bước giải.",
    "Bài nộp tuần này. Em gặp khó khăn ở phần cuối nhưng đã cố gắng hoàn thành đúng hạn.",
    "Em đã hoàn thành bài tập theo yêu cầu. Phần phân tích em thực hiện bằng công cụ đã học.",
    "Bài tập đã được hoàn thành. Em áp dụng kiến thức từ buổi học tuần trước.",
    "Em nộp bài muộn một chút do gặp vấn đề kỹ thuật. Nội dung bài em đã làm đầy đủ.",
    "Đây là bài làm của em cho tuần này. Em đã đọc thêm tài liệu tham khảo để bổ sung kiến thức.",
    "Bài tập hoàn thành. Em thấy đề bài thú vị và học được nhiều kiến thức mới.",
    "Em xin gửi bài tập. Quá trình làm bài giúp em hiểu sâu hơn về lý thuyết đã học.",
]


def lam_bai_tap(page, url_assign, group, ten_bai):
    """Xử lý nộp bài tập tự luận / Upload file (Assignment).

    Args:
        page: Playwright page object
        url_assign: URL bài tập
        group: Nhóm hành vi (1-8)
        ten_bai: Tên bài tập
    """
    print(f"   ✍️ Đang làm bài tập: {ten_bai}...")
    page.goto(url_assign)
    time.sleep(2)

    # Kiểm tra đã nộp chưa
    status = page.query_selector('.submissionstatussubmitted, .earlysubmission')
    if status:
        print(f"   ✅ Đã nộp bài tập này rồi - Bỏ qua!")
        return

    # Tìm nút thêm bài nộp
    selectors = [
        'button[type="submit"]:has-text("Add submission")',
        'button[type="submit"]:has-text("Edit submission")',
        'button:has-text("Thêm bài nộp")',
        'form[action*="assign"] button[type="submit"]',
    ]
    btn_add = None
    for sel in selectors:
        btn_add = page.query_selector(sel)
        if btn_add and btn_add.is_visible():
            break
        btn_add = None

    if not btn_add:
        print(f"   ⚠️ Không tìm thấy nút nộp bài")
        return

    btn_add.click()
    time.sleep(3)

    # Điền text online (Atto/TinyMCE editor)
    editor = page.query_selector('div[contenteditable="true"]')
    if editor:
        text_content = random.choice(NOI_DUNG_BAI_NOP)
        editor.click()
        time.sleep(0.3)
        page.keyboard.type(text_content)
        time.sleep(1)

    # Upload file nếu có input file
    file_inputs = page.query_selector_all('input[type="file"]')
    if file_inputs:
        dummy_file = os.path.join(os.getcwd(), 'bai_lam_tu_luan.txt')
        with open(dummy_file, 'w', encoding='utf-8') as f:
            f.write(f"Bài nộp cho: {ten_bai}\n")
        try:
            file_inputs[0].set_input_files(dummy_file)
            time.sleep(2)
        except Exception:
            pass

    # Bấm Save changes
    btn_save = page.query_selector('input[name="submitbutton"], button#id_submitbutton')
    if btn_save:
        btn_save.click()
        print(f"   ✅ Đã nộp bài tập thành công!")
        time.sleep(3)
