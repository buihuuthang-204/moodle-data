# -*- coding: utf-8 -*-
"""
Bot Modules — Tách từ AUTO_HOC_BAI.py để dễ bảo trì.

Modules:
  - bot_login  : Xử lý đăng nhập Moodle
  - bot_quiz   : Xử lý làm bài Quiz (multichoice)
  - bot_assign : Xử lý nộp bài tập Assignment
  - bot_forum  : Xử lý thảo luận Forum + Thông báo
"""

from bot_modules.bot_login import dang_nhap_moodle
from bot_modules.bot_quiz import lam_bai_quiz
from bot_modules.bot_assign import lam_bai_tap
from bot_modules.bot_forum import xem_thong_bao, xem_thao_luan

__all__ = [
    'dang_nhap_moodle',
    'lam_bai_quiz',
    'lam_bai_tap',
    'xem_thong_bao',
    'xem_thao_luan',
]
