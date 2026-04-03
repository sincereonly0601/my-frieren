# -*- coding: utf-8 -*-
"""一次性：把 _whim_aftermath_manual_56.AFT 寫入 whim_events.py 各則 aftermath_*。"""
from __future__ import annotations

from pathlib import Path

from _whim_aftermath_manual_56 import AFT

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "whim_events.py"

_KEYS = (
    "stoltz",
    "sword_village_chief",
    "gorilla_warrior",
    "count_granat",
    "lord_orden",
    "old_man_voll",
    "falsch",
    "norm_chairman",
    "miriald",
    "sein_brother",
    "supreme_mastery",
    "leka",
    "lernen",
    "gehn",
)
_FIELDS = (
    "aftermath_correct_para1",
    "aftermath_correct_para2",
    "aftermath_wrong_para1",
    "aftermath_wrong_para2",
)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _replace_one(text: str, key: str, quad: tuple[str, str, str, str]) -> str:
    """自 key=\"...\" 起，替換連續四個 aftermath_* 區塊為單一字串。"""
    needle = f'        key="{key}",'
    pos = text.find(needle)
    if pos < 0:
        raise SystemExit(f"missing key block: {key}")
    start = text.find("        aftermath_correct_para1=(", pos)
    if start < 0:
        raise SystemExit(f"missing aftermath_correct_para1 after {key}")
    end_field = "aftermath_wrong_para2"
    end_pat = f"        {end_field}="
    end_start = text.find(end_pat, start)
    if end_start < 0:
        raise SystemExit(f"missing {end_field} for {key}")
    paren = text.find("(", end_start)
    if paren < 0:
        raise SystemExit(f"no ( for {end_field} {key}")
    depth = 0
    i = paren
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                j = i + 1
                while j < len(text) and text[j] in " \t":
                    j += 1
                if j < len(text) and text[j] == ",":
                    end = j + 1
                    if end < len(text) and text[end] == "\n":
                        end += 1
                    break
        i += 1
    else:
        raise SystemExit(f"unclosed {end_field} for {key}")
    parts = []
    for i, fname in enumerate(_FIELDS):
        parts.append(f"        {fname}=(\n            \"{_esc(quad[i])}\"\n        ),\n")
    return text[:start] + "".join(parts) + text[end:]


def main() -> None:
    assert len(AFT) == len(_KEYS)
    text = TARGET.read_text(encoding="utf-8")
    for key, quad in zip(_KEYS, AFT, strict=True):
        text = _replace_one(text, key, quad)
    TARGET.write_text(text, encoding="utf-8")
    print("OK: whim_events aftermath_* synced from AFT")


if __name__ == "__main__":
    main()
