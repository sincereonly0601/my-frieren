"""
突發事件右下角小插圖：依事件 id 以向量／色塊拼出象徵圖（與內文主題對應，非寫實）。
"""

from __future__ import annotations

import pygame

# 內部點陣解析度（設計稿以 100 邏輯單位構圖，再依此尺寸繪製後縮放至畫面上的方框）。
# 使用最近鄰縮放（scale）而非 smoothscale，避免插值柔化導致圖示看起來糊。
_GLYPH_BASE_PX: int = 200


def draw_incident_illustration(
    surface: pygame.Surface,
    rect: pygame.Rect,
    incident_id: str,
) -> None:
    """
    在指定矩形內繪製與該突發事件對應的小圖。

    構圖為正方形，縮放採「contain」：等比例縮小以完整放入 rect，並於 rect 內水平／垂直置中，
    避免餘韻橫幅等非正方形區域將圖拉扁或拉長。

    Args:
        surface: 邏輯畫布。
        rect: 插圖區域（邏輯座標）。
        incident_id: `IncidentEvent.id`（例如 ``t1_01``）。
    """
    w, h = rect.w, rect.h
    if w < 16 or h < 16:
        return
    b = _GLYPH_BASE_PX
    inner = pygame.Surface((b, b), pygame.SRCALPHA)
    inner.fill((36, 42, 56, 255))
    edge = max(2, int(round(2 * b / 100)))
    inset = max(1, int(round(1 * b / 100)))
    pygame.draw.rect(inner, (95, 82, 62), (0, 0, b, b), edge)
    pygame.draw.rect(
        inner,
        (55, 62, 78),
        (edge, edge, b - 2 * edge, b - 2 * edge),
        inset,
    )
    _dispatch_incident_glyph(inner, incident_id, b, b)
    fit = min(w / b, h / b)
    nw = max(1, int(round(b * fit)))
    nh = max(1, int(round(b * fit)))
    scaled = pygame.transform.scale(inner, (nw, nh))
    x0 = rect.x + (w - nw) // 2
    y0 = rect.y + (h - nh) // 2
    surface.blit(scaled, (x0, y0))


def _dispatch_incident_glyph(surf: pygame.Surface, incident_id: str, w: int, h: int) -> None:
    """
    依事件 id 在 surf 上繪製圖形（座標相對於 surf 左上）。

    構圖以 100×100 設計稿為基準，經 s() 依實際 w 縮放（w、h 須為正方形）。

    Args:
        surf: 與插圖同尺寸的緩衝平面。
        incident_id: 事件鍵。
        w: 寬。
        h: 高。
    """
    scale = w / 100.0

    def s(v: float) -> int:
        return int(round(v * scale))

    cx, cy = w // 2, h // 2
    lw = lambda n: max(1, s(n))

    match incident_id:
        case "t1_01":
            pygame.draw.ellipse(surf, (88, 72, 52), (cx + s(-22), cy + s(-8), s(44), s(36)))
            pygame.draw.rect(surf, (62, 52, 40), (cx + s(-6), cy + s(-18), s(12), s(14)))
            pygame.draw.line(
                surf,
                (140, 120, 90),
                (cx + s(-18), cy + s(4)),
                (cx + s(18), cy + s(4)),
                lw(2),
            )
        case "t1_02":
            pygame.draw.rect(surf, (78, 62, 48), (cx + s(-8), cy + s(8), s(16), s(24)))
            pygame.draw.circle(surf, (92, 76, 58), (cx, cy + s(-8)), s(14))
            pygame.draw.line(
                surf,
                (70, 58, 45),
                (cx + s(-20), cy + s(-2)),
                (cx + s(20), cy + s(-2)),
                lw(3),
            )
        case "t1_03":
            pygame.draw.rect(surf, (58, 52, 70), (cx + s(-28), cy + s(10), s(56), s(8)))
            pygame.draw.rect(surf, (200, 175, 120), (cx + s(-16), cy + s(-4), s(32), s(14)))
            pygame.draw.rect(surf, (180, 160, 210), (cx + s(-4), cy + s(-22), s(8), s(20)))
        case "t1_04":
            pygame.draw.ellipse(surf, (120, 100, 70), (cx + s(-18), cy + s(-6), s(36), s(22)))
            pygame.draw.circle(surf, (90, 85, 78), (cx + s(10), cy + s(-10)), s(10))
            pygame.draw.circle(surf, (40, 40, 45), (cx + s(14), cy + s(-12)), max(1, s(2)))
        case "t1_05":
            pygame.draw.rect(surf, (52, 48, 40), (cx + s(4), cy + s(-4), s(28), s(18)))
            for ox in (-18, -8, 2):
                pygame.draw.line(
                    surf,
                    (70, 120, 70),
                    (cx + s(ox), cy + s(8)),
                    (cx + s(ox - 6), cy + s(-14)),
                    lw(3),
                )
        case "t1_06":
            pygame.draw.line(
                surf,
                (90, 80, 65),
                (cx + s(-20), cy + s(16)),
                (cx + s(-20), cy + s(-20)),
                lw(3),
            )
            pygame.draw.line(
                surf,
                (90, 80, 65),
                (cx + s(20), cy + s(16)),
                (cx + s(20), cy + s(-20)),
                lw(3),
            )
            pygame.draw.polygon(
                surf,
                (160, 90, 90),
                [
                    (cx + s(-20), cy + s(-20)),
                    (cx + s(-4), cy + s(-14)),
                    (cx + s(-20), cy + s(-8)),
                ],
            )
            pygame.draw.polygon(
                surf,
                (90, 110, 160),
                [
                    (cx + s(20), cy + s(-20)),
                    (cx + s(4), cy + s(-14)),
                    (cx + s(20), cy + s(-8)),
                ],
            )
        case "t1_07":
            pygame.draw.rect(surf, (52, 58, 78), (cx + s(-18), cy + s(-22), s(36), s(44)))
            pygame.draw.line(
                surf,
                (200, 200, 220),
                (cx, cy + s(-18)),
                (cx, cy + s(18)),
                lw(1),
            )
            pygame.draw.circle(surf, (220, 200, 120), (cx + s(-6), cy + s(-8)), s(4))
        case "t1_08":
            pygame.draw.rect(surf, (70, 62, 52), (cx + s(-26), cy + s(-20), s(22), s(36)))
            pygame.draw.rect(surf, (45, 42, 38), (cx + s(4), cy + s(-6), s(20), s(24)))
            pygame.draw.line(
                surf,
                (140, 120, 90),
                (cx + s(14), cy + s(-10)),
                (cx + s(14), cy + s(10)),
                lw(1),
            )
        case "t1_09":
            pygame.draw.circle(surf, (75, 82, 98), (cx + s(-16), cy + s(4)), s(10))
            pygame.draw.circle(surf, (75, 82, 98), (cx + s(16), cy + s(4)), s(10))
            pygame.draw.rect(surf, (200, 210, 255), (cx + s(-2), cy + s(-18), s(4), s(4)))
        case "t1_10":
            pygame.draw.rect(surf, (40, 44, 58), (cx + s(-24), cy + s(-20), s(48), s(40)))
            pygame.draw.rect(surf, (70, 90, 120), (cx + s(-18), cy + s(-14), s(36), s(28)))
            pygame.draw.circle(surf, (220, 230, 245), (cx + s(14), cy + s(-14)), s(8))
        case "t2_01":
            pygame.draw.rect(surf, (240, 236, 228), (cx + s(-22), cy + s(-18), s(40), s(36)))
            for dy in (-10, -4, 2, 8):
                pygame.draw.line(
                    surf,
                    (100, 100, 110),
                    (cx + s(-16), cy + s(dy)),
                    (cx + s(12), cy + s(dy)),
                    lw(1),
                )
            pygame.draw.polygon(
                surf,
                (60, 58, 55),
                [
                    (cx + s(18), cy + s(12)),
                    (cx + s(28), cy + s(8)),
                    (cx + s(22), cy + s(2)),
                ],
            )
        case "t2_02":
            pygame.draw.rect(surf, (55, 50, 48), (cx + s(8), cy + s(-22), s(20), s(44)))
            pygame.draw.circle(surf, (80, 88, 102), (cx + s(-12), cy + s(6)), s(12))
            pygame.draw.rect(surf, (45, 48, 58), (cx + s(-18), cy + s(10), s(12), s(18)))
        case "t2_03":
            pygame.draw.rect(surf, (62, 48, 42), (cx + s(-8), cy + s(-24), s(16), s(48)))
            pygame.draw.rect(surf, (200, 185, 140), (cx + s(-20), cy + s(-18), s(40), s(26)))
            pygame.draw.line(
                surf,
                (60, 50, 45),
                (cx + s(-14), cy + s(-10)),
                (cx + s(14), cy + s(-10)),
                lw(2),
            )
        case "t2_04":
            pygame.draw.polygon(
                surf,
                (120, 160, 220),
                [
                    (cx, cy + s(-22)),
                    (cx + s(18), cy + s(-4)),
                    (cx + s(10), cy + s(20)),
                    (cx + s(-10), cy + s(20)),
                    (cx + s(-18), cy + s(-4)),
                ],
            )
            pygame.draw.polygon(
                surf,
                (80, 110, 160),
                [
                    (cx, cy + s(-18)),
                    (cx + s(12), cy + s(-4)),
                    (cx, cy + s(12)),
                    (cx + s(-12), cy + s(-4)),
                ],
            )
        case "t2_05":
            pygame.draw.rect(surf, (48, 44, 40), (cx + s(-20), cy + s(-22), s(40), s(44)))
            for i in range(5):
                pygame.draw.circle(
                    surf,
                    (200, 190, 120),
                    (cx + s(-10 + (i % 3) * 10), cy + s(-12 + (i // 3) * 10)),
                    max(1, s(2)),
                )
        case "t2_06":
            pygame.draw.rect(surf, (52, 48, 42), (cx + s(-22), cy + s(-18), s(44), s(36)))
            pygame.draw.line(
                surf,
                (90, 85, 75),
                (cx + s(-16), cy + s(-8)),
                (cx + s(16), cy + s(-8)),
                lw(1),
            )
            pygame.draw.circle(surf, (220, 190, 100), (cx + s(14), cy + s(12)), s(7))
        case "t2_07":
            pygame.draw.arc(
                surf,
                (180, 180, 200),
                (cx + s(-20), cy + s(-8), s(40), s(30)),
                0.2,
                2.8,
                lw(2),
            )
            pygame.draw.circle(surf, (100, 200, 255), (cx, cy + s(10)), s(10))
            pygame.draw.circle(surf, (200, 240, 255), (cx, cy + s(10)), s(4))
        case "t2_08":
            pygame.draw.line(
                surf,
                (80, 70, 58),
                (cx, cy + s(-22)),
                (cx + s(-16), cy + s(22)),
                lw(3),
            )
            pygame.draw.line(
                surf,
                (80, 70, 58),
                (cx, cy + s(-22)),
                (cx + s(16), cy + s(22)),
                lw(3),
            )
            pygame.draw.rect(surf, (120, 110, 100), (cx + s(-14), cy + s(-20), s(28), s(22)))
        case "t2_09":
            pygame.draw.ellipse(surf, (90, 72, 55), (cx + s(-24), cy + s(-4), s(30), s(22)))
            pygame.draw.rect(surf, (240, 236, 228), (cx + s(2), cy + s(-18), s(22), s(36)))
            pygame.draw.line(
                surf,
                (80, 80, 88),
                (cx + s(6), cy + s(-10)),
                (cx + s(20), cy + s(-10)),
                lw(1),
            )
        case "t2_10":
            pygame.draw.rect(surf, (200, 60, 60), (cx + s(-14), cy + s(-22), s(28), s(40)))
            pygame.draw.line(
                surf,
                (40, 40, 45),
                (cx + s(-10), cy + s(-16)),
                (cx + s(10), cy + s(14)),
                lw(3),
            )
            pygame.draw.line(
                surf,
                (40, 40, 45),
                (cx + s(10), cy + s(-16)),
                (cx + s(-10), cy + s(14)),
                lw(3),
            )
        case "t3_01":
            pygame.draw.rect(surf, (235, 230, 218), (cx + s(-22), cy + s(-16), s(44), s(32)))
            pygame.draw.circle(surf, (140, 50, 45), (cx, cy + s(2)), s(9))
            pygame.draw.polygon(
                surf,
                (160, 60, 55),
                [(cx, cy + s(-4)), (cx + s(5), cy + s(6)), (cx + s(-5), cy + s(6))],
            )
        case "t3_02":
            pygame.draw.rect(surf, (58, 52, 48), (cx + s(-20), cy + s(-14), s(40), s(30)))
            pygame.draw.circle(surf, (200, 180, 90), (cx + s(12), cy + s(-18)), s(6))
            pygame.draw.rect(surf, (200, 180, 90), (cx + s(12), cy + s(-18), s(4), s(14)))
        case "t3_03":
            pygame.draw.circle(surf, (220, 210, 180), (cx + s(-14), cy + s(-10)), s(12))
            pygame.draw.rect(surf, (90, 85, 95), (cx + s(-4), cy + s(-6), s(24), s(28)))
            pygame.draw.rect(surf, (70, 68, 82), (cx + s(-8), cy + s(8), s(32), s(10)))
        case "t3_04":
            pygame.draw.polygon(
                surf,
                (180, 160, 200),
                [
                    (cx + s(-6), cy + s(-18)),
                    (cx + s(6), cy + s(-18)),
                    (cx + s(4), cy + s(8)),
                    (cx + s(-4), cy + s(8)),
                ],
            )
            pygame.draw.rect(surf, (120, 100, 90), (cx + s(-2), cy + s(8), s(4), s(14)))
            pygame.draw.circle(surf, (255, 220, 140), (cx + s(16), cy + s(-8)), s(8))
        case "t3_05":
            pygame.draw.polygon(
                surf,
                (100, 85, 70),
                [(cx, cy + s(-20)), (cx + s(-22), cy + s(8)), (cx + s(22), cy + s(8))],
            )
            pygame.draw.rect(surf, (85, 78, 68), (cx + s(-16), cy + s(8), s(32), s(22)))
            pygame.draw.circle(surf, (120, 130, 150), (cx + s(18), cy + s(-8)), s(10), lw(2))
        case "t3_06":
            pygame.draw.polygon(
                surf,
                (95, 90, 110),
                [(cx, cy + s(-24)), (cx + s(-24), cy + s(12)), (cx + s(24), cy + s(12))],
            )
            pygame.draw.rect(surf, (60, 55, 65), (cx + s(-8), cy + s(-2), s(16), s(20)))
            pygame.draw.rect(surf, (220, 200, 100), (cx + s(-4), cy + s(14), s(8), s(6)))
        case "t3_07":
            pygame.draw.rect(surf, (65, 60, 58), (cx + s(-26), cy + s(4), s(52), s(10)))
            pygame.draw.polygon(
                surf,
                (90, 110, 80),
                [
                    (cx + s(-8), cy + s(-16)),
                    (cx + s(12), cy + s(-8)),
                    (cx + s(4), cy + s(6)),
                    (cx + s(-14), cy + s(2)),
                ],
            )
        case "t3_08":
            pygame.draw.rect(surf, (230, 225, 210), (cx + s(-24), cy + s(-12), s(48), s(26)))
            pygame.draw.line(
                surf,
                (60, 55, 50),
                (cx + s(-18), cy + s(-4)),
                (cx + s(20), cy + s(8)),
                lw(2),
            )
            pygame.draw.polygon(
                surf,
                (210, 200, 185),
                [
                    (cx + s(10), cy + s(-12)),
                    (cx + s(26), cy + s(-4)),
                    (cx + s(12), cy + s(2)),
                ],
            )
        case "t3_09":
            pygame.draw.rect(surf, (238, 234, 226), (cx + s(-24), cy + s(-20), s(48), s(40)))
            pygame.draw.rect(surf, (255, 220, 100), (cx + s(4), cy + s(-8), s(16), s(22)))
            pygame.draw.line(
                surf,
                (80, 78, 75),
                (cx + s(-16), cy + s(-8)),
                (cx + s(8), cy + s(-8)),
                lw(1),
            )
        case "t3_10":
            pygame.draw.rect(surf, (225, 218, 205), (cx + s(-22), cy + s(-20), s(44), s(40)))
            pygame.draw.circle(surf, (120, 40, 40), (cx, cy + s(6)), s(10))
            pygame.draw.line(
                surf,
                (90, 70, 65),
                (cx + s(-14), cy + s(-12)),
                (cx + s(14), cy + s(-4)),
                lw(1),
            )
        case "t1_11":
            pygame.draw.polygon(
                surf,
                (85, 78, 68),
                [(cx, cy + s(-18)), (cx + s(-18), cy + s(16)), (cx + s(18), cy + s(16))],
            )
            pygame.draw.circle(surf, (200, 190, 120), (cx, cy + s(-6)), s(8))
        case "t1_12":
            pygame.draw.rect(surf, (240, 236, 228), (cx + s(-20), cy + s(-18), s(40), s(36)))
            pygame.draw.line(
                surf,
                (160, 50, 50),
                (cx + s(8), cy + s(-14)),
                (cx + s(8), cy + s(14)),
                lw(2),
            )
        case "t1_13":
            pygame.draw.circle(surf, (130, 200, 255), (cx, cy), s(22), lw(2))
            pygame.draw.line(
                surf,
                (255, 200, 120),
                (cx + s(12), cy + s(-8)),
                (cx + s(22), cy + s(8)),
                lw(2),
            )
        case "t1_14":
            pygame.draw.polygon(
                surf,
                (210, 185, 140),
                [(cx + s(-8), cy + s(-8)), (cx + s(8), cy + s(-8)), (cx, cy + s(10))],
            )
            pygame.draw.rect(surf, (90, 85, 78), (cx + s(-18), cy + s(12), s(36), s(8)))
        case "t1_15":
            pygame.draw.ellipse(surf, (100, 120, 200), (cx + s(-10), cy + s(-20), s(20), s(36)))
            pygame.draw.rect(surf, (80, 72, 62), (cx + s(-22), cy + s(8), s(44), s(6)))
        case "t1_16":
            pygame.draw.rect(surf, (200, 80, 60), (cx + s(-20), cy + s(-16), s(40), s(28)))
            pygame.draw.rect(surf, (60, 90, 70), (cx + s(-8), cy + s(12), s(16), s(10)))
        case "t1_17":
            pygame.draw.circle(surf, (120, 160, 130), (cx + s(-14), cy + s(2)), s(12))
            pygame.draw.circle(surf, (90, 110, 150), (cx + s(14), cy + s(2)), s(10))
            pygame.draw.line(surf, (220, 220, 230), (cx, cy + s(-18)), (cx, cy + s(-6)), lw(2))
        case "t1_18":
            for i in range(5):
                pygame.draw.circle(
                    surf,
                    (240, 240, 255),
                    (cx + s(-16 + i * 8), cy + s(-12 + (i % 2) * 4)),
                    max(1, s(2)),
                )
            pygame.draw.rect(surf, (70, 65, 80), (cx + s(-8), cy + s(8), s(16), s(14)))
        case "t1_19":
            pygame.draw.rect(surf, (62, 52, 48), (cx + s(-22), cy + s(-8), s(44), s(24)))
            pygame.draw.circle(surf, (90, 75, 65), (cx, cy + s(-14)), s(10))
        case "t1_20":
            pygame.draw.rect(surf, (75, 70, 65), (cx + s(-18), cy + s(-12), s(24), s(28)))
            pygame.draw.rect(surf, (120, 110, 100), (cx + s(6), cy + s(-6), s(14), s(20)))
        case "t2_11":
            pygame.draw.polygon(
                surf,
                (140, 120, 90),
                [(cx + s(-16), cy + s(12)), (cx, cy + s(-18)), (cx + s(16), cy + s(12))],
            )
            pygame.draw.circle(surf, (200, 60, 55), (cx + s(-10), cy + s(-4)), s(6))
            pygame.draw.circle(surf, (80, 130, 200), (cx + s(10), cy + s(-4)), s(6))
        case "t2_12":
            pygame.draw.circle(surf, (200, 200, 210), (cx + s(-14), cy + s(4)), s(14))
            pygame.draw.line(
                surf,
                (180, 70, 70),
                (cx + s(8), cy + s(-8)),
                (cx + s(18), cy + s(8)),
                lw(2),
            )
        case "t2_13":
            pygame.draw.rect(surf, (230, 228, 220), (cx + s(-22), cy + s(-16), s(44), s(32)))
            pygame.draw.line(surf, (160, 50, 50), (cx + s(-18), cy), (cx + s(18), cy), lw(2))
        case "t2_14":
            pygame.draw.rect(surf, (48, 44, 42), (cx + s(-18), cy + s(-10), s(36), s(24)))
            pygame.draw.line(surf, (200, 90, 85), (cx + s(-6), cy + s(-18)), (cx + s(-6), cy + s(18)), lw(2))
        case "t2_15":
            pygame.draw.polygon(
                surf,
                (100, 140, 200),
                [(cx + s(-20), cy + s(8)), (cx + s(20), cy + s(8)), (cx, cy + s(-18))],
            )
            pygame.draw.rect(surf, (220, 200, 100), (cx + s(-6), cy + s(10), s(12), s(8)))
        case "t2_16":
            pygame.draw.line(
                surf,
                (90, 85, 75),
                (cx + s(-22), cy + s(16)),
                (cx + s(22), cy + s(-16)),
                lw(3),
            )
            pygame.draw.circle(surf, (100, 200, 140), (cx + s(12), cy + s(8)), s(8))
        case "t2_17":
            pygame.draw.rect(surf, (235, 232, 220), (cx + s(-18), cy + s(-18), s(36), s(36)))
            pygame.draw.line(
                surf,
                (60, 55, 50),
                (cx + s(-12), cy + s(-8)),
                (cx + s(12), cy + s(8)),
                lw(1),
            )
        case "t2_18":
            pygame.draw.circle(surf, (95, 88, 82), (cx + s(-12), cy + s(4)), s(14))
            pygame.draw.circle(surf, (95, 88, 82), (cx + s(12), cy + s(4)), s(14))
            pygame.draw.line(surf, (200, 180, 60), (cx, cy + s(-16)), (cx, cy + s(16)), lw(2))
        case "t2_19":
            pygame.draw.circle(surf, (70, 65, 78), (cx + s(-16), cy + s(6)), s(10))
            pygame.draw.line(
                surf,
                (240, 230, 200),
                (cx + s(-6), cy + s(6)),
                (cx + s(18), cy + s(-12)),
                lw(2),
            )
        case "t2_20":
            pygame.draw.polygon(
                surf,
                (200, 200, 220),
                [(cx, cy + s(-22)), (cx + s(-20), cy + s(18)), (cx + s(20), cy + s(18))],
            )
            pygame.draw.circle(surf, (255, 220, 120), (cx, cy + s(-6)), s(6))
        case "t3_11":
            pygame.draw.rect(surf, (238, 234, 226), (cx + s(-22), cy + s(-14), s(44), s(28)))
            pygame.draw.line(surf, (180, 50, 50), (cx + s(-16), cy), (cx + s(16), cy), lw(2))
            pygame.draw.line(surf, (80, 120, 80), (cx, cy + s(-10)), (cx, cy + s(10)), lw(2))
        case "t3_12":
            pygame.draw.rect(surf, (110, 95, 85), (cx + s(-6), cy + s(-20), s(12), s(40)))
            pygame.draw.polygon(
                surf,
                (160, 150, 130),
                [(cx + s(-18), cy + s(8)), (cx + s(18), cy + s(8)), (cx, cy + s(-12))],
            )
        case "t3_13":
            pygame.draw.rect(surf, (200, 60, 45), (cx + s(-8), cy + s(-18), s(16), s(36)))
            pygame.draw.rect(surf, (230, 228, 220), (cx + s(-20), cy + s(-14), s(14), s(28)))
        case "t3_14":
            pygame.draw.line(
                surf,
                (90, 80, 70),
                (cx + s(-20), cy + s(16)),
                (cx + s(20), cy + s(-16)),
                lw(3),
            )
            pygame.draw.rect(surf, (220, 200, 100), (cx + s(-12), cy + s(-8), s(24), s(16)))
        case "t3_15":
            pygame.draw.ellipse(surf, (235, 230, 240), (cx + s(-20), cy + s(-12), s(40), s(28)))
            pygame.draw.line(surf, (120, 100, 140), (cx + s(-10), cy + s(-6)), (cx + s(10), cy + s(6)), lw(2))
        case "t3_16":
            pygame.draw.polygon(
                surf,
                (55, 50, 48),
                [(cx, cy + s(-18)), (cx + s(-22), cy + s(16)), (cx + s(22), cy + s(16))],
            )
            pygame.draw.circle(surf, (255, 220, 200), (cx, cy + s(4)), s(8))
        case "t3_17":
            pygame.draw.rect(surf, (60, 58, 72), (cx + s(-14), cy + s(-18), s(28), s(36)))
            pygame.draw.polygon(
                surf,
                (255, 220, 100),
                [(cx + s(8), cy + s(-14)), (cx + s(22), cy + s(2)), (cx + s(10), cy + s(8))],
            )
        case "t3_18":
            pygame.draw.rect(surf, (210, 200, 185), (cx + s(-22), cy + s(-16), s(44), s(32)))
            pygame.draw.line(surf, (160, 50, 50), (cx + s(-8), cy + s(-12)), (cx + s(8), cy + s(12)), lw(2))
        case "t3_19":
            pygame.draw.line(
                surf,
                (85, 78, 72),
                (cx, cy + s(-22)),
                (cx + s(-18), cy + s(20)),
                lw(3),
            )
            pygame.draw.line(
                surf,
                (85, 78, 72),
                (cx, cy + s(-22)),
                (cx + s(18), cy + s(20)),
                lw(3),
            )
            pygame.draw.circle(surf, (130, 200, 255), (cx, cy + s(4)), s(8))
        case "t3_20":
            pygame.draw.rect(surf, (225, 220, 208), (cx + s(-22), cy + s(-18), s(44), s(36)))
            pygame.draw.polygon(
                surf,
                (180, 160, 120),
                [(cx + s(-8), cy + s(-14)), (cx + s(8), cy + s(-14)), (cx + s(6), cy + s(12)), (cx + s(-6), cy + s(12))],
            )
        case _:
            pygame.draw.circle(surf, (100, 120, 160), (cx, cy), s(18), lw(2))
            pygame.draw.line(surf, (160, 175, 200), (cx, cy + s(-12)), (cx, cy + s(12)), lw(2))
            pygame.draw.line(surf, (160, 175, 200), (cx + s(-12), cy), (cx + s(12), cy), lw(2))
