# -*- coding: utf-8 -*-
"""
Module xử lý thảo luận Forum trên Moodle.
Tách ra từ AUTO_HOC_BAI.py để dễ bảo trì.
"""
import time
import random


def xem_thong_bao(page, group, announcement_url):
    """Click vào trang Thông báo (Announcements) và đọc bài viết."""
    print(f"   📢 Đang xem thông báo...")
    try:
        page.goto(announcement_url)
        time.sleep(2)

        # Click vào từng bài viết thông báo
        post_links = page.query_selector_all('td.topic.starter a')
        if not post_links:
            post_links = page.query_selector_all('.discussion-name a, .topic a')

        for post in post_links:
            try:
                post.click()
                if group == 1:   time.sleep(random.randint(5, 10))
                elif group == 2: time.sleep(random.randint(2, 4))
                elif group == 3: time.sleep(random.uniform(0.5, 1))
                elif group == 4: time.sleep(random.randint(8, 15))

                print(f"   📰 Đã đọc thông báo: {post.inner_text().strip()[:50]}")
                page.go_back()
                time.sleep(1)
            except Exception:
                pass

        print(f"   ✅ Đã xem xong thông báo!")
    except Exception as e:
        print(f"   ⚠️ Lỗi khi xem thông báo: {e}")


def xem_thao_luan(page, group, course_url):
    """Click vào các chủ đề thảo luận (Discussion forum) trên trang khóa học + ĐĂNG BÀI."""
    print(f"   💬 Đang xem và tham gia thảo luận...")
    
    NOI_DUNG_THAO_LUAN = [
        "Em thấy bài này rất hay và bổ ích. Cảm ơn thầy/cô đã chia sẻ!",
        "Em có thắc mắc về phần này, mong thầy/cô giải đáp thêm ạ.",
        "Phần kiến thức này rất hữu ích cho công việc sau này. Em sẽ tìm hiểu thêm.",
        "Em đã thực hành theo hướng dẫn và thấy kết quả tốt. Xin chia sẻ kinh nghiệm.",
        "Theo em hiểu, phần này liên quan đến thực tiễn rất nhiều. Rất thú vị!",
        "Em muốn hỏi thêm về cách áp dụng kiến thức này vào dự án thực tế.",
        "Cảm ơn các bạn đã chia sẻ. Em học được nhiều điều từ topic này.",
        "Em nghĩ đây là một chủ đề quan trọng cần thảo luận thêm.",
        "Bài học hôm nay rất dễ hiểu. Em đã nắm được kiến thức cơ bản.",
        "Em xin bổ sung thêm một số ý kiến cá nhân về vấn đề này.",
    ]
    
    TIEU_DE_BAI_MOI = [
        "Thắc mắc về bài học tuần này",
        "Chia sẻ kinh nghiệm thực hành",
        "Hỏi đáp kiến thức IT cơ bản",
        "Cảm nhận sau khi học xong chương này",
        "Trao đổi về bài tập nhóm",
    ]
    
    try:
        page.goto(course_url)
        time.sleep(2)

        all_links = page.query_selector_all('.aalink')
        forum_links = []
        for link in all_links:
            href = link.get_attribute('href')
            text = link.inner_text().strip()
            if href and 'forum' in href and 'view.php?id=6' not in href:
                forum_links.append((href, text))

        if group == 1:
            so_bai_xem = len(forum_links)
            so_bai_dang = random.randint(2, 3)
        elif group == 2:
            so_bai_xem = min(2, len(forum_links))
            so_bai_dang = random.randint(0, 1)
        elif group == 3:
            so_bai_xem = min(1, len(forum_links))
            so_bai_dang = 1
        elif group == 4:
            so_bai_xem = min(1, len(forum_links))
            so_bai_dang = random.randint(0, 1)
        elif group == 5:
            so_bai_xem = min(1, len(forum_links))
            so_bai_dang = random.randint(0, 1)
        elif group == 6:
            so_bai_xem = 0
            so_bai_dang = 0
        elif group == 7:
            so_bai_xem = min(1, len(forum_links))
            so_bai_dang = 0
        elif group == 8:
            so_bai_xem = min(2, len(forum_links))
            so_bai_dang = random.randint(0, 1)
        else:
            so_bai_xem = 0
            so_bai_dang = 0

        da_dang = 0

        if forum_links and so_bai_xem > 0:
            bai_can_xem = random.sample(forum_links, min(so_bai_xem, len(forum_links)))
            for forum_href, forum_text in bai_can_xem:
                try:
                    page.goto(forum_href)
                    time.sleep(2)

                    if da_dang < so_bai_dang:
                        try:
                            btn_add = page.query_selector('a[href*="post.php?forum="], button:has-text("Add discussion topic"), a:has-text("Add a new discussion topic")')
                            if btn_add and btn_add.is_visible():
                                btn_add.click()
                                time.sleep(2)
                                
                                subject_input = page.query_selector('input[name="subject"]')
                                if subject_input:
                                    tieu_de = random.choice(TIEU_DE_BAI_MOI) + f" #{random.randint(1,999)}"
                                    subject_input.fill(tieu_de)
                                    time.sleep(0.5)
                                
                                editor = page.query_selector('div[contenteditable="true"]')
                                if editor:
                                    noi_dung = random.choice(NOI_DUNG_THAO_LUAN)
                                    editor.click()
                                    time.sleep(0.3)
                                    page.keyboard.type(noi_dung)
                                    time.sleep(1)
                                
                                btn_submit = page.query_selector('input[name="submitbutton"], input#id_submitbutton')
                                if btn_submit:
                                    btn_submit.click()
                                    time.sleep(3)
                                    da_dang += 1
                                    print(f"   ✏️ Đã đăng bài thảo luận: {tieu_de[:40]}")
                        except Exception:
                            pass

                    page.goto(forum_href)
                    time.sleep(2)
                    discussion_links = page.query_selector_all('td.topic.starter a, .discussion-name a, .topic a')
                    for disc in discussion_links[:2]:
                        try:
                            disc.click()
                            if group == 1:    time.sleep(random.randint(5, 10))
                            elif group == 2:  time.sleep(random.randint(2, 4))
                            elif group == 3:  time.sleep(random.uniform(0.5, 1))
                            elif group == 4:  time.sleep(random.randint(8, 15))

                            if da_dang < so_bai_dang:
                                try:
                                    # Moodle 4.x: nút Reply là <a> với title
                                    btn_reply = page.query_selector('a[title="Phúc đáp"], a[title="Reply"], a:has-text("Phúc đáp"), a:has-text("Reply")')
                                    if btn_reply and btn_reply.is_visible():
                                        btn_reply.click()
                                        time.sleep(2)
                                        
                                        # Moodle 4.x inline reply dùng textarea, không phải contenteditable
                                        textarea = page.query_selector('textarea[title="Nội dung"], textarea[placeholder*="Viết câu trả lời"], textarea[name="post"]')
                                        if textarea:
                                            textarea.click()
                                            time.sleep(0.3)
                                            textarea.fill(random.choice(NOI_DUNG_THAO_LUAN))
                                            time.sleep(1)
                                        else:
                                            # Fallback: editor cũ (contenteditable)
                                            editor_reply = page.query_selector('div[contenteditable="true"]')
                                            if editor_reply:
                                                editor_reply.click()
                                                time.sleep(0.3)
                                                page.keyboard.type(random.choice(NOI_DUNG_THAO_LUAN))
                                                time.sleep(1)
                                        
                                        # Nút gửi
                                        btn_sub = page.query_selector('form.mform button.btn-primary, button:has-text("Gửi bài viết lên diễn đàn"), button:has-text("Post to forum"), input[name="submitbutton"], input#id_submitbutton')
                                        if btn_sub and btn_sub.is_visible():
                                            btn_sub.click()
                                            time.sleep(3)
                                            da_dang += 1
                                            print(f"   💬 Đã reply thảo luận!")
                                except Exception as e_reply:
                                    print(f"   ⚠️ Reply lỗi: {str(e_reply)[:50]}")

                            print(f"   📝 Đã đọc thảo luận: {disc.inner_text().strip()[:50]}")
                            page.go_back()
                            time.sleep(1)
                        except Exception:
                            pass

                except Exception:
                    pass

        print(f"   ✅ Thảo luận xong! Đã đăng {da_dang} bài.")
    except Exception as e:
        print(f"   ⚠️ Lỗi khi xem thảo luận: {e}")
