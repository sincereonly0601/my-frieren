"""
遭遇戰畫面：敵方 CG 缺檔時之程式占位、自動戰鬥播映、餘韻與畫廊格。
"""

from __future__ import annotations

# 自動播映：每隔多少邏輯幀前進一則戰報（60 FPS 時約 0.9 秒／則，可依手感再調）。
# 每則戰鬥日記影格前進一階所需遊戲 tick（60fps）；數值愈小播映愈快。
ENCOUNTER_BATTLE_TICKS_PER_STEP: int = 32

import math
import os
from pathlib import Path

import pygame

from encounter_defs import (
    ENCOUNTER_GALLERY_ORDER,
    EncounterEnemy,
    encounter_aftermath_two_paragraphs,
    encounter_battle_mode_title_zh,
    encounter_cg_battle_try_rel_paths,
    encounter_cg_rel_path,
    encounter_cg_try_ids,
    encounter_protagonist_pronoun_adjust_zh,
    get_enemy_by_id,
)
from encounter_sim import BattleFrame, BattleOutcome
from game_state import GameState
from play_portrait import draw_heroine_portrait

_ORIG_W = 320
_ORIG_H = 180

# 畫廊縮圖格外觀：與 ``main.draw_ending_gallery_screen`` 通關圖片格一致。
_GALLERY_CELL_BORDER_RGB: tuple[int, int, int] = (90, 100, 120)
_GALLERY_CELL_BORDER_W_LOGICAL: int = 2
_GALLERY_SEL_OUTLINE_RGB: tuple[int, int, int] = (255, 255, 255)
_GALLERY_SEL_OUTLINE_W_LOGICAL: int = 3
_GALLERY_SEL_INFLATE_LOGICAL_X: int = 3
_GALLERY_SEL_INFLATE_LOGICAL_Y: int = 3


def draw_gallery_cell_locked_cross(
    canvas: pygame.Surface,
    box_rect: pygame.Rect,
) -> None:
    """
    畫廊縮圖格「尚未解鎖」：深灰底與兩道對角線（與本模組「遭遇的強敵」網格一致）。

    Args:
        canvas: 目標畫布。
        box_rect: 圖片區矩形（不含格下方名稱列）。
    """
    pygame.draw.rect(canvas, (24, 26, 34), box_rect)
    pad = max(2, min(4, box_rect.w // 16, box_rect.h // 16))
    rgb = (55, 58, 70)
    lw = 2 if min(box_rect.w, box_rect.h) >= 24 else 1
    pygame.draw.line(
        canvas,
        rgb,
        (box_rect.x + pad, box_rect.y + pad),
        (box_rect.right - pad, box_rect.bottom - pad),
        lw,
    )
    pygame.draw.line(
        canvas,
        rgb,
        (box_rect.right - pad, box_rect.y + pad),
        (box_rect.x + pad, box_rect.bottom - pad),
        lw,
    )


def _scale_x(canvas_w: int, x: int) -> int:
    """邏輯 x 由 320 基準換算至實際畫布寬。"""
    return x * canvas_w // _ORIG_W


def _scale_y(canvas_h: int, y: int) -> int:
    """邏輯 y 由 180 基準換算至實際畫布高。"""
    return y * canvas_h // _ORIG_H


def _wrap_cjk(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """依字型寬度將中文／混排文字換行。"""
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


# 遭遇戰側欄立繪／CG 外框之寬高比（寬:高 = 2:3，直立）。
_ENCOUNTER_BATTLE_PORTRAIT_AR_W: int = 2
_ENCOUNTER_BATTLE_PORTRAIT_AR_H: int = 3


def _encounter_battle_side_title_block_height(
    small_font: pygame.font.Font,
    text: str,
    max_w: int,
) -> int:
    """
    遭遇戰側欄「名稱」區塊總高度（含行距與進入立繪前 +2 像素間距）。

    Args:
        small_font: 側欄字型。
        text: 顯示名稱。
        max_w: 換行寬。

    Returns:
        像素高度。
    """
    lines = _wrap_cjk(small_font, text, max_w)
    h = 0
    for line in lines:
        if line:
            h += small_font.get_height() + 1
    return h + 2


def _encounter_battle_portrait_wh_aspect(
    max_w: int,
    avail_h: int,
    *,
    ar_w: int,
    ar_h: int,
    min_h: int,
) -> tuple[int, int]:
    """
    在最大寬、最大高內求整數 ``(w, h)``，使寬:高盡量接近 ``ar_w : ar_h``。

    先以完整寬度算高；若超高則以可用高度反推寬（皆上捨入至整數比）。

    Args:
        max_w: 允許之最大寬。
        avail_h: 立繪區最大可用高度。
        ar_w: 寬比例。
        ar_h: 高比例。
        min_h: 高度下限。

    Returns:
        ``(w, h)``。
    """
    max_w = max(1, max_w)
    avail_h = max(1, avail_h)
    h = (max_w * ar_h + ar_w - 1) // ar_w
    h = min(avail_h, max(min_h, h))
    w = min(max_w, max(1, (h * ar_w + ar_h - 1) // ar_h))
    h = min(avail_h, max(min_h, (w * ar_h + ar_w - 1) // ar_w))
    return (w, h)


# 與 ``main`` 重大／突發餘韻一致：正文區左右內距、數值列色、數值與頁尾間距（邏輯格 → 依畫布高換算）
_TEXT_PAD_X = 16
_AFTERMATH_GAP_BEFORE_STAT_LY = 10
_AFTERMATH_GAP_BEFORE_HINT_LY = 6
_AFTERMATH_STAT_COLOR = (175, 212, 252)


def _aftermath_para_gap_px_ch(canvas_h: int) -> int:
    """
    餘韻段落間垂直距離（與 ``main._aftermath_para_gap_px`` 同公式，改以實際畫布高換算）。

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
    依頁尾字串計算「【Enter】…」列頂端 y（與 ``main._aftermath_footer_top_for_nav_raw`` 同邏輯）。

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
    取「下一頁／返回養成」中較吃高度的頁尾頂 y，供正文預留（與 ``main._aftermath_conservative_footer_top_px`` 同策略）。

    Args:
        canvas_h: 畫布高度。
        small_font: 頁尾字型。
        max_w: 換行寬。

    Returns:
        較小之 footer_top。
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


def _narrative_bottom_y_page0_with_bottom_stat_ch(
    canvas_h: int,
    small_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    max_w: int,
    stat_full_line: str,
) -> int:
    """
    第一頁正文下緣 y（不含），已預留底部數值列與頁尾（與 ``main._aftermath_narrative_bottom_y_page0_with_bottom_stat`` 同策略）。

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


def _encounter_cg_surface(
    asset_root: Path,
    enemy_id: str,
    max_w: int,
    max_h: int,
) -> pygame.Surface | None:
    """
    載入**畫廊／全螢幕用**遭遇 CG（``<id>.jpg``）並等比例縮放至不超過 (max_w, max_h)。

    Args:
        asset_root: 專案根目錄。
        enemy_id: 敵人鍵。
        max_w: 最大寬。
        max_h: 最大高。

    Returns:
        成功則為縮放後圖；缺檔或失敗則 None。
    """
    p: Path | None = None
    for eid in encounter_cg_try_ids(enemy_id):
        rel = encounter_cg_rel_path(eid)
        cand = asset_root / rel.replace("/", os.sep)
        if cand.is_file():
            p = cand
            break
    if p is None:
        return None
    try:
        raw = pygame.image.load(os.fsdecode(p)).convert_alpha()
    except (pygame.error, OSError):
        return None
    w, h = raw.get_size()
    if w <= 0 or h <= 0:
        return None
    scale = min(max_w / w, max_h / h, 1.0)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return pygame.transform.smoothscale(raw, (nw, nh))


def encounter_gallery_cg_fill(
    asset_root: Path,
    enemy_id: str,
    tw: int,
    th: int,
) -> pygame.Surface | None:
    """
    畫廊全螢幕用遭遇 CG：與結局頁相同的 **cover** 填滿矩形（置中裁切、無留白）。

    Args:
        asset_root: 專案根目錄。
        enemy_id: 敵人鍵。
        tw: 目標寬。
        th: 目標高。

    Returns:
        恰好 ``tw×th`` 之圖；缺檔或失敗則 None。
    """
    tw = max(1, tw)
    th = max(1, th)
    p: Path | None = None
    for eid in encounter_cg_try_ids(enemy_id):
        rel = encounter_cg_rel_path(eid)
        cand = asset_root / rel.replace("/", os.sep)
        if cand.is_file():
            p = cand
            break
    if p is None:
        return None
    try:
        raw = pygame.image.load(os.fsdecode(p)).convert_alpha()
    except (pygame.error, OSError):
        return None
    rw, rh = raw.get_size()
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


def _encounter_cg_surface_cover(
    asset_root: Path,
    enemy_id: str,
    box_w: int,
    box_h: int,
) -> pygame.Surface | None:
    """
    載入**戰鬥用**遭遇 CG（優先 ``<id>_battle.jpg``）並以 **cover** 填滿
    ``(box_w, box_h)``（等比放大後置中裁切，無留白）；無戰鬥圖則退回畫廊用 ``<id>.jpg``。

    Args:
        asset_root: 專案根目錄。
        enemy_id: 敵人鍵。
        box_w: 目標寬。
        box_h: 目標高。

    Returns:
        恰好 ``box_w×box_h`` 之裁切圖；缺檔或失敗則 None。
    """
    if box_w <= 0 or box_h <= 0:
        return None
    p: Path | None = None
    for rel in encounter_cg_battle_try_rel_paths(enemy_id):
        cand = asset_root / rel.replace("/", os.sep)
        if cand.is_file():
            p = cand
            break
    if p is None:
        return None
    try:
        raw = pygame.image.load(os.fsdecode(p)).convert_alpha()
    except (pygame.error, OSError):
        return None
    w, h = raw.get_size()
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


def draw_encounter_aftermath_banner_art(
    surf: pygame.Surface,
    rect: pygame.Rect,
    win: bool,
    tick: int,
) -> None:
    """
    遭遇戰餘韻頂部圖示：僅依勝／敗繪製固定裝飾（不載入敵方 CG）；敗北為墓碑造型。

    Args:
        surf: 畫布。
        rect: 頂部橫幅區域。
        win: 是否戰勝。
        tick: 影格（微動效）。
    """
    sub = surf.subsurface(rect)
    w, h = rect.w, rect.h
    ph = int(6 + 5 * abs(((tick // 5) % 20) - 10) / 10)
    if win:
        for yy in range(h):
            t = yy / max(h - 1, 1)
            r = int(36 + 35 * t)
            g = int(72 + 55 * t)
            b = int(58 + 40 * t)
            pygame.draw.line(sub, (r, g, b), (0, yy), (w - 1, yy))
        cx, cy = w // 2, h // 2
        rw = max(8, w // 4)
        rh = max(10, h // 3)
        pygame.draw.ellipse(
            sub,
            (ph + 140, ph + 200, ph + 120),
            (cx - rw, cy - rh // 2, rw * 2, rh),
            width=max(2, w // 120),
        )
        pygame.draw.circle(sub, (255, 230, 140), (cx, cy - rh // 6), max(5, w // 28), 2)
        # 簡化「桂冠／V」暗示勝利
        pygame.draw.lines(
            sub,
            (230, 245, 200),
            False,
            [
                (cx - rw // 2, cy + rh // 6),
                (cx - rw // 6, cy - rh // 8),
                (cx, cy + rh // 10),
                (cx + rw // 6, cy - rh // 8),
                (cx + rw // 2, cy + rh // 6),
            ],
            width=max(2, w // 100),
        )
    else:
        for yy in range(h):
            t = yy / max(h - 1, 1)
            r = int(28 + 22 * t)
            g = int(30 + 20 * t)
            b = int(42 + 28 * t)
            pygame.draw.line(sub, (r, g, b), (0, yy), (w - 1, yy))
        cx, cy = w // 2, h // 2
        m = min(w, h)
        tw = max(10, m * 14 // 32)
        th = max(16, m * 20 // 32)
        cap_h = max(4, min(tw // 2, th // 3))
        by1 = cy + th // 2
        by0 = by1 - th
        bx0 = cx - tw // 2
        bw = max(1, w // 200)
        stone = (104, 102, 118)
        stone_hi = (128, 126, 142)
        stone_dark = (72, 74, 90)
        # 碑身（弧頂以下）
        pygame.draw.rect(sub, stone, (bx0, by0 + cap_h, tw, th - cap_h))
        pygame.draw.line(
            sub,
            stone_hi,
            (bx0 + max(2, tw // 8), by0 + cap_h + 2),
            (bx0 + max(2, tw // 8), by1 - 3),
            1,
        )
        # 圓頂（與碑身同色銜接）
        pygame.draw.ellipse(sub, stone, (bx0, by0, tw, cap_h * 2))
        rx = max(1, tw // 2 - bw)
        ry = max(1, cap_h - bw)
        ecy = by0 + cap_h
        steps = max(8, tw // 3)
        dome_pts: list[tuple[int, int]] = []
        for si in range(steps + 1):
            t = math.pi + math.pi * si / steps
            dome_pts.append(
                (int(cx + rx * math.cos(t)), int(ecy + ry * math.sin(t)))
            )
        if len(dome_pts) > 1:
            pygame.draw.lines(sub, stone_dark, False, dome_pts, max(1, bw))
        pygame.draw.line(
            sub,
            stone_dark,
            (bx0, by0 + cap_h),
            (bx0, by1),
            max(1, bw),
        )
        pygame.draw.line(
            sub,
            stone_dark,
            (bx0 + tw - 1, by0 + cap_h),
            (bx0 + tw - 1, by1),
            max(1, bw),
        )
        pygame.draw.line(
            sub,
            stone_dark,
            (bx0, by1),
            (bx0 + tw, by1),
            max(1, bw),
        )
        # 簡化十字刻痕
        mid_y = by0 + cap_h + (th - cap_h) * 45 // 100
        pygame.draw.line(
            sub,
            (78, 80, 96),
            (cx, mid_y - tw // 5),
            (cx, mid_y + tw // 5),
            max(1, bw),
        )
        pygame.draw.line(
            sub,
            (78, 80, 96),
            (cx - tw // 5, mid_y),
            (cx + tw // 5, mid_y),
            max(1, bw),
        )
        # 底座
        foot_w = tw + max(4, tw // 4)
        foot_h = max(2, th // 10)
        pygame.draw.rect(
            sub,
            (86, 88, 104),
            (cx - foot_w // 2, by1 - foot_h, foot_w, foot_h),
        )
        pygame.draw.line(
            sub,
            stone_dark,
            (cx - foot_w // 2, by1 - foot_h),
            (cx + foot_w // 2, by1 - foot_h),
            max(1, bw),
        )


def draw_encounter_enemy_placeholder(
    surf: pygame.Surface,
    rect: pygame.Rect,
    enemy: EncounterEnemy,
    tick: int,
) -> None:
    """
    在矩形內繪製敵方占位圖（系統圖示風：魔紋框＋劍形記號）。

    Args:
        surf: 目標畫布。
        rect: 繪製區域。
        enemy: 敵人資料（顯示簡名）。
        tick: 影格（微動效果）。
    """
    sub = surf.subsurface(rect)
    w, h = rect.w, rect.h
    pulse = int(18 + 10 * abs(((tick // 4) % 20) - 10) / 10)
    for yy in range(h):
        t = yy / max(h - 1, 1)
        c = (32 + int(20 * t), 24 + int(18 * t), 48 + int(25 * t))
        pygame.draw.line(sub, c, (0, yy), (w - 1, yy))
    br = max(2, w // 40)
    pygame.draw.rect(sub, (pulse + 60, 50, 90), (0, 0, w, h), width=br)
    cx, cy = w // 2, h // 2
    # 簡化「劍＋星」符號
    pygame.draw.line(sub, (200, 210, 240), (cx - w // 5, cy + h // 6), (cx + w // 5, cy - h // 6), max(2, w // 64))
    pygame.draw.polygon(
        sub,
        (220, 225, 245),
        [
            (cx + w // 5, cy - h // 6),
            (cx + w // 5 + w // 20, cy - h // 6 - h // 30),
            (cx + w // 5, cy - h // 6 - h // 15),
        ],
    )
    pygame.draw.circle(sub, (255, 230, 160), (cx - w // 8, cy - h // 5), max(3, w // 35), 1)


def _encounter_banner_text_color(banner_zh: str) -> tuple[int, int, int]:
    """
    依戰報列前綴決定中欄文字色（我方偏冷、敵方偏暖、開場／結束中性）。

    Args:
        banner_zh: 該影格戰報全文。

    Returns:
        RGB 元組。
    """
    if banner_zh.startswith("【我方】"):
        return (150, 205, 255)
    if banner_zh.startswith("【敵方】"):
        return (255, 175, 175)
    return (210, 215, 228)


def _encounter_battle_diary_rows(
    frames: tuple[BattleFrame, ...],
    up_to_index: int,
    small_font: pygame.font.Font,
    max_w: int,
) -> list[tuple[str, tuple[int, int, int]]]:
    """
    將第 0 影格起至 ``up_to_index``（含）之戰報排成日記列（含換行後多行、條目間空行）。

    Args:
        frames: 完整影格序列。
        up_to_index: 目前播映索引上限（含）。
        small_font: 換行量測用字型。
        max_w: 中欄文字寬。

    Returns:
        ``(行文字, RGB)`` 列表；空字串表示僅佔一行的間距。
    """
    rows: list[tuple[str, tuple[int, int, int]]] = []
    hi = max(0, min(up_to_index, len(frames) - 1))
    for idx in range(0, hi + 1):
        b = frames[idx].banner_zh
        col = _encounter_banner_text_color(b)
        for wl in _wrap_cjk(small_font, b, max_w):
            rows.append((wl, col))
        if idx < hi:
            rows.append(("", (0, 0, 0)))
    return rows


def _encounter_diary_row_step_px(
    text: str,
    line_h: int,
    entry_gap_px: int,
) -> int:
    """
    交鋒紀錄單列垂直佔高：正文為緊湊行高，條目間空列僅佔小間距。

    Args:
        text: 該列文字；空字串表示條目間分隔。
        line_h: 有文字列之高度（字高＋微間距）。
        entry_gap_px: 分隔列高度（像素）。

    Returns:
        此列應向下推進的像素。
    """
    return line_h if text else entry_gap_px


def draw_encounter_battle_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    state: GameState,
    enemy: EncounterEnemy,
    outcome: BattleOutcome,
    frame_index: int,
    asset_root: Path,
    tick: int,
) -> None:
    """
    遭遇戰自動播映（Enter 僅在播至**最末影格**後由 ``main`` 接受以進入餘韻，中途不按鍵快轉）：
    左上為「遭遇戰 - ○○戰」與**敵方中文名同一標題列**（不另起副標行）；
    **頂部橫向雙生命條**（即時血量；左條標籤為 ``state.heroine_name``）；
    左欄標題為**玩家姓名**（與血條一致；空則「……」）；左右立繪／CG 外框**同尺寸**，寬:高固定 **2:3**（直立），
    且圖緣距視窗左右邊界同為 ``mx``（左圖左對齊、右圖右對齊）；空間不足時等比例縮小但仍維持 2:3。
    左右欄其下為**固定能力值**（生命＝上限、戰鬥、防禦；不隨回合變，與頂條即時血量分開）；
    中欄為**戰鬥日記**：自開戰起逐筆向下累積至目前影格，不覆寫舊文；過長時向上捲動，最新留在可視區底部。

    Args:
        canvas: 邏輯畫布。
        font: 標題用。
        small_font: 字幕與數值。
        state: 遊戲狀態。
        enemy: 敵人。
        outcome: 模擬結果。
        frame_index: 目前影格索引。
        asset_root: 專案根（載入 CG）。
        tick: 影格。
    """
    cw, ch = canvas.get_size()
    canvas.fill((16, 18, 28))
    mx = _scale_x(cw, 12)
    fi = max(0, min(frame_index, len(outcome.frames) - 1))
    fr = outcome.frames[fi]

    ty = _scale_y(ch, 5)
    head_line = f"{encounter_battle_mode_title_zh(enemy.tier)}　{enemy.name_zh}"
    fh = font.get_height()
    max_head_w = cw - 2 * mx
    for hl in _wrap_cjk(font, head_line, max_head_w):
        canvas.blit(font.render(hl, True, (255, 210, 175)), (mx, ty))
        ty += fh + 2
    # 標題換行時末行與血條標籤易重疊；多留垂直空間並讓標籤離條頂稍遠。
    ty += _scale_y(ch, 4) + max(_scale_y(ch, 8), small_font.get_height() // 2 + 2)

    bar_y = ty
    bar_w = cw - 2 * mx
    bar_h = max(6, _scale_y(ch, 8))
    bar_label_above = small_font.get_height() + max(4, _scale_y(ch, 3))
    pygame.draw.rect(canvas, (40, 44, 58), (mx, bar_y, bar_w // 2 - 4, bar_h))
    pw = (
        0
        if fr.player_hp_max <= 0
        else int((bar_w // 2 - 4) * fr.player_hp / fr.player_hp_max)
    )
    pygame.draw.rect(canvas, (70, 140, 220), (mx, bar_y, pw, bar_h))
    player_bar_name = (getattr(state, "heroine_name", None) or "").strip() or "……"
    canvas.blit(
        small_font.render(
            f"{player_bar_name}　{fr.player_hp}/{fr.player_hp_max}",
            True,
            (210, 220, 235),
        ),
        (mx, bar_y - bar_label_above),
    )
    ex = mx + bar_w // 2 + 4
    pygame.draw.rect(canvas, (40, 44, 58), (ex, bar_y, bar_w // 2 - 4, bar_h))
    ew = (
        0
        if fr.enemy_hp_max <= 0
        else int((bar_w // 2 - 4) * fr.enemy_hp / fr.enemy_hp_max)
    )
    pygame.draw.rect(canvas, (200, 80, 95), (ex, bar_y, ew, bar_h))
    canvas.blit(
        small_font.render(
            f"{enemy.name_zh}　{fr.enemy_hp}/{fr.enemy_hp_max}",
            True,
            (235, 200, 200),
        ),
        (ex, bar_y - bar_label_above),
    )
    ty = bar_y + bar_h + _scale_y(ch, 10)

    hint_h = small_font.get_height() + _scale_y(ch, 12)
    body_bottom = ch - hint_h
    # 左右欄同寬，立繪／CG 框對稱；中欄「交鋒紀錄」可換行寬度（邏輯約 56 寬上限、至多約畫布寬 1/6）。
    side_w = min(_scale_x(cw, 56), max(_scale_x(cw, 44), cw // 6))
    gap = _scale_x(cw, 8)
    center_w = cw - 2 * mx - 2 * side_w - 2 * gap
    if center_w < _scale_x(cw, 100):
        side_w = max(_scale_x(cw, 40), side_w - _scale_x(cw, 10))
        center_w = cw - 2 * mx - 2 * side_w - 2 * gap

    lx = mx
    rx_col = cw - mx - side_w
    cx = mx + side_w + gap
    inner_w = max(24, side_w - _scale_x(cw, 6))
    player_col_title = (getattr(state, "heroine_name", None) or "").strip() or "……"
    max_title_h = max(
        _encounter_battle_side_title_block_height(
            small_font, player_col_title, inner_w
        ),
        _encounter_battle_side_title_block_height(
            small_font, enemy.name_zh, inner_w
        ),
    )
    stat_line_step = small_font.get_height() + 2
    stats_block_h = 3 * stat_line_step + _scale_y(ch, 6)
    avail_portrait_h = body_bottom - ty - max_title_h - stats_block_h
    min_ph = _scale_y(ch, 44)
    avail_h = max(1, avail_portrait_h)
    min_h_use = min(min_ph, avail_h)
    portrait_w, portrait_h = _encounter_battle_portrait_wh_aspect(
        inner_w,
        avail_h,
        ar_w=_ENCOUNTER_BATTLE_PORTRAIT_AR_W,
        ar_h=_ENCOUNTER_BATTLE_PORTRAIT_AR_H,
        min_h=min_h_use,
    )
    # 右側 CG 矩形左緣：使圖右緣恰為 ``cw - mx``，與左側圖左緣 ``mx`` 對稱。
    rx_img = cw - mx - portrait_w

    # --- 左：玩家（標題為姓名，與頂部血條標籤一致） ---
    ly = ty
    for nl in _wrap_cjk(small_font, player_col_title, inner_w):
        canvas.blit(small_font.render(nl, True, (200, 215, 235)), (lx, ly))
        ly += small_font.get_height() + 1
    ly += 2
    pl = pygame.Rect(lx, ly, portrait_w, portrait_h)
    draw_heroine_portrait(canvas, pl, state, tick, cover=True)
    ly += portrait_h + _scale_y(ch, 6)
    for stat_line in (
        f"生命　{fr.player_hp_max}",
        f"戰鬥　{outcome.player_atk}",
        f"防禦　{outcome.player_def}",
    ):
        canvas.blit(small_font.render(stat_line, True, (185, 195, 210)), (lx, ly))
        ly += small_font.get_height() + 2

    # --- 右：敵方（名稱自欄位左緣起算；CG 右對齊視窗邊距 ``mx``） ---
    ry = ty
    for nl in _wrap_cjk(small_font, enemy.name_zh, inner_w):
        canvas.blit(small_font.render(nl, True, (235, 200, 205)), (rx_col, ry))
        ry += small_font.get_height() + 1
    ry += 2
    er = pygame.Rect(rx_img, ry, portrait_w, portrait_h)
    cg_cov = _encounter_cg_surface_cover(asset_root, enemy.id, er.w, er.h)
    if cg_cov is not None:
        canvas.blit(cg_cov, (er.x, er.y))
    else:
        draw_encounter_enemy_placeholder(canvas, er, enemy, tick)
    ry += portrait_h + _scale_y(ch, 6)
    for stat_line in (
        f"生命　{fr.enemy_hp_max}",
        f"戰鬥　{outcome.enemy_atk}",
        f"防禦　{outcome.enemy_def}",
    ):
        canvas.blit(small_font.render(stat_line, True, (210, 190, 195)), (rx_img, ry))
        ry += small_font.get_height() + 2

    # --- 中：戰鬥日記（由上往下累積，不消除舊筆；過長則捲動） ---
    center_top = ty
    fh_log = small_font.get_height()
    lh_title = fh_log + 3
    mw = max(40, center_w - _scale_x(cw, 4))
    canvas.blit(
        small_font.render("交鋒紀錄", True, (140, 150, 170)),
        (cx, center_top),
    )
    content_top = center_top + lh_title + _scale_y(ch, 4)
    log_bottom = body_bottom - _scale_y(ch, 3)
    # 方框上緣與首行字距過近時，字頂易視覺上「壓線」；框內頂留白後再開始列印。
    diary_pad_top = max(3, _scale_y(ch, 3))
    inner_top = content_top + diary_pad_top
    # 紀錄本體：行距略緊；條目間空行改為小間距（非整行高）。
    diary_line_h = fh_log + 1
    diary_entry_gap = max(2, _scale_y(ch, 2))

    view_h = max(diary_line_h * 2, log_bottom - content_top)
    log_rect = pygame.Rect(cx - 2, content_top - 1, center_w + 4, view_h + 2)
    pygame.draw.rect(canvas, (38, 42, 54), log_rect, 1)

    diary_rows = _encounter_battle_diary_rows(outcome.frames, fi, small_font, mw)
    total_h = (
        sum(
            _encounter_diary_row_step_px(t, diary_line_h, diary_entry_gap)
            for t, _ in diary_rows
        )
        if diary_rows
        else 0
    )
    inner_h = max(1, log_bottom - inner_top)
    if total_h <= inner_h:
        y_log = float(inner_top)
    else:
        y_log = float(inner_top - (total_h - inner_h))

    # 捲動時首行 y 會小於 inner_top；若整行 blit 會畫進「框內頂留白」甚至超過方框上緣，須裁切。
    diary_clip = pygame.Rect(
        log_rect.left,
        inner_top,
        log_rect.width,
        max(1, log_bottom - inner_top),
    )
    prev_clip = canvas.get_clip()
    canvas.set_clip(prev_clip.clip(diary_clip))
    try:
        for text, col in diary_rows:
            step = _encounter_diary_row_step_px(text, diary_line_h, diary_entry_gap)
            y_i = int(y_log)
            clip_h = diary_line_h if text else step
            if y_i + clip_h > inner_top and y_i < log_bottom:
                if text:
                    canvas.blit(small_font.render(text, True, col), (cx, y_i))
            y_log += step
    finally:
        canvas.set_clip(prev_clip)

    hint = (
        "交鋒自動播映中（請待播畢）"
        if fi < len(outcome.frames) - 1
        else "Enter 進入餘韻"
    )
    hy = ch - _scale_y(ch, 10) - small_font.get_height()
    canvas.blit(small_font.render(hint, True, (130, 145, 168)), (mx, hy))


def draw_encounter_aftermath_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    enemy: EncounterEnemy,
    win: bool,
    paragraphs: tuple[str, ...],
    stat_participation_line: str,
    stat_treasure_line: str,
    *,
    aftermath_has_treasure: bool,
    aftermath_treasure_name_zh: str | None = None,
    protagonist_gender: str = "female",
    tick: int,
) -> None:
    """
    遭遇戰餘韻：頂部為**固定**勝／敗圖示（不依敵人 CG）；**單頁**兩段正文；
    勝利且有寶物名時首行為「戰勝對象：…　獲得寶物：…」；底部「數值變化」與「寶物加成」分兩行（加成列僅數值）。

    Args:
        canvas: 邏輯畫布。
        intro_font: 正文／數值列。
        small_font: 頁尾。
        enemy: 敵人（文案用）。
        win: 是否勝利。
        paragraphs: 餘韻段落（經正規化後固定為兩段顯示）。
        stat_participation_line: 含「數值變化：」前綴之參戰五維說明。
        stat_treasure_line: 「寶物加成：」＋僅五維增量短文；無寶物時空字串。
        aftermath_has_treasure: 勝利且確有寶物增量（無名稱時首行仍標「獲得寶物」字樣）。
        aftermath_treasure_name_zh: 寶物簡名；非空則併入首行「獲得寶物：」後。
        protagonist_gender: 主角性別；男性時餘韻正文「妳」改為「你」。
        tick: 影格。
    """
    cw, ch = canvas.get_size()
    canvas.fill((22, 26, 36))
    art_h = min(150 * ch // _ORIG_H, max(78, int(ch * 0.24)))
    art_rect = pygame.Rect(0, 0, cw, art_h)
    draw_encounter_aftermath_banner_art(canvas, art_rect, win, tick)
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (cw, art_h), 2)

    mx = _scale_x(cw, 20)
    max_w = cw - 2 * mx - _TEXT_PAD_X
    nav_raw = "【Enter】返回養成"
    footer_top = _footer_top_for_nav_raw_ch(ch, small_font, max_w, nav_raw)
    stat_budget_for_wrap = stat_participation_line.strip()
    if stat_treasure_line.strip():
        stat_budget_for_wrap = (
            stat_participation_line + "\n" + stat_treasure_line.strip()
        )
    para_limit_y = _narrative_bottom_y_page0_with_bottom_stat_ch(
        ch, small_font, intro_font, max_w, stat_budget_for_wrap
    )
    fh = intro_font.get_height()

    y = art_h + 8 * ch // _ORIG_H
    if win:
        _tn = (aftermath_treasure_name_zh or "").strip()
        if _tn:
            # 全形空白拉開敵名與寶物段，避免窄螢幕換行時仍盡量同列可讀。
            head_first = f"戰勝對象：{enemy.name_zh}　　　　　獲得寶物：{_tn}"
        else:
            head_first = f"戰勝對象：{enemy.name_zh}"
            if aftermath_has_treasure:
                head_first += "　獲得寶物"
        col = (180, 230, 200)
    else:
        head_first = f"敗北：{enemy.name_zh}"
        col = (230, 190, 190)
    for line in _wrap_cjk(intro_font, head_first, max_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(line, True, col), (mx, y))
        y += fh + 4
    y += 4 * ch // _ORIG_H

    para_a, para_b = encounter_aftermath_two_paragraphs(paragraphs)
    para_a = encounter_protagonist_pronoun_adjust_zh(para_a, protagonist_gender)
    para_b = encounter_protagonist_pronoun_adjust_zh(para_b, protagonist_gender)
    for line in _wrap_cjk(intro_font, para_a, max_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(line, True, (210, 215, 228)), (mx, y))
        y += fh + 2
    if para_b:
        y += _aftermath_para_gap_px_ch(ch)
        for line in _wrap_cjk(intro_font, para_b, max_w):
            if y + fh > para_limit_y:
                break
            canvas.blit(intro_font.render(line, True, (210, 215, 228)), (mx, y))
            y += fh + 2

    if stat_participation_line.strip() or stat_treasure_line.strip():
        gap_stat_above_nav = _AFTERMATH_GAP_BEFORE_HINT_LY * ch // _ORIG_H
        fh_stat = intro_font.get_height() + 2
        gap_tight = max(1, ch // 200)
        lines_p = (
            _wrap_cjk(intro_font, stat_participation_line, max_w)
            if stat_participation_line.strip()
            else []
        )
        lines_t = (
            _wrap_cjk(intro_font, stat_treasure_line.strip(), max_w)
            if stat_treasure_line.strip()
            else []
        )
        stat_block_h = len(lines_p) * fh_stat
        if lines_p and lines_t:
            stat_block_h += gap_tight
        stat_block_h += len(lines_t) * fh_stat
        sy = footer_top - gap_stat_above_nav - stat_block_h
        yi = sy
        for sl in lines_p:
            canvas.blit(
                intro_font.render(sl, True, _AFTERMATH_STAT_COLOR),
                (mx, yi),
            )
            yi += fh_stat
        if lines_p and lines_t:
            yi += gap_tight
        for sl in lines_t:
            canvas.blit(
                intro_font.render(sl, True, _AFTERMATH_STAT_COLOR),
                (mx, yi),
            )
            yi += fh_stat

    fy = footer_top
    nav_lines = _wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def draw_encounter_gallery_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    gallery_page_index: int,
    gallery_slot_index: int,
    enemy_unlocked: set[str],
    section_header: str,
    asset_root: Path,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    「遭遇的強敵」畫廊網格：每格占位圖或 CG 縮圖；未解鎖時仍顯示敵人中文名，圖為剪影。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題。
        small_font: 標籤。
        gallery_page_index: 頁碼。
        gallery_slot_index: 游標格。
        enemy_unlocked: 已戰勝解鎖之敵 id。
        section_header: 區塊標題。
        asset_root: 專案根。
        star_xy: 星空座標。
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
    order = ENCOUNTER_GALLERY_ORDER
    total = len(order)
    pc = max(1, (total + per_page - 1) // per_page)
    pi = max(0, min(gallery_page_index, pc - 1))
    start = pi * per_page
    keys_page = list(order[start : start + per_page])
    n_sp = len(keys_page)

    hdr = f"{section_header}　（{pi + 1}／{pc}）"
    y = _scale_y(ch, 8)
    for line in _wrap_cjk(menu_font, hdr, cw - 2 * mx):
        canvas.blit(menu_font.render(line, True, (255, 230, 190)), (mx, y))
        y += menu_font.get_height() + 2

    hint_raw = "方向鍵選擇　換頁　已解鎖可 Enter 全螢幕　Esc 返回"
    gallery_hint_lines = _wrap_cjk(small_font, hint_raw, cw - 2 * mx)
    lh_label = small_font.get_height()
    gallery_hint_block_h = len(gallery_hint_lines) * lh_label + max(0, len(gallery_hint_lines) - 1) * 2
    grid_bottom = ch - _scale_y(ch, 8) - gallery_hint_block_h

    n_cols = 3
    n_rows = 2
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

    for idx, eid in enumerate(keys_page):
        row = idx // n_cols
        col = idx % n_cols
        cx = x0 + col * (cell_w + gap_x)
        cy = y + row * row_stride_y
        box_rect = pygame.Rect(cx, cy, cell_w, box_h)
        unlocked = eid in enemy_unlocked
        enemy = get_enemy_by_id(eid)
        pygame.draw.rect(canvas, (28, 32, 44), box_rect)
        if unlocked:
            cg = _encounter_cg_surface(asset_root, eid, box_rect.w - 4, box_rect.h - 4)
            if cg is not None:
                canvas.blit(
                    cg,
                    (
                        box_rect.x + (box_rect.w - cg.get_width()) // 2,
                        box_rect.y + (box_rect.h - cg.get_height()) // 2,
                    ),
                )
            elif enemy is not None:
                draw_encounter_enemy_placeholder(canvas, box_rect, enemy, tick)
            else:
                pygame.draw.rect(canvas, (36, 40, 52), box_rect)
        else:
            draw_gallery_cell_locked_cross(canvas, box_rect)
        border_w = max(1, _scale_x(cw, _GALLERY_CELL_BORDER_W_LOGICAL))
        pygame.draw.rect(canvas, _GALLERY_CELL_BORDER_RGB, box_rect, width=border_w)
        slot_box_rects.append(box_rect)
        label = enemy.name_zh if enemy is not None else eid
        name_col = (210, 218, 232) if unlocked else (175, 184, 202)
        ly = box_rect.bottom + name_gap
        for li, lab_line in enumerate(_wrap_cjk(small_font, label, cell_w)):
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
