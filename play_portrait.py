"""
遊玩畫面主角立繪：幼年／少年／青年三階段，柔和可愛的像素風（大眼、腮紅、粉嫩色調）。
髮色與衣裙會依五維屬性（智力、力量、社交、信仰、務實）微調。
`assets/portraits/` 可放置 JPG／PNG；女性優先 `childhood_female.jpg`，再嘗試 `childhood.jpg`；
男性優先 `childhood_male.jpg`，其次 `childhood_m.jpg`，再回退通用檔名。
"""

from __future__ import annotations

import os
from pathlib import Path

import pygame

from game_state import GameState

# 與專案根目錄同層的立繪圖檔（優先於程式繪圖）。
_PORTRAIT_DIR = Path(__file__).resolve().parent / "assets" / "portraits"
# 階段鍵 → 立繪檔名候選（`assets/portraits/`，依序嘗試，先 JPG 再 PNG）。
_STAGE_IMAGE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "childhood": ("childhood.jpg", "childhood.png"),
    "adolescence": ("adolescence.jpg", "adolescence.png"),
    "young_adult": ("young_adult.jpg", "young_adult.png"),
}
_raw_png_cache: dict[tuple[str, str], pygame.Surface | None] = {}
_scaled_png_cache: dict[tuple[str, int, str], pygame.Surface] = {}
_scaled_png_cover_cache: dict[tuple[str, int, int, str], pygame.Surface] = {}


def _clamp(v: int, lo: int, hi: int) -> int:
    """將整數限制在區間內。"""
    return max(lo, min(hi, v))


def _shade_rgb(rgb: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    """
    將 RGB 三色同步加亮或變暗（用於陰影／高光）。

    Args:
        rgb: 基準色。
        delta: 正值變亮、負值變暗。

    Returns:
        限制在 0–255 的新 RGB。
    """
    return tuple(_clamp(int(c) + delta, 0, 255) for c in rgb)


def _life_stage(state: GameState) -> str:
    """
    取得立繪用階段鍵（相容舊存檔 phase 字串）。

    Args:
        state: 遊戲狀態。

    Returns:
        `childhood`／`adolescence`／`young_adult` 之一。
    """
    p = state.phase
    if p in ("childhood", "adolescence", "young_adult"):
        return p
    if p in ("youth", "adult"):
        return "young_adult"
    return "childhood"


def _portrait_gender_key(state: GameState) -> str:
    """回傳立繪檔名用性別鍵（``male``／``female``）。"""
    g = getattr(state, "protagonist_gender", "female")
    return "male" if g == "male" else "female"


def _portrait_filename_candidates(stage: str, gender_key: str) -> tuple[str, ...]:
    """
    依性別回傳嘗試載入的檔名順序。

    - 女性：``*_female.jpg``／``*_female.png`` → ``childhood.jpg`` 等預設檔名。
    - 男性：``*_male.*`` → ``*_m.*`` → 預設檔名（最後可與女性共用同一檔）。

    Args:
        stage: 階段鍵。
        gender_key: ``male`` 或 ``female``。

    Returns:
        檔名元組。
    """
    base = _STAGE_IMAGE_CANDIDATES.get(stage, ())
    if gender_key == "male":
        male_first: list[str] = []
        for name in base:
            stem, ext = os.path.splitext(name)
            male_first.append(f"{stem}_male{ext}")
            male_first.append(f"{stem}_m{ext}")
        return tuple(male_first) + base
    female_first: list[str] = []
    for name in base:
        stem, ext = os.path.splitext(name)
        female_first.append(f"{stem}_female{ext}")
    return tuple(female_first) + base


def _resolve_portrait_png_path(stage: str, gender_key: str) -> Path | None:
    """
    解析某階段立繪圖檔（JPG／PNG）的實際路徑。

    Args:
        stage: `childhood`／`adolescence`／`young_adult`。
        gender_key: ``male`` 或 ``female``。

    Returns:
        存在則回傳檔案路徑，否則 None。
    """
    for name in _portrait_filename_candidates(stage, gender_key):
        p = _PORTRAIT_DIR / name
        if p.is_file():
            return p
    return None


def _load_portrait_png_raw(stage: str, gender_key: str) -> pygame.Surface | None:
    """
    載入並快取原始立繪點陣圖（JPG／PNG；PNG 可含 alpha）。

    Args:
        stage: 階段鍵。
        gender_key: ``male`` 或 ``female``。

    Returns:
        成功則為 Surface，失敗或無檔則 None。
    """
    ck = (stage, gender_key)
    if ck in _raw_png_cache:
        return _raw_png_cache[ck]
    path = _resolve_portrait_png_path(stage, gender_key)
    if path is None:
        _raw_png_cache[ck] = None
        return None
    try:
        surf = pygame.image.load(os.fsdecode(path)).convert_alpha()
    except (pygame.error, OSError):
        _raw_png_cache[ck] = None
        return None
    _raw_png_cache[ck] = surf
    return surf


def _scaled_portrait_png(stage: str, target_w: int, gender_key: str) -> pygame.Surface | None:
    """
    將立繪縮放為固定寬度 `target_w`（維持長寬比），供格子橫向貼滿；
    高度由比例決定，可大於格子高度（由呼叫端整張貼上、不裁切）。

    Args:
        stage: 階段鍵。
        target_w: 目標寬（像素，通常為立繪格內寬）。
        gender_key: ``male`` 或 ``female``。

    Returns:
        有對應圖檔則為縮放後 Surface（寬為 `target_w`），否則 None。
    """
    raw = _load_portrait_png_raw(stage, gender_key)
    if raw is None:
        return None
    tw = max(1, target_w)
    key = (stage, tw, gender_key)
    if key in _scaled_png_cache:
        return _scaled_png_cache[key]
    rw, rh = raw.get_size()
    if rw <= 0 or rh <= 0:
        return None
    nw = tw
    nh = max(1, int(round(rh * nw / rw)))
    out = pygame.transform.smoothscale(raw, (nw, nh))
    _scaled_png_cache[key] = out
    return out


def _scaled_portrait_png_cover(
    stage: str,
    box_w: int,
    box_h: int,
    gender_key: str,
) -> pygame.Surface | None:
    """
    將立繪縮放為**覆蓋**矩形（維持長寬比，取較大倍率使寬高皆不少於格子，超出部分由呼叫端裁切）。

    Args:
        stage: 階段鍵。
        box_w: 目標框寬。
        box_h: 目標框高。
        gender_key: ``male`` 或 ``female``。

    Returns:
        有對應圖檔則為縮放後 Surface；否則 None。
    """
    raw = _load_portrait_png_raw(stage, gender_key)
    if raw is None:
        return None
    bw = max(1, box_w)
    bh = max(1, box_h)
    key = (stage, bw, bh, gender_key)
    if key in _scaled_png_cover_cache:
        return _scaled_png_cover_cache[key]
    rw, rh = raw.get_size()
    if rw <= 0 or rh <= 0:
        return None
    scale = max(bw / rw, bh / rh)
    nw = max(1, int(round(rw * scale)))
    nh = max(1, int(round(rh * scale)))
    out = pygame.transform.smoothscale(raw, (nw, nh))
    _scaled_png_cover_cache[key] = out
    return out


def _palette_from_state(state: GameState) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """
    由五維屬性推算髮色、裙色、膚色基調。

    Args:
        state: 遊戲狀態。

    Returns:
        (hair_rgb, dress_rgb, skin_rgb)。
    """
    soc_p = _clamp(state.social - state.pragmatic, -25, 25)
    hair_r = _clamp(95 + soc_p // 2, 72, 130)
    hair_g = _clamp(68 - soc_p // 3, 52, 95)
    hair_b = _clamp(88 + state.fth_stat // 8, 72, 125)
    dr = _clamp(255 - state.int_stat // 5, 200, 255)
    dg = _clamp(175 + state.fth_stat // 6, 150, 220)
    db = _clamp(205 + state.str_stat // 7, 185, 245)
    skin = (255, 228, 218)
    return (hair_r, hair_g, hair_b), (dr, dg, db), skin


def _draw_flat_portrait_backing(sub: pygame.Surface, w: int, h: int) -> None:
    """
    外部立繪 PNG 用的素色底（與養成畫面結局 CG 區塊色調一致，避免半透明邊緣露出程式背景／閃星）。

    @param sub - 立繪子平面（全幅填滿）
    @param w - 寬
    @param h - 高
    """
    sub.fill((32, 38, 50))


def _draw_soft_background(sub: pygame.Surface, w: int, h: int) -> None:
    """繪製粉紫系柔和漸層背景，並在人物區加一層極淡的暖色光暈（僅內建立繪模式使用）。"""
    for yy in range(0, h, 2):
        t = yy / max(h, 1)
        r = int(52 + t * 18)
        g = int(48 + t * 22)
        b = int(78 + t * 28)
        r = min(255, r + 12)
        b = min(255, b + 10)
        pygame.draw.rect(sub, (r, g, b), (0, yy, w, 2))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, int(h * 0.42)
    pygame.draw.ellipse(glow, (255, 230, 245, 28), (cx - w * 42 // 100, cy - h * 35 // 100, w * 84 // 100, h * 58 // 100))
    sub.blit(glow, (0, 0))


def _draw_ground_shadow(
    sub: pygame.Surface,
    cx: int,
    ground_y: int,
    w: int,
    h: int,
) -> None:
    """
    腳下雙層柔影，讓角色較有落地感。

    Args:
        sub: 目標平面。
        cx: 水平中心。
        ground_y: 腳底基準 y。
        w, h: 畫布寬高（用於比例）。
    """
    ew, eh = w * 70 // 100, max(14, h // 28)
    pygame.draw.ellipse(sub, (72, 78, 102), (cx - ew // 2, ground_y - 4, ew, eh))
    pygame.draw.ellipse(sub, (86, 92, 118), (cx - w * 33 // 100, ground_y - 6, w * 66 // 100, 22))


def _draw_sparkle(sub: pygame.Surface, x: int, y: int, tick: int, seed: int) -> None:
    """小星星裝飾（輕微閃爍）。"""
    if ((tick // 14) + seed) % 5 != 0:
        return
    pygame.draw.rect(sub, (255, 252, 255), (x, y, 2, 2))


def _draw_cute_eyes(
    sub: pygame.Surface,
    cx: int,
    eye_y: int,
    tick: int,
    spread: int,
    eye_w: int,
    eye_h: int,
    iris: tuple[int, int, int],
    chibi: bool,
) -> None:
    """
    繪製偏可愛風大眼（白底、彩色虹膜、高光、腮紅可選）。

    Args:
        sub: 目標平面。
        cx: 臉水平中心。
        eye_y: 雙眼基準 y。
        tick: 影格（眨眼）。
        spread: 內眼角與中心距離相關參數。
        eye_w: 眼寬。
        eye_h: 眼高。
        iris: 虹膜色。
        chibi: True 時畫較大腮紅點。
    """
    blink = 0 < (tick % 150) < 7
    lx = cx - spread - eye_w
    rx = cx + spread
    if blink:
        pygame.draw.line(sub, (72, 64, 88), (lx, eye_y), (lx + eye_w, eye_y), 2)
        pygame.draw.line(sub, (72, 64, 88), (rx, eye_y), (rx + eye_w, eye_y), 2)
        return
    # 眼白（底層略灰，上緣較立體）
    pygame.draw.ellipse(sub, (248, 248, 252), (lx, eye_y - 6, eye_w, eye_h + 4))
    pygame.draw.ellipse(sub, (248, 248, 252), (rx, eye_y - 6, eye_w, eye_h + 4))
    pygame.draw.line(sub, (220, 218, 232), (lx + 1, eye_y - 4), (lx + eye_w - 1, eye_y - 4), 1)
    pygame.draw.line(sub, (220, 218, 232), (rx + 1, eye_y - 4), (rx + eye_w - 1, eye_y - 4), 1)
    # 虹膜
    ir = eye_w * 55 // 100
    ih = eye_h * 70 // 100
    pygame.draw.ellipse(sub, iris, (lx + (eye_w - ir) // 2, eye_y - 2, ir, ih))
    pygame.draw.ellipse(sub, iris, (rx + (eye_w - ir) // 2, eye_y - 2, ir, ih))
    pygame.draw.arc(
        sub,
        _shade_rgb(iris, -28),
        (lx + (eye_w - ir) // 2, eye_y - 2, ir, ih),
        3.6,
        5.9,
        max(1, eye_w // 10),
    )
    pygame.draw.arc(
        sub,
        _shade_rgb(iris, -28),
        (rx + (eye_w - ir) // 2, eye_y - 2, ir, ih),
        3.6,
        5.9,
        max(1, eye_w // 10),
    )
    # 瞳孔
    pr = max(3, eye_w // 4)
    pygame.draw.circle(sub, (40, 36, 52), (lx + eye_w // 2, eye_y + eye_h // 3), pr)
    pygame.draw.circle(sub, (40, 36, 52), (rx + eye_w // 2, eye_y + eye_h // 3), pr)
    # 高光（主＋次）
    pygame.draw.circle(sub, (255, 255, 255), (lx + eye_w // 3, eye_y - 1), 3)
    pygame.draw.circle(sub, (255, 255, 255), (rx + eye_w // 3, eye_y - 1), 3)
    pygame.draw.circle(sub, (255, 255, 255), (lx + eye_w * 2 // 3, eye_y + 2), 2)
    pygame.draw.circle(sub, (255, 255, 255), (rx + eye_w * 2 // 3, eye_y + 2), 2)
    # 上眼線
    pygame.draw.arc(sub, (72, 64, 88), (lx - 1, eye_y - 8, eye_w + 2, eye_h + 6), 2.2, 4.1, 2)
    pygame.draw.arc(sub, (72, 64, 88), (rx - 1, eye_y - 8, eye_w + 2, eye_h + 6), 2.2, 4.1, 2)
    if chibi:
        pygame.draw.circle(sub, (255, 200, 208), (cx - 14, eye_y + 10), 7)
        pygame.draw.circle(sub, (255, 200, 208), (cx + 14, eye_y + 10), 7)
        pygame.draw.circle(sub, (255, 175, 188), (cx - 14, eye_y + 10), 4)
        pygame.draw.circle(sub, (255, 175, 188), (cx + 14, eye_y + 10), 4)


def draw_heroine_portrait(
    surf: pygame.Surface,
    rect: pygame.Rect,
    state: GameState,
    tick: int,
    *,
    cover: bool = False,
) -> None:
    """
    在指定矩形內繪製三階段主角立繪。

    若 `assets/portraits/` 下有對應階段圖檔（女性優先 `childhood_female.jpg` 等，男性優先 `childhood_male.jpg` 或 `childhood_m.jpg`，
    再回退 `childhood.jpg`／`.png`），則優先顯示圖檔：
    預設為寬度貼滿、高度等比例、底部對齊（可高出格子不裁切）；
    ``cover=True`` 時改為**填滿**矩形（等比例放大後置中，左右或上下超出部分裁掉）。
    格內未蓋到處為素色底；邊框仍沿 ``rect``。
    無圖檔則繪製內建程式立繪（漸層＋閃星裝飾；不受 ``cover`` 影響）。

    Args:
        surf: 目標畫布。
        rect: 立繪區域。
        state: 遊戲狀態。
        tick: 影格計數。
        cover: 圖檔模式是否以覆蓋填滿格子。
    """
    sub = surf.subsurface(rect)
    w, h = rect.w, rect.h
    stage = _life_stage(state)
    gkey = _portrait_gender_key(state)

    if cover:
        cov = _scaled_portrait_png_cover(stage, w, h, gkey)
        if cov is not None:
            clip = surf.get_clip()
            surf.set_clip(rect)
            pygame.draw.rect(surf, (32, 38, 50), rect)
            iw, ih = cov.get_size()
            surf.blit(
                cov,
                (rect.x + (w - iw) // 2, rect.y + (h - ih) // 2),
            )
            surf.set_clip(clip)
            bw = max(2, h // 120)
            pygame.draw.rect(surf, (200, 175, 210), rect, width=bw)
            pygame.draw.rect(
                surf,
                (120, 100, 150),
                (rect.x + bw + 2, rect.y + bw + 2, w - 2 * bw - 4, h - 2 * bw - 4),
                width=1,
            )
            return

    scaled_png = _scaled_portrait_png(stage, max(1, w), gkey)
    if scaled_png is not None:
        _draw_flat_portrait_backing(sub, w, h)
        sh = scaled_png.get_height()
        surf.blit(scaled_png, (rect.x, rect.bottom - sh))
        bw = max(2, h // 120)
        pygame.draw.rect(surf, (200, 175, 210), rect, width=bw)
        pygame.draw.rect(
            surf,
            (120, 100, 150),
            (rect.x + bw + 2, rect.y + bw + 2, w - 2 * bw - 4, h - 2 * bw - 4),
            width=1,
        )
        return

    hair, dress, skin = _palette_from_state(state)

    _draw_soft_background(sub, w, h)
    for i in range(6):
        _draw_sparkle(sub, 20 + i * 47, 18 + (i * 31) % (h // 3), tick, i)

    cx = w // 2
    ground_y = h - _clamp(h // 10, 10, 40)
    _draw_ground_shadow(sub, cx, ground_y, w, h)

    if stage == "childhood":
        _draw_cute_child(sub, cx, ground_y, w, h, hair, dress, skin, tick)
    elif stage == "adolescence":
        _draw_cute_teen(sub, cx, ground_y, w, h, hair, dress, skin, tick)
    else:
        _draw_cute_young_adult(sub, cx, ground_y, w, h, hair, dress, skin, tick)

    bw = max(2, h // 120)
    pygame.draw.rect(sub, (200, 175, 210), (0, 0, w, h), width=bw)
    pygame.draw.rect(sub, (120, 100, 150), (bw + 2, bw + 2, w - 2 * bw - 4, h - 2 * bw - 4), width=1)


def _draw_cute_child(
    sub: pygame.Surface,
    cx: int,
    ground_y: int,
    w: int,
    h: int,
    hair: tuple[int, int, int],
    dress: tuple[int, int, int],
    skin: tuple[int, int, int],
    tick: int,
) -> None:
    """幼年：圓臉、雙馬尾、蓬蓬裙。"""
    body_w, body_h = w * 38 // 100 + 6, h * 26 // 100
    body_x = cx - body_w // 2
    body_y = ground_y - body_h
    pygame.draw.ellipse(sub, _shade_rgb(dress, -20), (body_x + 3, body_y + body_h // 3 + 2, body_w - 4, body_h * 2 // 3))
    pygame.draw.ellipse(sub, dress, (body_x, body_y + body_h // 3, body_w, body_h * 2 // 3))
    pygame.draw.rect(sub, dress, (body_x, body_y, body_w, body_h * 2 // 3))
    pygame.draw.rect(sub, (dress[0] - 25, dress[1] - 20, dress[2] - 18), (body_x + 4, body_y + 8, body_w - 8, body_h - 14))
    hl = max(2, body_w // 14)
    pygame.draw.rect(sub, _shade_rgb(dress, 22), (cx - hl // 2, body_y + body_h // 4, hl, body_h * 3 // 4))
    # 小蝴蝶結
    pygame.draw.circle(sub, (255, 140, 170), (cx, body_y + 6), 6)

    pygame.draw.rect(sub, skin, (cx - 9, body_y - 4, 18, 11))

    face_w = w * 30 // 100 + 18
    face_h = h * 34 // 100 + 12
    fx = cx - face_w // 2
    fy = body_y - face_h + 10
    pygame.draw.ellipse(sub, _shade_rgb(skin, -18), (fx + 2, fy + 3, face_w - 2, face_h - 2))
    pygame.draw.ellipse(sub, skin, (fx, fy, face_w, face_h))

    # 雙馬尾（陰影＋本體＋高光）
    for ox, oy in ((1, 2), (face_w + 1, 2)):
        pygame.draw.circle(sub, _shade_rgb(hair, -22), (fx + ox, fy + face_h // 3 + oy), 15)
    pygame.draw.circle(sub, hair, (fx - 2, fy + face_h // 3), 14)
    pygame.draw.circle(sub, hair, (fx + face_w + 2, fy + face_h // 3), 14)
    pygame.draw.ellipse(sub, _shade_rgb(hair, -14), (fx - 6, fy - 2, face_w + 14, face_h // 2 + 18))
    pygame.draw.ellipse(sub, hair, (fx - 8, fy - 6, face_w + 16, face_h // 2 + 20))
    pygame.draw.ellipse(sub, _shade_rgb(hair, 28), (fx - 4, fy - 2, face_w // 2 + 8, face_h // 4 + 6))
    pygame.draw.arc(sub, (hair[0] - 15, hair[1] - 10, hair[2] - 10), (fx + 4, fy + 8, face_w - 8, face_h - 6), 0, 3.14, 3)
    pygame.draw.rect(sub, (hair[0] - 8, hair[1] - 6, hair[2] - 8), (fx + 6, fy + 12, face_w - 12, 12))

    iris = (120, 170, 220)
    eye_y = fy + face_h // 2 - 4
    _draw_cute_eyes(sub, cx, eye_y, tick, spread=13, eye_w=13, eye_h=14, iris=iris, chibi=True)
    # 小笑嘴
    pygame.draw.arc(sub, (220, 120, 140), (cx - 10, fy + face_h - 22, 20, 14), 3.5, 5.8, 2)


def _draw_cute_teen(
    sub: pygame.Surface,
    cx: int,
    ground_y: int,
    w: int,
    h: int,
    hair: tuple[int, int, int],
    dress: tuple[int, int, int],
    skin: tuple[int, int, int],
    tick: int,
) -> None:
    """少年：及肩髮、水手領、髮夾。"""
    body_w, body_h = w * 28 // 100 + 8, h * 40 // 100 + 6
    body_x = cx - body_w // 2
    body_y = ground_y - body_h
    pygame.draw.rect(sub, (240, 248, 255), (body_x, body_y, body_w, body_h // 3 + 4))
    pygame.draw.rect(sub, _shade_rgb(dress, -18), (body_x + body_w * 55 // 100, body_y + body_h // 3, body_w * 45 // 100, body_h * 2 // 3))
    pygame.draw.rect(sub, dress, (body_x, body_y + body_h // 3, body_w, body_h * 2 // 3))
    pygame.draw.polygon(
        sub,
        (255, 255, 255),
        [(body_x + 2, body_y + 14), (cx, body_y + 26), (body_x + body_w - 2, body_y + 14)],
    )
    pygame.draw.line(sub, (230, 235, 245), (cx, body_y + 16), (cx, body_y + body_h // 3 + 2), 1)
    pygame.draw.rect(sub, (dress[0] - 18, dress[1] - 14, dress[2] - 20), (body_x + 4, body_y + 24, body_w - 8, body_h - 30))
    pygame.draw.rect(sub, (255, 150, 180), (cx - 8, body_y + 12, 16, 8))

    pygame.draw.rect(sub, skin, (cx - 10, body_y - 5, 20, 13))

    face_w = w * 24 // 100 + 14
    face_h = h * 28 // 100 + 10
    fx = cx - face_w // 2
    fy = body_y - face_h + 4
    pygame.draw.ellipse(sub, _shade_rgb(skin, -16), (fx + 2, fy + 2, face_w - 3, face_h - 3))
    pygame.draw.ellipse(sub, skin, (fx, fy, face_w, face_h))

    pygame.draw.ellipse(sub, _shade_rgb(hair, -16), (fx - 4, fy - 1, face_w + 10, face_h // 2 + 12))
    pygame.draw.ellipse(sub, hair, (fx - 6, fy - 4, face_w + 12, face_h // 2 + 14))
    pygame.draw.rect(sub, _shade_rgb(hair, -12), (fx - 2, fy + 8, face_w + 6, face_h // 2 + 6))
    pygame.draw.rect(sub, hair, (fx - 4, fy + 6, face_w + 8, face_h // 2 + 8))
    pygame.draw.ellipse(sub, _shade_rgb(hair, 26), (fx - 2, fy - 2, face_w // 2 + 10, face_h // 4 + 4))
    pygame.draw.rect(sub, (255, 220, 100), (fx + face_w - 16, fy + 6, 10, 6))

    iris = (100, 155, 210)
    eye_y = fy + face_h // 2 - 2
    _draw_cute_eyes(sub, cx, eye_y, tick, spread=15, eye_w=12, eye_h=13, iris=iris, chibi=True)
    pygame.draw.arc(sub, (200, 110, 130), (cx - 8, fy + face_h - 20, 16, 12), 3.6, 5.7, 2)


def _draw_cute_young_adult(
    sub: pygame.Surface,
    cx: int,
    ground_y: int,
    w: int,
    h: int,
    hair: tuple[int, int, int],
    dress: tuple[int, int, int],
    skin: tuple[int, int, int],
    tick: int,
) -> None:
    """青年：長髮、露肩可愛小禮服。"""
    body_w, body_h = w * 29 // 100 + 6, h * 42 // 100 + 10
    body_x = cx - body_w // 2
    body_y = ground_y - body_h
    pygame.draw.ellipse(sub, _shade_rgb(dress, -22), (body_x - 1, body_y + 14, body_w + 6, body_h - 10))
    pygame.draw.ellipse(sub, dress, (body_x - 4, body_y + 12, body_w + 8, body_h - 8))
    pygame.draw.arc(sub, _shade_rgb(dress, 18), (body_x + 6, body_y + 20, body_w - 12, body_h - 28), 4.5, 5.5, 2)
    pygame.draw.rect(sub, (dress[0] - 12, dress[1] - 10, dress[2] - 12), (body_x + 5, body_y + 28, body_w - 10, body_h - 36))
    pygame.draw.ellipse(sub, skin, (cx - 14, body_y + 4, 28, 16))

    pygame.draw.rect(sub, skin, (cx - 10, body_y - 4, 20, 12))

    face_w = w * 23 // 100 + 10
    face_h = h * 28 // 100 + 14
    fx = cx - face_w // 2
    fy = body_y - face_h + 2
    pygame.draw.ellipse(sub, _shade_rgb(skin, -15), (fx + 2, fy + 2, face_w - 3, face_h - 3))
    pygame.draw.ellipse(sub, skin, (fx, fy, face_w, face_h))

    pygame.draw.ellipse(sub, _shade_rgb(hair, -18), (fx - 10, fy - 7, face_w + 22, face_h // 2 + 10))
    pygame.draw.ellipse(sub, hair, (fx - 12, fy - 10, face_w + 24, face_h // 2 + 12))
    pygame.draw.rect(sub, _shade_rgb(hair, -14), (fx - 8, fy + 4, face_w + 18, face_h + 18))
    pygame.draw.rect(sub, hair, (fx - 10, fy + 2, face_w + 20, face_h + 22))
    pygame.draw.ellipse(sub, _shade_rgb(hair, 24), (fx - 6, fy - 6, face_w // 2 + 14, face_h // 3 + 6))
    pygame.draw.rect(sub, (hair[0] - 10, hair[1] - 8, hair[2] - 8), (fx + 5, fy + 10, face_w - 10, 9))

    iris = (90, 145, 200)
    eye_y = fy + face_h // 2
    _draw_cute_eyes(sub, cx, eye_y, tick, spread=14, eye_w=11, eye_h=12, iris=iris, chibi=True)
    pygame.draw.arc(sub, (195, 105, 125), (cx - 8, fy + face_h - 18, 16, 11), 3.65, 5.65, 2)
