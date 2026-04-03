"""
奇遇事件 UI 與畫廊繪製：導引、測驗、餘韻、奇遇 CG 全螢幕與網格。
"""

from __future__ import annotations

from pathlib import Path

import pygame

from whim_events import (
    COMPANION_EVENT_CG_STEM_SUFFIX,
    WHIM_ENCOUNTERS,
    WHIM_CG_BASENAME_ORDER,
    WhimEncounter,
)
from encounter_draw import draw_gallery_cell_locked_cross
from whim_questions import WhimQuestion


_ORIG_W = 320
_ORIG_H = 180

# 畫廊縮圖格外觀：與 ``main.draw_ending_gallery_screen`` 通關圖片格一致。
_GALLERY_CELL_BORDER_RGB: tuple[int, int, int] = (90, 100, 120)
_GALLERY_CELL_BORDER_W_LOGICAL: int = 2
_GALLERY_SEL_OUTLINE_RGB: tuple[int, int, int] = (255, 255, 255)
_GALLERY_SEL_OUTLINE_W_LOGICAL: int = 3
_GALLERY_SEL_INFLATE_LOGICAL_X: int = 3
_GALLERY_SEL_INFLATE_LOGICAL_Y: int = 3


def _scale_x(canvas_w: int, x: int) -> int:
    """以 320x180 邏輯座標縮放至實際畫布寬。"""
    return x * canvas_w // _ORIG_W


def _scale_y(canvas_h: int, y: int) -> int:
    """以 320x180 邏輯座標縮放至實際畫布高。"""
    return y * canvas_h // _ORIG_H


def _wrap_cjk(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """依字型寬度換行中文／混排文字。"""
    if max_width <= 0:
        return [text] if text else [""]
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines if lines else [""]


# --- 奇遇事件版面：導引兩段正文總行數、測驗開場／題幹／選項行數（見 ``draw_whim_event_screen``）---
_WHIM_BODY_LINES_MIN: int = 9
_WHIM_BODY_LINES_MAX: int = 11
_WHIM_QUIZ_OPENING_LINES: int = 4
_WHIM_QUIZ_STEM_LINES_MIN: int = 1
_WHIM_QUIZ_STEM_LINES_MAX: int = 2
# 測驗階段選擇題題幹（含【】）字色：淺藍，在深底上與開場灰白、選項區分。
_WHIM_QUIZ_STEM_RGB: tuple[int, int, int] = (165, 205, 255)


def _whim_fit_one_line_cjk(font: pygame.font.Font, text: str, max_width: int) -> str:
    """
    強制單行顯示：先依寬度換行再只取首行；仍超寬則截斷並加「…」。

    Args:
        font: 量測用字型。
        text: 原文。
        max_width: 單行最大像素寬。

    Returns:
        寬度不超過 ``max_width`` 的單行字串。
    """
    if max_width <= 0:
        return ""
    lines = _wrap_cjk(font, text, max_width)
    if not lines or not lines[0]:
        return ""
    first = lines[0]
    if len(lines) == 1 and font.size(first)[0] <= max_width:
        return first
    ell = "…"
    if font.size(first + ell)[0] <= max_width:
        return first + ell
    while len(first) > 0 and font.size(first + ell)[0] > max_width:
        first = first[:-1]
    return first + ell if first else ell


def _whim_clamp_line_count(lines: list[str], min_n: int, max_n: int) -> list[str]:
    """
    將換行結果截斷或底部補空行，使行數落在 ``[min_n, max_n]``（含）。

    Args:
        lines: 換行後之各行。
        min_n: 最少行數。
        max_n: 最多行數。

    Returns:
        長度介於 ``min_n``～``max_n`` 的列表。
    """
    out = lines[:max_n]
    if len(out) < min_n:
        out = out + [""] * (min_n - len(out))
    return out


def _whim_body_two_paragraph_lines(
    font: pygame.font.Font,
    para1: str,
    para2: str,
    max_w: int,
    min_total: int = _WHIM_BODY_LINES_MIN,
    max_total: int = _WHIM_BODY_LINES_MAX,
) -> tuple[list[str], list[str]]:
    """
    導引兩段正文：換行後總行數固定於 ``min_total``～``max_total``（超出自第二段末截、不足則第二段底補空行）。

    Args:
        font: 導引正文用字型。
        para1: 第一段原文。
        para2: 第二段原文。
        max_w: 換行寬。
        min_total: 兩段合計最少行數。
        max_total: 兩段合計最多行數。

    Returns:
        ``(第一段各行, 第二段各行)``。
    """
    a = _wrap_cjk(font, para1, max_w)
    b = _wrap_cjk(font, para2, max_w)
    while len(a) + len(b) > max_total:
        if len(b) > 0:
            b.pop()
        elif len(a) > 0:
            a.pop()
        else:
            break
    while len(a) + len(b) < min_total:
        b.append("")
    return a, b


# 與 ``encounter_draw``／``main`` 餘韻頁：數值列色、數值與頁尾間距（邏輯格 → 依畫布換算）
_AFTERMATH_GAP_BEFORE_STAT_LY = 10
_AFTERMATH_GAP_BEFORE_HINT_LY = 6
_WHIM_AFTERMATH_STAT_COLOR: tuple[int, int, int] = (175, 212, 252)

# 測驗：選項區與底部操作提示之間的一行串場（全遊戲共用）
_WHIM_QUIZ_OPTIONS_BRIDGE_ZH: str = "選擇一個你覺得最正確的選項……"
# 題幹前後全形括號，與開場／對話敘事區隔（視為「問題」區塊）
_WHIM_QUIZ_STEM_PREFIX: str = "【"
_WHIM_QUIZ_STEM_SUFFIX: str = "】"


def _aftermath_para_gap_px(canvas_h: int) -> int:
    """
    餘韻段落間垂直距離（與 ``main._aftermath_para_gap_px`` 同公式）。

    Args:
        canvas_h: 畫布高度。

    Returns:
        像素。
    """
    return 3 * canvas_h // _ORIG_H


def _footer_top_for_nav_raw_ch(
    canvas_h: int,
    small_font: pygame.font.Font,
    max_w: int,
    nav_raw: str,
) -> int:
    """
    依頁尾字串計算操作列頂端 y（與 ``main._aftermath_footer_top_for_nav_raw`` 同邏輯）。

    Args:
        canvas_h: 畫布高度。
        small_font: 頁尾字型。
        max_w: 換行寬。
        nav_raw: 本頁操作說明全文。

    Returns:
        頁尾區塊頂端 y。
    """
    nav_lines = _wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    bottom_pad = 8 * canvas_h // _ORIG_H
    return canvas_h - bottom_pad - nav_content_h


def _conservative_footer_top_ch(
    canvas_h: int,
    small_font: pygame.font.Font,
    max_w: int,
) -> int:
    """
    取「下一頁／返回養成」中較吃高度之頁尾頂 y（與 ``main._aftermath_conservative_footer_top_px`` 同策略）。

    Args:
        canvas_h: 畫布高度。
        small_font: 頁尾字型。
        max_w: 換行寬。

    Returns:
        較小之 ``footer_top``。
    """
    a = _footer_top_for_nav_raw_ch(
        canvas_h, small_font, max_w, "【Enter】下一頁"
    )
    b = _footer_top_for_nav_raw_ch(
        canvas_h, small_font, max_w, "【Enter】返回養成"
    )
    return min(a, b)


def _aftermath_stat_lines_height_ch(
    intro_font: pygame.font.Font,
    max_w: int,
    full_stat_line: str,
) -> int:
    """
    「數值變化」換行後總高度（與 ``main._aftermath_stat_lines_height_px`` 同邏輯）。

    Args:
        intro_font: 與餘韻正文同級字型。
        max_w: 換行寬。
        full_stat_line: 含前綴之全文。

    Returns:
        像素高度；空白則 0。
    """
    if not full_stat_line.strip():
        return 0
    lines = _wrap_cjk(intro_font, full_stat_line, max_w)
    fh = intro_font.get_height() + 2
    return len(lines) * fh


def _aftermath_narrative_bottom_y_page0_with_bottom_stat_ch(
    canvas_h: int,
    small_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    max_w: int,
    stat_full_line: str,
) -> int:
    """
    第一頁正文下緣 y（不含），已預留底部「數值變化」與頁尾（比照突發餘韻）。

    Args:
        canvas_h: 畫布高度。
        small_font: 頁尾字型。
        intro_font: 餘韻／數值列字型。
        max_w: 換行寬。
        stat_full_line: 數值變化全文。

    Returns:
        敘事最底允許之 y。
    """
    footer_top = _conservative_footer_top_ch(canvas_h, small_font, max_w)
    if not stat_full_line.strip():
        return footer_top - 8 * canvas_h // _ORIG_H
    gap_stat_above_nav = _AFTERMATH_GAP_BEFORE_HINT_LY * canvas_h // _ORIG_H
    gap_narrative_above_stat = _AFTERMATH_GAP_BEFORE_STAT_LY * canvas_h // _ORIG_H
    sh = _aftermath_stat_lines_height_ch(intro_font, max_w, stat_full_line)
    return footer_top - gap_stat_above_nav - sh - gap_narrative_above_stat


def _whim_left_rect_2x3(
    mx: int,
    top_y: int,
    hint_y: int,
    cw: int,
    ch: int,
) -> tuple[pygame.Rect, int]:
    """
    左欄奇遇 CG 區：寬高比固定 **2:3**（直立），不超過可用高度與欄寬上限。

    Args:
        mx: 左內距。
        top_y: 區塊頂端 y。
        hint_y: 頁尾提示頂端 y（CG 區不得侵入）。
        cw: 畫布寬。
        ch: 畫布高。

    Returns:
        ``(left_rect, panel_w)``；``panel_w`` 供右欄文字起算。
    """
    gap = _scale_y(ch, 4)
    avail_h = max(1, hint_y - top_y - gap)
    w_cap = _scale_x(cw, 100)
    h_if_full_w = (w_cap * 3 + 1) // 2
    if h_if_full_w <= avail_h:
        w, h = w_cap, h_if_full_w
    else:
        h = avail_h
        w = max(1, (h * 2 + 2) // 3)
    left_rect = pygame.Rect(mx, top_y, w, h)
    return left_rect, w


def _whim_unified_left_hint_y(ch: int, small_font: pygame.font.Font) -> int:
    """
    奇遇導引／測驗／餘韻三階段**共用**之頁尾提示頂端 y，用於計算左欄 2:3 CG 框。

    若各階改用不同底緣（例如餘韻另算 ``footer_top``），``avail_h`` 會變，CG 寬高跟著變動；
    此處與導引、測驗頁底欄一致，使三張畫面左圖尺寸固定。

    Args:
        ch: 畫布高度。
        small_font: 頁尾字型。

    Returns:
        頁尾提示第一行頂端 y。
    """
    bottom_pad = _scale_y(ch, 14)
    return ch - bottom_pad - small_font.get_height()


_WHIM_CG_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")


def _resolve_companion_base_cg_path(asset_root: Path, cg_basename: str) -> Path | None:
    """
    解析夥伴／奇遇**主圖**路徑（不含 ``_friend`` 小圖；僅 ``assets/cg/companions/``）。

    先嘗試現行 slug（如 ``stoltz``），再嘗試舊版 ``whim_*`` 主檔名。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 檔名主鍵（無副檔名）。

    Returns:
        存在之檔案路徑；否則 None。
    """
    d = asset_root / "assets" / "cg" / "companions"
    base = (cg_basename or "").strip()
    if not base:
        return None
    stems = (base, f"whim_{base}") if not base.startswith("whim_") else (base,)
    for stem in stems:
        for suf in _WHIM_CG_SUFFIXES:
            p = d / f"{stem}{suf}"
            if p.is_file():
                return p
    return None


def _resolve_whim_event_cg_path(asset_root: Path, cg_basename: str) -> Path | None:
    """
    解析**奇遇流程左欄**用圖：優先 ``{{slug}}{_friend}``，再回退主圖（見 ``_resolve_companion_base_cg_path``）。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 與 ``WhimEncounter.cg_basename`` 相同之 slug。

    Returns:
        存在之檔案路徑；否則 None。
    """
    d = asset_root / "assets" / "cg" / "companions"
    base = (cg_basename or "").strip()
    if not base:
        return None
    suf = COMPANION_EVENT_CG_STEM_SUFFIX
    stems: list[str] = []
    if not base.startswith("whim_"):
        stems.extend(
            [
                f"{base}{suf}",
                f"whim_{base}{suf}",
                base,
                f"whim_{base}",
            ]
        )
    else:
        stems.extend([f"{base}{suf}", base])
    for stem in stems:
        for ext in _WHIM_CG_SUFFIXES:
            p = d / f"{stem}{ext}"
            if p.is_file():
                return p
    return None


def _load_whim_cg_surface(
    asset_root: Path,
    cg_basename: str,
    *,
    tw: int,
    th: int,
) -> pygame.Surface | None:
    """載入並等比縮放奇遇 CG（contain）；缺檔回傳 None。"""
    resolved = _resolve_companion_base_cg_path(asset_root, cg_basename)
    if resolved is None:
        return None
    try:
        raw = pygame.image.load(str(resolved)).convert_alpha()
    except (pygame.error, OSError):
        return None

    rw, rh = raw.get_width(), raw.get_height()
    if rw <= 0 or rh <= 0:
        return None
    scale = min(tw / rw, th / rh)
    if scale <= 0:
        return None
    nw = max(1, int(rw * scale))
    nh = max(1, int(rh * scale))
    return pygame.transform.smoothscale(raw, (nw, nh))


def _resolve_companion_cg_path(asset_root: Path, cg_basename: str) -> Path | None:
    """
    解析「同行的夥伴」畫廊／全螢幕用**主圖**路徑（不含 ``_friend``；僅 ``assets/cg/companions/``）。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 檔名主鍵（無副檔名）。

    Returns:
        存在之檔案路徑；否則 None。
    """
    return _resolve_companion_base_cg_path(asset_root, cg_basename)


def _load_companion_cg_surface(
    asset_root: Path,
    cg_basename: str,
    *,
    tw: int,
    th: int,
) -> pygame.Surface | None:
    """
    載入夥伴畫廊 CG（contain）；缺檔回傳 None。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 主檔名鍵。
        tw: 目標最大寬。
        th: 目標最大高。

    Returns:
        縮放後表面；失敗則 None。
    """
    resolved = _resolve_companion_cg_path(asset_root, cg_basename)
    if resolved is None:
        return None
    try:
        raw = pygame.image.load(str(resolved)).convert_alpha()
    except (pygame.error, OSError):
        return None

    rw, rh = raw.get_width(), raw.get_height()
    if rw <= 0 or rh <= 0:
        return None
    scale = min(tw / rw, th / rh)
    if scale <= 0:
        return None
    nw = max(1, int(rw * scale))
    nh = max(1, int(rh * scale))
    return pygame.transform.smoothscale(raw, (nw, nh))


def load_companion_gallery_cg_fill(
    asset_root: Path,
    cg_basename: str,
    tw: int,
    th: int,
) -> pygame.Surface | None:
    """
    畫廊全螢幕用夥伴 CG：與結局頁相同的 **cover** 填滿矩形（置中裁切、無留白）。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 主檔名鍵。
        tw: 目標寬。
        th: 目標高。

    Returns:
        恰好 ``tw×th`` 之圖；缺檔或失敗則 None。
    """
    tw = max(1, tw)
    th = max(1, th)
    resolved = _resolve_companion_cg_path(asset_root, cg_basename)
    if resolved is None:
        return None
    try:
        raw = pygame.image.load(str(resolved)).convert_alpha()
    except (pygame.error, OSError):
        return None
    rw, rh = raw.get_width(), raw.get_height()
    if rw <= 0 or rh <= 0:
        return None
    scale = max(tw / rw, th / rh)
    nw = max(1, int(rw * scale))
    nh = max(1, int(rh * scale))
    scaled = pygame.transform.smoothscale(raw, (nw, nh))
    out = pygame.Surface((tw, th), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))
    bx = (tw - nw) // 2
    by = (th - nh) // 2
    out.blit(scaled, (bx, by))
    return out


def draw_companion_gallery_placeholder(
    canvas: pygame.Surface,
    rect: pygame.Rect,
    title_zh: str,
) -> None:
    """
    夥伴 CG 缺檔時的佔位（與奇遇小卡風格一致）。

    Args:
        canvas: 目標畫布。
        rect: 繪製區域。
        title_zh: 標題文字。
    """
    _draw_placeholder_mini(canvas, rect, title=title_zh, color=(70, 155, 140))


def _load_whim_cg_surface_cover(
    asset_root: Path,
    cg_basename: str,
    box_w: int,
    box_h: int,
) -> pygame.Surface | None:
    """
    載入奇遇 CG 並以 **cover** 填滿長方形（等比放大後置中裁切，類遭遇戰立繪區）。

    Args:
        asset_root: 專案根目錄。
        cg_basename: 檔名主鍵。
        box_w: 目標寬。
        box_h: 目標高。

    Returns:
        恰好 ``box_w×box_h`` 之圖；缺檔或失敗則 None。
    """
    if box_w <= 0 or box_h <= 0:
        return None
    resolved = _resolve_whim_event_cg_path(asset_root, cg_basename)
    if resolved is None:
        return None
    try:
        raw = pygame.image.load(str(resolved)).convert_alpha()
    except (pygame.error, OSError):
        return None
    w, h = raw.get_width(), raw.get_height()
    if w <= 0 or h <= 0:
        return None
    scale = max(box_w / w, box_h / h)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    scaled = pygame.transform.smoothscale(raw, (nw, nh))
    x0 = max(0, (nw - box_w) // 2)
    y0 = max(0, (nh - box_h) // 2)
    clip = pygame.Rect(x0, y0, min(box_w, nw), min(box_h, nh))
    out = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))
    out.blit(scaled, (0, 0), clip)
    return out


def _draw_whim_left_cg_cover(
    canvas: pygame.Surface,
    asset_root: Path,
    encounter: WhimEncounter,
    left_rect: pygame.Rect,
) -> None:
    """
    於左側長方形繪製奇遇人物 CG（cover 裁切）；缺檔則占位。

    Args:
        canvas: 畫布。
        asset_root: 資源根。
        encounter: 當前奇遇。
        left_rect: 左欄矩形。
    """
    cov = _load_whim_cg_surface_cover(
        asset_root, encounter.cg_basename, left_rect.w, left_rect.h
    )
    if cov is not None:
        canvas.blit(cov, (left_rect.x, left_rect.y))
    else:
        _draw_placeholder_mini(
            canvas, left_rect, title=encounter.display_name, color=(55, 95, 140)
        )
    pygame.draw.rect(
        canvas,
        (90, 120, 175),
        left_rect,
        width=max(1, left_rect.width // 160),
        border_radius=max(2, min(left_rect.w, left_rect.h) // 24),
    )


def _draw_placeholder_mini(
    canvas: pygame.Surface,
    rect: pygame.Rect,
    *,
    title: str,
    color: tuple[int, int, int] = (70, 155, 190),
) -> None:
    """缺檔占位：以底色＋字串做簡單表示。"""
    canvas.fill((0, 0, 0), rect)
    pygame.draw.rect(canvas, color, rect, width=max(1, rect.width // 40))
    pygame.draw.rect(canvas, (25, 25, 40), rect, width=1)
    initials = "".join([c for c in title if c.strip()])[:2]
    initials = initials if initials else "？"
    font = pygame.font.SysFont("microsoftyahei", max(12, rect.width // 9), bold=True)
    surf = font.render(initials, True, (220, 245, 255))
    canvas.blit(
        surf,
        (
            rect.x + (rect.width - surf.get_width()) // 2,
            rect.y + (rect.height - surf.get_height()) // 2,
        ),
    )


_WHIM_BY_CG_BASENAME: dict[str, WhimEncounter] = {w.cg_basename: w for w in WHIM_ENCOUNTERS}


def draw_whim_event_screen(
    canvas: pygame.Surface,
    *,
    title_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    font: pygame.font.Font,
    tick: int,
    phase: int,
    encounter: WhimEncounter,
    question: WhimQuestion,
    option_index: int,
    chosen_index: int | None,
    is_correct: bool | None,
    aftermath_page_index: int,
    stat_effect_full_line: str,
    asset_root: Path,
    protagonist_gender: str,
    option_perm: tuple[int, int, int] | None = None,
) -> None:
    """
    奇遇事件 UI 主畫面（含三階段）。

    Notes:
        版面約定（與 ``whim_events.WhimEncounter`` 文案一致）：

        - **導引（phase 0）**：標題／地點下之正文固定**兩段**（``preamble_para1``、``preamble_para2``），
          換行後**合計** ``9``～``11`` 行；超出截斷、不足則第二段底補空行。
        - **測驗（phase 1）**：``quiz_opening_zh`` 固定 **4** 行；題幹（含【】）**1～2** 行；
          三個選項各**單行**（過寬以「…」截斷）。

    Args:
        option_perm: 測驗畫面選項排列；``(a,b,c)`` 表示第 i 列顯示 ``question.options[perm[i]]``。
            ``None`` 時依題庫原始順序（0,1,2）。
    """
    cw, ch = canvas.get_size()
    mx = _scale_x(cw, 14)
    col_gap = _scale_x(cw, 8)
    top_y = _scale_y(ch, 10)
    bottom_pad = _scale_y(ch, 14)
    hint_y_unified = _whim_unified_left_hint_y(ch, small_font)

    if phase == 0:
        canvas.fill((20, 26, 34))
        left_rect, panel_w = _whim_left_rect_2x3(mx, top_y, hint_y_unified, cw, ch)
        _draw_whim_left_cg_cover(canvas, asset_root, encounter, left_rect)

        text_x = mx + panel_w + col_gap
        text_w = max(40, cw - text_x - mx)
        y = top_y
        text_limit_y = hint_y_unified - _scale_y(ch, 6)
        max_w = text_w
        hdr = f"奇遇事件　—　{encounter.display_name}"
        for hl in _wrap_cjk(title_font, hdr, max_w):
            if y + title_font.get_height() > text_limit_y:
                break
            canvas.blit(title_font.render(hl, True, (255, 230, 175)), (text_x, y))
            y += title_font.get_height() + 2

        y += _scale_y(ch, 2)
        loc_line = f"地點　{encounter.location_zh}"
        for ll in _wrap_cjk(intro_font, loc_line, max_w):
            if y + intro_font.get_height() > text_limit_y:
                break
            canvas.blit(intro_font.render(ll, True, (255, 214, 170)), (text_x, y))
            y += intro_font.get_height() + 2

        y += _scale_y(ch, 4)
        fh = intro_font.get_height()
        pgap = _aftermath_para_gap_px(ch)
        p1_lines, p2_lines = _whim_body_two_paragraph_lines(
            intro_font,
            encounter.preamble_para1,
            encounter.preamble_para2,
            max_w,
            min_total=_WHIM_BODY_LINES_MIN,
            max_total=_WHIM_BODY_LINES_MAX,
        )
        for line in p1_lines:
            if y + fh > text_limit_y:
                break
            canvas.blit(intro_font.render(line, True, (230, 232, 240)), (text_x, y))
            y += fh + 2
        y += pgap
        for line in p2_lines:
            if y + fh > text_limit_y:
                break
            canvas.blit(intro_font.render(line, True, (230, 232, 240)), (text_x, y))
            y += fh + 2

        hint = "Enter 開始測驗"
        hs = small_font.render(hint, True, (160, 170, 190))
        canvas.blit(hs, ((cw - hs.get_width()) // 2, ch - bottom_pad - hs.get_height()))
        return

    if phase == 1:
        canvas.fill((16, 20, 28))
        key_hint_y = hint_y_unified
        left_rect, panel_w = _whim_left_rect_2x3(mx, top_y, hint_y_unified, cw, ch)
        _draw_whim_left_cg_cover(canvas, asset_root, encounter, left_rect)

        text_x = mx + panel_w + col_gap
        text_w = max(40, cw - text_x - mx)
        quiz_font = intro_font
        fh = quiz_font.get_height()
        line_step = fh + 2
        pad_x = _scale_x(cw, 10)
        gap_y = _scale_y(ch, 1)
        n_opts = len(question.options)
        opt_w = text_w

        bridge_lines = _wrap_cjk(quiz_font, _WHIM_QUIZ_OPTIONS_BRIDGE_ZH, text_w)
        fh_bridge = fh + 2
        bridge_block_h = len(bridge_lines) * fh_bridge
        gap_bridge_to_keys = _scale_y(ch, 4)
        gap_opts_to_bridge = _scale_y(ch, 4)
        bridge_top_y = key_hint_y - gap_bridge_to_keys - bridge_block_h
        opt_bottom = bridge_top_y - gap_opts_to_bridge

        # 選項列：每格單行（過寬則「…」）；三列總高固定（略加高以利閱讀）
        min_cell_floor = max(_scale_y(ch, 10), fh + 12)
        grid_h_min = n_opts * min_cell_floor + max(0, n_opts - 1) * gap_y
        gap_before_opts = _scale_y(ch, 6)
        gap_mid_open_stem = _scale_y(ch, 4)
        content_limit_y = opt_bottom - gap_before_opts - grid_h_min

        opening_lines = _whim_clamp_line_count(
            _wrap_cjk(quiz_font, encounter.quiz_opening_zh, text_w),
            _WHIM_QUIZ_OPENING_LINES,
            _WHIM_QUIZ_OPENING_LINES,
        )
        stem_for_display = (
            f"{_WHIM_QUIZ_STEM_PREFIX}{question.stem}{_WHIM_QUIZ_STEM_SUFFIX}"
        )
        stem_lines = _whim_clamp_line_count(
            _wrap_cjk(quiz_font, stem_for_display, text_w),
            _WHIM_QUIZ_STEM_LINES_MIN,
            _WHIM_QUIZ_STEM_LINES_MAX,
        )

        line_y = top_y
        for hl in opening_lines:
            if line_y + fh > content_limit_y:
                break
            canvas.blit(
                quiz_font.render(hl, True, (245, 240, 230)), (text_x, line_y)
            )
            line_y += line_step
        line_y += gap_mid_open_stem
        for hl in stem_lines:
            if line_y + fh > content_limit_y:
                break
            canvas.blit(
                quiz_font.render(hl, True, _WHIM_QUIZ_STEM_RGB), (text_x, line_y)
            )
            line_y += line_step

        opt_top = line_y + gap_before_opts
        avail = opt_bottom - opt_top
        max_grid_h = n_opts * min_cell_floor + max(0, n_opts - 1) * gap_y
        min_cell = min_cell_floor
        if avail >= max_grid_h:
            opt_top += (avail - max_grid_h) // 2
        else:
            inner_h = avail - max(0, n_opts - 1) * gap_y
            min_cell = max(fh + 1, inner_h // n_opts) if inner_h > 0 else min_cell_floor

        fh_opt = quiz_font.get_height()
        perm = option_perm if option_perm is not None else (0, 1, 2)
        for i in range(n_opts):
            opt = question.options[perm[i]]
            rect = pygame.Rect(text_x, opt_top + i * (min_cell + gap_y), opt_w, min_cell)
            selected = i == option_index
            bg = (40, 46, 64) if selected else (24, 26, 38)
            pygame.draw.rect(canvas, bg, rect)
            pygame.draw.rect(
                canvas,
                (145, 185, 230) if selected else (70, 78, 96),
                rect,
                width=max(1, rect.width // 120),
            )
            label = f"{i + 1}. {opt}"
            one = _whim_fit_one_line_cjk(quiz_font, label, opt_w - pad_x)
            ty = rect.y + (rect.height - fh_opt) // 2
            canvas.blit(
                quiz_font.render(
                    one, True, (255, 240, 220) if selected else (210, 215, 228)
                ),
                (rect.x + _scale_x(cw, 5), ty + 1),
            )

        by = bridge_top_y
        bridge_col = (175, 182, 198)
        for bl in bridge_lines:
            canvas.blit(quiz_font.render(bl, True, bridge_col), (text_x, by))
            by += fh_bridge

        hint_raw = "【↑↓】選擇　【Enter】確認"
        hs = small_font.render(hint_raw, True, (150, 162, 178))
        canvas.blit(hs, ((cw - hs.get_width()) // 2, key_hint_y))
        return

    # phase == 2 aftermath（頁尾操作列：與突發／遭遇餘韻相同之 ``footer_top``、左對齊、``【Enter】返回養成``）
    canvas.fill((20, 26, 34))
    nav_raw_whim = "【Enter】返回養成"
    left_rect, panel_w = _whim_left_rect_2x3(mx, top_y, hint_y_unified, cw, ch)
    text_x = mx + panel_w + col_gap
    text_w = max(40, cw - text_x - mx)
    footer_top = _footer_top_for_nav_raw_ch(ch, small_font, text_w, nav_raw_whim)
    _draw_whim_left_cg_cover(canvas, asset_root, encounter, left_rect)
    para_limit_y = _aftermath_narrative_bottom_y_page0_with_bottom_stat_ch(
        ch, small_font, intro_font, text_w, stat_effect_full_line
    )
    fh = intro_font.get_height() + 2
    pgap = _aftermath_para_gap_px(ch)

    y = top_y
    hdr = "餘韻"
    for hl in _wrap_cjk(title_font, hdr, text_w):
        if y + title_font.get_height() > para_limit_y:
            break
        canvas.blit(title_font.render(hl, True, (255, 214, 170)), (text_x, y))
        y += title_font.get_height() + 2
    y += _scale_y(ch, 4)

    verdict = "你答對了。" if is_correct else "你答錯了。"
    p1 = (
        encounter.aftermath_correct_para1
        if is_correct
        else encounter.aftermath_wrong_para1
    )
    p2 = (
        encounter.aftermath_correct_para2
        if is_correct
        else encounter.aftermath_wrong_para2
    )

    for vl in _wrap_cjk(intro_font, verdict, text_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(vl, True, (230, 232, 240)), (text_x, y))
        y += fh
    y += pgap
    for line in _wrap_cjk(intro_font, p1, text_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(line, True, (230, 232, 240)), (text_x, y))
        y += fh
    y += pgap
    for line in _wrap_cjk(intro_font, p2, text_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(line, True, (230, 232, 240)), (text_x, y))
        y += fh

    if stat_effect_full_line.strip():
        gap_stat_above_nav = _AFTERMATH_GAP_BEFORE_HINT_LY * ch // _ORIG_H
        stat_lines = _wrap_cjk(intro_font, stat_effect_full_line, text_w)
        stat_block_h = len(stat_lines) * fh
        sy = footer_top - gap_stat_above_nav - stat_block_h
        for i, sl in enumerate(stat_lines):
            canvas.blit(
                intro_font.render(sl, True, _WHIM_AFTERMATH_STAT_COLOR),
                (text_x, sy + i * fh),
            )

    fy = footer_top
    nav_lines = _wrap_cjk(small_font, nav_raw_whim, text_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    for i, fl in enumerate(nav_lines):
        canvas.blit(
            small_font.render(fl, True, (140, 150, 170)),
            (text_x, fy),
        )
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def draw_whim_gallery_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    gallery_page_index: int,
    gallery_slot_index: int,
    whim_unlocked_keys: set[str],
    section_header: str,
    asset_root: Path,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    奇遇人物畫廊網格：每格占位圖或縮圖；未解鎖仍顯示名稱但不顯示 CG。
    """
    cw, ch = canvas.get_size()
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(cw, 16)
    per_page = 6
    total = len(WHIM_CG_BASENAME_ORDER)
    pc = max(1, (total + per_page - 1) // per_page)
    pi = max(0, min(gallery_page_index, pc - 1))
    start = pi * per_page
    keys_page = list(WHIM_CG_BASENAME_ORDER[start : start + per_page])
    n_sp = len(keys_page)

    hdr = f"{section_header}　（{pi + 1}／{pc}）"
    y = _scale_y(ch, 8)
    for line in _wrap_cjk(menu_font, hdr, cw - 2 * mx):
        canvas.blit(menu_font.render(line, True, (255, 230, 190)), (mx, y))
        y += menu_font.get_height() + 2

    hint_raw = "方向鍵選擇　換頁　Enter 看全螢幕　Esc 返回"
    gallery_hint_lines = _wrap_cjk(small_font, hint_raw, cw - 2 * mx)
    lh_label = small_font.get_height()
    gallery_hint_block_h = len(gallery_hint_lines) * lh_label + max(0, len(gallery_hint_lines) - 1) * 2
    grid_bottom = ch - _scale_y(ch, 8) - gallery_hint_block_h

    n_cols, n_rows = 3, 2
    gap_x = _scale_x(cw, 6)
    gap_y = _scale_y(ch, 4)
    avail_h = max(_scale_y(ch, 72), grid_bottom - y)
    row_inner_h = (avail_h - (n_rows - 1) * gap_y) // n_rows
    name_gap = _scale_y(ch, 2)
    label_h = lh_label * 2 + 2
    box_h = max(1, row_inner_h - name_gap - label_h)
    cell_w = (cw - 2 * mx - (n_cols - 1) * gap_x) // n_cols
    grid_total_w = n_cols * cell_w + (n_cols - 1) * gap_x
    x0 = (cw - grid_total_w) // 2
    row_stride_y = row_inner_h + gap_y

    slot_box_rects: list[pygame.Rect] = []

    for idx, cg_key in enumerate(keys_page):
        row = idx // n_cols
        col = idx % n_cols
        cx = x0 + col * (cell_w + gap_x)
        cy = y + row * row_stride_y
        box_rect = pygame.Rect(cx, cy, cell_w, box_h)
        unlocked = cg_key in whim_unlocked_keys
        pygame.draw.rect(canvas, (28, 32, 44), box_rect)
        cg_surface = None
        if unlocked:
            cg_surface = _load_whim_cg_surface(
                asset_root, cg_key, tw=box_rect.w - 6, th=box_rect.h - 6
            )
        if cg_surface is not None:
            canvas.blit(
                cg_surface,
                (
                    box_rect.x + (box_rect.w - cg_surface.get_width()) // 2,
                    box_rect.y + (box_rect.h - cg_surface.get_height()) // 2,
                ),
            )
        elif unlocked:
            # 已解鎖但缺檔：維持迷你占位以利辨識
            name = _WHIM_BY_CG_BASENAME.get(cg_key).display_name if cg_key in _WHIM_BY_CG_BASENAME else cg_key
            _draw_placeholder_mini(
                canvas,
                box_rect,
                title=name,
                color=(70, 155, 190),
            )
        else:
            draw_gallery_cell_locked_cross(canvas, box_rect)

        border_w = max(1, _scale_x(cw, _GALLERY_CELL_BORDER_W_LOGICAL))
        pygame.draw.rect(canvas, _GALLERY_CELL_BORDER_RGB, box_rect, width=border_w)
        slot_box_rects.append(box_rect)

        # 名稱
        name = _WHIM_BY_CG_BASENAME.get(cg_key).display_name if cg_key in _WHIM_BY_CG_BASENAME else cg_key
        name_col = (210, 218, 232) if unlocked else (175, 184, 202)
        ly = box_rect.bottom + name_gap
        for li, lab_line in enumerate(_wrap_cjk(small_font, name, cell_w)):
            if li >= 2:
                break
            canvas.blit(
                small_font.render(lab_line, True, name_col),
                (cx, ly + li * (lh_label + 1)),
            )

    if n_sp > 0:
        sel_i = max(0, min(gallery_slot_index, n_sp - 1))
        if 0 <= sel_i < len(slot_box_rects):
            sel_box = slot_box_rects[sel_i]
            ow = max(2, _scale_x(cw, _GALLERY_SEL_OUTLINE_W_LOGICAL))
            pygame.draw.rect(
                canvas,
                _GALLERY_SEL_OUTLINE_RGB,
                sel_box.inflate(
                    _scale_x(cw, _GALLERY_SEL_INFLATE_LOGICAL_X),
                    _scale_y(ch, _GALLERY_SEL_INFLATE_LOGICAL_Y),
                ),
                width=ow,
            )

    hy = ch - _scale_y(ch, 8) - gallery_hint_block_h
    for i, hl in enumerate(gallery_hint_lines):
        hs = small_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, ((cw - hs.get_width()) // 2, hy))
        hy += lh_label + (2 if i + 1 < len(gallery_hint_lines) else 0)


def draw_whim_cg_fullscreen(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    cg_key: str,
    asset_root: Path,
    tick: int,
) -> None:
    """
    奇遇 CG 全螢幕檢視；缺檔時放大占位。
    """
    cw, ch = canvas.get_size()
    canvas.fill((12, 14, 20))

    name = _WHIM_BY_CG_BASENAME.get(cg_key).display_name if cg_key in _WHIM_BY_CG_BASENAME else cg_key
    title = f"奇遇人物　—　{name}"
    y = _scale_y(ch, 14)
    for hl in _wrap_cjk(small_font, title, cw - 2 * _scale_x(cw, 20)):
        canvas.blit(small_font.render(hl, True, (255, 230, 190)), (_scale_x(cw, 20), y))
        y += small_font.get_height() + 2

    # CG 區（留底欄）
    footer_h = _scale_y(ch, 64)
    img_rect = pygame.Rect(
        _scale_x(cw, 20),
        y + _scale_y(ch, 6),
        cw - 2 * _scale_x(cw, 20),
        ch - y - footer_h - _scale_y(ch, 10),
    )

    tw, th = img_rect.w, img_rect.h
    cg_surface = _load_whim_cg_surface(asset_root, cg_key, tw=tw, th=th)
    if cg_surface is not None:
        canvas.blit(
            cg_surface,
            (
                img_rect.x + (img_rect.w - cg_surface.get_width()) // 2,
                img_rect.y + (img_rect.h - cg_surface.get_height()) // 2,
            ),
        )
    else:
        _draw_placeholder_mini(canvas, img_rect, title=name, color=(70, 155, 190))

    hint = "Enter 返回畫廊"
    hs = small_font.render(hint, True, (140, 150, 170))
    canvas.blit(hs, ((cw - hs.get_width()) // 2, ch - _scale_y(ch, 14) - hs.get_height()))


def draw_companion_gallery_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    gallery_page_index: int,
    gallery_slot_index: int,
    companion_unlocked_keys: set[str],
    companion_key_order: tuple[str, ...],
    section_header: str,
    asset_root: Path,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    「同行的夥伴」畫廊網格：與奇遇人物網格相同邏輯；圖檔優先讀取 companions 資料夾。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題字級。
        small_font: 標籤與提示。
        gallery_page_index: 目前頁（0-based）。
        gallery_slot_index: 六格內游標。
        companion_unlocked_keys: 已解鎖主檔名鍵集合。
        companion_key_order: 欄位順序（通常為奇遇表順序＋僅見於 ``companions/`` 之檔名）。
        section_header: 區塊標題列。
        asset_root: 專案根目錄。
        star_xy: 背景星點座標。
        tick: 影格。
    """
    cw, ch = canvas.get_size()
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(cw, 16)
    per_page = 6
    total = len(companion_key_order)
    pc = max(1, (total + per_page - 1) // per_page)
    pi = max(0, min(gallery_page_index, pc - 1))
    start = pi * per_page
    keys_page = list(companion_key_order[start : start + per_page])
    n_sp = len(keys_page)

    hdr = f"{section_header}　（{pi + 1}／{pc}）"
    y = _scale_y(ch, 8)
    for line in _wrap_cjk(menu_font, hdr, cw - 2 * mx):
        canvas.blit(menu_font.render(line, True, (255, 230, 190)), (mx, y))
        y += menu_font.get_height() + 2

    hint_raw = "方向鍵選擇　換頁　Enter 看全螢幕　Esc 返回"
    gallery_hint_lines = _wrap_cjk(small_font, hint_raw, cw - 2 * mx)
    lh_label = small_font.get_height()
    gallery_hint_block_h = len(gallery_hint_lines) * lh_label + max(0, len(gallery_hint_lines) - 1) * 2
    grid_bottom = ch - _scale_y(ch, 8) - gallery_hint_block_h

    n_cols, n_rows = 3, 2
    gap_x = _scale_x(cw, 6)
    gap_y = _scale_y(ch, 4)
    avail_h = max(_scale_y(ch, 72), grid_bottom - y)
    row_inner_h = (avail_h - (n_rows - 1) * gap_y) // n_rows
    name_gap = _scale_y(ch, 2)
    label_h = lh_label * 2 + 2
    box_h = max(1, row_inner_h - name_gap - label_h)
    cell_w = (cw - 2 * mx - (n_cols - 1) * gap_x) // n_cols
    grid_total_w = n_cols * cell_w + (n_cols - 1) * gap_x
    x0 = (cw - grid_total_w) // 2
    row_stride_y = row_inner_h + gap_y

    slot_box_rects: list[pygame.Rect] = []

    for idx, cg_key in enumerate(keys_page):
        row = idx // n_cols
        col = idx % n_cols
        cx = x0 + col * (cell_w + gap_x)
        cy = y + row * row_stride_y
        box_rect = pygame.Rect(cx, cy, cell_w, box_h)
        unlocked = cg_key in companion_unlocked_keys
        pygame.draw.rect(canvas, (28, 32, 44), box_rect)
        cg_surface = None
        if unlocked:
            cg_surface = _load_companion_cg_surface(
                asset_root, cg_key, tw=box_rect.w - 6, th=box_rect.h - 6
            )
        if cg_surface is not None:
            canvas.blit(
                cg_surface,
                (
                    box_rect.x + (box_rect.w - cg_surface.get_width()) // 2,
                    box_rect.y + (box_rect.h - cg_surface.get_height()) // 2,
                ),
            )
        elif unlocked:
            name = (
                _WHIM_BY_CG_BASENAME.get(cg_key).display_name
                if cg_key in _WHIM_BY_CG_BASENAME
                else cg_key
            )
            _draw_placeholder_mini(
                canvas,
                box_rect,
                title=name,
                color=(70, 155, 140),
            )
        else:
            draw_gallery_cell_locked_cross(canvas, box_rect)

        border_w = max(1, _scale_x(cw, _GALLERY_CELL_BORDER_W_LOGICAL))
        pygame.draw.rect(canvas, _GALLERY_CELL_BORDER_RGB, box_rect, width=border_w)
        slot_box_rects.append(box_rect)

        name = (
            _WHIM_BY_CG_BASENAME.get(cg_key).display_name
            if cg_key in _WHIM_BY_CG_BASENAME
            else cg_key
        )
        name_col = (210, 218, 232) if unlocked else (175, 184, 202)
        ly = box_rect.bottom + name_gap
        for li, lab_line in enumerate(_wrap_cjk(small_font, name, cell_w)):
            if li >= 2:
                break
            lab_surf = small_font.render(lab_line, True, name_col)
            lx = cx + (cell_w - lab_surf.get_width()) // 2
            canvas.blit(lab_surf, (lx, ly + li * (lh_label + 1)))

    if n_sp > 0:
        sel_i = max(0, min(gallery_slot_index, n_sp - 1))
        if 0 <= sel_i < len(slot_box_rects):
            sel_box = slot_box_rects[sel_i]
            ow = max(2, _scale_x(cw, _GALLERY_SEL_OUTLINE_W_LOGICAL))
            pygame.draw.rect(
                canvas,
                _GALLERY_SEL_OUTLINE_RGB,
                sel_box.inflate(
                    _scale_x(cw, _GALLERY_SEL_INFLATE_LOGICAL_X),
                    _scale_y(ch, _GALLERY_SEL_INFLATE_LOGICAL_Y),
                ),
                width=ow,
            )

    hy = ch - _scale_y(ch, 8) - gallery_hint_block_h
    for i, hl in enumerate(gallery_hint_lines):
        hs = small_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, ((cw - hs.get_width()) // 2, hy))
        hy += lh_label + (2 if i + 1 < len(gallery_hint_lines) else 0)

