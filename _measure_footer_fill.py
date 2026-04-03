"""量測底欄描述兩行填滿度（臨時腳本）。"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
import main as m
from encounter_defs import ENCOUNTER_BY_ID
from gallery_rewards import _REWARD_CAPTION_BY_REL_PATH
from whim_events import WHIM_ENCOUNTERS


def main() -> None:
    font = m._make_small_font()
    _, max_w, *_ = m._gallery_fullscreen_layout(font)

    def stat(text: str) -> tuple[int, float, float, int]:
        t = (text or "").strip()
        lines = m.wrap_cjk(font, t, max_w)
        n = len(lines)
        w1 = font.size(lines[0])[0] if lines else 0
        w2 = font.size(lines[1])[0] if n > 1 else 0
        r1 = w1 / max_w if max_w else 0
        r2 = w2 / max_w if max_w and n > 1 else 0
        return n, r1, r2, len(t)

    print("max_w", max_w)
    for w in WHIM_ENCOUNTERS:
        n, r1, r2, L = stat(w.gallery_footer_zh)
        if n < 2 or r1 < 0.82 or (n == 2 and r2 < 0.55):
            print(f"C {w.cg_basename} lines={n} r1={r1:.2f} r2={r2:.2f} len={L}")
    for eid, e in sorted(ENCOUNTER_BY_ID.items()):
        n, r1, r2, L = stat(e.gallery_intro_zh)
        if n < 2 or r1 < 0.82 or (n == 2 and r2 < 0.55):
            print(f"E {eid} lines={n} r1={r1:.2f} r2={r2:.2f} len={L}")
    for rel, cap in sorted(_REWARD_CAPTION_BY_REL_PATH.items()):
        n, r1, r2, L = stat(cap)
        if n < 2 or r1 < 0.82 or (n == 2 and r2 < 0.45):
            print(f"R {rel.split('/')[-1]} lines={n} r1={r1:.2f} r2={r2:.2f} len={L}")
    pygame.quit()


if __name__ == "__main__":
    main()
