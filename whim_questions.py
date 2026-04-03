"""
奇遇測驗題庫：以《葬送的芙莉蓮》本篇已公開主線情節為範圍（避免後續暴雷）。

固定 ``q01``～``q110`` 共 110 題；每題三選一，``correct_index`` 為題庫檔案中選項 **A／B／C** 的索引 0～2。
實際遊玩時選項順序會於每次進入測驗時**隨機打亂**（見 ``main.py``），正解以選項**內容**為準。

題幹與選項內人物譯名優先採台灣木棉花代理之官方用語（例如考官 Sense 為「冉則」）。
題幹長度宜配合奇遇測驗畫面 **1～2** 行；芙莉蓮測驗另於 ``frieren_quiz`` 繪製時自動補讀句尾，使該模式兩行皆有正文。選項文案宜單行可讀（過寬會以「…」截斷）。
JSON 可選 ``explanation_zh``：芙莉蓮測驗答題後「詳解」用；未填則顯示預設說明。
題庫資料見同目錄 ``whim_questions.json``。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WhimQuestion:
    """
    單一測驗題。

    Attributes:
        qid: 題目編號字串（``q01``～``q110``）。
        stem: 題幹。
        options: 三個選項文案（**題庫固定順序**：索引 0=A、1=B、2=C）。
        correct_index: 正解在 ``options`` 中的索引 0～2。
        explanation_zh: 詳解（可選；芙莉蓮測驗回饋用；缺則使用預設說明）。
    """

    qid: str
    stem: str
    options: tuple[str, str, str]
    correct_index: int
    explanation_zh: str = ""


def _whim_json_path() -> Path:
    """題庫 JSON 路徑（原始碼目錄；PyInstaller 一體包時回退 ``_MEIPASS``）。"""
    here = Path(__file__).resolve().parent
    p = here / "whim_questions.json"
    if p.is_file():
        return p
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            alt = Path(meipass) / "whim_questions.json"
            if alt.is_file():
                return alt
    return p


def _normalize_lernen_zh(text: str) -> str:
    """
    將舊版或誤植「列克」「烈克」統一為「列魯寧」（一級魔法使 Lernen 之譯名）。

    Args:
        text: 題幹、選項或詳解片段。

    Returns:
        正規化後字串。
    """
    if not text:
        return text
    return text.replace("列克", "列魯寧").replace("烈克", "列魯寧")


def _load_whim_questions_from_json() -> tuple[WhimQuestion, ...]:
    """從 ``whim_questions.json`` 載入題庫。"""
    path = _whim_json_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[WhimQuestion] = []
    for i, item in enumerate(raw):
        opts = item["options"]
        if len(opts) != 3:
            raise ValueError(f"Question {i} must have 3 options")
        ci = int(item["correct_index"])
        if ci not in (0, 1, 2):
            raise ValueError(f"Question {i} bad correct_index")
        expl = _normalize_lernen_zh(str(item.get("explanation_zh") or "").strip())
        stem = _normalize_lernen_zh(str(item["stem"]))
        opts_norm = (
            _normalize_lernen_zh(str(opts[0])),
            _normalize_lernen_zh(str(opts[1])),
            _normalize_lernen_zh(str(opts[2])),
        )
        out.append(
            WhimQuestion(
                f"q{i + 1:02d}",
                stem,
                opts_norm,
                ci,
                expl,
            )
        )
    return tuple(out)


WHIM_QUESTIONS: tuple[WhimQuestion, ...] = _load_whim_questions_from_json()

_WHIM_QUESTION_BY_ID: dict[str, WhimQuestion] = {q.qid: q for q in WHIM_QUESTIONS}


def whim_question_by_index(index: int) -> WhimQuestion:
    """
    以 0 起算索引取得題目（循環安全）。

    Args:
        index: 題序索引。

    Returns:
        對應 ``WhimQuestion``。
    """
    if not WHIM_QUESTIONS:
        raise RuntimeError("WHIM_QUESTIONS 為空")
    return WHIM_QUESTIONS[index % len(WHIM_QUESTIONS)]


def whim_question_by_id(qid: str) -> WhimQuestion | None:
    """依 ``qid`` 取得題目；無則 None。"""
    return _WHIM_QUESTION_BY_ID.get(qid)
