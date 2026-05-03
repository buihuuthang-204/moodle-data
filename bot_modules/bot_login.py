# -*- coding: utf-8 -*-
"""
Module xử lý đăng nhập Moodle.
Tách ra từ AUTO_HOC_BAI.py để dễ bảo trì.
"""
import time


def dang_nhap_moodle(page, login_url, username, password):
    """Thực hiện đăng nhập vào Moodle.

    Args:
        page: Playwright page object
        login_url: URL trang đăng nhập
        username: Tên đăng nhập
        password: Mật khẩu

    Returns:
        bool: True nếu đăng nhập thành công, False nếu thất bại.
    """
    for attempt in range(3):
        page.goto(login_url)
        time.sleep(2)

        page.evaluate("""() => {
            let u = document.querySelector('input[name="username"]');
            let p = document.querySelector('input[name="password"]');
            if (u) { u.value = ''; u.focus(); }
            if (p) { p.value = ''; }
        }""")
        time.sleep(0.5)

        page.evaluate(f"""() => {{
            let u = document.querySelector('input[name="username"]');
            if (u) {{ u.value = '{username}'; u.dispatchEvent(new Event('input')); }}
        }}""")
        time.sleep(0.3)

        page.evaluate(f"""() => {{
            let p = document.querySelector('input[name="password"]');
            if (p) {{ p.value = '{password}'; p.dispatchEvent(new Event('input')); }}
        }}""")
        time.sleep(0.3)

        page.click('#loginbtn')
        time.sleep(3)

        if '/login/' not in page.url:
            return True
        else:
            print(f"   ⚠️ Login lần {attempt+1} thất bại, thử lại...")
            time.sleep(1)
            
    return False
