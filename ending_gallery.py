"""
圖片畫廊解鎖紀錄（跨存檔共用）。

通關結局 CG 之合法鍵見 ``GALLERY_ENDING_KEYS``；另預留「同行的夥伴」「遭遇的強敵」等分類欄位。
「獎勵圖片」之**實際解鎖條件**由 ``gallery_rewards`` 依通關集合與 ``assets/cg/rewards/`` 內圖檔（檔名規則見該模組）即時計算；
寫入 JSON 之 ``reward_keys`` 僅為同步紀錄（作弊清空時一併歸零）。
「遭遇的強敵」之 ``enemy_keys`` 於養成中戰勝對應敵人時寫入（見 ``encounter_defs``／``register_enemy_gallery_unlock``）。
「同行的夥伴」展示之已解鎖鍵為 ``companion_keys`` 與奇遇 ``whim_keys`` 之聯集，且須在
``assets/cg/companions/`` 有對應圖檔（見 ``load_companion_gallery_unlocked``）。
資料檔：可寫入資料根目錄 ``ending_gallery_unlock.json``。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

# 夥伴畫廊圖檔副檔名（與結局 CG 慣例一致，小寫比對）。
_COMPANION_CG_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)

from endings import ENDING_CG_UNLOCK_DISPLAY_ORDER
from whim_events import (
    WHIM_CG_BASENAME_ORDER,
    canonical_companion_disk_stem,
    canonical_whim_gallery_key,
)

# 與解鎖條件頁之 ``ENDING_CG_UNLOCK_DISPLAY_ORDER`` 相同（通關圖片子畫面每頁六格；前 11 女角、後 11 男角，日後可擴充）。
GALLERY_ENDING_KEYS: Final[tuple[str, ...]] = ENDING_CG_UNLOCK_DISPLAY_ORDER
GALLERY_FEMALE_ENDING_KEYS: Final[tuple[str, ...]] = GALLERY_ENDING_KEYS[:11]
GALLERY_MALE_ENDING_KEYS: Final[tuple[str, ...]] = GALLERY_ENDING_KEYS[11:]

# JSON 內各分類鍵（與主選單「圖片畫廊」通關圖片＋預留項對應；清空時一併歸零）。
_GALLERY_JSON_SECTIONS: Final[tuple[str, ...]] = (
    "ending_keys",
    "companion_keys",
    "enemy_keys",
    "whim_keys",
    "reward_keys",
)


def gallery_unlock_file(game_root: Path) -> Path:
    """回傳解鎖紀錄 JSON 路徑。"""
    return game_root / "ending_gallery_unlock.json"


def _normalize_str_list(val: object) -> list[str]:
    """
    將 JSON 欄位正規化為非空字串列表。

    Args:
        val: 任意 JSON 解出值。

    Returns:
        字串列表（已去除空白項）。
    """
    if not isinstance(val, list):
        return []
    out: list[str] = []
    for x in val:
        if isinstance(x, str):
            s = x.strip()
            if s:
                out.append(s)
        elif x is not None:
            s = str(x).strip()
            if s:
                out.append(s)
    return out


def _empty_gallery_document() -> dict[str, list[str]]:
    """
    建立各分類皆為空列表的畫廊文件內容。

    Returns:
        欄位名 → 空列表。
    """
    return {k: [] for k in _GALLERY_JSON_SECTIONS}


def _load_raw_gallery_document(game_root: Path) -> dict[str, list[str]]:
    """
    讀取完整畫廊 JSON；支援舊版僅含 ``keys``／``unlocked`` 之檔案。

    Args:
        game_root: 可寫入資料根目錄。

    Returns:
        各分類鍵名對應字串列表（至少含四個欄位）。
    """
    p = gallery_unlock_file(game_root)
    if not p.is_file():
        return _empty_gallery_document()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return _empty_gallery_document()
    if not isinstance(data, dict):
        return _empty_gallery_document()
    doc = _empty_gallery_document()
    if "ending_keys" in data:
        doc["ending_keys"] = _normalize_str_list(data.get("ending_keys"))
    else:
        legacy = data.get("keys", data.get("unlocked", []))
        doc["ending_keys"] = _normalize_str_list(legacy)
    for sec in _GALLERY_JSON_SECTIONS:
        if sec == "ending_keys":
            continue
        doc[sec] = _normalize_str_list(data.get(sec))
    return doc


def _write_gallery_document(game_root: Path, doc: dict[str, list[str]]) -> None:
    """
    寫入完整畫廊 JSON；結局鍵僅保留 ``GALLERY_ENDING_KEYS`` 內合法值。

    Args:
        game_root: 可寫入資料根目錄。
        doc: 各分類字串列表（可缺欄，缺則視為空）。
    """
    p = gallery_unlock_file(game_root)
    valid_e = set(GALLERY_ENDING_KEYS)
    out: dict[str, list[str]] = {}
    for sec in _GALLERY_JSON_SECTIONS:
        raw = _normalize_str_list(doc.get(sec, []))
        if sec == "ending_keys":
            out[sec] = sorted({x for x in raw if x in valid_e})
        else:
            out[sec] = sorted(set(raw))
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def load_gallery_unlocked(game_root: Path) -> set[str]:
    """
    讀取已解鎖**通關結局** key 集合；檔案不存在或毀損時回傳空集合。

    Args:
        game_root: 可寫入資料根目錄（`main` 之 ``_GAME_USERDATA_ROOT``）。

    Returns:
        合法結局鍵的子集。
    """
    doc = _load_raw_gallery_document(game_root)
    valid = set(GALLERY_ENDING_KEYS)
    return {x for x in doc["ending_keys"] if x in valid}


def save_gallery_unlocked(
    game_root: Path,
    keys: set[str],
    *,
    asset_root: Path | None = None,
) -> None:
    """
    寫入通關結局解鎖鍵；其餘分類（夥伴／強敵／獎勵）自磁碟合併保留。

    Args:
        game_root: 專案根目錄。
        keys: 要儲存的結局鍵集合。
        asset_root: 若提供，會依目前通關與 ``assets/cg/rewards/`` 內圖檔重算並寫入 ``reward_keys``（供紀錄／除錯）。
    """
    doc = _load_raw_gallery_document(game_root)
    ek_set = keys & set(GALLERY_ENDING_KEYS)
    doc["ending_keys"] = list(ek_set)
    if asset_root is not None:
        from gallery_rewards import eligible_reward_tokens, sorted_reward_tokens_for_display

        doc["reward_keys"] = list(
            sorted_reward_tokens_for_display(
                eligible_reward_tokens(set(ek_set), asset_root)
            )
        )
    _write_gallery_document(game_root, doc)


def clear_all_gallery_unlock_data(game_root: Path) -> None:
    """
    清空圖片畫廊之全部持久化解鎖紀錄：通關圖片與預留分類欄位皆歸空。

    Args:
        game_root: 可寫入資料根目錄。
    """
    _write_gallery_document(game_root, _empty_gallery_document())


def load_whim_gallery_unlocked(game_root: Path) -> set[str]:
    """
    讀取已解鎖奇遇 CG 的鍵集合。

    Args:
        game_root: 可寫入資料根目錄。

    Returns:
        已解鎖奇遇鍵集合（若檔案不存在或毀損回傳空集合）。
    """
    doc = _load_raw_gallery_document(game_root)
    return {
        canonical_whim_gallery_key(x)
        for x in _normalize_str_list(doc.get("whim_keys"))
    }


def register_whim_gallery_unlock(
    game_root: Path,
    keys_mutable: set[str],
    whim_key: str,
) -> None:
    """
    奇遇事件回答正確後登錄其 NPC CG 解鎖鍵並持久化（冪等）。

    Args:
        game_root: 專案根目錄。
        keys_mutable: 執行中記憶體內已解鎖集合（就地更新）。
        whim_key: CG 檔案主檔名鍵（見 whim_events.py：``cg_basename``）。
    """
    if not isinstance(whim_key, str):
        return
    whim_key = canonical_whim_gallery_key(whim_key)
    if not whim_key:
        return
    if whim_key in keys_mutable:
        return
    keys_mutable.add(whim_key)
    doc = _load_raw_gallery_document(game_root)
    merged = (
        {canonical_whim_gallery_key(x) for x in _normalize_str_list(doc.get("whim_keys"))}
        | keys_mutable
    )
    doc["whim_keys"] = sorted(merged)
    _write_gallery_document(game_root, doc)


def load_enemy_gallery_unlocked(game_root: Path) -> set[str]:
    """
    讀取遭遇戰敵人 CG 已解鎖 id 集合（見 ``encounter_defs``）。

    Args:
        game_root: 可寫入資料根目錄。

    Returns:
        合法敵人 id 之子集。
    """
    from encounter_defs import is_valid_encounter_id, resolve_encounter_id

    doc = _load_raw_gallery_document(game_root)
    return {
        resolve_encounter_id(x)
        for x in doc["enemy_keys"]
        if is_valid_encounter_id(x)
    }


def register_enemy_gallery_unlock(
    game_root: Path,
    keys_mutable: set[str],
    enemy_id: str,
) -> None:
    """
    遭遇戰勝利後登錄敵人畫廊格並持久化（冪等）。

    Args:
        game_root: 專案根目錄。
        keys_mutable: 執行中記憶體內之敵人解鎖集合（就地更新）。
        enemy_id: ``EncounterEnemy.id``。
    """
    from encounter_defs import is_valid_encounter_id, resolve_encounter_id

    if not is_valid_encounter_id(enemy_id):
        return
    canon = resolve_encounter_id(enemy_id)
    if canon in keys_mutable:
        return
    keys_mutable.add(canon)
    doc = _load_raw_gallery_document(game_root)
    merged = {
        resolve_encounter_id(x)
        for x in set(doc["enemy_keys"]) | keys_mutable
        if is_valid_encounter_id(x)
    }
    doc["enemy_keys"] = sorted(merged)
    _write_gallery_document(game_root, doc)


def register_gallery_unlock(
    game_root: Path,
    keys_mutable: set[str],
    ending_key: str,
    *,
    asset_root: Path | None = None,
) -> None:
    """
    登錄一次通關解鎖並持久化（冪等：已存在則不重寫檔）。

    Args:
        game_root: 專案根目錄。
        keys_mutable: 執行中記憶體內的解鎖集合（會就地更新）。
        ending_key: `Ending.key`。
        asset_root: 若提供，一併更新 JSON 內之 ``reward_keys`` 紀錄。
    """
    if ending_key not in GALLERY_ENDING_KEYS:
        return
    if ending_key in keys_mutable:
        return
    keys_mutable.add(ending_key)
    save_gallery_unlocked(game_root, keys_mutable, asset_root=asset_root)


def discover_companion_gallery_keys(asset_root: Path) -> tuple[str, ...]:
    """
    掃描 ``assets/cg/companions/`` 內圖檔，以主檔名（無副檔名）經 ``canonical_companion_disk_stem``
    正規化後作為夥伴畫廊鍵（``foo_friend`` 與 ``foo`` 視為同一鍵 ``foo``）。

    Args:
        asset_root: 專案根目錄（內含 ``assets`` 資料夾）。

    Returns:
        排序後、不重複之主檔名元組；目錄不存在或為空則為空元組。
    """
    d = asset_root / "assets" / "cg" / "companions"
    if not d.is_dir():
        return ()
    stems: set[str] = set()
    for p in d.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in _COMPANION_CG_SUFFIXES:
            continue
        name = p.stem.strip()
        if name:
            stems.add(canonical_companion_disk_stem(name))
    return tuple(sorted(stems))


def load_companion_gallery_unlocked(game_root: Path, asset_root: Path) -> set[str]:
    """
    讀取「同行的夥伴」畫廊可展示之已解鎖鍵。

    含 ``companion_keys`` 與奇遇 ``whim_keys``；合法鍵為奇遇定義之
    ``WHIM_CG_BASENAME_ORDER`` 與磁碟上 ``companions/`` 圖檔主檔名之聯集。

    Args:
        game_root: 可寫入資料根目錄。
        asset_root: 專案根目錄。

    Returns:
        合法夥伴鍵之子集。
    """
    # 奇遇可解鎖之 NPC 一律有合法鍵（見 ``WHIM_CG_BASENAME_ORDER``），無需磁碟已有圖檔；
    # 另併入僅存在於資料夾、未定義於奇遇表之檔名。
    whim_slots = set(WHIM_CG_BASENAME_ORDER)
    disk_stems = set(discover_companion_gallery_keys(asset_root))
    allowed = whim_slots | disk_stems
    doc = _load_raw_gallery_document(game_root)
    whim = {
        canonical_whim_gallery_key(x)
        for x in _normalize_str_list(doc.get("whim_keys"))
    }
    comp = {
        canonical_whim_gallery_key(x)
        for x in _normalize_str_list(doc.get("companion_keys"))
    }
    return (whim | comp) & allowed


def companion_gallery_key_order(asset_root: Path) -> tuple[str, ...]:
    """
    「同行的夥伴」網格欄位順序：先依奇遇定義之 CG 主檔名（與奇遇事件可解鎖 NPC 一對一），
    再追加僅出現在 ``companions/`` 且不在上列之檔名（字母序）。

    Args:
        asset_root: 專案根目錄。

    Returns:
        主檔名鍵元組（每頁六格，與其他畫廊相同）。
    """
    base = list(WHIM_CG_BASENAME_ORDER)
    disk = set(discover_companion_gallery_keys(asset_root))
    extras = sorted(disk - set(base))
    return tuple(base + extras)


def cheat_unlock_companion_enemy_gallery_cg(
    game_root: Path,
    asset_root: Path,
) -> None:
    """
    作弊：寫入「同行的夥伴」所需之 ``whim_keys`` 與 ``companion_keys``，並解鎖全部遭遇敵。

    奇遇 NPC 之解鎖鍵存在 ``whim_keys``（見 ``register_whim_gallery_unlock``）；僅寫
    ``companion_keys``（``assets/cg/companions/`` 檔名）無法解鎖主線奇遇事件登錄之 NPC。
    故一併將 ``whim_keys`` 設為 ``WHIM_CG_BASENAME_ORDER`` 全列。

    Args:
        game_root: 可寫入資料根目錄。
        asset_root: 專案根目錄。
    """
    from encounter_defs import ALL_ENCOUNTER_IDS

    doc = _load_raw_gallery_document(game_root)
    doc["whim_keys"] = list(WHIM_CG_BASENAME_ORDER)
    doc["companion_keys"] = list(discover_companion_gallery_keys(asset_root))
    doc["enemy_keys"] = sorted(set(ALL_ENCOUNTER_IDS))
    _write_gallery_document(game_root, doc)
