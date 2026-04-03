"""
結局敘事規格驗證：每則結局須為三頁（敘事×2＋CG 大圖），
敘事每頁正文以與遊戲相同之換行寬度量測，須為 5～6 行（含）；
CG 頁 ``quote`` 須在底欄單行寬度內完整顯示（不觸發刪節）。

執行：python _verify_ending_narrative_rules.py
"""

from __future__ import annotations

import sys

import pygame

from endings import ENDINGS
from main import (
    CANVAS_WIDTH,
    _TEXT_PAD_X,
    _make_intro_font,
    _make_small_font,
    _scale_x,
    wrap_cjk,
)

_MIN_NARRATIVE_LINES: int = 5
_MAX_NARRATIVE_LINES: int = 6


def main() -> int:
    """
    逐一檢查 ``ENDINGS``：敘事頁行數與 CG 頁 ``quote`` 換行數。

    Returns:
        全部通過為 ``0``，任一失敗為 ``1``。
    """
    pygame.init()
    intro = _make_intro_font()
    small = _make_small_font()
    mx = _scale_x(20)
    max_w_body = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    mx_cg = _scale_x(12)
    max_w_quote = CANVAS_WIDTH - 2 * mx_cg
    ok = True
    for key in sorted(ENDINGS.keys()):
        e = ENDINGS[key]
        np = e.narrative_pages
        if len(np) != 2:
            print(f"FAIL {key}: narrative_pages 須為 2 段，實際 {len(np)}")
            ok = False
            continue
        for i, page in enumerate(np):
            n_lines = len(wrap_cjk(intro, page, max_w_body))
            if n_lines < _MIN_NARRATIVE_LINES or n_lines > _MAX_NARRATIVE_LINES:
                print(
                    f"FAIL {key}: page {i + 1} narrative lines={n_lines} "
                    f"(need {_MIN_NARRATIVE_LINES}-{_MAX_NARRATIVE_LINES})"
                )
                ok = False
        q_lines = len(wrap_cjk(small, e.quote, max_w_quote))
        if q_lines > 1:
            print(f"FAIL {key}: quote 在 CG 底欄為 {q_lines} 行（上限 1）")
            ok = False
    if ok:
        print(
            "OK: all endings pass (2 narrative pages, 5-6 lines each; quote 1 line)"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
