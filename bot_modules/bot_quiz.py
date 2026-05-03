# -*- coding: utf-8 -*-
"""
Module xử lý làm bài Quiz trên Moodle.
Tách ra từ AUTO_HOC_BAI.py để dễ bảo trì.
"""
import time
import random


def lam_bai_quiz(page, url_quiz, group, ten_bai, correct_answers):
    """Thực hiện làm 1 bài quiz trên Moodle.

    Args:
        page: Playwright page object
        url_quiz: URL của bài quiz
        group: Nhóm hành vi (1-8)
        ten_bai: Tên bài quiz
        correct_answers: Danh sách đáp án đúng
    """
    print(f"   ✍️ Đang làm bài: {ten_bai}...")
    page.goto(url_quiz)
    time.sleep(2)

    # Delay trước khi bắt đầu quiz
    delays = {1: (10, 30), 2: (5, 15), 3: (1, 3), 4: (15, 40)}
    lo, hi = delays.get(group, (2, 2))
    pre_delay = random.randint(lo, hi) if lo != hi else lo
    print(f"   ⏳ [{ten_bai[:20]}] Reading delay {pre_delay}s...")
    time.sleep(pre_delay)

    try:
        # B1: Click nút bắt đầu
        btn_attempt = _find_start_button(page)
        if not btn_attempt:
            print(f"   [B1] Khong tim thay nut bat dau - bo qua!")
            return

        label = (btn_attempt.inner_text() or '???').strip()
        btn_attempt.click()
        print(f"   [B1] Da click: [{label}]")
        time.sleep(2)

        # B2: Modal xác nhận
        _handle_confirm_modal(page)

        # B2.5: Đảm bảo ở trang đầu
        _go_to_first_page(page)

        # B3: Vòng lặp trả lời
        _answer_questions(page, group, correct_answers)

        # B4: Nộp bài
        _submit_quiz(page)

        print(f"   🎉 Đã nộp xong bài {ten_bai}!")
    except Exception as e:
        print(f"   Loi tong the quiz: {e}")


def _find_start_button(page):
    """Tìm nút Attempt/Continue/Re-attempt."""
    selectors = [
        'div.quizattempt button.btn-primary',
        'div.quizattempt a.btn-primary',
        'form.quizstartbuttondiv button',
        'input[type="submit"].btn-primary',
        '.singlebutton button.btn-primary',
        'button.btn-primary',
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue

    # Scroll xuống để tìm
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None


def _handle_confirm_modal(page):
    """Xử lý modal xác nhận bắt đầu làm bài."""
    try:
        page.wait_for_selector('.moodle-dialogue', timeout=2000)
        time.sleep(1)
        btn = page.query_selector('input#id_submitbutton')
        if not btn:
            btn = page.query_selector('.moodle-dialogue input[type="submit"]')
        if btn and btn.is_visible():
            btn.click()
            print(f"   ✅ [B2] Đã xác nhận Bắt đầu làm bài!")
            time.sleep(2)
    except Exception:
        print(f"   ℹ️ [B2] Không có modal → đang tiếp tục bài làm có sẵn")


def _go_to_first_page(page):
    """Quay về trang đầu tiên nếu đang ở giữa."""
    while True:
        try:
            btn_prev = page.query_selector('input#mod_quiz-prev-nav')
            if btn_prev and btn_prev.is_visible():
                btn_prev.click()
                time.sleep(1.5)
            else:
                break
        except Exception:
            break


def _answer_questions(page, group, correct_answers):
    """Trả lời câu hỏi trên từng trang."""
    trang = 1
    while True:
        time.sleep(2)
        questions = page.query_selector_all('.que.multichoice')
        if not questions:
            break

        print(f"   📄 Trang {trang}: {len(questions)} câu hỏi")
        for q in questions:
            try:
                # Độ trễ theo nhóm
                delays = {1: (5, 15), 2: (3, 8), 3: (0.5, 2), 4: (8, 20)}
                lo, hi = delays.get(group, (2, 5))
                time.sleep(random.uniform(lo, hi))

                options = q.query_selector_all('input[type="radio"]')

                is_correct = group in [1, 3] or (group == 2 and random.random() < 0.8) or (group == 4 and random.random() < 0.3)

                answered = False
                if is_correct and correct_answers:
                    answered = _try_correct_answer(page, options, correct_answers)

                if not answered and options:
                    chosen = random.choice(options)
                    page.evaluate("(el) => el.click()", chosen)
            except Exception:
                break

        # Chuyển trang
        try:
            btn_next = page.query_selector('input#mod_quiz-next-nav')
            if btn_next and btn_next.is_visible():
                btn_next.click()
                trang += 1
            else:
                btn_finish = page.query_selector('a.endtestlink')
                if btn_finish and btn_finish.is_visible():
                    btn_finish.click()
                break
        except Exception:
            break


def _try_correct_answer(page, options, correct_answers):
    """Thử chọn đáp án đúng."""
    for opt in options:
        try:
            text = page.evaluate("""(el) => {
                let p = el.closest('.r0, .r1');
                if (p) return p.innerText;
                p = el.closest('.answer div, .flex-fill');
                if (p) return p.innerText;
                let lbl = document.querySelector('label[for="' + el.id + '"]');
                if (lbl) return lbl.innerText;
                return el.parentElement ? el.parentElement.innerText : '';
            }""", opt)
            text = text.replace('\xa0', ' ').strip().lower()
            if not text or 'clear my choice' in text:
                continue
            if any(ans.lower().strip() in text for ans in correct_answers):
                page.evaluate("(el) => el.click()", opt)
                return True
        except Exception:
            continue
    return False


def _submit_quiz(page):
    """Nộp bài và xác nhận."""
    time.sleep(2)
    selectors_submit = [
        'button:has-text("Nộp bài và kết thúc")',
        'button:has-text("Submit all and finish")',
        '.submitbtns button.btn-primary',
    ]
    for sel in selectors_submit:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            time.sleep(2)
            # Modal xác nhận cuối
            for csel in ['button[data-action="confirm"]', 'div.modal-dialog button.btn-primary']:
                cbtn = page.query_selector(csel)
                if cbtn and cbtn.is_visible():
                    cbtn.click()
                    time.sleep(3)
                    break
            break
