"""驗證夥伴／強敵底欄不超過兩行；獎勵底欄不超過一行；trim 均不刪字。"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
import main as m
from encounter_defs import ENCOUNTER_BY_ID
from gallery_rewards import _REWARD_CAPTION_BY_REL_PATH, reward_gallery_scene_fallback_zh
from whim_events import WHIM_ENCOUNTERS


def _check_two_lines(label: str, text: str) -> None:
    font = m._make_small_font()
    _, max_w, *_ = m._gallery_fullscreen_layout(font)
    t = (text or "").strip()
    trim = m._gallery_trim_footer_desc_to_two_visible_lines(
        font, t, max_w, prefer_greedy_first_line_wrap=True
    )
    n = len(m.wrap_cjk(font, trim, max_w))
    if n > 2:
        raise SystemExit(f"{label}: trim 後仍 {n} 行")
    if len(t) != len(trim):
        raise SystemExit(f"{label}: 被裁掉 {len(t)-len(trim)} 字 in={len(t)} out={len(trim)}")


def _check_one_line(label: str, text: str) -> None:
    font = m._make_small_font()
    _, max_w, *_ = m._gallery_fullscreen_layout_reward_one_line(font)
    t = (text or "").strip()
    trim = m._gallery_trim_footer_desc_to_one_visible_line(font, t, max_w)
    n = len(m.wrap_cjk(font, trim, max_w))
    if n > 1:
        raise SystemExit(f"{label}: trim 後仍 {n} 行（獎勵應一行）")
    if len(t) != len(trim):
        raise SystemExit(f"{label}: 被裁掉 {len(t)-len(trim)} 字 in={len(t)} out={len(trim)}")


def main() -> None:
    for w in WHIM_ENCOUNTERS:
        _check_two_lines(f"companion:{w.cg_basename}", w.gallery_footer_zh)
    for eid, e in ENCOUNTER_BY_ID.items():
        _check_two_lines(f"encounter:{eid}", e.gallery_intro_zh)
    for rel, cap in _REWARD_CAPTION_BY_REL_PATH.items():
        _check_one_line(f"reward:{rel}", cap)
    _check_one_line("fallback", reward_gallery_scene_fallback_zh("x"))
    print("OK: companions/encounters <=2 lines; rewards <=1 line; no trim loss")
    pygame.quit()


if __name__ == "__main__":
    main()
