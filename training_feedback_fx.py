"""
培養結算回饋：優先使用 ``assets/training_fx/`` 每動作**一張**插圖，缺檔時回退為向量圖示。

解析順序（前者優先）：
1. ``manifest.json``（可明確指定檔名，改版圖時建議用此對應）
2. 檔名慣例：``{prefix}.{ext}`` 或 ``{prefix}_*.{ext}``（多檔時依檔名尾端數字排序，**只取第一張**）

慣例前綴（鍵 1～8）：
- 鍵 1：女性優先 ``read_female``，無則 ``read``；男性優先 ``read_male``，無則 ``read``
- 鍵 2～8：女性優先 ``train_female`` 等，無則 ``train`` 等；男性優先 ``train_male`` 等，無則同上中性前綴

``manifest.json`` 鍵：``"1"``～``"8"``；另可 ``"1_female"``～``"8_female"``／``"1_male"``～``"8_male"``（依性別先試對應鍵再試數字鍵）。
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pygame

_FX_DIR = Path(__file__).resolve().parent / "assets" / "training_fx"
_MANIFEST_NAME = "manifest.json"
_FX_EXTS: tuple[str, ...] = (".png", ".webp", ".jpg", ".jpeg")
# 預設回饋面板相對原比例的邊長倍率（右下角小圖用）。
_FEEDBACK_PANEL_SCALE: float = 2.0

# 培養鍵 → 圖檔前綴（各放一張即可，建議 ``{prefix}_01.png``）
_ACTION_FRAME_PREFIX: dict[int, str] = {
    1: "read",
    2: "train",
    3: "pray",
    4: "chat",
    5: "work",
    6: "copy",
    7: "visit",
    8: "solo",
}

_READ_MALE_PREFIX = "read_male"
_READ_FEMALE_PREFIX = "read_female"
# 培養鍵 2～8：男性專用前綴（鍵 1 用 ``read_male``）。
_MALE_ACTION_PREFIX: dict[int, str] = {
    2: "train_male",
    3: "pray_male",
    4: "chat_male",
    5: "work_male",
    6: "copy_male",
    7: "visit_male",
    8: "solo_male",
}
# 培養鍵 2～8：女性專用前綴（鍵 1 用 ``read_female``）。
_FEMALE_ACTION_PREFIX: dict[int, str] = {
    2: "train_female",
    3: "pray_female",
    4: "chat_female",
    5: "work_female",
    6: "copy_female",
    7: "visit_female",
    8: "solo_female",
}

# 快取鍵含檔案 mtime，替換圖檔後會重新載入。
_RAW_IMAGE_CACHE: dict[tuple[Any, ...], pygame.Surface | None] = {}
_SCALED_IMAGE_CACHE: dict[tuple[Any, ...], pygame.Surface | None] = {}
_manifest_entries: dict[str, list[str]] = {}
_manifest_mtime_ns: int | None = None


def _frame_sort_key(path: Path) -> tuple[int, str]:
    """依檔名尾端數字排序（無數字者排最後）。"""
    m = re.search(r"(\d+)(?!.*\d)", path.stem)
    if m is None:
        return (10**9, path.name)
    return (int(m.group(1)), path.name)


def _raw_image_bucket(action_key: int, gender_key: str) -> tuple[int, str]:
    """
    圖檔快取分桶：男性／女性各獨立，避免男女圖檔混用快取。

    Args:
        action_key: 培養 1～8。
        gender_key: ``male`` 或 ``female``。

    Returns:
        ``(action_key, "male"|"female")``；非男非女時視為 ``female`` 桶。
    """
    if gender_key == "male":
        return (action_key, "male")
    return (action_key, "female")


def _glob_prefix(prefix: str) -> list[Path]:
    """
    列出目錄內 ``{prefix}.{ext}`` 與 ``{prefix}_*.{ext}``，合併去重後排序。

    Args:
        prefix: 檔名前綴。

    Returns:
        路徑列表。
    """
    if not _FX_DIR.is_dir():
        return []
    matched: list[Path] = []
    seen: set[str] = set()
    for ext in _FX_EXTS:
        exact = _FX_DIR / f"{prefix}{ext}"
        if exact.is_file():
            key = str(exact.resolve())
            if key not in seen:
                seen.add(key)
                matched.append(exact)
        for p in _FX_DIR.glob(f"{prefix}_*{ext}"):
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                matched.append(p)
    matched.sort(key=_frame_sort_key)
    return matched


def _load_manifest() -> dict[str, list[str]]:
    """
    讀取 ``manifest.json``；檔案變更時重新解析。

    Returns:
        鍵為 ``"1"``～``"8"``、``"1_male"``～``"8_male"``、``"1_female"``～``"8_female"``，值為相對檔名列表。
    """
    global _manifest_entries, _manifest_mtime_ns
    path = _FX_DIR / _MANIFEST_NAME
    if not path.is_file():
        _manifest_entries = {}
        _manifest_mtime_ns = None
        return _manifest_entries
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        _manifest_entries = {}
        _manifest_mtime_ns = None
        return _manifest_entries
    if _manifest_mtime_ns == mtime and _manifest_entries:
        return _manifest_entries
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _manifest_entries = {}
        _manifest_mtime_ns = mtime
        return _manifest_entries
    out: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if not isinstance(k, str):
                continue
            names: list[str] = []
            if isinstance(v, str):
                names = [v]
            elif isinstance(v, list):
                names = [x for x in v if isinstance(x, str)]
            if names:
                out[k] = names
    _manifest_entries = out
    _manifest_mtime_ns = mtime
    return _manifest_entries


def _paths_from_manifest(action_key: int, gender_key: str) -> list[Path]:
    """
    依 manifest 鍵尋找第一個存在的檔案。

    Args:
        action_key: 1～8。
        gender_key: 性別鍵。

    Returns:
        單元素路徑列表或空列表。
    """
    m = _load_manifest()
    if gender_key == "male":
        keys = [f"{action_key}_male", str(action_key)]
    elif gender_key == "female":
        keys = [f"{action_key}_female", str(action_key)]
    else:
        keys = [str(action_key)]
    for key in keys:
        for fn in m.get(key, []):
            p = (_FX_DIR / fn).resolve()
            if p.is_file():
                return [p]
    return []


def _paths_for_action(action_key: int, gender_key: str) -> list[Path]:
    """
    解析某培養動作可能有的圖檔路徑（已排序；載入時只取第一張）。

    Args:
        action_key: 1～8。
        gender_key: 主角性別鍵。

    Returns:
        路徑列表（可能為空）。
    """
    mp = _paths_from_manifest(action_key, gender_key)
    if mp:
        return mp
    if action_key == 1 and gender_key == "male":
        male_paths = _glob_prefix(_READ_MALE_PREFIX)
        if male_paths:
            return male_paths
        return _glob_prefix(_ACTION_FRAME_PREFIX[1])
    if action_key == 1 and gender_key == "female":
        fem_paths = _glob_prefix(_READ_FEMALE_PREFIX)
        if fem_paths:
            return fem_paths
        return _glob_prefix(_ACTION_FRAME_PREFIX[1])
    if action_key == 1:
        return _glob_prefix(_ACTION_FRAME_PREFIX[1])
    if gender_key == "male" and action_key != 1:
        male_pfx = _MALE_ACTION_PREFIX.get(action_key)
        if male_pfx is not None:
            male_paths = _glob_prefix(male_pfx)
            if male_paths:
                return male_paths
    if gender_key == "female" and action_key != 1:
        fem_pfx = _FEMALE_ACTION_PREFIX.get(action_key)
        if fem_pfx is not None:
            fem_paths = _glob_prefix(fem_pfx)
            if fem_paths:
                return fem_paths
    prefix = _ACTION_FRAME_PREFIX.get(action_key)
    if prefix is None:
        return []
    return _glob_prefix(prefix)


def _path_mtime_key(path: Path | None) -> tuple[str, int]:
    """
    供快取鍵使用：路徑字串與修改時間（奈秒）。

    Args:
        path: 圖檔路徑；可為 ``None``。

    Returns:
        ``("", 0)`` 表示無檔；否則 ``(resolve 字串, mtime_ns)``。
    """
    if path is None or not path.is_file():
        return ("", 0)
    try:
        st = path.stat()
        return (str(path.resolve()), int(st.st_mtime_ns))
    except OSError:
        return ("", 0)


def _load_raw_image(action_key: int, *, gender_key: str = "female") -> pygame.Surface | None:
    """
    載入指定培養動作的第一張插圖（快取）。

    Args:
        action_key: 培養 1～8。
        gender_key: ``male``／``female``；依性別優先 ``*_male*``／``*_female*``（鍵 1 為 ``read_male``／``read_female``）。

    Returns:
        成功則為 Surface，否則 ``None``。
    """
    bucket = _raw_image_bucket(action_key, gender_key)
    paths = _paths_for_action(action_key, gender_key)
    path0 = paths[0] if paths else None
    pk = _path_mtime_key(path0)
    ck = (bucket, pk[0], pk[1])
    if ck in _RAW_IMAGE_CACHE:
        return _RAW_IMAGE_CACHE[ck]
    surf: pygame.Surface | None = None
    if path0:
        try:
            surf = pygame.image.load(str(path0)).convert_alpha()
        except (pygame.error, OSError):
            surf = None
    _RAW_IMAGE_CACHE[ck] = surf
    return surf


def _scaled_training_image(
    action_key: int,
    w: int,
    h: int,
    *,
    gender_key: str = "female",
    fit: str = "contain",
) -> pygame.Surface | None:
    """
    將插圖縮放進矩形並快取；``contain`` 完整納入（可能留白），``cover`` 填滿（裁切超出）。

    Args:
        action_key: 培養 1～8。
        w: 目標寬（``cover`` 時輸出即此寬）。
        h: 目標高（``cover`` 時輸出即此高）。
        gender_key: 主角性別（依性別優先 ``*_male*``／``*_female*`` 檔）。
        fit: ``contain`` 或 ``cover``。

    Returns:
        有素材則為 Surface；``contain`` 時可能小於 w×h；``cover`` 時必為 w×h；否則 ``None``。
    """
    bucket = _raw_image_bucket(action_key, gender_key)
    w0, h0 = max(1, w), max(1, h)
    paths = _paths_for_action(action_key, gender_key)
    path0 = paths[0] if paths else None
    pk = _path_mtime_key(path0)
    skey = (bucket, pk[0], pk[1], w0, h0, fit)
    if skey in _SCALED_IMAGE_CACHE:
        return _SCALED_IMAGE_CACHE[skey]
    raw = _load_raw_image(action_key, gender_key=gender_key)
    if raw is None:
        _SCALED_IMAGE_CACHE[skey] = None
        return None
    rw, rh = raw.get_size()
    if rw <= 0 or rh <= 0:
        _SCALED_IMAGE_CACHE[skey] = None
        return None
    if fit == "cover":
        scale = max(w0 / rw, h0 / rh)
        nw = max(w0, int(math.ceil(rw * scale - 1e-9)))
        nh = max(h0, int(math.ceil(rh * scale - 1e-9)))
        scaled = pygame.transform.smoothscale(raw, (nw, nh))
        out = pygame.Surface((w0, h0), pygame.SRCALPHA)
        out.fill((0, 0, 0, 0))
        sx = max(0, (nw - w0) // 2)
        sy = max(0, (nh - h0) // 2)
        out.blit(scaled, (0, 0), pygame.Rect(sx, sy, w0, h0))
        _SCALED_IMAGE_CACHE[skey] = out
        return out
    scale = min(w0 / rw, h0 / rh)
    nw = max(1, int(rw * scale))
    nh = max(1, int(rh * scale))
    out = pygame.transform.smoothscale(raw, (nw, nh))
    _SCALED_IMAGE_CACHE[skey] = out
    return out


def _panel_rect(canvas: pygame.Surface) -> pygame.Rect:
    """
    回傳培養結算回饋插圖面板矩形（右下角，避開最底邊）。

    寬高為原設計的 ``_FEEDBACK_PANEL_SCALE`` 倍。
    """
    w, h = canvas.get_size()
    bw = max(72, w // 5)
    bh = max(52, h // 8)
    sc = _FEEDBACK_PANEL_SCALE
    bw = max(1, int(round(bw * sc)))
    bh = max(1, int(round(bh * sc)))
    margin_r = 14
    margin_b = 78
    x = w - bw - margin_r
    y = h - bh - margin_b
    x = max(8, min(x, w - bw - 8))
    y = max(8, min(y, h - bh - 8))
    return pygame.Rect(x, y, bw, bh)


def _draw_book(surf: pygame.Surface, t: float) -> None:
    """深度閱讀／靜心抄寫：翻頁與墨點。"""
    r = surf.get_rect()
    page_w = r.w // 3
    l = pygame.Rect(r.centerx - page_w - 4, r.centery - 12, page_w, 24)
    rr = pygame.Rect(r.centerx + 4, r.centery - 12, page_w, 24)
    pygame.draw.rect(surf, (230, 228, 215), l, border_radius=4)
    pygame.draw.rect(surf, (230, 228, 215), rr, border_radius=4)
    pygame.draw.line(surf, (160, 140, 120), (r.centerx, l.y), (r.centerx, l.bottom), 2)
    y = int(r.centery - 8 + math.sin(t * 7.0) * 6)
    pygame.draw.circle(surf, (80, 60, 45), (r.centerx + 18, y), 3)


def _draw_dumbbell(surf: pygame.Surface, t: float) -> None:
    """體能訓練／獨處鍛鍊：啞鈴上下震動。"""
    r = surf.get_rect()
    dy = int(math.sin(t * 9.0) * 6)
    y = r.centery + dy
    pygame.draw.line(surf, (185, 195, 210), (r.centerx - 20, y), (r.centerx + 20, y), 4)
    pygame.draw.rect(surf, (120, 130, 150), (r.centerx - 30, y - 10, 8, 20), border_radius=2)
    pygame.draw.rect(surf, (120, 130, 150), (r.centerx - 22, y - 8, 6, 16), border_radius=2)
    pygame.draw.rect(surf, (120, 130, 150), (r.centerx + 16, y - 8, 6, 16), border_radius=2)
    pygame.draw.rect(surf, (120, 130, 150), (r.centerx + 22, y - 10, 8, 20), border_radius=2)


def _draw_prayer(surf: pygame.Surface, t: float) -> None:
    """聖堂祈禱：十字光與呼吸感。"""
    r = surf.get_rect()
    glow = 130 + int(40 * (0.5 + 0.5 * math.sin(t * 5.5)))
    c = (glow, glow, 120)
    pygame.draw.line(surf, c, (r.centerx, r.centery - 16), (r.centerx, r.centery + 16), 3)
    pygame.draw.line(surf, c, (r.centerx - 10, r.centery), (r.centerx + 10, r.centery), 3)
    pygame.draw.circle(surf, (220, 210, 150, 90), (r.centerx, r.centery), 18, 1)


def _draw_chat(surf: pygame.Surface, t: float) -> None:
    """同儕相聚：雙對話框輕微位移。"""
    r = surf.get_rect()
    dx = int(math.sin(t * 6.0) * 4)
    a = pygame.Rect(r.centerx - 28 + dx, r.centery - 14, 24, 16)
    b = pygame.Rect(r.centerx + 4 - dx, r.centery - 2, 24, 16)
    pygame.draw.rect(surf, (170, 210, 255), a, border_radius=5)
    pygame.draw.rect(surf, (210, 175, 255), b, border_radius=5)
    pygame.draw.polygon(
        surf, (170, 210, 255), [(a.x + 6, a.bottom), (a.x + 10, a.bottom), (a.x + 8, a.bottom + 4)]
    )
    pygame.draw.polygon(
        surf, (210, 175, 255), [(b.right - 10, b.bottom), (b.right - 6, b.bottom), (b.right - 8, b.bottom + 4)]
    )


def _draw_work(surf: pygame.Surface, t: float) -> None:
    """幫忙營生：工具輪轉感。"""
    r = surf.get_rect()
    ang = t * 4.0
    for i in range(4):
        a = ang + i * (math.pi / 2)
        x = int(r.centerx + math.cos(a) * 14)
        y = int(r.centery + math.sin(a) * 14)
        pygame.draw.line(surf, (220, 190, 140), (r.centerx, r.centery), (x, y), 3)
    pygame.draw.circle(surf, (130, 100, 70), (r.centerx, r.centery), 5)


def _draw_visit(surf: pygame.Surface, t: float) -> None:
    """義工走訪：腳步點亮效果。"""
    r = surf.get_rect()
    base = r.centery + 10
    for i in range(4):
        x = r.centerx - 22 + i * 14
        lit = (int(t * 8.0) + i) % 4 == 0
        color = (230, 220, 165) if lit else (120, 130, 145)
        pygame.draw.circle(surf, color, (x, base - (i % 2) * 6), 4)


def _paint_feedback_box_surface(
    box: pygame.Surface,
    action_key: int,
    now_ms: int,
    *,
    gender_key: str,
    image_fit: str = "contain",
    image_margin: int = 5,
) -> None:
    """
    在已建立的 RGBA Surface 上繪製培養回饋：有插圖則透明底；否則深色底框＋向量圖示。

    Args:
        box: 目標平面。
        action_key: 培養 1～8。
        now_ms: 毫秒時間（向量圖示動態用）。
        gender_key: 主角性別。
        image_fit: 點陣圖適配方式，``contain`` 或 ``cover``。
        image_margin: 插圖區與盒緣內縮像素（每邊；向量回退時仍用整盒）。
    """
    m = max(0, image_margin)
    iw = max(8, box.get_width() - 2 * m)
    ih = max(8, box.get_height() - 2 * m)
    img = _scaled_training_image(
        action_key, iw, ih, gender_key=gender_key, fit=image_fit
    )
    if img is not None:
        box.fill((0, 0, 0, 0))
        if image_fit == "cover" and img.get_size() == (iw, ih):
            box.blit(img, (m, m))
        else:
            box.blit(
                img,
                (
                    m + (iw - img.get_width()) // 2,
                    m + (ih - img.get_height()) // 2,
                ),
            )
        return

    t = now_ms / 1000.0
    box.fill((32, 38, 50, 210))
    pygame.draw.rect(box, (110, 124, 155), box.get_rect(), width=2, border_radius=8)
    pygame.draw.rect(box, (255, 255, 255, 20), box.get_rect().inflate(-8, -8), border_radius=6)

    if action_key in (1, 6):
        _draw_book(box, t)
    elif action_key in (2, 8):
        _draw_dumbbell(box, t)
    elif action_key == 3:
        _draw_prayer(box, t)
    elif action_key == 4:
        _draw_chat(box, t)
    elif action_key == 5:
        _draw_work(box, t)
    elif action_key == 7:
        _draw_visit(box, t)


def draw_training_feedback_fx_into_rect(
    canvas: pygame.Surface,
    dest_rect: pygame.Rect,
    action_key: int,
    now_ms: int,
    *,
    gender_key: str = "female",
    image_fit: str = "contain",
    image_margin: int = 5,
) -> None:
    """
    將培養回饋插圖／向量繪入畫布上指定矩形（例如 toast 右欄）。

    Args:
        canvas: 邏輯畫布。
        dest_rect: 區域。
        action_key: 培養 1～8。
        now_ms: 毫秒時間。
        gender_key: 主角性別。
        image_fit: 點陣圖 ``contain``（完整顯示、可留白）或 ``cover``（填滿裁切）。
        image_margin: 插圖區每邊內縮像素。
    """
    if dest_rect.w <= 0 or dest_rect.h <= 0:
        return
    box = pygame.Surface((dest_rect.w, dest_rect.h), pygame.SRCALPHA)
    _paint_feedback_box_surface(
        box,
        action_key,
        now_ms,
        gender_key=gender_key,
        image_fit=image_fit,
        image_margin=image_margin,
    )
    canvas.blit(box, dest_rect.topleft)


def draw_training_feedback_fx(
    canvas: pygame.Surface,
    action_key: int,
    now_ms: int,
    panel_rect: pygame.Rect | None = None,
    *,
    gender_key: str = "female",
) -> None:
    """
    繪製培養結算回饋（右下角或自訂矩形）：插圖優先，否則向量圖示。

    Args:
        canvas: 邏輯畫布。
        action_key: 培養選項 1～8。
        now_ms: 目前毫秒時間。
        panel_rect: 自訂矩形；``None`` 時用內建右下角位置。
        gender_key: 主角性別；依性別優先 ``*_male*``／``*_female*`` 檔。
    """
    panel = _panel_rect(canvas) if panel_rect is None else panel_rect
    box = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
    _paint_feedback_box_surface(box, action_key, now_ms, gender_key=gender_key)
    canvas.blit(box, panel.topleft)
