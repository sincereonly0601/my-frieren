"""
重大事件插圖：前言／結語階段上方區塊的像素風場景（原創，氛圍取向邊境遺跡、公會、北境）。
"""

from __future__ import annotations

import pygame


def draw_major_event_illustration(
    target: pygame.Surface,
    rect: pygame.Rect,
    *,
    age_year: int,
    is_resolution: bool,
    choice_index: int,
    tick: int,
) -> None:
    """
    在指定矩形內繪製重大事件對應插圖。

    Args:
        target: 主畫布。
        rect: 插圖區域。
        age_year: 8／13／18。
        is_resolution: True 為選後結語用圖，False 為前言。
        choice_index: 結語時 0～2（前言時忽略）。
        tick: 影格計數。
    """
    w, h = rect.width, rect.height
    surf = pygame.Surface((w, h))

    if age_year == 8:
        _draw_ruin_stone(surf, w, h, tick, is_resolution, choice_index)
    elif age_year == 13:
        _draw_guild_hall(surf, w, h, tick, is_resolution, choice_index)
    else:
        _draw_north_board(surf, w, h, tick, is_resolution, choice_index)

    pygame.draw.rect(surf, (18, 22, 30), (0, 0, w, 3))
    pygame.draw.rect(surf, (18, 22, 30), (0, h - 3, w, 3))
    pygame.draw.rect(surf, (18, 22, 30), (0, 0, 3, h))
    pygame.draw.rect(surf, (18, 22, 30), (w - 3, 0, 3, h))
    target.blit(surf, rect.topleft)


def _accent(choice_index: int, is_resolution: bool) -> tuple[int, int, int]:
    """結語時依選項略變色調。"""
    if not is_resolution:
        return (120, 128, 150)
    if choice_index == 0:
        return (130, 160, 210)
    if choice_index == 1:
        return (200, 120, 110)
    return (200, 185, 130)


def _draw_ruin_stone(
    surf: pygame.Surface, w: int, h: int, tick: int, is_res: bool, ch: int
) -> None:
    """遺跡石室與符文牆。"""
    acc = _accent(ch, is_res)
    for yy in range(h):
        t = yy / max(h, 1)
        surf.fill(
            (int(28 + t * 22), int(32 + t * 18), int(48 + t * 25)),
            (0, yy, w, 1),
        )
    pygame.draw.polygon(surf, (42, 48, 58), [(0, h), (w // 2, h // 2), (w, h)])
    wx = w // 2 - 70
    pygame.draw.rect(surf, (55, 58, 68), (wx, h // 4, 140, h - h // 4))
    pygame.draw.rect(surf, (72, 76, 88), (wx + 12, h // 4 + 16, 116, h - h // 4 - 28))
    for i in range(6):
        for j in range(8):
            if (i + j + tick // 20) % 3 != 0:
                continue
            sx = wx + 24 + j * 14
            sy = h // 4 + 28 + i * 16
            pygame.draw.rect(surf, acc, (sx, sy, 6, 4))
    pygame.draw.circle(surf, (255, 220, 160), (w // 2 - 40, h // 3), 6)
    pygame.draw.circle(surf, (255, 235, 200), (w // 2 - 40, h // 3), 3)


def _draw_guild_hall(
    surf: pygame.Surface, w: int, h: int, tick: int, is_res: bool, ch: int
) -> None:
    """公會試問長桌。"""
    acc = _accent(ch, is_res)
    surf.fill((40, 44, 56))
    pygame.draw.rect(surf, (52, 56, 70), (0, h // 2, w, h // 2))
    pygame.draw.rect(surf, (70, 74, 90), (w // 8, h // 3, w * 3 // 4, h // 3))
    pygame.draw.rect(surf, (45, 50, 62), (w // 8, h // 3 + 8, w * 3 // 4, 8))
    for i in range(3):
        x0 = w // 6 + i * (w // 4)
        pygame.draw.rect(surf, (85, 90, 108), (x0, h // 4, 28, 40))
        pygame.draw.rect(surf, acc, (x0 + 8, h // 4 + 10, 12, 8))
    pygame.draw.line(surf, (200, 200, 210), (w // 8, h * 2 // 3), (w * 7 // 8, h * 2 // 3), 2)
    tw = 2 + (tick // 15) % 3
    pygame.draw.line(surf, (255, 240, 200), (w // 2, h // 2), (w // 2, h // 2 + 20), tw)


def _draw_north_board(
    surf: pygame.Surface, w: int, h: int, tick: int, is_res: bool, ch: int
) -> None:
    """告示與遠山／路標。"""
    acc = _accent(ch, is_res)
    for yy in range(h):
        surf.fill((int(50 + yy * 40 // h), int(60 + yy * 35 // h), int(85 + yy * 30 // h)), (0, yy, w, 1))
    pygame.draw.polygon(surf, (70, 80, 100), [(w, h // 2), (w, h), (w * 2 // 3, h)])
    pygame.draw.rect(surf, (48, 42, 38), (w // 4, h // 3, w // 2, h // 2))
    pygame.draw.rect(surf, (220, 210, 185), (w // 4 + 8, h // 3 + 8, w // 2 - 16, h // 2 - 16))
    for dy in range(0, 40, 10):
        pygame.draw.line(surf, (90, 85, 78), (w // 4 + 16, h // 3 + 20 + dy), (w * 3 // 4 - 16, h // 3 + 20 + dy), 1)
    pygame.draw.rect(surf, acc, (w // 4 + 12, h // 3 + 12, 24, 12))
    pygame.draw.polygon(surf, (200, 60, 55), [(w * 3 // 4, h // 3), (w * 3 // 4 + 8, h // 3), (w * 3 // 4 + 4, h // 3 - 14)])
