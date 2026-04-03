"""
開場三頁插圖：以矩形／色塊拼組的像素風場景（原創構圖，氛圍取向奇幻旅途與靜謐日常）。
"""

from __future__ import annotations

import pygame


def _pixel_hline(surf: pygame.Surface, y: int, x0: int, x1: int, color: tuple[int, int, int], step: int = 2) -> None:
    """以固定步長畫水平粗線，維持像素感。"""
    for x in range(x0, x1, step):
        pygame.draw.rect(surf, color, (x, y, step, step))


def _draw_scene_winter_bridge(surf: pygame.Surface, w: int, h: int, tick: int) -> None:
    """
    第一頁：冬夜將盡、石橋與遠林（邊境與失去）。

    Args:
        surf: 目標平面。
        w: 寬度。
        h: 高度。
        tick: 影格計數（星光微動）。
    """
    for yy in range(0, h, 3):
        t = yy / max(h, 1)
        c = (
            int(32 + t * 40),
            int(38 + t * 35),
            int(58 + t * 45),
        )
        _pixel_hline(surf, yy, 0, w, c, 3)

    horizon = int(h * 0.62)
    for yy in range(horizon, h, 2):
        g = 200 + (yy - horizon) % 20
        _pixel_hline(surf, yy, 0, w, (g, g, 210), 4)

    bx, by, bw, bh = w // 2 - 80, horizon - 24, 160, 8
    pygame.draw.rect(surf, (72, 78, 92), (bx, by, bw, bh))
    pygame.draw.rect(surf, (52, 58, 70), (bx + 20, by - 16, 12, 16))
    pygame.draw.rect(surf, (52, 58, 70), (bx + bw - 32, by - 16, 12, 16))

    for i in range(8):
        tx = 40 + i * 48
        pygame.draw.rect(surf, (28, 34, 48), (tx, horizon - 40 - (i % 3) * 8, 14, 40))

    pygame.draw.rect(surf, (24, 22, 30), (w // 2 - 6, horizon - 52, 12, 28))
    pygame.draw.rect(surf, (20, 18, 26), (w // 2 - 18, horizon - 36, 36, 10))

    for s in range(12):
        sx = (s * 73 + tick // 6) % (w - 8)
        sy = 20 + (s * 37) % (horizon - 40)
        br = 2 if (tick // 10 + s) % 3 == 0 else 1
        pygame.draw.rect(surf, (220, 228, 255), (sx, sy, br, br))


def _draw_scene_sanctuary(surf: pygame.Surface, w: int, h: int, tick: int) -> None:
    """
    第二頁：聖堂高窗與燭火（收容與祈願）。

    Args:
        surf: 目標平面。
        w: 寬度。
        h: 高度。
        tick: 影格計數（燭火搖曳）。
    """
    surf.fill((36, 40, 52))
    for yy in range(0, h, 4):
        for xx in range(0, w, 8):
            c = (42, 46, 58) if ((xx // 8 + yy // 4) % 2) == 0 else (34, 38, 50)
            pygame.draw.rect(surf, c, (xx, yy, 8, 4))

    wx0, wy0 = w // 2 - 70, 36
    ww, wh = 140, h - 80
    pygame.draw.rect(surf, (55, 68, 98), (wx0, wy0, ww, wh))
    pygame.draw.rect(surf, (78, 110, 150), (wx0 + 10, wy0 + 14, ww - 20, wh - 28))
    pygame.draw.rect(surf, (48, 58, 78), (wx0 + ww // 2 - 3, wy0 + 10, 6, wh - 20))
    pygame.draw.rect(surf, (48, 58, 78), (wx0 + 12, wy0 + wh // 2 - 3, ww - 24, 6))

    flick = (tick // 5) % 3
    cx, cy = w // 2, h - 34
    layers = [(28, (90, 70, 45)), (20, (150, 110, 55)), (14, (210, 160, 70)), (8, (255, 220 + flick * 8, 140))]
    for size, col in layers:
        pygame.draw.rect(surf, col, (cx - size // 2, cy - size // 2, size, size))

    pygame.draw.rect(surf, (180, 140, 70), (w // 2 - 8, h - 52, 16, 28))
    pygame.draw.rect(surf, (255, 230, 160), (w // 2 - 4, h - 58, 8, 8))

    pygame.draw.rect(surf, (90, 88, 100), (24, h - 70, w - 48, 10))


def _draw_scene_bakery(surf: pygame.Surface, w: int, h: int, tick: int) -> None:
    """
    第三頁：夜窗外的麵包店暖光（平凡與歸屬）。

    Args:
        surf: 目標平面。
        w: 寬度。
        h: 高度。
        tick: 影格計數（麵包熱氣）。
    """
    surf.fill((28, 36, 58))
    for yy in range(0, h, 2):
        _pixel_hline(surf, yy, 0, w // 2 - 4, (26, 34, 56), 2)

    ix0 = w // 2 - 4
    pygame.draw.rect(surf, (62, 48, 38), (ix0, 24, w - ix0 - 16, h - 48))
    pygame.draw.rect(surf, (120, 88, 55), (ix0 + 12, 40, w - ix0 - 40, h - 88))

    pygame.draw.rect(surf, (200, 170, 90), (ix0 + 28, 52, w - ix0 - 72, h - 120))
    pygame.draw.rect(surf, (42, 52, 72), (ix0 + 36, 60, (w - ix0) // 2 - 30, (h - 140) // 2))

    pygame.draw.rect(surf, (110, 72, 48), (ix0 + 44, h - 100, 36, 22))
    pygame.draw.rect(surf, (130, 88, 55), (ix0 + 88, h - 96, 32, 18))
    pygame.draw.rect(surf, (100, 66, 42), (ix0 + 130, h - 102, 28, 24))

    st = tick // 4
    for i in range(4):
        pygame.draw.rect(
            surf,
            (240, 248, 255),
            (ix0 + 60 + i * 14, 70 - ((st + i) % 6), 3, 3),
        )

    pygame.draw.rect(surf, (48, 42, 38), (ix0 + 8, h - 36, w - ix0 - 24, 8))


def _draw_scene_guardian_notice(surf: pygame.Surface, w: int, h: int, tick: int) -> None:
    """
    監護人須知用插圖：室內桌邊、暖窗、卷軸／紙張與一大一小剪影（原創色塊構圖）。

    Args:
        surf: 目標平面。
        w: 寬度。
        h: 高度。
        tick: 影格（燈光微動）。
    """
    surf.fill((38, 44, 62))
    for yy in range(0, h, 4):
        t = yy / max(h, 1)
        c = (int(36 + t * 8), int(42 + t * 10), int(58 + t * 12))
        pygame.draw.rect(surf, c, (0, yy, w, 4))

    wx, wy, ww, wh = w // 2 - w * 14 // 100, h // 12, w * 28 // 100, h * 32 // 100
    pygame.draw.rect(surf, (72, 82, 100), (wx, wy, ww, wh))
    pygame.draw.rect(surf, (255, 236, 210), (wx + 8, wy + 10, ww - 16, wh - 20))
    pygame.draw.rect(surf, (255, 248, 220), (wx + 12, wy + 14, ww - 24, wh - 28))

    table_y = h * 62 // 100
    pygame.draw.rect(surf, (52, 44, 38), (w * 18 // 100, table_y, w * 64 // 100, h * 4 // 100))
    pygame.draw.rect(surf, (48, 40, 36), (w * 16 // 100, table_y + h * 4 // 100, w * 68 // 100, h * 3 // 100))

    sx = w // 2 - 36
    pygame.draw.rect(surf, (245, 240, 228), (sx, table_y - h * 14 // 100, 72, h * 12 // 100))
    pygame.draw.rect(surf, (200, 195, 185), (sx + 4, table_y - h * 14 // 100 + 4, 64, 4))

    lamp_x = w * 72 // 100
    pygame.draw.rect(surf, (55, 50, 45), (lamp_x, table_y - h * 22 // 100, 10, h * 18 // 100))
    pygame.draw.circle(surf, (255, 230, 160), (lamp_x + 5, table_y - h * 24 // 100), 8 + (tick // 18) % 2)

    pygame.draw.ellipse(surf, (32, 36, 48), (w * 28 // 100, table_y - h * 20 // 100, w * 10 // 100, h * 22 // 100))
    pygame.draw.ellipse(surf, (42, 46, 58), (w * 58 // 100, table_y - h * 16 // 100, w * 8 // 100, h * 18 // 100))


def draw_guardian_illustration(target: pygame.Surface, rect: pygame.Rect, tick: int) -> None:
    """
    在指定矩形內繪製「監護人須知」像素風插圖。

    Args:
        target: 主畫布。
        rect: 插圖區域。
        tick: 主迴圈遞增計數。
    """
    w, h = rect.width, rect.height
    surf = pygame.Surface((w, h))
    _draw_scene_guardian_notice(surf, w, h, tick)
    pygame.draw.rect(surf, (18, 20, 28), (0, 0, w, 3))
    pygame.draw.rect(surf, (18, 20, 28), (0, h - 3, w, 3))
    pygame.draw.rect(surf, (18, 20, 28), (0, 0, 3, h))
    pygame.draw.rect(surf, (18, 20, 28), (w - 3, 0, 3, h))
    target.blit(surf, rect.topleft)


def draw_prologue_illustration(target: pygame.Surface, rect: pygame.Rect, page_index: int, tick: int) -> None:
    """
    在指定矩形內繪製對應頁的像素風插圖。

    Args:
        target: 主畫布。
        rect: 插圖區域（通常為畫面上方區塊）。
        page_index: 0～2 對應三頁故事。
        tick: 主迴圈遞增計數，供微動畫使用。
    """
    w, h = rect.width, rect.height
    surf = pygame.Surface((w, h))
    if page_index <= 0:
        _draw_scene_winter_bridge(surf, w, h, tick)
    elif page_index == 1:
        _draw_scene_sanctuary(surf, w, h, tick)
    else:
        _draw_scene_bakery(surf, w, h, tick)

    pygame.draw.rect(surf, (18, 20, 28), (0, 0, w, 3))
    pygame.draw.rect(surf, (18, 20, 28), (0, h - 3, w, 3))
    pygame.draw.rect(surf, (18, 20, 28), (0, 0, 3, h))
    pygame.draw.rect(surf, (18, 20, 28), (w - 3, 0, 3, h))
    target.blit(surf, rect.topleft)
