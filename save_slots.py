"""
五格存檔欄位：路徑、讀寫、依檔案修改時間找出「最新進度」。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from game_state import START_AGE_MONTHS, TOTAL_TRAINING_QUARTERS, GameState

SLOT_COUNT = 5
SAVES_SUBDIR = "saves"


def _age_phrase_from_time_left(time_left: int) -> str:
    """
    由剩餘季數推算存檔當下遊戲內年紀（與 `GameState.age_months` 規則一致）。

    Args:
        time_left: 剩餘培養季數。

    Returns:
        例如「5 歲 3 個月」。
    """
    tl = max(0, min(TOTAL_TRAINING_QUARTERS, int(time_left)))
    am = START_AGE_MONTHS + (TOTAL_TRAINING_QUARTERS - tl) * 3
    return f"{am // 12} 歲 {am % 12} 個月"


def _format_saved_at_local(iso_str: str) -> str:
    """
    將存檔內 ISO 時間轉成系統本地日期＋時間字串。

    Args:
        iso_str: `GameState.saved_at` 寫入的 ISO 字串（可含時區）。

    Returns:
        例如「2025-03-21 20:30:00」；無法解析則回傳原文或占位說明。
    """
    s = (iso_str or "").strip()
    if not s:
        return "（尚無記錄時間）"
    try:
        normalized = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        local = dt.astimezone()
        return local.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return s


def saves_directory(root: str | Path | None = None) -> Path:
    """
    回傳存檔目錄路徑（專案下的 saves/）。

    Args:
        root: 專案根目錄；省略則以本檔所在目錄為準。

    Returns:
        `Path` 目錄（不一定已存在）。
    """
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    return base / SAVES_SUBDIR


def slot_path(slot_index: int, root: str | Path | None = None) -> Path:
    """
    回傳指定欄位的 JSON 檔路徑（1-based）。

    Args:
        slot_index: 1～SLOT_COUNT。
        root: 專案根目錄。

    Returns:
        例如 saves/save_1.json。
    """
    if slot_index < 1 or slot_index > SLOT_COUNT:
        raise ValueError(f"slot_index 須為 1～{SLOT_COUNT}")
    return saves_directory(root) / f"save_{slot_index}.json"


def slot_file_mtime(slot_index: int, root: str | Path | None = None) -> float | None:
    """
    回傳存檔檔案最後修改時間。

    Args:
        slot_index: 1～SLOT_COUNT。
        root: 專案根目錄。

    Returns:
        若檔案不存在則為 None，否則為 `stat().st_mtime`。
    """
    p = slot_path(slot_index, root)
    if not p.is_file():
        return None
    return p.stat().st_mtime


def latest_slot(root: str | Path | None = None) -> int | None:
    """
    找出修改時間最新的非空存檔欄位。

    Args:
        root: 專案根目錄。

    Returns:
        欄位編號 1～5；若皆無檔則為 None。
    """
    best: tuple[float, int] | None = None
    for i in range(1, SLOT_COUNT + 1):
        mt = slot_file_mtime(i, root)
        if mt is None:
            continue
        if best is None or mt > best[0]:
            best = (mt, i)
    return best[1] if best else None


def save_to_slot(state: GameState, slot_index: int, root: str | Path | None = None) -> None:
    """
    將狀態寫入指定欄位。

    Args:
        state: 遊戲狀態。
        slot_index: 1～SLOT_COUNT。
        root: 專案根目錄。
    """
    state.save_to_file(slot_path(slot_index, root))


def load_from_slot(slot_index: int, root: str | Path | None = None) -> GameState:
    """
    自指定欄位載入狀態。

    Args:
        slot_index: 1～SLOT_COUNT。
        root: 專案根目錄。

    Returns:
        還原後的 `GameState`。

    Raises:
        FileNotFoundError: 檔案不存在。
    """
    return GameState.load_from_file(slot_path(slot_index, root))


def slot_summary(slot_index: int, root: str | Path | None = None) -> dict[str, Any]:
    """
    讀取欄位摘要供選單顯示（不載入完整遊戲邏輯時的輕量資訊）。

    Args:
        slot_index: 1～SLOT_COUNT。
        root: 專案根目錄。

    Returns:
        包含 `empty`、`saved_at`、`time_left`、`phase`、`age_phrase`、
        `saved_at_local`（本地時間顯示字串）、`gender_zh`（``男``／``女``）、
        `protagonist_gender`（``male``／``female``）等鍵的字典。
    """
    p = slot_path(slot_index, root)
    if not p.is_file():
        return {"empty": True, "path": str(p)}
    raw = json.loads(p.read_text(encoding="utf-8"))
    tl = int(raw.get("time_left", TOTAL_TRAINING_QUARTERS))
    saved_iso = raw.get("saved_at", "") or ""
    pg = raw.get("protagonist_gender", "female")
    if pg not in ("male", "female"):
        pg = "female"
    gender_zh = "男" if pg == "male" else "女"
    return {
        "empty": False,
        "path": str(p),
        "saved_at": saved_iso,
        "time_left": tl,
        "phase": raw.get("phase", ""),
        "heroine_name": raw.get("heroine_name", "") or "孩子",
        "protagonist_gender": pg,
        "gender_zh": gender_zh,
        "age_phrase": _age_phrase_from_time_left(tl),
        "saved_at_local": _format_saved_at_local(saved_iso),
    }
