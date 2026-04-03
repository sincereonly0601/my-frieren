"""
匯出網頁版規則層所需之靜態資料（與桌面版 Python 模組同源）。

執行（專案根目錄）::

    python tools/export_web_sim_data.py

輸出至 ``web/src/sim/data/``（含 ``gallery_rewards.json``、``gallery_reward_captions.json``）；
修改重大／突發／遭遇／結局／奇遇文案或 ``assets/cg/rewards/`` 檔案後請重新執行。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
WEB_DATA = ROOT / "web" / "src" / "sim" / "data"


def _major_to_dict(m) -> dict:
    return {
        "age_year": m.age_year,
        "title": m.title,
        "preamble_title": m.preamble_title,
        "preamble_body": list(m.preamble_body),
        "preamble_merged_zh": m.preamble_merged_zh,
        "choice_prompt_zh": m.choice_prompt_zh,
        "resolution_bodies": [list(x) for x in m.resolution_bodies],
        "options": [
            {
                "label": o.label,
                "deltas": dict(o.deltas),
                "flags_add": sorted(o.flags_add),
                "flags_add_if_male": sorted(o.flags_add_if_male),
                "extra_deltas": dict(o.extra_deltas),
            }
            for o in m.options
        ],
    }


def _incident_to_dict(e) -> dict:
    return {
        "id": e.id,
        "tier": e.tier,
        "title": e.title,
        "body": e.body,
        "options": [{"label": o.label, "deltas": dict(o.deltas)} for o in e.options],
    }


def _enemy_to_dict(e) -> dict:
    return {
        "id": e.id,
        "tier": e.tier,
        "name_zh": e.name_zh,
        "name_en": e.name_en,
        "difficulty": e.difficulty,
        "base_hp": e.base_hp,
        "base_atk": e.base_atk,
        "base_def": e.base_def,
        "move_names": list(e.move_names),
        "ultimate_zh": e.ultimate_zh,
        "aftermath_win": list(e.aftermath_win),
        "aftermath_lose": list(e.aftermath_lose),
        "treasure_deltas": dict(e.treasure_deltas),
        "treasure_name_zh": e.treasure_name_zh,
        "gallery_intro_zh": e.gallery_intro_zh,
    }


def _ending_to_dict(k: str, e) -> dict:
    return {
        "key": k,
        "name": e.name,
        "title": e.title,
        "narrative_pages": list(e.narrative_pages),
        "quote": e.quote,
        "cg_path": e.cg_path,
    }


def _whim_to_dict(w) -> dict:
    return {
        "key": w.key,
        "display_name": w.display_name,
        "epithet": w.epithet,
        "location_zh": w.location_zh,
        "preamble_para1": w.preamble_para1,
        "preamble_para2": w.preamble_para2,
        "chat": w.chat,
        "quiz_opening_zh": w.quiz_opening_zh,
        "aftermath_correct_para1": w.aftermath_correct_para1,
        "aftermath_correct_para2": w.aftermath_correct_para2,
        "aftermath_wrong_para1": w.aftermath_wrong_para1,
        "aftermath_wrong_para2": w.aftermath_wrong_para2,
        "deltas_correct": dict(w.deltas_correct),
        "deltas_wrong": dict(w.deltas_wrong),
        "cg_basename": w.cg_basename,
        "gallery_footer_zh": w.gallery_footer_zh,
    }


def main() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)

    from endings import ENDINGS
    from encounter_defs import _BOSSES, _ELITES, _MONSTERS
    from incident_aftermath_table import INCIDENT_AFTERMATH_BY_ID
    from incident_events import ALL_INCIDENTS
    from major_events import MAJOR_EVENTS
    from whim_events import WHIM_ENCOUNTERS, WHIM_ENCOUNTER_KEYS_ORDER

    majors = [_major_to_dict(m) for m in MAJOR_EVENTS]
    (WEB_DATA / "majors.json").write_text(
        json.dumps(majors, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    incidents = [_incident_to_dict(e) for e in ALL_INCIDENTS]
    (WEB_DATA / "incidents.json").write_text(
        json.dumps(incidents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    aftermath: dict[str, list[list[str]]] = {}
    for eid, triple in INCIDENT_AFTERMATH_BY_ID.items():
        aftermath[eid] = [list(paragraphs) for paragraphs in triple]
    (WEB_DATA / "incident_aftermath.json").write_text(
        json.dumps(aftermath, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    encounters = {
        "monsters": [_enemy_to_dict(e) for e in _MONSTERS],
        "elites": [_enemy_to_dict(e) for e in _ELITES],
        "bosses": [_enemy_to_dict(e) for e in _BOSSES],
    }
    (WEB_DATA / "encounters.json").write_text(
        json.dumps(encounters, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    endings_out = [_ending_to_dict(k, v) for k, v in ENDINGS.items()]
    (WEB_DATA / "endings.json").write_text(
        json.dumps(endings_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    whims = [_whim_to_dict(w) for w in WHIM_ENCOUNTERS]
    (WEB_DATA / "whim_encounters.json").write_text(
        json.dumps(whims, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (WEB_DATA / "whim_npc_keys_order.json").write_text(
        json.dumps(list(WHIM_ENCOUNTER_KEYS_ORDER), ensure_ascii=False),
        encoding="utf-8",
    )

    from gallery_rewards import (
        _REWARD_CAPTION_BY_REL_PATH,
        reward_cg_tables,
        reward_gallery_scene_fallback_zh,
    )

    _rels_by_token, _, _ = reward_cg_tables(ROOT)
    reward_paths = sorted({r for paths in _rels_by_token.values() for r in paths})
    (WEB_DATA / "gallery_rewards.json").write_text(
        json.dumps(reward_paths, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reward_entries: list[dict] = []
    for tok in sorted(_rels_by_token.keys()):
        req_keys = tok.split("+")
        for rel in sorted(_rels_by_token[tok]):
            reward_entries.append(
                {"rel": rel, "token": tok, "required_keys": req_keys}
            )
    (WEB_DATA / "gallery_reward_entries.json").write_text(
        json.dumps(reward_entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _fb = reward_gallery_scene_fallback_zh("x")
    _fb_one = "".join(_fb.split())
    reward_caption_map: dict[str, str] = {}
    for rel in reward_paths:
        raw = _REWARD_CAPTION_BY_REL_PATH.get(rel)
        if raw and str(raw).strip():
            reward_caption_map[rel] = "".join(str(raw).strip().split())
        else:
            reward_caption_map[rel] = _fb_one
    (WEB_DATA / "gallery_reward_captions.json").write_text(
        json.dumps(reward_caption_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    wq_src = ROOT / "whim_questions.json"
    wq_dst = ROOT / "web" / "src" / "data" / "whim_questions.json"
    wq_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(wq_src, wq_dst)

    print(f"OK: wrote {WEB_DATA} and {wq_dst}")


if __name__ == "__main__":
    main()
