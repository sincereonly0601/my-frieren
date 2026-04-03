"""
葬送的魔法使夢工廠：可調整大小的桌面視窗、內部邏輯畫布、標題選單與五格存檔。
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Literal

import pygame

os.environ.setdefault("SDL_IME_SHOW_UI", "1")

# SDL2 輸入法組字（Pygame 2.0+）
_PYGAME_TEXTEDITING = getattr(pygame, "TEXTEDITING", None)

from ending_gallery import (
    GALLERY_ENDING_KEYS,
    GALLERY_FEMALE_ENDING_KEYS,
    GALLERY_MALE_ENDING_KEYS,
    cheat_unlock_companion_enemy_gallery_cg,
    clear_all_gallery_unlock_data,
    companion_gallery_key_order,
    load_companion_gallery_unlocked,
    load_enemy_gallery_unlocked,
    load_whim_gallery_unlocked,
    load_gallery_unlocked,
    register_enemy_gallery_unlock,
    register_gallery_unlock,
    register_whim_gallery_unlock,
    save_gallery_unlocked,
)
from gallery_rewards import (
    all_reward_gallery_slots,
    reward_gallery_footer_source_zh,
    reward_token_label_zh,
    sorted_reward_gallery_slots_for_display,
)
from endings import (
    ENDING_CG_UNLOCK_HINT_ITEMS_BY_KEY,
    ENDINGS,
    Ending,
    resolve_ending,
)
from encounter_defs import (
    ENCOUNTER_GALLERY_ORDER,
    ENCOUNTER_TRIGGER_YEARS,
    EncounterEnemy,
    encounter_protagonist_pronoun_adjust_zh,
    format_encounter_deltas_brief,
    get_enemy_by_id,
    pick_random_encounter,
)
from encounter_draw import (
    ENCOUNTER_BATTLE_TICKS_PER_STEP,
    draw_encounter_aftermath_screen,
    draw_encounter_battle_screen,
    draw_encounter_enemy_placeholder,
    draw_encounter_gallery_screen,
    draw_gallery_cell_locked_cross,
    encounter_gallery_cg_fill,
)
from encounter_sim import BattleOutcome, simulate_encounter
from adopter_questionnaire import (
    ADOPTER_QUESTIONNAIRE_COUNT,
    draw_adopter_questionnaire_result_screen,
    draw_adopter_questionnaire_screen,
    finalize_adopter_questionnaire,
)
from game_state import GameState, TOTAL_TRAINING_QUARTERS
from incident_events import (
    INCIDENT_TRIGGER_YEARS,
    IncidentEvent,
    format_incident_deltas_brief,
    pick_random_incident,
)
from incident_art import draw_incident_illustration
from intro_art import draw_guardian_illustration, draw_prologue_illustration
from major_event_art import draw_major_event_illustration
from major_events import (
    MAJOR_TRIGGER_YEARS,
    MajorEvent,
    MajorEventOption,
    format_major_deltas_brief,
    format_major_extra_brief,
    major_event_for_age,
)
from play_portrait import draw_heroine_portrait
from whim_draw import (
    draw_companion_gallery_placeholder,
    draw_companion_gallery_screen,
    draw_whim_event_screen,
    load_companion_gallery_cg_fill,
)
from whim_events import WHIM_ENCOUNTERS, WhimEncounter
from save_slots import (
    SLOT_COUNT,
    load_from_slot,
    save_to_slot,
    slot_path,
    slot_summary,
)
from story import (
    GUARDIAN_INTRO_SECTIONS,
    GUARDIAN_SECTION_HEADERS,
    PROLOGUE_SECTIONS,
    PROLOGUE_SECTION_HEADERS,
)
from training_actions import (
    TRAINING_ACTIONS,
    format_action_stat_effects_line,
    format_training_feedback_modal_message,
)
from training_feedback_fx import (
    draw_training_feedback_fx,
    draw_training_feedback_fx_into_rect,
)

from whim_events import (
    WhimEncounter,
    format_whim_deltas_line,
    whim_active_index_for_completed_quarters,
    whim_encounter_by_key,
    whim_resolved_question_for_index,
    seed_whim_schedule_for_new_playthrough,
)
from whim_questions import WHIM_QUESTIONS, WhimQuestion
from frieren_quiz import (
    FRIEREN_QUIZ_NUM_QUESTIONS,
    FrierenQuizPhase,
    draw_frieren_quiz_confirm,
    draw_frieren_quiz_screen,
    load_frieren_quiz_certificate_earned,
    save_frieren_quiz_certificate_earned,
)


def _ensure_whim_schedule_at_play_entry(state: GameState, rng: random.Random) -> None:
    """
    進入養成且本局為滿季、尚未排程奇遇時寫入排程。

    讀檔 ``goto_after_load`` 與契約完成進入 PLAY 皆須呼叫；若已有排程則不覆寫
    （見 ``seed_whim_schedule_for_new_playthrough``）。

    Args:
        state: 遊戲狀態。
        rng: 亂數源。
    """
    if state.time_left == TOTAL_TRAINING_QUARTERS and not state.whim_slots:
        seed_whim_schedule_for_new_playthrough(state, rng)


GAME_TITLE = "葬送的魔法使夢工廠"
TITLE_SCREEN_CREDIT_ZH = "本遊戲由林洋鈺製作"

_ORIG_W, _ORIG_H = 320, 180
CANVAS_WIDTH = 960
CANVAS_HEIGHT = 540


def _resolve_asset_root() -> Path:
    """
    內建資源根目錄（CG、BGM、打包入執行檔之 assets）。

    PyInstaller 一檔／目錄打包時為 ``sys._MEIPASS``；開發時為專案目錄。

    Returns:
        必為已解析之絕對路徑。
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parent


def _resolve_userdata_root() -> Path:
    """
    可寫入資料根目錄（存檔、saves/、ending_gallery_unlock.json）。

    打包後為 ``.exe`` 所在資料夾，方便使用者備份；開發時為專案目錄。

    Returns:
        必為已解析之絕對路徑。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


_GAME_ASSET_ROOT = _resolve_asset_root()
_GAME_USERDATA_ROOT = _resolve_userdata_root()
_BGM_DIR = _GAME_ASSET_ROOT / "assets" / "bgm"

_WHIM_BY_CG_BASENAME: dict[str, WhimEncounter] = {
    w.cg_basename: w for w in WHIM_ENCOUNTERS
}

# 結局 CG：``endings.Ending.cg_path`` 慣用 .jpg；若僅提供 .png 等亦可自動對應。
_ENDING_CG_ALT_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")


def _resolve_ending_cg_disk_path(rel: str) -> Path | None:
    """
    將結局 CG 的相對路徑解析為實際存在之檔案。

    若 ``rel`` 指向之檔案不存在，則以相同主檔名依序嘗試 .jpg、.jpeg、.png、.webp。

    Args:
        rel: 相對於資源根目錄之路徑（與 ``Ending.cg_path`` 相同）。

    Returns:
        存在則為絕對 ``Path``，否則 None。
    """
    base = _GAME_ASSET_ROOT / rel
    if base.is_file():
        return base
    stem = base.with_suffix("")
    for ext in _ENDING_CG_ALT_EXTENSIONS:
        cand = stem.with_suffix(ext)
        if cand.is_file():
            return cand
    return None


def _delete_all_save_slot_files(root: Path) -> None:
    """
    刪除指定根目錄下五格存檔 JSON（``saves/save_1.json``～``save_5.json``）；無檔則略過。

    Args:
        root: 與 ``_GAME_USERDATA_ROOT`` 相同之可寫入根目錄。
    """
    for i in range(1, SLOT_COUNT + 1):
        p = slot_path(i, root)
        if p.is_file():
            p.unlink()


# 檔名須與 ``assets/bgm`` 內 OGG 一致（含空白）。
_BGM_OPENING = _BGM_DIR / "Journey of a Lifetime.ogg"
_BGM_PROLOGUE = _BGM_DIR / "Fear Brought Me This Far.ogg"
_BGM_CHILDHOOD = _BGM_DIR / "Time Flows Ever Onward.ogg"
_BGM_MAJOR = _BGM_DIR / "Zoltraak.ogg"
_BGM_ADOLESCENCE = _BGM_DIR / "The End of One Journey.ogg"
_ENDING_CG_RAW_CACHE: dict[str, pygame.Surface | None] = {}
_ENDING_CG_SCALED_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}
_ENDING_CG_FILL_CACHE: dict[tuple[str, int, int, str, float], pygame.Surface] = {}

INITIAL_WINDOW_SCALE = 1
WINDOW_FLAGS = pygame.RESIZABLE

_FONT_UI_PX = max(19, min(26, CANVAS_HEIGHT // 22))
_FONT_SMALL_PX = max(15, min(20, CANVAS_HEIGHT // 30))
# 開場連貫畫面主文：前言、監護人標題／內文、取名、問卷主文、契約標題與偽古文、署名（同像素；標題僅加粗／楷體區分）
_FONT_ONBOARDING_PX = max(18, min(21, CANVAS_HEIGHT // 26))
# 監護人須知主標題（略大於內文，仍屬開場階層）
_FONT_GUARDIAN_TITLE_PX = max(20, min(26, CANVAS_HEIGHT // 21))
# 主標／副標：主標加大、副標略小，仍留垂直空間給選單
_FONT_TITLE_SCREEN_MAIN_PX = max(38, min(68, 24 * CANVAS_HEIGHT // _ORIG_H))
_FONT_TITLE_SCREEN_SUB_PX = max(20, min(40, 13 * CANVAS_HEIGHT // _ORIG_H))
# 標題畫面：選單與底部說明（比先前略大，仍明顯小於副標）
_FONT_TITLE_MENU_PX = max(20, min(26, CANVAS_HEIGHT // 24))
_FONT_TITLE_HINT_PX = max(14, min(18, CANVAS_HEIGHT // 30))
# 芙莉蓮測驗：題目／選項／詳解／結算／頁尾提示同一固定字級（不依 CANVAS_HEIGHT 公式變動）
_FRIEREN_QUIZ_FONT_PX = 22
# 結算四字印：以主測驗字級乘倍率直接繪製（略大於舊版 2.35，仍避開與內框／底欄明顯衝突）。
_FRIEREN_QUIZ_SEAL_FONT_PX = max(28, int(round(_FRIEREN_QUIZ_FONT_PX * 2.62)))
# 契約手寫感署名：楷／行楷視覺偏小，字級明顯大於 UI 主文，使真名像實際簽名。
_FONT_CONTRACT_SIGNATURE_PX = max(30, min(46, 15 * CANVAS_HEIGHT // _ORIG_H))
# 重大／突發事件前導：主標（介於標題畫面主標與一般 UI 之間，粗體）、標題下說明；外框重大＝紅脈動、突發＝紫紅冷調
_FONT_EVENT_ALERT_TITLE_PX = max(40, min(62, 22 * CANVAS_HEIGHT // _ORIG_H))
_FONT_EVENT_ALERT_TEASER_PX = max(17, min(24, CANVAS_HEIGHT // 24))
_TEXT_PAD_X = 16
# 重大／突發事件數值提示停留時間（毫秒）：餘韻畫面與無餘韻直接回養成時皆用此值
_TOAST_DURATION_PLAY_EVENT_MS = 1500

# 進入重大／突發事件前之全畫面提示（加大主標＋一句前導；Enter 後進本傳）。
_EVENT_ALERT_TITLE_MAJOR_ZH = "重大事件"
_EVENT_ALERT_TITLE_INCIDENT_ZH = "突發事件"
_EVENT_ALERT_TEASER_BY_MAJOR_AGE: dict[int, str] = {
    8: "石室深處的符文將映入眼底——邊境、禁書與無名術式，即將在妳面前展開第一頁。",
    13: "口試廳燈火穩定，紀錄員的筆卻不停——俘虜的一句話，即將逼出妳對公義的界定。",
    17: "告示板前雨絲與紅字交錯——北境、徵召與餘生，即將等妳簽下無法假裝沒看見的選擇。",
}
_EVENT_ALERT_TEASER_INCIDENT_ZH = (
    "平穩的日子裡即將泛起漣漪：一則旅途中的插曲，正等妳讀完、選完、承擔後果。"
)
_EVENT_ALERT_TEASER_FALLBACK_ZH = "關鍵抉擇即將展開——Enter 後細讀內文，為這段養成寫下新的一筆。"
_EVENT_ALERT_TITLE_ENCOUNTER_ZH = "遭遇戰"
_EVENT_ALERT_TEASER_ENCOUNTER_BY_AGE: dict[int, str] = {
    6: "小路轉角傳來非人的氣息——這一戰無法迴避，咒文與意志即將正面受試。",
    11: "名號與危險同幅膨脹：強敵當前，勝負將在電光石火間分曉。",
    16: "壓迫感如暴風眼逼近——頭目級的存在，正把妳逼進不得不拔術式的距離。",
}


def _event_alert_title_zh(
    major_age: int | None,
    *,
    is_encounter: bool = False,
) -> str:
    """
    依即將進入之事件類型回傳全畫面中央標題。

    Args:
        major_age: 若非 ``None`` 表示即將進入重大事件（8／13／17）；``None`` 且非遭遇戰則為突發事件。
        is_encounter: 即將進入遭遇戰。

    Returns:
        顯示用中文標題。
    """
    if is_encounter:
        return _EVENT_ALERT_TITLE_ENCOUNTER_ZH
    if major_age is None:
        return _EVENT_ALERT_TITLE_INCIDENT_ZH
    return _EVENT_ALERT_TITLE_MAJOR_ZH


def _event_alert_teaser_zh(
    major_age: int | None,
    *,
    is_encounter: bool = False,
    encounter_age: int | None = None,
) -> str:
    """
    前導畫面標題下方一句說明，依事件類型／滿歲區分以吸引閱讀本傳。

    Args:
        major_age: ``None`` 為突發事件；8／13／17 為對應重大事件。
        is_encounter: 遭遇戰前導。
        encounter_age: 遭遇戰滿歲（6／11／16）。

    Returns:
        說明全文（可換行為多行顯示）。
    """
    if is_encounter and encounter_age is not None:
        return _EVENT_ALERT_TEASER_ENCOUNTER_BY_AGE.get(
            encounter_age,
            _EVENT_ALERT_TEASER_FALLBACK_ZH,
        )
    if major_age is None:
        return _EVENT_ALERT_TEASER_INCIDENT_ZH
    return _EVENT_ALERT_TEASER_BY_MAJOR_AGE.get(major_age, _EVENT_ALERT_TEASER_FALLBACK_ZH)


def _make_event_alert_title_font() -> pygame.font.Font:
    """
    重大／突發事件前導畫面主標字型（加大、粗體）。

    Returns:
        ``SysFont`` 實例。
    """
    names = (
        "microsoftyaheiui",
        "microsoftyahei",
        "pingfang sc",
        "noto sans cjk tc",
        "simsun",
    )
    return pygame.font.SysFont(",".join(names), _FONT_EVENT_ALERT_TITLE_PX, bold=True)


def _make_event_alert_teaser_font() -> pygame.font.Font:
    """
    前導畫面主標下方說明用字型（小於主標、大於頁尾提示）。

    Returns:
        ``SysFont`` 實例。
    """
    names = (
        "microsoftyaheiui",
        "microsoftyahei",
        "pingfang sc",
        "noto sans cjk tc",
        "simsun",
    )
    return pygame.font.SysFont(",".join(names), _FONT_EVENT_ALERT_TEASER_PX)


def draw_event_alert_screen(
    canvas: pygame.Surface,
    title_font: pygame.font.Font,
    teaser_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    event_alert_major_age: int | None,
    tick: int,
    *,
    event_alert_is_encounter: bool = False,
    event_alert_is_whim: bool = False,
    encounter_alert_age: int | None = None,
    protagonist_gender: str = "female",
) -> None:
    """
    重大／突發／遭遇戰進場前之全畫面提示（加大粗體主標、標題下前導句、脈動邊框；Enter 後進本傳）。
    重大事件與遭遇戰外框為紅色系脈動；突發事件為紫紅冷調。

    Args:
        canvas: 邏輯畫布。
        title_font: 中央主標（建議粗體大字）。
        teaser_font: 主標下方前導說明。
        hint_font: 底列操作提示。
        event_alert_major_age: 與執行緒狀態 ``event_alert_major_age`` 相同；用以區分標題與前導文案。
        tick: 影格（邊框明暗用）。
        event_alert_is_encounter: 遭遇戰前導（紅框）。
        event_alert_is_whim: 奇遇事件前導（冷調藍框）。
        encounter_alert_age: 遭遇戰滿歲（6／11／16），供前導句選擇。
        protagonist_gender: 遭遇戰前導句內「妳／你」依此調整。
    """
    use_red_frame = (
        not event_alert_is_whim
        and (
            (event_alert_major_age is not None and not event_alert_is_encounter)
            or event_alert_is_encounter
        )
    )
    use_whim_frame = event_alert_is_whim
    canvas.fill(
        (16, 22, 30)
        if use_whim_frame
        else ((18, 10, 12) if use_red_frame else (14, 17, 26))
    )
    pulse = 0.5 + 0.5 * math.sin(tick * 0.09)
    if use_whim_frame:
        edge_r = int(55 + 75 * pulse)
        edge_g = int(120 + 120 * pulse)
        edge_b = int(190 + 45 * pulse)
        band_a = int(44 + 30 * pulse)
        ol_rgb = (25, 85, 130)
    elif use_red_frame:
        edge_r = int(120 + 135 * pulse)
        edge_g = int(18 + 42 * pulse)
        edge_b = int(22 + 48 * pulse)
        band_a = int(44 + 30 * pulse)
        ol_rgb = (32, 10, 14)
    else:
        edge_r = int(70 + 95 * pulse)
        edge_g = int(55 + 75 * pulse)
        edge_b = int(95 + 70 * pulse)
        band_a = int(38 + 22 * pulse)
        ol_rgb = (20, 24, 40)
    overlay = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
    overlay.fill((*ol_rgb, band_a))
    canvas.blit(overlay, (0, 0))
    frame_pad = _scale_x(5)
    inner = pygame.Rect(
        frame_pad,
        frame_pad,
        CANVAS_WIDTH - 2 * frame_pad,
        CANVAS_HEIGHT - 2 * frame_pad,
    )
    pygame.draw.rect(canvas, (edge_r, edge_g, edge_b), inner, width=max(2, _scale_x(3)))
    if event_alert_is_whim:
        title_zh = "奇遇事件"
    else:
        title_zh = _event_alert_title_zh(
            event_alert_major_age,
            is_encounter=event_alert_is_encounter,
        )
    title_surf = title_font.render(title_zh, True, (255, 228, 200))
    if event_alert_is_whim:
        teaser_zh = (
            "你在轉角與某段故事對上眼——"
            "彷彿下一幕正要開口，等你應聲。"
        )
    else:
        teaser_zh = _event_alert_teaser_zh(
            event_alert_major_age,
            is_encounter=event_alert_is_encounter,
            encounter_age=encounter_alert_age,
        )
        if event_alert_is_encounter:
            teaser_zh = encounter_protagonist_pronoun_adjust_zh(
                teaser_zh, protagonist_gender
            )
    mx_teaser = _scale_x(28)
    max_teaser_w = CANVAS_WIDTH - 2 * mx_teaser
    teaser_lines = wrap_cjk(teaser_font, teaser_zh, max_teaser_w)
    th = title_surf.get_height()
    title_teaser_gap = _scale_y(14)
    lh_teaser = teaser_font.get_height() + 3
    teaser_h = len(teaser_lines) * lh_teaser if teaser_lines else 0
    hint = "Enter 繼續"
    hy = CANVAS_HEIGHT - _scale_y(14) - hint_font.get_height()
    hs = hint_font.render(hint, True, (160, 170, 190))
    content_h = th + title_teaser_gap + teaser_h
    block_top = max(_scale_y(20), (hy - _scale_y(10) - content_h) // 2)
    canvas.blit(
        title_surf,
        ((CANVAS_WIDTH - title_surf.get_width()) // 2, block_top),
    )
    ty = block_top + th + title_teaser_gap
    teaser_col = (195, 205, 225)
    for tl in teaser_lines:
        surf = teaser_font.render(tl, True, teaser_col)
        canvas.blit(surf, ((CANVAS_WIDTH - surf.get_width()) // 2, ty))
        ty += lh_teaser
    canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy))


TITLE_MENU_ITEMS = (
    "新遊戲",
    "讀取進度",
    "圖片畫廊",
    "遊戲設定",
    "結束遊戲",
)
# 標題「遊戲設定」內選項（↑↓ Enter；Esc 回標題）。索引 0～4 始終可見；5～7 須輸入密技後才顯示。
CHEAT_MENU_ITEMS: tuple[str, ...] = (
    "芙莉蓮測驗",
    "各人物結局CG圖解鎖條件",
    "背景音樂",
    "清空畫廊已解鎖的CG圖",
    "清空所有存檔",
    "作弊開局：略過前言並進入高屬性養成",
    "解鎖畫廊全部結局CG圖",
    "解鎖畫廊全部夥伴與敵人CG圖",
)
# 開啟隱藏作弊項之密技確認視窗鍵（Enter 第二次確認、Esc 取消）
_CHEAT_MODAL_CONFIRM_GALLERY = "confirm_gallery_on"
_CHEAT_MODAL_CONFIRM_BOOTSTRAP = "confirm_bootstrap_on"
_CHEAT_MODAL_CONFIRM_CLEAR_GALLERY = "confirm_clear_gallery_unlock"
_CHEAT_MODAL_CONFIRM_CLEAR_SAVES = "confirm_clear_all_saves"
_CHEAT_MODAL_CONFIRM_UNLOCK_COMPANION_ENEMY = "confirm_unlock_companion_enemy_cg"
_CHEAT_MODAL_MESSAGES: dict[str, str] = {
    _CHEAT_MODAL_CONFIRM_GALLERY: (
        "確定要開啟「解鎖畫廊全部結局CG圖」作弊功能？\n\nEnter 確定　Esc 取消"
    ),
    _CHEAT_MODAL_CONFIRM_BOOTSTRAP: (
        "確定要開啟「作弊開局：略過前言並進入高屬性養成」？\n\n"
        "開啟後請從標題選「新遊戲」生效。\n\nEnter 確定　Esc 取消"
    ),
    _CHEAT_MODAL_CONFIRM_CLEAR_GALLERY: (
        "確定要清空「圖片畫廊」內所有已解鎖的 CG 紀錄？\n\nEnter 確定　Esc 取消"
    ),
    _CHEAT_MODAL_CONFIRM_CLEAR_SAVES: (
        "確定要刪除所有存檔？\n\nEnter 確定　Esc 取消"
    ),
    _CHEAT_MODAL_CONFIRM_UNLOCK_COMPANION_ENEMY: (
        "確定要解鎖「同行的夥伴(奇遇)」與「遭遇的強敵(遭遇戰)」畫廊內全部 CG？\n\n"
        "Enter 確定　Esc 取消"
    ),
}
# 於遊戲設定畫面內依序輸入（每次進入會重置進度；遊戲重啟後隱藏項目還原）。
# 僅接受 ←／→（與選單 ↑↓ 分離；不接受 A／D）。
_CHEAT_SECRET_SEQUENCE: tuple[str, ...] = (
    "left",
    "right",
    "left",
    "right",
    "left",
    "left",
    "right",
    "right",
)
# 標題版面：副標→首選項 ≈ _scale_y(4)+_scale_y(2)；選項間距 ≈ _scale_y(3)
# 副標與選單間距（加大＝整塊選單下移）
_TITLE_SUB_TO_MENU_GAP = (13 + 2) * CANVAS_HEIGHT // _ORIG_H
_TITLE_MENU_ITEM_GAP_Y = 3 * CANVAS_HEIGHT // _ORIG_H
# 畫廊：無對應結局資料鍵時的占位名稱（通關圖片未解鎖仍顯示 ``Ending.name``）
_GALLERY_UNKNOWN_NAME = "？？？？"
_GALLERY_SLOTS_PER_PAGE: int = 6
# 圖片畫廊主選單；「獎勵圖片」為組合 CG（見 ``gallery_rewards``）。
_GALLERY_HUB_MENU_ITEMS: tuple[str, ...] = (
    "通關圖片+結局(男性)",
    "通關圖片+結局(女性)",
    "同行的夥伴(奇遇)",
    "遭遇的強敵(遭遇戰)",
    "獎勵圖片",
)
_GALLERY_HUB_LOCKED_INDICES: frozenset[int] = frozenset()
# 插圖過高會吃掉內文；0.40 在 540p 約 216px
_INTRO_ART_HEIGHT_RATIO = 0.40
# 監護人須知上方插圖高度比例
_GUARDIAN_ART_HEIGHT_RATIO = 0.28
# 監護人須知與取名同頁：插圖縮高、底部保留取名區
_GUARDIAN_COMBINED_ART_RATIO = 0.17

_PLAY_PHASE_LABELS: dict[str, str] = {
    "childhood": "幼年",
    "adolescence": "少年",
    "young_adult": "青年",
    "youth": "青年",
    "adult": "青年",
}


def _play_phase_display_zh(phase: str, protagonist_gender: str) -> str:
    """
    依人生階段與主角性別回傳養成畫面 HUD 用中文階段稱呼。

    中期（adolescence）時，女性主角顯示「少女」、男性維持「少年」，以降低違和感。

    Args:
        phase: ``GameState.phase``（childhood／adolescence／young_adult 等）。
        protagonist_gender: ``female`` 或 ``male``。

    Returns:
        階段顯示字串；未知 ``phase`` 則原樣回傳。
    """
    if phase == "adolescence" and protagonist_gender != "male":
        return "少女"
    return _PLAY_PHASE_LABELS.get(phase, phase)


_PLAY_STATS_PANEL_MAX_W = min(320, CANVAS_WIDTH * 32 // 100)
_PLAY_PORTRAIT_MIN_FRAC_NUM = 11
_PLAY_PORTRAIT_MIN_FRAC_DEN = 20
# 主區與底部列之間細縫（邏輯格數愈小，主區愈高）
_PLAY_BAR_TOP_SPACER = 2 * CANVAS_HEIGHT // _ORIG_H
_PLAY_ACTION_EXTRA_GAP_Y = 1 * CANVAS_HEIGHT // _ORIG_H
# 遊玩 HUD：外緣留白（邏輯格數，0＝貼齊 CANVAS 四邊）；左欄與立繪間隙
_PLAY_HUD_EDGE_PAD_LOGICAL_X = 0
_PLAY_HUD_EDGE_PAD_LOGICAL_Y = 0
_PLAY_HUD_STATS_PORTRAIT_GAP_LOGICAL_X = 2
# 遊玩畫面底部條：結局／一般；培養中略高以容納 4×2 格＋最底功能註釋
_PLAY_ACTION_BAR_H = 56 * CANVAS_HEIGHT // _ORIG_H
# 略高於結局列，讓 4×2 培養格略大、底註可用較大字
_PLAY_ACTION_BAR_TRAINING_H = 78 * CANVAS_HEIGHT // _ORIG_H
# 培養格第二行（五維增減）與最底註釋列共用（略小於 `_FONT_SMALL_PX`）
_FONT_PLAY_FOOTER_PX = max(12, min(16, CANVAS_HEIGHT // 36))
# --- 培養結算回饋：訊息字串由 ``format_training_feedback_modal_message`` 產生；版面為固定邏輯格換算（不依內文／畫布比例變動）。 ---
_TRAINING_FEEDBACK_MODAL_HEADER = "本季培養回饋"
_TRAINING_FEEDBACK_MODAL_HINT = "【Enter】關閉"
_TRAINING_FEEDBACK_MODAL_STAT_PREFIX = "數值變化："
_TRAINING_FEEDBACK_MODAL_COLOR_HEADER = (42, 46, 58)
# 內文「深度閱讀：」等行動引導列（全形冒號前為行動名）。
_TRAINING_FEEDBACK_MODAL_COLOR_ACTION_LEAD = (48, 78, 108)
_TRAINING_FEEDBACK_MODAL_COLOR_BODY = (40, 42, 54)
_TRAINING_FEEDBACK_MODAL_COLOR_STAT = (28, 70, 116)
_TRAINING_FEEDBACK_MODAL_COLOR_HINT = (100, 104, 118)
_TRAINING_FEEDBACK_MODAL_SHELL_FILL = (255, 248, 220, 252)
_TRAINING_FEEDBACK_MODAL_SHELL_STROKE = (88, 96, 118)
_TRAINING_FEEDBACK_MODAL_SHELL_INNER_GLOW = (255, 255, 255, 55)
# 內距（320×180 邏輯格 → ``_scale_x`` / ``_scale_y``）；左右分開，左側較小可讓文字區整體靠左。
_TRAINING_FEEDBACK_MODAL_INNER_PAD_LEFT_LOGICAL_X = 10
_TRAINING_FEEDBACK_MODAL_INNER_PAD_RIGHT_LOGICAL_X = 18
_TRAINING_FEEDBACK_MODAL_INNER_PAD_LOGICAL_Y = 3
# 左欄換行寬上限（邏輯格）；實際寬度另受右側插圖區擠壓，見 ``draw_training_feedback_modal``。
_TRAINING_FEEDBACK_MODAL_TEXT_COL_LOGICAL_W = 168
# 左欄文字與右側插圖之間留白（邏輯格），避免長句與圖重疊。
_TRAINING_FEEDBACK_MODAL_TEXT_FX_GAP_LOGICAL_X = 6
# 有行動引導列時，敘事相對左緣微縮排（邏輯格）。
_TRAINING_FEEDBACK_MODAL_TEXT_BODY_INDENT_LOGICAL_X = 2
# 垂直間距（邏輯格）：標題／行動引導／敘事／數值／Enter 說明之間段落留白。
_TRAINING_FEEDBACK_MODAL_GAP_AFTER_HEADER_LOGICAL_Y = 8
_TRAINING_FEEDBACK_MODAL_GAP_AFTER_ACTION_LEAD_LOGICAL_Y = 6
_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_STAT_LOGICAL_Y = 10
# 內文與 Enter 說明之間最小間距；若內容較短，說明改貼近內容區底緣（見 ``HINT_BOTTOM_INSET``）。
_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y = 6
# Enter 說明距內容區底緣（邏輯格）；僅在垂直方向有餘裕時生效。
_TRAINING_FEEDBACK_MODAL_HINT_BOTTOM_INSET_LOGICAL_Y = 8
_TRAINING_FEEDBACK_MODAL_LINE_GAP_LOGICAL_Y = 4
_TRAINING_FEEDBACK_MODAL_STAT_LINE_GAP_LOGICAL_Y = 2
# 重大／突發餘韻內「數值變化」列（深色底；語意與前綴比照培養回饋 modal）
_EVENT_AFTERMATH_STAT_COLOR_ON_DARK = (175, 212, 252)
# 右側前景插圖矩形（邏輯格，固定；所有培養共用）。
_TRAINING_FEEDBACK_MODAL_FX_LOGICAL_W = 141
_TRAINING_FEEDBACK_MODAL_FX_LOGICAL_H = 100
# 插圖與內容區上、下距離（``_scale_x``／``_scale_y`` 換算；內容區高 = 圖高 + 2×此距離）。
_TRAINING_FEEDBACK_MODAL_FX_INSET_LOGICAL_X = 6
# 插圖與內容區右緣距離（可小於上欄，數值愈小圖愈靠右）。
# 0 = 圖右緣貼齊內容區右邊；負值 = 再往螢幕右伸入外框內距（每 -1 邏輯約 3px @960 寬）。
_TRAINING_FEEDBACK_MODAL_FX_INSET_RIGHT_LOGICAL_X = -3

# 蓋印動畫影格數（播畢後停格，僅 Enter 進入養成）。
_CONTRACT_SEAL_ANIM_DONE_AT = 90
# 動畫相位上限（與印鑑／火漆關鍵幀對齊）。
_CONTRACT_SEAL_PHASE_MAX = 85


class Screen(Enum):
    """目前畫面狀態。"""

    TITLE = auto()
    INTRO = auto()
    GUARDIAN_INTRO = auto()
    NAME_ENTRY = auto()
    ADOPTER_QUESTIONNAIRE = auto()
    CONTRACT_SEAL = auto()
    SLOT_SELECT = auto()
    SAVE_SLOT = auto()
    PLAY = auto()
    EVENT_ALERT = auto()
    WHIM_EVENT = auto()
    INCIDENT = auto()
    ENCOUNTER_BATTLE = auto()
    MAJOR_EVENT = auto()
    ENDING = auto()
    GALLERY_HUB = auto()
    GALLERY = auto()
    CHEAT_MENU = auto()
    CHEAT_GALLERY_HINTS = auto()
    FRIEREN_QUIZ = auto()


def _bgm_track_for_screen(
    screen_mode: Screen,
    state: GameState,
    *,
    event_alert_next: Screen | None = None,
) -> Path:
    """
    依目前畫面與養成階段選擇 BGM 檔（``assets/bgm`` 內 OGG）。

    對應：標題／畫廊／作弊／存檔選單＝開場曲；開場前言／監護人須知／取名／領養者問卷／契約＝Fear；
    幼年養成＝Time；少年養成＝The End of One Journey；青年養成＝Fear；
    突發事件（INCIDENT）與養成（PLAY）**同一套階段曲**，進場不切歌、持續循環；
    重大事件／遭遇戰＝Zoltraak；
    事件前導（EVENT_ALERT）：配樂**一律**與確認 Enter 後即將進入之畫面相同（無例外）。
    結局＝開場曲。

    Args:
        screen_mode: 目前畫面列舉。
        state: 遊戲狀態（``phase``：childhood／adolescence／young_adult）。
        event_alert_next: 前導確認後要進入的畫面（僅 ``EVENT_ALERT`` 時需帶入；其餘可省略）。

    Returns:
        音檔路徑（是否存在由播放端檢查）。
    """
    if screen_mode in (Screen.MAJOR_EVENT, Screen.ENCOUNTER_BATTLE):
        return _BGM_MAJOR
    if screen_mode is Screen.EVENT_ALERT:
        if event_alert_next is not None:
            return _bgm_track_for_screen(event_alert_next, state)
        return _bgm_track_for_screen(Screen.PLAY, state)
    if screen_mode is Screen.ENDING:
        return _BGM_OPENING
    if screen_mode in (
        Screen.INTRO,
        Screen.GUARDIAN_INTRO,
        Screen.NAME_ENTRY,
        Screen.ADOPTER_QUESTIONNAIRE,
        Screen.CONTRACT_SEAL,
    ):
        return _BGM_PROLOGUE
    if screen_mode in (Screen.PLAY, Screen.INCIDENT, Screen.WHIM_EVENT):
        if state.phase == "childhood":
            return _BGM_CHILDHOOD
        if state.phase == "adolescence":
            return _BGM_ADOLESCENCE
        return _BGM_PROLOGUE
    return _BGM_OPENING


def _get_scaled_ending_cg(cg_path: str, tw: int, th: int) -> pygame.Surface | None:
    """
    載入結局 CG 並等比例縮放至不超過 (tw, th)（contain）。

    Args:
        cg_path: 相對專案根目錄之路徑。
        tw: 最大寬。
        th: 最大高。

    Returns:
        成功則為縮放後 Surface，否則 None。
    """
    resolved = _resolve_ending_cg_disk_path(cg_path)
    if resolved is None:
        return None
    if cg_path not in _ENDING_CG_RAW_CACHE:
        try:
            _ENDING_CG_RAW_CACHE[cg_path] = pygame.image.load(os.fsdecode(resolved)).convert_alpha()
        except (pygame.error, OSError):
            _ENDING_CG_RAW_CACHE[cg_path] = None
    raw = _ENDING_CG_RAW_CACHE[cg_path]
    if raw is None:
        return None
    key_sc = (cg_path, tw, th)
    if key_sc not in _ENDING_CG_SCALED_CACHE:
        rw, rh = raw.get_size()
        if rw <= 0 or rh <= 0:
            return None
        scale = min(tw / rw, th / rh)
        nw = max(1, int(rw * scale))
        nh = max(1, int(rh * scale))
        _ENDING_CG_SCALED_CACHE[key_sc] = pygame.transform.smoothscale(raw, (nw, nh))
    return _ENDING_CG_SCALED_CACHE[key_sc]


def _get_scaled_ending_cg_fill(
    cg_path: str,
    tw: int,
    th: int,
    *,
    vertical_align: Literal["center", "bottom"] = "center",
    bottom_toward_center_blend: float = 0.0,
) -> pygame.Surface | None:
    """
    載入結局 CG 並等比例縮放為「覆蓋」目標矩形（cover）：畫面填滿 tw×th，超出部分裁切。

    Args:
        cg_path: 相對專案根目錄之路徑。
        tw: 輸出寬（像素）。
        th: 輸出高（像素）。
        vertical_align: 垂直裁切錨點。``center`` 為置中；``bottom`` 為底對齊（保留圖片下方、裁掉上方，適合底部字幕）。
        bottom_toward_center_blend: 僅 ``vertical_align`` 為 ``bottom`` 時有效；0 為純底對齊，0～1 之間向置中插值，
            可略多露出圖片上方（仍偏保留下方字幕區）。

    Returns:
        恰好為 tw×th 的 Surface；失敗則 None。
    """
    resolved = _resolve_ending_cg_disk_path(cg_path)
    if resolved is None:
        return None
    if cg_path not in _ENDING_CG_RAW_CACHE:
        try:
            _ENDING_CG_RAW_CACHE[cg_path] = pygame.image.load(os.fsdecode(resolved)).convert_alpha()
        except (pygame.error, OSError):
            _ENDING_CG_RAW_CACHE[cg_path] = None
    raw = _ENDING_CG_RAW_CACHE[cg_path]
    if raw is None:
        return None
    tw = max(1, tw)
    th = max(1, th)
    blend = max(0.0, min(1.0, float(bottom_toward_center_blend)))
    key_fill = (cg_path, tw, th, vertical_align, blend)
    if key_fill not in _ENDING_CG_FILL_CACHE:
        rw, rh = raw.get_size()
        if rw <= 0 or rh <= 0:
            return None
        scale = max(tw / rw, th / rh)
        nw = max(1, int(rw * scale))
        nh = max(1, int(rh * scale))
        scaled = pygame.transform.smoothscale(raw, (nw, nh))
        out = pygame.Surface((tw, th), pygame.SRCALPHA)
        out.fill((0, 0, 0, 0))
        bx = (tw - nw) // 2
        if vertical_align == "center":
            by = (th - nh) // 2
        else:
            by_bottom = th - nh
            by_center = (th - nh) // 2
            by = int(by_bottom + (by_center - by_bottom) * blend)
        out.blit(scaled, (bx, by))
        _ENDING_CG_FILL_CACHE[key_fill] = out
    return _ENDING_CG_FILL_CACHE[key_fill]


def _scale_x(x: int) -> int:
    """邏輯畫布 x 由 320p 基準換算。"""
    return x * CANVAS_WIDTH // _ORIG_W


def _scale_y(y: int) -> int:
    """邏輯畫布 y 由 180p 基準換算。"""
    return y * CANVAS_HEIGHT // _ORIG_H


def _make_ui_font() -> pygame.font.Font:
    """一般 UI 字型。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_UI_PX)


def _make_small_font() -> pygame.font.Font:
    """小字。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_SMALL_PX)


_play_footer_font: pygame.font.Font | None = None
_play_footer_font_cached_px: int = -1


def _get_play_footer_font() -> pygame.font.Font:
    """
    培養格第二行（五維增減）與最底功能註釋共用字型（延遲建立）。

    Returns:
        註釋／數值行字型。
    """
    global _play_footer_font, _play_footer_font_cached_px
    if (
        _play_footer_font is None
        or _play_footer_font_cached_px != _FONT_PLAY_FOOTER_PX
    ):
        names = (
            "microsoftyaheiui",
            "microsoftyahei",
            "pingfang sc",
            "noto sans cjk tc",
            "simsun",
        )
        _play_footer_font = pygame.font.SysFont(",".join(names), _FONT_PLAY_FOOTER_PX)
        _play_footer_font_cached_px = _FONT_PLAY_FOOTER_PX
    return _play_footer_font


def _make_title_screen_main_font() -> pygame.font.Font:
    """標題畫面主標。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_TITLE_SCREEN_MAIN_PX, bold=True)


def _make_title_screen_sub_font() -> pygame.font.Font:
    """標題畫面副標。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_TITLE_SCREEN_SUB_PX)


def _make_intro_font() -> pygame.font.Font:
    """開場連貫畫面主文：前言內文與章節小標（與監護人／取名／問卷／契約內文同像素）。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_ONBOARDING_PX)


def _make_title_menu_font() -> pygame.font.Font:
    """標題畫面四選項用字型。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_TITLE_MENU_PX)


def _make_title_hint_font() -> pygame.font.Font:
    """標題畫面底部操作說明用字型。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_TITLE_HINT_PX)


def _make_frieren_quiz_font() -> pygame.font.Font:
    """
    芙莉蓮測驗專用字型（標題、題幹、選項、回饋、結算、操作提示同一字級）。

    Returns:
        ``SysFont`` 實例；像素為 ``_FRIEREN_QUIZ_FONT_PX``。
    """
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FRIEREN_QUIZ_FONT_PX)


def _make_frieren_quiz_seal_font() -> pygame.font.Font:
    """
    芙莉蓮測驗結算四字印用字型（較大字級、粗體，不經縮放即可達視覺尺寸）。

    Returns:
        ``SysFont`` 實例；像素為 ``_FRIEREN_QUIZ_SEAL_FONT_PX``。
    """
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FRIEREN_QUIZ_SEAL_FONT_PX, bold=True)


def _make_guardian_header_font() -> pygame.font.Font:
    """監護人須知標題列（字級略大於內文，粗體）。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_GUARDIAN_TITLE_PX, bold=True)


def _make_guardian_body_font() -> pygame.font.Font:
    """監護人須知內文（與前言／取名等開場主文同字級）。"""
    names = ("microsoftyaheiui", "microsoftyahei", "pingfang sc", "noto sans cjk tc", "simsun")
    return pygame.font.SysFont(",".join(names), _FONT_ONBOARDING_PX)


def _make_contract_signature_font() -> pygame.font.Font:
    """
    契約真名署名：優先系統內建行楷／楷體（較像手寫簽名），否則退回一般黑體。

    字級使用 ``_FONT_CONTRACT_SIGNATURE_PX``（明顯大於偽古文與標籤，使真名像實際簽名）。

    Returns:
        `pygame.font.Font`。
    """
    names = (
        "stkaiti",
        "stxingkai",
        "stxinwei",
        "kaiti",
        "simkai",
        "dfkai-sb",
        "fzkaiti",
        "microsoftjhenghei",
        "microsoftyaheiui",
        "microsoftyahei",
        "segoescript",
    )
    return pygame.font.SysFont(",".join(names), _FONT_CONTRACT_SIGNATURE_PX, italic=False)


def wrap_cjk(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """
    依字型寬度將中文／混排文字換行。

    Args:
        font: 量測用字型。
        text: 原文。
        max_width: 單行最大像素寬。

    Returns:
        各行字串。
    """
    if max_width <= 0:
        return [text] if text else [""]
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines if lines else [""]


_WEAK_ZH_LINE_END = frozenset("，；、：")


def _gallery_try_split_two_lines_no_weak_line1_end(
    font: pygame.font.Font,
    full: str,
    max_w: int,
) -> tuple[str, str] | None:
    """
    尋找切分點使前後兩段皆單行可排，且第一行末字非弱句讀（避免「第一行以逗號／分號結尾」）。

    Args:
        font: 與底欄相同之字型。
        full: 單段正文。
        max_w: 單行最大像素寬。

    Returns:
        可拆則 (前段, 後段)；否則 None（由呼叫端改回 ``wrap_cjk``）。
    """
    s = (full or "").strip()
    n = len(s)
    if n < 2 or max_w <= 0:
        return None
    for k in range(n - 1, 0, -1):
        a, b = s[:k], s[k:]
        if not b.strip():
            continue
        if font.size(a)[0] > max_w or font.size(b)[0] > max_w:
            continue
        if a[-1] in _WEAK_ZH_LINE_END:
            continue
        return (a, b)
    return None


def _menu_prefix_column_width(font: pygame.font.Font) -> int:
    """
    選單游標列「▶ 」與未選「  」之像素寬取較大者，供固定前綴欄寬；正文自欄右緣起畫，
    切換選項時僅變色、不因前綴寬差而左右位移。

    Args:
        font: 與該選單列相同之字型。

    Returns:
        前綴欄寬（像素，至少為 1）。
    """
    return max(1, font.size("▶ ")[0], font.size("  ")[0])


def _blit_event_style_choice_cell(
    canvas: pygame.Surface,
    mx: int,
    y: int,
    max_w: int,
    font: pygame.font.Font,
    label: str,
    selected: bool,
    *,
    opt_gap_after: int | None = None,
    compact: bool = False,
) -> int:
    """
    繪製單一選項方框（填色、圓角邊框、內文），與突發／重大事件選項列一致。

    Args:
        canvas: 畫布。
        mx: 選項區基準左 x（文字自 ``mx + pad_x`` 起；方框左為 ``mx - pad_x``）。
        y: 此方框頂 y。
        max_w: 與 ``draw_incident_screen`` 相同之欄寬度量（內文可用寬為 ``max_w - 2*pad_x``）。
        font: 選項字級。
        label: 已含編號之整段標籤（例如 ``1. 男孩``）。
        selected: 是否為目前游標選中。
        opt_gap_after: 底緣與下一選項頂之距離；``None`` 時依是否 ``compact`` 決定。
        compact: 為 True 時縮小上下內距、行距與預設選項間距（監護人性別等短選項用）。

    Returns:
        下一選項應開始的 y（已含選項間距）。
    """
    line_extra = 1 if compact else 2
    lh = font.get_height() + line_extra
    pad_x = _scale_x(6)
    pad_y = _scale_y(3 if compact else 5)
    inner_tw = max(1, max_w - 2 * pad_x)
    cell_w = max_w + 2 * pad_x
    lines = wrap_cjk(font, label, inner_tw)
    block_h = len(lines) * lh + 2 * pad_y
    cell = pygame.Rect(mx - pad_x, y, cell_w, block_h)
    fill = (58, 74, 102) if selected else (36, 40, 52)
    border = (140, 165, 205) if selected else (70, 78, 96)
    # 選中與否皆相同邊框粗細，避免框線由 1→2 像素時內容視覺上左右偏移。
    bw = 2
    rad = max(3, min(cell.h // 8, cell.w // 8))
    pygame.draw.rect(canvas, fill, cell, border_radius=rad)
    pygame.draw.rect(canvas, border, cell, width=bw, border_radius=rad)
    title_col = (248, 250, 255) if selected else (210, 216, 228)
    ty = y + pad_y
    for L in lines:
        canvas.blit(font.render(L, True, title_col), (mx + pad_x, ty))
        ty += lh
    if opt_gap_after is None:
        gap = _scale_y(2 if compact else 4)
    else:
        gap = opt_gap_after
    return y + block_h + gap


def _event_style_choice_column_height(
    font: pygame.font.Font,
    max_w: int,
    labels: tuple[str, ...],
    *,
    opt_gap: int | None = None,
    compact: bool = False,
) -> int:
    """
    估算一欄事件風格選項方框之總高度（選項之間含間距、最後不含尾距）。

    Args:
        font: 選項字。
        max_w: 與 ``_blit_event_style_choice_cell`` 之 ``max_w`` 相同。
        labels: 各選項已編號之標籤。
        opt_gap: 選項間距；``None`` 則依 ``compact`` 決定。
        compact: 須與繪製時傳入 ``_blit_event_style_choice_cell`` 者一致。

    Returns:
        像素高度。
    """
    line_extra = 1 if compact else 2
    lh = font.get_height() + line_extra
    pad_x = _scale_x(6)
    pad_y = _scale_y(3 if compact else 5)
    inner_tw = max(1, max_w - 2 * pad_x)
    if opt_gap is None:
        g = _scale_y(2 if compact else 4)
    else:
        g = opt_gap
    total = 0
    for i, lab in enumerate(labels):
        n_lines = len(wrap_cjk(font, lab, inner_tw))
        block_h = n_lines * lh + 2 * pad_y
        total += block_h
        if i + 1 < len(labels):
            total += g
    return total


def _resolution_art_h() -> int:
    """
    重大／突發餘韻畫面上方插圖區高度（與各 draw_*_resolution／aftermath 一致）。

    Returns:
        像素高度。
    """
    return min(230, max(120, int(CANVAS_HEIGHT * _INTRO_ART_HEIGHT_RATIO)))


def _resolution_art_h_aftermath_compact() -> int:
    """
    餘韻畫面專用：較矮的插圖區，空出垂直空間以盡量將全文＋數值變化壓在單頁。

    Returns:
        像素高度。
    """
    return min(168, max(86, int(CANVAS_HEIGHT * 0.275)))


def _aftermath_para_gap_px() -> int:
    """餘韻段落之段後間距（邏輯格換算，較一般 4 格略緊以省垂直空間）。"""
    return 3 * CANVAS_HEIGHT // _ORIG_H


def _resolution_text_limit_y(small_font: pygame.font.Font, max_w: int) -> tuple[int, int]:
    """
    餘韻正文下緣與頁尾頂端（預留操作說明列）。

    Args:
        small_font: 頁尾字型。
        max_w: 單行最大寬。

    Returns:
        ``(text_limit_y, footer_top)``。
    """
    nav_raw = "【Enter】返回養成"
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    footer_top = CANVAS_HEIGHT - bottom_pad - nav_content_h
    text_limit_y = footer_top - 8 * CANVAS_HEIGHT // _ORIG_H
    return text_limit_y, footer_top


def _aftermath_conservative_footer_top_px(
    small_font: pygame.font.Font,
    max_w: int,
) -> int:
    """
    餘韻頁尾操作列頂端 y（取「下一頁／返回養成」中較吃垂直空間者，供分頁保守預留）。

    Args:
        small_font: 頁尾字型。
        max_w: 換行寬。

    Returns:
        較小之 ``footer_top``（敘事可用高度較緊）。
    """
    lh_s = small_font.get_height()
    nav_gap = 2
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    tops: list[int] = []
    for nav_raw in ("【Enter】下一頁", "【Enter】返回養成"):
        nav_lines = wrap_cjk(small_font, nav_raw, max_w)
        nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
        tops.append(CANVAS_HEIGHT - bottom_pad - nav_content_h)
    return min(tops)


def _aftermath_footer_top_for_nav_raw(
    small_font: pygame.font.Font,
    max_w: int,
    nav_raw: str,
) -> int:
    """
    依實際頁尾字串計算操作列頂端 y。

    Args:
        small_font: 頁尾字型。
        max_w: 換行寬。
        nav_raw: 本頁 Enter 說明全文。

    Returns:
        ``footer_top``。
    """
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    return CANVAS_HEIGHT - bottom_pad - nav_content_h


def _aftermath_stat_lines_height_px(
    intro_font: pygame.font.Font,
    max_w: int,
    full_stat_line: str,
) -> int:
    """
    「數值變化」換行後之總高度（不含與正文／頁尾間距）。

    Args:
        intro_font: 與餘韻正文同級之字型。
        max_w: 換行寬。
        full_stat_line: 含前綴之全文。

    Returns:
        像素高度；空白則 0。
    """
    if not full_stat_line.strip():
        return 0
    lines = wrap_cjk(intro_font, full_stat_line, max_w)
    fh = intro_font.get_height() + 2
    return len(lines) * fh


def _aftermath_narrative_bottom_y_page0_with_bottom_stat(
    small_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    max_w: int,
    stat_full_line: str,
) -> int:
    """
    第一頁：正文下緣 y（不含），已預留底部「數值變化」與頁尾提示（比照培養回饋數值在下的層次）。

    Args:
        small_font: 頁尾字型。
        intro_font: 餘韻／數值列字型。
        max_w: 換行寬。
        stat_full_line: 數值變化全文。

    Returns:
        敘事最底允許之 y（與既有 ``if y + fh > text_limit_y`` 用法一致）。
    """
    footer_top = _aftermath_conservative_footer_top_px(small_font, max_w)
    if not stat_full_line.strip():
        return footer_top - 8 * CANVAS_HEIGHT // _ORIG_H
    gap_stat_above_nav = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y)
    gap_narrative_above_stat = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_STAT_LOGICAL_Y)
    sh = _aftermath_stat_lines_height_px(intro_font, max_w, stat_full_line)
    return footer_top - gap_stat_above_nav - sh - gap_narrative_above_stat


def _major_resolution_paragraph_pages(
    event: MajorEvent,
    chosen_index: int,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    *,
    stat_bottom_line: str = "",
) -> list[tuple[str, ...]]:
    """
    重大事件結語段落：**固定單頁**（與突發／遭遇餘韻一致；過長內文於畫面內截斷）。

    ``intro_font``／``small_font``／``stat_bottom_line`` 保留參數以維持呼叫端簽名一致。

    Args:
        event: 目前重大事件。
        chosen_index: 已選選項 0～2。
        intro_font: 餘韻正文／標題字型（未用於分頁）。
        small_font: 頁尾字型（未用於分頁）。
        stat_bottom_line: 底部「數值變化」全文（未用於分頁）。

    Returns:
        僅一頁之段落元組列表；無段落則空列表。
    """
    del intro_font, small_font, stat_bottom_line
    paras = event.resolution_bodies[chosen_index]
    if not paras:
        return []
    return [tuple(paras)]


def _incident_aftermath_paragraph_pages(
    event: IncidentEvent,
    chosen_index: int,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    *,
    stat_bottom_line: str = "",
) -> list[tuple[str, ...]]:
    """
    突發事件餘韻段落：**固定單頁**（與重大／遭遇餘韻一致；過長內文於畫面內截斷）。

    ``intro_font``／``small_font``／``stat_bottom_line`` 保留參數以維持呼叫端簽名一致。

    Args:
        event: 目前突發事件。
        chosen_index: 已選選項 0～2。
        intro_font: 餘韻正文／標題字型（未用於分頁）。
        small_font: 頁尾字型（未用於分頁）。
        stat_bottom_line: 底部「數值變化」全文（未用於分頁）。

    Returns:
        僅一頁之段落元組列表；無餘韻則空列表。
    """
    del intro_font, small_font, stat_bottom_line
    opt = event.options[chosen_index]
    if not opt.aftermath:
        return []
    return [tuple(opt.aftermath)]


def _fit_one_line_cjk(font: pygame.font.Font, text: str, max_width: int) -> str:
    """
    強制單行顯示：先換行再只取首行；仍超寬則截斷並加「…」。

    Args:
        font: 量測用字型。
        text: 原文。
        max_width: 單行最大像素寬。

    Returns:
        寬度不超過 `max_width` 的單行字串。
    """
    if max_width <= 0:
        return ""
    lines = wrap_cjk(font, text, max_width)
    if not lines or not lines[0]:
        return ""
    first = lines[0]
    if len(lines) == 1 and font.size(first)[0] <= max_width:
        return first
    ell = "…"
    if font.size(first + ell)[0] <= max_width:
        return first + ell
    while len(first) > 0 and font.size(first + ell)[0] > max_width:
        first = first[:-1]
    return first + ell if first else ell


def _training_menu_navigate(cursor: int, key: int) -> int:
    """
    依方向鍵在 4×2 培養選單上移動游標（上列 0～3、下列 4～7，由左而右）。

    Args:
        cursor: 目前索引 0～7。
        key: `pygame.K_UP`／`DOWN`／`LEFT`／`RIGHT`。

    Returns:
        新索引（仍於 0～7）。
    """
    c = max(0, min(len(TRAINING_ACTIONS) - 1, cursor))
    row = c // 4
    col = c % 4
    if key == pygame.K_UP:
        row = max(0, row - 1)
    elif key == pygame.K_DOWN:
        row = min(1, row + 1)
    elif key == pygame.K_LEFT:
        col = max(0, col - 1)
    elif key == pygame.K_RIGHT:
        col = min(3, col + 1)
    else:
        return c
    return row * 4 + col


def _guardian_combined_art_h() -> int:
    """監護人＋取名同頁時上方插圖區高度。"""
    ch = CANVAS_HEIGHT
    return min(
        132 * ch // 540,
        max(80 * ch // 540, int(ch * _GUARDIAN_COMBINED_ART_RATIO)),
    )


def _guardian_name_panel_height() -> int:
    """監護人畫面底部性別／取名區高度（供舊幾何後備；實際頂緣以 ``_guardian_panel_top_fixed`` 為準）。"""
    ch = CANVAS_HEIGHT
    return max(138 * ch // 540, min(208 * ch // 540, ch * 36 // 100))


def _guardian_fixed_footer_top(
    small_font: pygame.font.Font,
    pw: int,
    name_entry_step: int,
) -> int:
    """
    監護人頁底操作說明列頂端 y（固定自畫布下緣起算，與餘韻頁尾預留方式一致）。

    Args:
        small_font: 頁尾字型。
        pw: 換行寬。
        name_entry_step: 0 或 1。

    Returns:
        第一行說明文字之 y。
    """
    raw = (
        "Enter 確認（至少一字）　Esc 返回標題"
        if name_entry_step == 1
        else "Esc 返回標題"
    )
    lines = wrap_cjk(small_font, raw, pw) or [raw]
    lh = small_font.get_height() + 2
    nav_h = len(lines) * lh
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    return CANVAS_HEIGHT - bottom_pad - nav_h


def _guardian_form_content_height(
    onboarding_font: pygame.font.Font,
    pw: int,
    name_entry_step: int,
) -> int:
    """
    性別／取名區塊內容高度（不含底線與頁尾）。

    Args:
        onboarding_font: 表單主字。
        pw: 換行寬。
        name_entry_step: 0 或 1。

    Returns:
        像素高度。
    """
    oh = onboarding_font.get_height()
    gap = 3
    h = 0
    if name_entry_step == 0:
        for _ in wrap_cjk(
            onboarding_font,
            "請選擇孩子的性別（↑↓ 切換，Enter 進入取名）。",
            pw,
        ):
            h += oh + gap
        h += _scale_y(4)
        h += _event_style_choice_column_height(
            onboarding_font,
            pw,
            ("1. 男孩", "2. 女孩"),
            compact=True,
        )
    else:
        for _ in wrap_cjk(
            onboarding_font,
            "請為孩子取名字（會顯示在養成畫面與結局）。",
            pw,
        ):
            h += oh + gap
        h += _scale_y(4)
        h += oh
    return h


def _guardian_panel_top_fixed(
    small_font: pygame.font.Font,
    onboarding_font: pygame.font.Font,
    pw: int,
) -> int:
    """
    監護人頁「性別／取名」區塊頂緣 y：**固定**於畫布，不隨取名步驟改變，避免分界線跳動。

    以下半部較吃緊之頁尾（通常為取名步驟）與兩步驟中較高之表單內容預留空間，並將分界線再上移一截，讓性別／取名區更鬆。

    Args:
        small_font: 頁尾字型。
        onboarding_font: 表單主字。
        pw: 表單區換行寬。

    Returns:
        分隔線／區塊內容參考之頂 y（橫線畫在 ``panel_top - 2``）。
    """
    ft_tight = min(
        _guardian_fixed_footer_top(small_font, pw, 0),
        _guardian_fixed_footer_top(small_font, pw, 1),
    )
    max_form = max(
        _guardian_form_content_height(onboarding_font, pw, 0),
        _guardian_form_content_height(onboarding_font, pw, 1),
    )
    gap_above_footer = _scale_y(10)
    pad_below_line = _scale_y(6)
    pad_above_footer = _scale_y(8)
    form_clearance = max_form + pad_below_line + pad_above_footer
    extra_lift = _scale_y(14)
    panel_top = ft_tight - gap_above_footer - form_clearance - extra_lift
    art_h = _guardian_combined_art_h()
    # 不得與「監護人須知」標題與首段正文打架（約等於插圖下緣＋標題＋一行緩衝）
    min_panel = art_h + 78 * CANVAS_HEIGHT // _ORIG_H
    panel_top = max(min_panel, panel_top)
    # ``min_panel`` 會把分界線壓得太低時，下方高度可能小於表單實際所需（性別兩格會少畫「女孩」）。
    h0 = _guardian_form_content_height(onboarding_font, pw, 0)
    h1 = _guardian_form_content_height(onboarding_font, pw, 1)
    ft0 = _guardian_fixed_footer_top(small_font, pw, 0)
    ft1 = _guardian_fixed_footer_top(small_font, pw, 1)
    reserve_below = _scale_y(6) + _scale_y(8)
    panel_top_cap = min(ft0 - reserve_below - h0, ft1 - reserve_below - h1)
    if panel_top_cap >= min_panel and panel_top > panel_top_cap:
        panel_top = panel_top_cap
    return panel_top


def _guardian_panel_name_field_rect(
    small_font: pygame.font.Font,
    onboarding_font: pygame.font.Font,
    name_entry_step: int,
) -> pygame.Rect:
    """
    監護人同頁底部區：輸入名字列矩形（與 ``draw_guardian_intro_screen`` 幾何一致）。

    Args:
        small_font: 與繪製頁尾相同之字型。
        onboarding_font: 與繪製取名列相同之字型。
        name_entry_step: 0 或 1。

    Returns:
        邏輯座標矩形；步驟 0 時回傳寬高占位（不啟用 IME）。
    """
    px = _scale_x(24)
    pw = CANVAS_WIDTH - 2 * px
    panel_top = _guardian_panel_top_fixed(small_font, onboarding_font, pw)
    y = panel_top + _scale_y(6)
    if name_entry_step != 1:
        ft = _guardian_fixed_footer_top(small_font, pw, 0)
        return pygame.Rect(px, panel_top, pw, max(1, ft - panel_top - _scale_y(4)))
    for L in wrap_cjk(
        onboarding_font,
        "請為孩子取名字（會顯示在養成畫面與結局）。",
        pw,
    ):
        y += onboarding_font.get_height() + 3
    y += _scale_y(4)
    return pygame.Rect(px, y, pw, onboarding_font.get_height() + _scale_y(6))


def _set_text_input_rect_for_screen(screen: pygame.Surface, logic_rect: pygame.Rect) -> None:
    """
    依視窗縮放與黑邊，把邏輯矩形換算成視窗座標並呼叫 `set_text_input_rect`。

    Args:
        screen: 實際視窗 Surface。
        logic_rect: 960×540 邏輯座標上的矩形。
    """
    sw, sh = screen.get_size()
    sx = sw / CANVAS_WIDTH
    sy = sh / CANVAS_HEIGHT
    scale = min(sx, sy)
    nw = CANVAS_WIDTH * scale
    nh = CANVAS_HEIGHT * scale
    ox = (sw - nw) / 2.0
    oy = (sh - nh) / 2.0
    sr = pygame.Rect(
        int(ox + logic_rect.x * scale),
        int(oy + logic_rect.y * scale),
        max(1, int(logic_rect.w * scale)),
        max(1, int(logic_rect.h * scale)),
    )
    try:
        pygame.key.set_text_input_rect(sr)
    except (AttributeError, pygame.error):
        pass


def draw_title_screen(
    canvas: pygame.Surface,
    main_font: pygame.font.Font,
    sub_font: pygame.font.Font,
    menu_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    menu_index: int,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製標題與選單。

    主／副標維持大字；選單與底部說明使用較小字型。底部說明由下往上對齊，選單不與說明重疊。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    tw = CANVAS_WIDTH - _scale_x(24)
    ty = _scale_y(14)
    for tl in wrap_cjk(main_font, GAME_TITLE, tw):
        tsurf = main_font.render(tl, True, (255, 240, 220))
        canvas.blit(tsurf, ((CANVAS_WIDTH - tsurf.get_width()) // 2, ty))
        ty += main_font.get_height() + 4

    sub_y = ty + _scale_y(4)
    for sl in wrap_cjk(sub_font, "養成 × 奇幻 × 告別", tw):
        ssurf = sub_font.render(sl, True, (180, 190, 210))
        canvas.blit(ssurf, ((CANVAS_WIDTH - ssurf.get_width()) // 2, sub_y))
        sub_y += sub_font.get_height() + 2

    hint_raw = "↑↓ 選擇　Enter 確定　Esc：結束遊戲／標題離開"
    hint_lines = wrap_cjk(hint_font, hint_raw, CANVAS_WIDTH - _scale_x(20))
    if not hint_lines:
        hint_lines = [hint_raw]
    lh_hint = hint_font.get_height()
    hint_line_gap = 2
    # 說明列盡量靠近畫布底，把垂直空間留給選單（避免「結束遊戲」被裁切）
    bottom_margin = 6 * CANVAS_HEIGHT // _ORIG_H
    hint_block_h = len(hint_lines) * lh_hint + max(0, len(hint_lines) - 1) * hint_line_gap
    hint_y = CANVAS_HEIGHT - bottom_margin - hint_block_h
    menu_bottom_max = hint_y - 4 * CANVAS_HEIGHT // _ORIG_H

    lh_menu = menu_font.get_height()
    my = sub_y + _TITLE_SUB_TO_MENU_GAP
    mx = CANVAS_WIDTH // 2
    pw = _menu_prefix_column_width(menu_font)
    for idx, label in enumerate(TITLE_MENU_ITEMS):
        col = (255, 230, 160) if idx == menu_index else (190, 200, 220)
        prefix = "▶ " if idx == menu_index else "  "
        label_lines = wrap_cjk(menu_font, label, max(8, tw - pw)) or [label]
        if my + lh_menu > menu_bottom_max:
            break
        text_w = max(menu_font.size(L)[0] for L in label_lines)
        block_w = pw + text_w
        left_x = mx - block_w // 2
        canvas.blit(menu_font.render(prefix, True, col), (left_x, my))
        for L in label_lines:
            if my + lh_menu > menu_bottom_max:
                break
            canvas.blit(menu_font.render(L, True, col), (left_x + pw, my))
            my += lh_menu + 1
        my += _TITLE_MENU_ITEM_GAP_Y

    hy = hint_y
    for i, hl in enumerate(hint_lines):
        hs = hint_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy))
        hy += lh_hint + (hint_line_gap if i + 1 < len(hint_lines) else 0)

    credit_surf = hint_font.render(TITLE_SCREEN_CREDIT_ZH, True, (130, 138, 155))
    cred_mx = _scale_x(12)
    cred_my = _scale_y(8)
    canvas.blit(
        credit_surf,
        (
            CANVAS_WIDTH - cred_mx - credit_surf.get_width(),
            CANVAS_HEIGHT - cred_my - credit_surf.get_height(),
        ),
    )


def draw_gallery_hub_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    hub_index: int,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製「圖片畫廊」主選單：通關圖片+結局（男／女）、同行的夥伴(奇遇)、遭遇的強敵(遭遇戰)、獎勵圖片。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題與選項字級。
        hint_font: 頁尾操作說明。
        hub_index: 目前選中項索引（0～``len(_GALLERY_HUB_MENU_ITEMS)-1``）。
        star_xy: 與標題畫面相同之星空座標。
        tick: 影格（星空閃爍）。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    # 與「遊戲設定」畫面相同：左緣邊距與選項靠左對齊
    mx = _scale_x(20)
    tw = CANVAS_WIDTH - 2 * mx
    y = _scale_y(14)
    hdr = "圖片畫廊"
    for line in wrap_cjk(menu_font, hdr, tw):
        canvas.blit(menu_font.render(line, True, (255, 200, 160)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(10)

    lh_menu = menu_font.get_height()
    menu_gap = _scale_y(5)
    hint_raw = "↑↓ 選擇　Enter 確定　Esc 返回標題"
    hint_lines = wrap_cjk(hint_font, hint_raw, tw)
    if not hint_lines:
        hint_lines = [hint_raw]
    lh_hint = hint_font.get_height()
    hint_gap = 2
    hint_h = len(hint_lines) * lh_hint + max(0, len(hint_lines) - 1) * hint_gap
    bottom_pad = _scale_y(8)
    menu_bottom = CANVAS_HEIGHT - bottom_pad - hint_h - _scale_y(6)
    pw = _menu_prefix_column_width(menu_font)

    for idx, label in enumerate(_GALLERY_HUB_MENU_ITEMS):
        locked = idx in _GALLERY_HUB_LOCKED_INDICES
        if locked:
            col = (155, 162, 178) if idx == hub_index else (105, 112, 128)
        else:
            col = (255, 230, 160) if idx == hub_index else (190, 200, 220)
        prefix = "▶ " if idx == hub_index else "  "
        lab = f"{label}　（尚未開放）" if locked else label
        lines = wrap_cjk(menu_font, lab, max(8, tw - pw)) or [lab]
        if y + lh_menu > menu_bottom:
            break
        canvas.blit(menu_font.render(prefix, True, col), (mx, y))
        for L in lines:
            if y + lh_menu > menu_bottom:
                break
            canvas.blit(menu_font.render(L, True, col), (mx + pw, y))
            y += lh_menu + 1
        y += menu_gap

    hy = CANVAS_HEIGHT - bottom_pad - hint_h
    for i, hl in enumerate(hint_lines):
        hs = hint_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, (mx, hy))
        hy += lh_hint + (hint_gap if i + 1 < len(hint_lines) else 0)


def _cheat_menu_key_to_direction(key: int) -> str | None:
    """
    將鍵盤事件對應為密技方向字串。

    Args:
        key: ``pygame`` 鍵碼。

    Returns:
        ``up``／``down``／``left``／``right``，或無法對應時為 None。
    """
    if key in (pygame.K_UP, pygame.K_w):
        return "up"
    if key in (pygame.K_DOWN, pygame.K_s):
        return "down"
    if key in (pygame.K_LEFT, pygame.K_a):
        return "left"
    if key in (pygame.K_RIGHT, pygame.K_d):
        return "right"
    return None


def _cheat_menu_navigate_grid(
    menu_index: int,
    vis: tuple[int, ...],
    key: int,
) -> int | None:
    """
    作弊隱藏項已開啟時：以雙欄網格移動游標（左欄 0～4、右欄 5～7 列對齊；左 3～4 對應右 7）。

    Args:
        menu_index: 目前游標（``vis`` 索引）。
        vis: 可見項之 ``CHEAT_MENU_ITEMS`` 索引元組（解鎖後恆為 0～7）。
        key: 鍵盤事件鍵碼。

    Returns:
        新游標索引；該鍵不負責導覽時為 None。
    """
    if not vis:
        return None
    item_i = vis[menu_index]
    if item_i <= 4:
        col, row = 0, item_i
    else:
        col, row = 1, item_i - 5

    def _idx_for_item(target: int) -> int | None:
        try:
            return vis.index(target)
        except ValueError:
            return None

    if key in (pygame.K_UP, pygame.K_w):
        if col == 0:
            new_item = (row - 1) % 5
        else:
            new_item = 5 + (row - 1) % 3
        return _idx_for_item(new_item)
    if key in (pygame.K_DOWN, pygame.K_s):
        if col == 0:
            new_item = (row + 1) % 5
        else:
            new_item = 5 + (row + 1) % 3
        return _idx_for_item(new_item)
    if key in (pygame.K_LEFT, pygame.K_a):
        if col == 1:
            return _idx_for_item(row)
        return None
    if key in (pygame.K_RIGHT, pygame.K_d):
        if col == 0:
            if row <= 2:
                return _idx_for_item(5 + row)
            return _idx_for_item(7)
        return None
    return None


def _cheat_menu_row_label(
    item_i: int,
    cheat_gallery_all_on: bool,
    cheat_bootstrap_on: bool,
    cheat_bgm_on: bool,
) -> str:
    """
    作弊選單單列顯示文字（部分選項附帶（開）／（關））。

    Args:
        item_i: ``CHEAT_MENU_ITEMS`` 索引。
        cheat_gallery_all_on: 畫廊全解鎖作弊是否開啟。
        cheat_bootstrap_on: 作弊開局是否開啟。
        cheat_bgm_on: 背景音樂是否播放（非靜音）。

    Returns:
        該列完整標籤。
    """
    base = CHEAT_MENU_ITEMS[item_i]
    if item_i == 2:
        return f"{base}（{'開' if cheat_bgm_on else '關'}）"
    if item_i == 5:
        return f"{base}（{'開' if cheat_bootstrap_on else '關'}）"
    if item_i == 6:
        return f"{base}（{'開' if cheat_gallery_all_on else '關'}）"
    # 夥伴／強敵畫廊一鍵解鎖：目前視為關閉態（與可切換項同樣標示，避免誤以為已常駐開啟）。
    if item_i == 7:
        return f"{base}（關）"
    return base


def _cheat_menu_visible_item_indices(extras_unlocked: bool) -> tuple[int, ...]:
    """
    作弊選單目前可見的選項索引（對應 ``CHEAT_MENU_ITEMS``）。

    Args:
        extras_unlocked: 是否已輸入密技顯示隱藏項。

    Returns:
        可見項之 ``CHEAT_MENU_ITEMS`` 索引元組。
    """
    return (0, 1, 2, 3, 4, 5, 6, 7) if extras_unlocked else (0, 1, 2, 3, 4)


def draw_cheat_menu_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    menu_index: int,
    extras_unlocked: bool,
    cheat_gallery_all_on: bool,
    cheat_bootstrap_on: bool,
    cheat_bgm_on: bool,
    cheat_menu_modal: str | None,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    標題選單下的遊戲設定：一般選項與測試用捷徑。

    版面：前四項於左欄；密技解鎖後三項作弊選項於右欄（與左欄前三列頂端對齊），
    右欄**靠左**；第一列自 ``right_x`` 起；第二、三列與第一列「標籤」首字對齊（前綴欄寬取
    ``▶``／空白 較寬者）。解鎖作弊時於左右欄之間繪垂直分隔線（與右欄同顯隱）。單行過寬則截斷加「…」。
    隱藏項解鎖後，游標以 **↑↓←→**（及 **WASD**）雙欄網格移動，不再僅限上下鍵。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題與選項字。
        small_font: 說明字。
        menu_index: 目前游標（僅在可見選項列中 0 起算）。
        extras_unlocked: 是否已顯示隱藏作弊項。
        cheat_gallery_all_on: 畫廊全解鎖作弊是否開啟。
        cheat_bootstrap_on: 作弊開局是否開啟。
        cheat_bgm_on: 背景音樂是否開啟（非靜音）。
        cheat_menu_modal: 確認開啟作弊時的非 None 鍵（見 ``_CHEAT_MODAL_MESSAGES``）。
        star_xy: 星空座標（與標題畫面共用）。
        tick: 影格。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(20)
    tw = CANVAS_WIDTH - 2 * mx
    y = _scale_y(14)
    for hl in wrap_cjk(menu_font, "遊戲設定", tw):
        canvas.blit(menu_font.render(hl, True, (255, 200, 160)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(10)

    lh = menu_font.get_height()
    gap = _scale_y(5)
    lh_s = small_font.get_height()
    hint_gap = 2
    hint_raw = (
        "↑↓←→ 選擇（左右切換欄）　Enter 確認／開關　Esc 返回標題"
        if extras_unlocked
        else "↑↓ 選擇　Enter 確認／開關　Esc 返回標題"
    )
    hint_lines = wrap_cjk(small_font, hint_raw, tw)
    if not hint_lines:
        hint_lines = [hint_raw]
    hint_h = len(hint_lines) * lh_s + max(0, len(hint_lines) - 1) * hint_gap
    bottom_pad = _scale_y(8)
    footer_block_h = hint_h
    menu_bottom = CANVAS_HEIGHT - bottom_pad - footer_block_h - _scale_y(6)

    menu_start_y = y
    # 左欄／右欄分界；作弊三列靠左，前綴欄寬固定使「標籤」首字縱向對齊。
    col_gap = _scale_x(8)
    avail = tw - col_gap
    left_col_w = avail * 40 // 100
    right_x = mx + left_col_w + col_gap
    right_edge = CANVAS_WIDTH - mx
    cheat_max_w = max(1, right_edge - right_x)
    pw_sel = menu_font.size("▶ ")[0]
    pw_unsel = menu_font.size("  ")[0]
    cheat_prefix_col_w = max(pw_sel, pw_unsel)

    def _cheat_row_blit_x(disp_i: int) -> int:
        """右欄列：前綴欄寬固定，使標籤首字縱向對齊。"""
        prefix = "▶ " if disp_i == menu_index else "  "
        pw = menu_font.size(prefix)[0]
        return right_x + cheat_prefix_col_w - pw

    if extras_unlocked:
        div_x = mx + left_col_w + col_gap // 2
        pygame.draw.line(
            canvas,
            (58, 66, 84),
            (div_x, menu_start_y),
            (div_x, menu_bottom),
            1,
        )

    vis = _cheat_menu_visible_item_indices(extras_unlocked)
    for disp_i, item_i in enumerate(vis):
        label = _cheat_menu_row_label(
            item_i, cheat_gallery_all_on, cheat_bootstrap_on, cheat_bgm_on
        )
        col = (255, 230, 160) if disp_i == menu_index else (190, 200, 220)
        prefix = "▶ " if disp_i == menu_index else "  "
        full = prefix + label
        if item_i <= 4:
            row = item_i
            cx = mx
            max_w = left_col_w
        else:
            row = item_i - 5
            max_w = cheat_max_w
        row_y = menu_start_y + row * (lh + gap)
        if row_y + lh > menu_bottom:
            break
        # 左欄：前綴欄寬固定，標籤緊接其右，避免「▶／空白」寬差造成文字橫移。
        if item_i <= 4:
            lab = _fit_one_line_cjk(menu_font, label, max(1, max_w - cheat_prefix_col_w))
            canvas.blit(menu_font.render(prefix, True, col), (cx, row_y))
            canvas.blit(
                menu_font.render(lab, True, col),
                (cx + cheat_prefix_col_w, row_y),
            )
        else:
            line = _fit_one_line_cjk(menu_font, full, max_w)
            surf = menu_font.render(line, True, col)
            blit_x = _cheat_row_blit_x(disp_i)
            canvas.blit(surf, (blit_x, row_y))

    hy_main = CANVAS_HEIGHT - bottom_pad - hint_h
    for i, fl in enumerate(hint_lines):
        canvas.blit(
            small_font.render(fl, True, (130, 138, 155)),
            (mx, hy_main),
        )
        hy_main += lh_s + (hint_gap if i + 1 < len(hint_lines) else 0)

    if cheat_menu_modal and cheat_menu_modal in _CHEAT_MODAL_MESSAGES:
        ov = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
        ov.fill((12, 14, 22, 235))
        canvas.blit(ov, (0, 0))
        msg = _CHEAT_MODAL_MESSAGES[cheat_menu_modal]
        modal_lines: list[str] = []
        for block in msg.split("\n\n"):
            b = block.strip()
            if not b:
                continue
            modal_lines.extend(wrap_cjk(small_font, b, tw) or [b])
            modal_lines.append("")
        if modal_lines and modal_lines[-1] == "":
            modal_lines.pop()
        lh_m = small_font.get_height() + 3
        total_h = len(modal_lines) * lh_m
        sy = max(_scale_y(24), (CANVAS_HEIGHT - total_h) // 2)
        for ln in modal_lines:
            if ln == "":
                sy += lh_m // 2
                continue
            surf = small_font.render(ln, True, (238, 240, 252))
            canvas.blit(surf, ((CANVAS_WIDTH - surf.get_width()) // 2, sy))
            sy += lh_m


# 解鎖條件說明：女性／男性路線分開進入；路線內一人獨佔一頁（順序同 ``GALLERY_FEMALE_ENDING_KEYS``／``GALLERY_MALE_ENDING_KEYS``）。
_CHEAT_GALLERY_HINT_PAGE_KEYS_FEMALE: tuple[tuple[str, ...], ...] = tuple(
    (ek,) for ek in GALLERY_FEMALE_ENDING_KEYS
)
_CHEAT_GALLERY_HINT_PAGE_KEYS_MALE: tuple[tuple[str, ...], ...] = tuple(
    (ek,) for ek in GALLERY_MALE_ENDING_KEYS
)
_CHEAT_HINT_GENDER_FEMALE = "female"
_CHEAT_HINT_GENDER_MALE = "male"


def _cheat_gallery_hint_page_tuples(gender: str) -> tuple[tuple[str, ...], ...]:
    """
    依性別回傳解鎖條件畫面之分頁鍵組。

    Args:
        gender: ``_CHEAT_HINT_GENDER_FEMALE`` 或 ``_CHEAT_HINT_GENDER_MALE``。

    Returns:
        每頁恰含一個結局 key 的元組序列（與畫廊鍵序一致）。
    """
    if gender == _CHEAT_HINT_GENDER_FEMALE:
        return _CHEAT_GALLERY_HINT_PAGE_KEYS_FEMALE
    if gender == _CHEAT_HINT_GENDER_MALE:
        return _CHEAT_GALLERY_HINT_PAGE_KEYS_MALE
    raise ValueError(f"unknown cheat hint gender: {gender!r}")


def _cheat_gallery_hint_num_pages(gender: str) -> int:
    """
    解鎖條件畫面在指定性別路線下的總頁數。

    Args:
        gender: 女性或男性路線鍵。

    Returns:
        頁數（≥1）。
    """
    return len(_cheat_gallery_hint_page_tuples(gender))


_CHEAT_GALLERY_HINT_FOOT_PICK = (
    "↑／↓ 選擇　Enter 確認　Esc 返回遊戲設定"
)
_CHEAT_GALLERY_HINT_FOOT_PAGES = (
    "←／→ 切換頁面　Esc 返回路線選擇"
)
_CHEAT_HINT_BULLET_PREFIX = "・ "


def _cheat_gallery_hint_layout(
    gender: str,
    page_index: int,
    head_font: pygame.font.Font,
    body_font: pygame.font.Font,
) -> tuple[list[tuple[bool, str]], int, int, int, int, int, int, str]:
    """
    結局 CG 解鎖條件畫面：依性別路線分頁，每人獨立一頁；條列換行、不捲動。

    Args:
        gender: ``_CHEAT_HINT_GENDER_FEMALE`` 或 ``_CHEAT_HINT_GENDER_MALE``。
        page_index: 頁碼 0～該路線頁數−1。
        head_font: 小節標題字。
        body_font: 說明內文字。

    Returns:
        (rows, line_h, content_top_y, visible_lines, max_scroll_line, mx, tw, title_line)。
        ``max_scroll_line`` 恆為 0（保留簽名以利呼叫端相容）。
    """
    mx = _scale_x(14)
    tw = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    pages = _cheat_gallery_hint_page_tuples(gender)
    num_pages = len(pages)
    pi = max(0, min(page_index, num_pages - 1))
    keys = pages[pi]
    rows: list[tuple[bool, str]] = []
    for ek in keys:
        meta = ENDINGS[ek]
        items = ENDING_CG_UNLOCK_HINT_ITEMS_BY_KEY[ek]
        for L in wrap_cjk(head_font, meta.name, tw):
            rows.append((True, L))
        for it in items:
            block = f"{_CHEAT_HINT_BULLET_PREFIX}{it}"
            lines = wrap_cjk(body_font, block, tw) or [block]
            for li, L in enumerate(lines):
                if li > 0 and L:
                    L = f"　　{L.lstrip()}"
                rows.append((False, L))
        rows.append((False, ""))
    line_h = max(head_font.get_height(), body_font.get_height()) + 3
    y0 = _scale_y(10)
    route_zh = "女性路線" if gender == _CHEAT_HINT_GENDER_FEMALE else "男性路線"
    title_line = f"各人物結局 CG 解鎖條件　{route_zh}　（{pi + 1}／{num_pages}）"
    h_banner = 0
    for _ in wrap_cjk(head_font, title_line, tw):
        h_banner += head_font.get_height() + 2
    content_top = y0 + h_banner + _scale_y(6)
    visible = max(1, len(rows))
    max_scroll = 0
    return rows, line_h, content_top, visible, max_scroll, mx, tw, title_line


def draw_cheat_ending_hints_screen(
    canvas: pygame.Surface,
    head_font: pygame.font.Font,
    body_font: pygame.font.Font,
    star_xy: list[tuple[int, int]],
    tick: int,
    page_index: int,
    hint_gender: str | None,
    gender_menu_index: int,
) -> None:
    """
    遊戲設定：各人物結局 CG 解鎖條件；先選男性／女性路線，再左右換頁（每人一頁、不捲動）。

    Args:
        canvas: 邏輯畫布。
        head_font: 標題／小節標題。
        body_font: 內文。
        star_xy: 星空座標。
        tick: 影格。
        page_index: 條件列表頁碼（0 起算；僅在已選路線時有效）。
        hint_gender: 已選路線（``female``／``male``）；``None`` 時顯示路線選擇。
        gender_menu_index: 路線選擇游標（0 男性、1 女性）。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(14)
    tw = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    footer_pad = 8 * CANVAS_HEIGHT // _ORIG_H

    if hint_gender is None:
        # 與「遊戲設定」「圖片畫廊」主選單相同：左緣 _scale_x(20)、標題後 _scale_y(10)、選項間 _scale_y(5)。
        pick_mx = _scale_x(20)
        pick_tw = CANVAS_WIDTH - 2 * pick_mx
        title = "各人物結局 CG 解鎖條件"
        y = _scale_y(14)
        for L in wrap_cjk(head_font, title, pick_tw):
            canvas.blit(head_font.render(L, True, (255, 200, 160)), (pick_mx, y))
            y += head_font.get_height() + 2
        y += _scale_y(10)
        lh = head_font.get_height()
        gap = _scale_y(5)
        opts = ("男性主角路線", "女性主角路線")
        pw_pick = _menu_prefix_column_width(head_font)
        for idx, label in enumerate(opts):
            sel = idx == gender_menu_index
            col = (255, 230, 160) if sel else (190, 200, 220)
            prefix = "▶ " if sel else "  "
            lines = wrap_cjk(head_font, label, max(8, pick_tw - pw_pick)) or [label]
            canvas.blit(head_font.render(prefix, True, col), (pick_mx, y))
            for L in lines:
                canvas.blit(head_font.render(L, True, col), (pick_mx + pw_pick, y))
                y += lh + 1
            y += gap
        mx, tw = pick_mx, pick_tw
        foot = _CHEAT_GALLERY_HINT_FOOT_PICK
    else:
        rows, line_h, content_top, visible, _max_sl, mx2, tw2, title_line = (
            _cheat_gallery_hint_layout(hint_gender, page_index, head_font, body_font)
        )
        mx, tw = mx2, tw2
        sl = 0
        y = _scale_y(10)
        for L in wrap_cjk(head_font, title_line, tw):
            canvas.blit(head_font.render(L, True, (255, 210, 170)), (mx, y))
            y += head_font.get_height() + 2

        yy = content_top
        end_i = min(len(rows), sl + visible)
        for i in range(sl, end_i):
            is_head, text = rows[i]
            col = (255, 220, 175) if is_head else (210, 215, 228)
            if text:
                canvas.blit(
                    (head_font if is_head else body_font).render(text, True, col),
                    (mx, yy),
                )
            yy += line_h
        foot = _CHEAT_GALLERY_HINT_FOOT_PAGES

    hint_lines = wrap_cjk(body_font, foot, tw) or [foot]
    hy = CANVAS_HEIGHT - footer_pad - len(hint_lines) * body_font.get_height()
    for i, hl in enumerate(hint_lines):
        canvas.blit(body_font.render(hl, True, (130, 138, 155)), (mx, hy))
        hy += body_font.get_height() + (2 if i + 1 < len(hint_lines) else 0)


def _make_cheat_bootstrap_state() -> GameState:
    """
    建立略過開場流程、屬性偏高的測試用養成狀態。

    Returns:
        已 `refresh_life_phase` 的 `GameState`。
    """
    s = GameState()
    s.intro_done = True
    s.guardian_intro_done = True
    s.onboarding_complete = True
    s.heroine_name = "測試"
    s.apply_deltas(
        {
            "int_stat": 55,
            "str_stat": 55,
            "fth_stat": 55,
            "pragmatic": 55,
            "social": 55,
            "truth_seek": 12,
            "romantic": 0,
            "solitude": 0,
        }
    )
    s.corruption = 0
    s.time_left = 50
    s.refresh_life_phase()
    return s


# 畫廊 3×2 格點：0～2 上排、3～5 下排；末頁不足 6 格時以 n_slots 截斷移動。
_GALLERY_NAV_SIX: dict[int, dict[str, int | None]] = {
    0: {"up": None, "down": 3, "left": None, "right": 1},
    1: {"up": None, "down": 4, "left": 0, "right": 2},
    2: {"up": None, "down": 5, "left": 1, "right": None},
    3: {"up": 0, "down": None, "left": None, "right": 4},
    4: {"up": 1, "down": None, "left": 3, "right": 5},
    5: {"up": 2, "down": None, "left": 4, "right": None},
}


def _gallery_page_count(gallery_items: tuple[object, ...]) -> int:
    """
    依目前子分類之項目數量，回傳畫廊總頁數（每頁六格；至少一頁）。

    Args:
        gallery_items: 該分類之結局 key 序，或獎勵 slot 序（每元素可為字串或 tuple）。

    Returns:
        總頁數（≥1）。
    """
    return max(
        1,
        (len(gallery_items) + _GALLERY_SLOTS_PER_PAGE - 1) // _GALLERY_SLOTS_PER_PAGE,
    )


def _gallery_keys_on_page(page_index: int, gallery_items: tuple[object, ...]) -> list[object]:
    """
    回傳畫廊某一頁的項目列表（至多六格）。

    Args:
        page_index: 頁碼 0 起。
        gallery_items: 目前子分類之鍵序或獎勵 slot 序。

    Returns:
        該頁項目列表（末頁可能不足六格）。
    """
    pc = _gallery_page_count(gallery_items)
    pi = max(0, min(page_index, pc - 1))
    i0 = pi * _GALLERY_SLOTS_PER_PAGE
    return list(gallery_items[i0 : i0 + _GALLERY_SLOTS_PER_PAGE])


def _gallery_neighbor_slot(slot_index: int, direction: str, n_slots: int) -> int | None:
    """
    畫廊游標在方向鍵下的下一格索引（無則 None）。版面為上排三格、下排三格（3×2）。

    Args:
        slot_index: 該頁內格索引 0～5。
        direction: "up"／"down"／"left"／"right"。
        n_slots: 該頁實際格數（末頁可能不足六格）。

    Returns:
        目標格索引，或無法移動時為 None。
    """
    if n_slots <= 0:
        return None
    row = _GALLERY_NAV_SIX.get(slot_index)
    if row is None:
        return None
    nxt = row.get(direction)
    if not isinstance(nxt, int) or nxt < 0 or nxt >= n_slots:
        return None
    return nxt


def _gallery_cell_unlocked_with_file(
    ek: str, gallery_unlocked: set[str]
) -> tuple[bool, Ending | None]:
    """
    該格是否已通關且 CG 路徑上檔案存在（實際縮圖載入仍可能在繪製時失敗）。

    Returns:
        (是否符合條件, 結局資料或 None)。
    """
    meta = ENDINGS.get(ek)
    if meta is None:
        return False, None
    unlocked = ek in gallery_unlocked
    path_ok = _resolve_ending_cg_disk_path(meta.cg_path) is not None
    if unlocked and path_ok:
        return True, meta
    return False, meta


def _gallery_can_open_fullscreen(ek: str, gallery_unlocked: set[str]) -> bool:
    """
    是否允許以全畫面開啟該結局 CG（已通關且可成功載入縮放圖）。

    Args:
        ek: 結局 key。
        gallery_unlocked: 已解鎖集合。

    Returns:
        可開啟則 True。
    """
    ok, meta = _gallery_cell_unlocked_with_file(ek, gallery_unlocked)
    if not ok or meta is None:
        return False
    tw = max(64, CANVAS_WIDTH - _scale_x(32))
    th = max(64, CANVAS_HEIGHT - _scale_y(80))
    return _get_scaled_ending_cg(meta.cg_path, tw, th) is not None


def _reward_can_open_fullscreen(rel_path: str) -> bool:
    """
    獎勵組合圖是否可全畫面載入（路徑存在且縮圖成功）。

    Args:
        rel_path: CG 相對路徑（``assets/cg/rewards/...``）。

    Returns:
        可開啟則 True。
    """
    tw = max(64, CANVAS_WIDTH - _scale_x(32))
    th = max(64, CANVAS_HEIGHT - _scale_y(80))
    return _get_scaled_ending_cg(rel_path, tw, th) is not None


def draw_reward_gallery_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    gallery_page_index: int,
    gallery_slot_index: int,
    reward_slots: tuple[
        tuple[str, str, tuple[str, ...], str | None, bool],
        ...,
    ],
    section_header: str,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製「獎勵圖片」子頁：每頁最多六格組合縮圖；無任何可顯示項目時顯示說明文字。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題列。
        small_font: 格內標籤與頁尾。
        gallery_page_index: 頁碼 0 起。
        gallery_slot_index: 該頁格游標。
        reward_slots: 每項為
            ``(規範 token, CG 相對路徑, 檔名由左而右 key 序, 館藏註解或 None, cg_revealed)``；
            ``cg_revealed`` 為 False 時僅畫外框與角色名、不顯示縮圖；註解僅全螢幕使用。
        section_header: 標題列前綴（如「獎勵圖片」）。
        star_xy: 星空座標。
        tick: 影格。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(16)
    lh_label = small_font.get_height()
    gallery_hint_raw = (
        "方向鍵 選擇　換頁　有縮圖之格可 Enter 全螢幕　Esc 返回圖片畫廊"
    )
    gallery_hint_lines = wrap_cjk(
        small_font, gallery_hint_raw, CANVAS_WIDTH - 2 * mx
    )
    if not gallery_hint_lines:
        gallery_hint_lines = [gallery_hint_raw]
    gallery_hint_line_gap = 2
    gallery_hint_block_h = len(gallery_hint_lines) * lh_label + max(
        0, len(gallery_hint_lines) - 1
    ) * gallery_hint_line_gap
    grid_bottom = CANVAS_HEIGHT - _scale_y(8) - gallery_hint_block_h

    pc = _gallery_page_count(reward_slots)
    pi = max(0, min(gallery_page_index, pc - 1))
    hdr = f"{section_header}　（{pi + 1}／{pc}）"
    y = _scale_y(8)
    for line in wrap_cjk(menu_font, hdr, CANVAS_WIDTH - 2 * mx):
        canvas.blit(menu_font.render(line, True, (255, 230, 190)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(3)

    if not reward_slots:
        empty_raw = (
            "專案中尚未於 assets/cg/rewards/ 放置任何獎勵圖檔。"
            "檔名為結局 key（一至四個，單人時例如 frieren；多人則以底線連接），副檔名 jpg／png／webp 等皆可；"
            "同一組多張可在檔名最後加 _1、_2 區分。"
            "全螢幕註解請在原始碼 ``gallery_rewards._REWARD_CAPTION_BY_REL_PATH`` 依圖檔路徑增列。"
        )
        ey = y + _scale_y(24)
        for el in wrap_cjk(small_font, empty_raw, CANVAS_WIDTH - 2 * mx):
            canvas.blit(small_font.render(el, True, (160, 168, 188)), (mx, ey))
            ey += lh_label + 2
        hy = CANVAS_HEIGHT - _scale_y(8) - gallery_hint_block_h
        for i, hl in enumerate(gallery_hint_lines):
            hs = small_font.render(hl, True, (130, 138, 155))
            canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy))
            hy += lh_label + (
                gallery_hint_line_gap if i + 1 < len(gallery_hint_lines) else 0
            )
        return

    keys_page = _gallery_keys_on_page(pi, reward_slots)
    n_cols_ref = 3
    n_rows_ref = 2
    gap_x = _scale_x(6)
    gap_y = _scale_y(4)
    name_gap = _scale_y(2)
    label_line_gap = 1
    label_lines_max = 2
    label_block_h = (
        lh_label * label_lines_max
        + max(0, label_lines_max - 1) * label_line_gap
    )
    avail_h = max(_scale_y(72), grid_bottom - y)
    row_inner_h = (avail_h - (n_rows_ref - 1) * gap_y) // n_rows_ref
    box_h = max(1, row_inner_h - name_gap - label_block_h)
    cell_w = (CANVAS_WIDTH - 2 * mx - (n_cols_ref - 1) * gap_x) // n_cols_ref
    grid_total_w = n_cols_ref * cell_w + (n_cols_ref - 1) * gap_x
    x0 = (CANVAS_WIDTH - grid_total_w) // 2
    row_stride_y = row_inner_h + gap_y

    slot_image_rects: list[
        tuple[tuple[str, str, tuple[str, ...], str | None, bool], pygame.Rect]
    ] = []

    def _draw_one_cell(
        slot: tuple[str, str, tuple[str, ...], str | None, bool], cx: int, cy: int
    ) -> None:
        tok, rel, key_ord, _note_zh, cg_revealed = slot
        box_rect = pygame.Rect(cx, cy, cell_w, box_h)
        slot_image_rects.append((slot, box_rect))
        border_w = max(1, _scale_x(2))
        path_ok = _resolve_ending_cg_disk_path(rel) is not None
        pygame.draw.rect(canvas, (28, 32, 44), box_rect)
        show_cg = cg_revealed and path_ok
        drew_thumb = False
        if show_cg:
            cg_fill = _get_scaled_ending_cg_fill(
                rel, max(1, box_rect.w), max(1, box_rect.h)
            )
            if cg_fill is not None:
                canvas.blit(cg_fill, box_rect.topleft)
                drew_thumb = True
        if not drew_thumb:
            draw_gallery_cell_locked_cross(canvas, box_rect)

        # 與通關圖片畫廊一致：內框固定色，選取由頁尾白框疊加（見下方）。
        pygame.draw.rect(canvas, (90, 100, 120), box_rect, width=border_w)

        name_w = max(1, cell_w - _scale_x(2))
        title_zh = reward_token_label_zh(
            tok,
            filename_key_order=key_ord,
        )
        label_rgb = (200, 205, 220) if cg_revealed else (150, 158, 175)
        if path_ok:
            name_lines = wrap_cjk(small_font, title_zh, name_w)[:label_lines_max]
        else:
            name_lines = wrap_cjk(
                small_font, _GALLERY_UNKNOWN_NAME, name_w
            )[:label_lines_max]
        ny_line = box_rect.bottom + name_gap
        for nl in name_lines:
            ns = small_font.render(nl, True, label_rgb)
            nx = cx + (cell_w - ns.get_width()) // 2
            canvas.blit(ns, (nx, ny_line))
            ny_line += lh_label + label_line_gap

    y_top = y
    for idx, slot_item in enumerate(keys_page):
        row = idx // n_cols_ref
        col = idx % n_cols_ref
        cx = x0 + col * (cell_w + gap_x)
        cy = y_top + row * row_stride_y
        _draw_one_cell(slot_item, cx, cy)

    n_slots = len(keys_page)
    sel = max(0, min(gallery_slot_index, n_slots - 1))
    if 0 <= sel < len(slot_image_rects):
        _, sel_box = slot_image_rects[sel]
        ow = max(2, _scale_x(3))
        pygame.draw.rect(
            canvas,
            (255, 255, 255),
            sel_box.inflate(_scale_x(3), _scale_y(3)),
            width=ow,
        )

    hy = CANVAS_HEIGHT - _scale_y(8) - gallery_hint_block_h
    for i, hl in enumerate(gallery_hint_lines):
        hs = small_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy))
        hy += lh_label + (
            gallery_hint_line_gap if i + 1 < len(gallery_hint_lines) else 0
        )


_GALLERY_FS_HINT_RETURN = "【Enter】返回畫廊"
# 畫廊全螢幕底欄敘事（強敵／夥伴）規則：文案單段連續、不分段；可見至多兩行，超出由
# ``_gallery_trim_footer_desc_to_two_visible_lines`` 自尾端縮短；強敵／夥伴繪製時並設
# ``prefer_greedy_first_line_wrap``，第一行貪婪塞滿行寬以免上行右側大塊留白。
# 「獎勵圖片」全螢幕底欄敘述僅一行正文＋提示，見 ``_gallery_trim_footer_desc_to_one_visible_line``。


def _gallery_fullscreen_layout(
    small_font: pygame.font.Font,
) -> tuple[int, int, int, int, pygame.Rect, pygame.Rect, int, int]:
    """
    大 CG 全螢幕：上方圖區與結局第三頁同高；底欄固定三行文字高度。

    Returns:
        mx, max_w, lh_s, band_h, cg_rect, bar, pad_top, pad_bt
    """
    mx = _scale_x(12)
    max_w = CANVAS_WIDTH - 2 * mx
    lh_s = small_font.get_height() + 2
    pad_top = _scale_y(4)
    pad_bt = _scale_y(5)
    band_h = pad_top + 3 * lh_s + pad_bt
    cg_rect = pygame.Rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT - band_h)
    bar = pygame.Rect(0, CANVAS_HEIGHT - band_h, CANVAS_WIDTH, band_h)
    return mx, max_w, lh_s, band_h, cg_rect, bar, pad_top, pad_bt


def _gallery_fullscreen_layout_reward_one_line(
    small_font: pygame.font.Font,
) -> tuple[int, int, int, int, pygame.Rect, pygame.Rect, int, int]:
    """
    獎勵 CG 全螢幕：底欄僅「一行敘述＋一行提示」，圖區較 ``_gallery_fullscreen_layout`` 略高。

    Returns:
        mx, max_w, lh_s, band_h, cg_rect, bar, pad_top, pad_bt
    """
    mx = _scale_x(12)
    max_w = CANVAS_WIDTH - 2 * mx
    lh_s = small_font.get_height() + 2
    pad_top = _scale_y(4)
    pad_bt = _scale_y(5)
    band_h = pad_top + 2 * lh_s + pad_bt
    cg_rect = pygame.Rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT - band_h)
    bar = pygame.Rect(0, CANVAS_HEIGHT - band_h, CANVAS_WIDTH, band_h)
    return mx, max_w, lh_s, band_h, cg_rect, bar, pad_top, pad_bt


def _gallery_fullscreen_draw_footer(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    bar: pygame.Rect,
    mx: int,
    max_w: int,
    lh_s: int,
    pad_top: int,
    pad_bt: int,
    *,
    line1: str,
    line2: str,
    hint_text: str,
) -> None:
    """
    畫廊大 CG 底欄：第一行姓名、第二行簡介、第三行提示（右對齊）。

    Args:
        canvas: 邏輯畫布。
        small_font: 小字。
        bar: 底欄矩形。
        mx: 左右邊距。
        max_w: 文字最大寬。
        lh_s: 單行高（含行距）。
        pad_top: 欄內頂距。
        pad_bt: 欄內底距。
        line1: 第一行。
        line2: 第二行。
        hint_text: 第三行提示全文。
    """
    title_h = lh_s
    hint_h = lh_s
    line1_fit = _fit_one_line_cjk(small_font, line1, max_w)
    line2_fit = _fit_one_line_cjk(small_font, line2, max_w)
    hint_one = _fit_one_line_cjk(small_font, hint_text, max_w)
    ty = bar.y + pad_top
    canvas.blit(small_font.render(line1_fit, True, (255, 230, 190)), (mx, ty))
    ty += title_h
    canvas.blit(small_font.render(line2_fit, True, (200, 205, 220)), (mx, ty))
    hy = bar.bottom - pad_bt - hint_h
    hint_surf = small_font.render(hint_one, True, (140, 150, 170))
    hint_x = CANVAS_WIDTH - mx - hint_surf.get_width()
    canvas.blit(hint_surf, (hint_x, hy))


def _normalize_footer_blob_continuous_zh(text: str) -> str:
    """
    將畫廊底欄來源字串併成單行連續正文（移除換行與多餘空白，不分段）。

    Args:
        text: 原始文案。

    Returns:
        無換行字串。
    """
    s = (text or "").strip()
    if not s:
        return s
    return "".join(s.split())


def _companion_gallery_desc_short(meta: WhimEncounter) -> str:
    """
    同行的夥伴全螢幕底欄：優先使用 ``WhimEncounter.gallery_footer_zh``（單段連續；可見至多兩行，不以刪節號硬截）。

    Args:
        meta: 奇遇 NPC 資料。

    Returns:
        一段短文（不含名稱疊字；名稱另繪於圖上）。
    """
    authored = _normalize_footer_blob_continuous_zh(meta.gallery_footer_zh or "")
    if authored:
        return authored
    head = f"{meta.location_zh}——{meta.epithet}。"
    for para in (meta.preamble_para1, meta.preamble_para2):
        raw = _normalize_footer_blob_continuous_zh(para or "")
        if not raw:
            continue
        for seg in raw.split("。"):
            seg = seg.strip()
            if seg:
                return head + seg + "。"
    return head


def _gallery_footer_try_punct_split(
    font: pygame.font.Font,
    s: str,
    max_w: int,
) -> tuple[str, str] | None:
    """
    依「。」或「；」拆成兩段；略過首段過短之斷點（避免「地點——稱號。」單獨佔滿第一行）。

    Args:
        font: 量測用字型。
        s: 單一邏輯行全文。
        max_w: 單行最大像素寬。

    Returns:
        可拆則 (前段, 後段)，否則 None。
    """
    min_px = max_w * 0.36
    min_chars = 26
    for sep in ("。", "；"):
        start = 0
        while True:
            idx = s.find(sep, start)
            if idx == -1:
                break
            a = s[: idx + 1].strip()
            b = s[idx + 1 :].strip()
            if not b:
                start = idx + 1
                continue
            if len(a) < min_chars and font.size(a)[0] < min_px:
                start = idx + 1
                continue
            return (a, b)
    return None


def _gallery_footer_try_comma_split(
    font: pygame.font.Font,
    s: str,
    max_w: int,
) -> tuple[str, str] | None:
    """
    依「，」拆成兩段；首段須達一定寬度，避免頭重腳輕。

    Args:
        font: 量測用字型。
        s: 單一邏輯行全文。
        max_w: 單行最大像素寬。

    Returns:
        可拆則 (前段, 後段)，否則 None。
    """
    min_px = max_w * 0.34
    start = 0
    while True:
        idx = s.find("，", start)
        if idx == -1:
            return None
        a = s[: idx + 1].strip()
        b = s[idx + 1 :].strip()
        if not b:
            start = idx + 1
            continue
        if font.size(a)[0] >= min_px:
            return (a, b)
        start = idx + 1


def _gallery_footer_balanced_split(
    font: pygame.font.Font,
    s: str,
    max_w: int,
) -> tuple[str, str]:
    """
    將單一邏輯行依像素寬度拆成兩段，使兩行字量較均衡（結局畫廊等預設路徑仍用此；**不**用於強敵／夥伴／獎勵全螢幕）。

    無句讀或句讀拆得太頭輕腳重時使用；過短則不拆。

    Args:
        font: 量測用字型。
        s: 已能單行排入 max_w 之字串（或將由後續 _fit 截斷）。
        max_w: 單行最大像素寬。

    Returns:
        (前段, 後段)；不應拆時後段為空字串。
    """
    raw = (s or "").strip()
    if not raw:
        return "", ""
    if max_w <= 0:
        return raw, ""
    total_w = font.size(raw)[0]
    # 極短：不硬拆，避免第二行只剩一兩個字
    if total_w <= max_w * 0.26 and len(raw) < 14:
        return raw, ""
    # 目標斷點：約行寬中段，使兩行長度不過度失衡（與貪婪第一行塞滿不同）
    target_mid = max_w * 0.54
    acc = ""
    break_at = len(raw)
    for i, ch in enumerate(raw):
        acc += ch
        if font.size(acc)[0] >= target_mid:
            break_at = i + 1
            break
    lo = max(1, break_at - 10)
    for j in range(break_at - 1, lo - 1, -1):
        if raw[j] in "、，。；：．.!?":
            break_at = j + 1
            break
    a = raw[:break_at].strip()
    b = raw[break_at:].strip()
    if not b or not a:
        return raw, ""
    return a, b


def _gallery_footer_two_lines_from_text(
    font: pygame.font.Font,
    text: str,
    max_w: int,
    *,
    prefer_greedy_first_line_wrap: bool = False,
) -> tuple[str, str]:
    """
    將一段敘述濃縮為底欄兩行（單行過寬則截字；多行則首行取第一換行段、次行合併其餘）。

    單一換行段時：預設依句讀再試逗號，最後像素平衡拆行。
    若 ``prefer_greedy_first_line_wrap`` 為 True（強敵／夥伴／獎勵全螢幕底欄），先試
    ``_gallery_try_split_two_lines_no_weak_line1_end``：兩行皆單行可排且**第一行末字非逗號／分號等弱句讀**；
    不可行時再退回 ``wrap_cjk`` **貪婪換行**（第一行盡量塞滿至 ``max_w``，餘字入第二行）。

    Args:
        font: 量測用字型。
        text: 原文。
        max_w: 單行最大寬。
        prefer_greedy_first_line_wrap: 為 True 時第一行貪婪塞滿寬度。

    Returns:
        (第一行, 第二行)。
    """
    t = (text or "").strip()
    if not t:
        return "—", ""
    if prefer_greedy_first_line_wrap:
        split = _gallery_try_split_two_lines_no_weak_line1_end(font, t, max_w)
        if split is not None:
            a, b = split
            return (
                _fit_one_line_cjk(font, a, max_w),
                _fit_one_line_cjk(font, b, max_w),
            )
        lines = wrap_cjk(font, t, max_w)
        if not lines:
            return _fit_one_line_cjk(font, t, max_w), ""
        if len(lines) == 1:
            return _fit_one_line_cjk(font, lines[0], max_w), ""
        line1 = _fit_one_line_cjk(font, lines[0], max_w)
        rest = "".join(lines[1:])
        line2 = _fit_one_line_cjk(font, rest, max_w)
        return line1, line2
    lines = wrap_cjk(font, t, max_w)
    if not lines:
        return _fit_one_line_cjk(font, t, max_w), ""
    if len(lines) == 1:
        s = lines[0]
        ps = _gallery_footer_try_punct_split(font, s, max_w)
        if ps is not None:
            a, b = ps
            return (
                _fit_one_line_cjk(font, a, max_w),
                _fit_one_line_cjk(font, b, max_w),
            )
        cs = _gallery_footer_try_comma_split(font, s, max_w)
        if cs is not None:
            a, b = cs
            return (
                _fit_one_line_cjk(font, a, max_w),
                _fit_one_line_cjk(font, b, max_w),
            )
        a2, b2 = _gallery_footer_balanced_split(font, s, max_w)
        if b2:
            return (
                _fit_one_line_cjk(font, a2, max_w),
                _fit_one_line_cjk(font, b2, max_w),
            )
        return _fit_one_line_cjk(font, s, max_w), ""
    line1 = _fit_one_line_cjk(font, lines[0], max_w)
    if len(lines) > 2:
        rest = "".join(lines[1:])
        line2 = _fit_one_line_cjk(font, rest, max_w)
    else:
        line2 = _fit_one_line_cjk(font, lines[1], max_w)
    return line1, line2


def _gallery_trim_footer_desc_to_two_visible_lines(
    font: pygame.font.Font,
    text: str,
    max_w: int,
    *,
    prefer_greedy_first_line_wrap: bool = False,
) -> str:
    """
    自尾端縮短原文，使畫廊全螢幕底欄敘事**不超過兩行可見**且可讀（與繪製時雙重 ``_fit_one_line_cjk`` 一致）。

    以 ``wrap_cjk`` 至多兩行；兩敘事行經 ``_fit_one_line_cjk`` 後不得出現非原文結尾之「…」。文案應單段連續，長度盡量寫滿但不超過兩行。

    Args:
        font: 與底欄相同之字型。
        text: 來源敘述。
        max_w: 單行最大像素寬。
        prefer_greedy_first_line_wrap: 傳予 ``_gallery_footer_two_lines_from_text``；強敵／夥伴／獎勵全螢幕應為 True。

    Returns:
        可完整納入兩行底欄之敘述（可能變短）。
    """
    t = (text or "").strip()
    if not t:
        return t
    max_w = max(1, int(max_w))
    ell = "…"
    while len(t) > 0:
        src_tail_ell = t.rstrip().endswith(ell)
        if len(wrap_cjk(font, t, max_w)) > 2:
            t = t[:-1].rstrip()
            continue
        a, b = _gallery_footer_two_lines_from_text(
            font, t, max_w, prefer_greedy_first_line_wrap=prefer_greedy_first_line_wrap
        )
        line1_fit = _fit_one_line_cjk(font, a, max_w)
        line2_fit = _fit_one_line_cjk(font, b, max_w) if b else ""
        if ell in line1_fit and not src_tail_ell:
            t = t[:-1].rstrip()
            continue
        if b and ell in line2_fit and not src_tail_ell:
            t = t[:-1].rstrip()
            continue
        return t
    return t


def _gallery_trim_footer_desc_to_one_visible_line(
    font: pygame.font.Font,
    text: str,
    max_w: int,
) -> str:
    """
    自尾端縮短原文，使畫廊全螢幕底欄敘事**不超過一行可見**（與繪製時 ``_fit_one_line_cjk`` 一致）。

    以 ``wrap_cjk`` 至多一行；經 ``_fit_one_line_cjk`` 後不得出現非原文結尾之「…」。獎勵文案應單段連續，
    長度盡量寫滿但不超過一行。

    Args:
        font: 與底欄相同之字型。
        text: 來源敘述。
        max_w: 單行最大像素寬。

    Returns:
        可完整納入一行底欄之敘述（可能變短）。
    """
    t = (text or "").strip()
    if not t:
        return t
    max_w = max(1, int(max_w))
    ell = "…"
    while len(t) > 0:
        src_tail_ell = t.rstrip().endswith(ell)
        if len(wrap_cjk(font, t, max_w)) > 1:
            t = t[:-1].rstrip()
            continue
        line1_fit = _fit_one_line_cjk(font, t, max_w)
        if ell in line1_fit and not src_tail_ell:
            t = t[:-1].rstrip()
            continue
        return t
    return t


def _gallery_fullscreen_draw_footer_single_desc(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    bar: pygame.Rect,
    mx: int,
    max_w: int,
    lh_s: int,
    pad_top: int,
    pad_bt: int,
    *,
    line1: str,
    hint_text: str,
) -> None:
    """
    畫廊大 CG 底欄：一行場景／角色敘述，第二行為右對齊提示（獎勵全螢幕用）。

    Args:
        canvas: 邏輯畫布。
        small_font: 小字。
        bar: 底欄矩形。
        mx: 左右邊距。
        max_w: 文字最大寬。
        lh_s: 單行高（含行距）。
        pad_top: 欄內頂距。
        pad_bt: 欄內底距。
        line1: 敘述一行。
        hint_text: 底端提示全文。
    """
    body_rgb = (200, 205, 220)
    title_h = lh_s
    hint_h = lh_s
    line1_fit = _fit_one_line_cjk(small_font, line1, max_w)
    hint_one = _fit_one_line_cjk(small_font, hint_text, max_w)
    ty = bar.y + pad_top
    canvas.blit(small_font.render(line1_fit, True, body_rgb), (mx, ty))
    hy = bar.bottom - pad_bt - hint_h
    hint_surf = small_font.render(hint_one, True, (140, 150, 170))
    hint_x = CANVAS_WIDTH - mx - hint_surf.get_width()
    canvas.blit(hint_surf, (hint_x, hy))


def _gallery_fullscreen_draw_footer_dual_desc(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    bar: pygame.Rect,
    mx: int,
    max_w: int,
    lh_s: int,
    pad_top: int,
    pad_bt: int,
    *,
    line1: str,
    line2: str,
    hint_text: str,
) -> None:
    """
    畫廊大 CG 底欄：兩行皆為場景／角色敘述（同色），第三行提示右對齊。

    Args:
        canvas: 邏輯畫布。
        small_font: 小字。
        bar: 底欄矩形。
        mx: 左右邊距。
        max_w: 文字最大寬。
        lh_s: 單行高（含行距）。
        pad_top: 欄內頂距。
        pad_bt: 欄內底距。
        line1: 第一行描述。
        line2: 第二行描述。
        hint_text: 第三行提示全文。
    """
    body_rgb = (200, 205, 220)
    title_h = lh_s
    hint_h = lh_s
    line1_fit = _fit_one_line_cjk(small_font, line1, max_w)
    line2_fit = _fit_one_line_cjk(small_font, line2, max_w)
    hint_one = _fit_one_line_cjk(small_font, hint_text, max_w)
    ty = bar.y + pad_top
    canvas.blit(small_font.render(line1_fit, True, body_rgb), (mx, ty))
    ty += title_h
    canvas.blit(small_font.render(line2_fit, True, body_rgb), (mx, ty))
    hy = bar.bottom - pad_bt - hint_h
    hint_surf = small_font.render(hint_one, True, (140, 150, 170))
    hint_x = CANVAS_WIDTH - mx - hint_surf.get_width()
    canvas.blit(hint_surf, (hint_x, hy))


def _draw_cg_name_overlay_top_left(
    canvas: pygame.Surface,
    cg_rect: pygame.Rect,
    font: pygame.font.Font,
    name_zh: str,
) -> None:
    """
    在 CG 區左上角繪製角色名：半透明底＋前景文字（與「同行的夥伴」「遭遇的強敵」共用）。

    Args:
        canvas: 邏輯畫布。
        cg_rect: 上方圖區矩形。
        font: 名稱用字型（通常與底欄小字同級）。
        name_zh: 顯示名稱（過寬則截字）。
    """
    raw = (name_zh or "").strip() or "……"
    pad_x = _scale_x(6)
    pad_y = _scale_y(5)
    inner_max = max(1, cg_rect.w - pad_x * 2 - _scale_x(4))
    line = _fit_one_line_cjk(font, raw, inner_max)
    surf = font.render(line, True, (255, 242, 228))
    sw, sh = surf.get_width(), surf.get_height()
    bx = cg_rect.x + pad_x
    by = cg_rect.y + pad_y
    bw = sw + _scale_x(10)
    bh = sh + _scale_y(8)
    panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
    panel.fill((14, 18, 28, 188))
    canvas.blit(panel, (bx, by))
    canvas.blit(surf, (bx + _scale_x(5), by + _scale_y(4)))


def draw_companion_cg_fullscreen(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    cg_key: str,
    asset_root: Path,
    tick: int,
) -> None:
    """
    「同行的夥伴」全螢幕檢視；名稱置於圖區左上半透明底，底欄兩行連續敘述（第一行貪婪塞滿至行寬）。

    Args:
        canvas: 邏輯畫布。
        small_font: 底欄字與名稱疊字。
        cg_key: CG 主檔名鍵。
        asset_root: 專案根目錄。
        tick: 影格（預留）。
    """
    _ = tick
    canvas.fill((22, 26, 34))
    mx, max_w, lh_s, _, cg_rect, bar, pad_top, pad_bt = _gallery_fullscreen_layout(
        small_font
    )
    tw = max(1, cg_rect.w)
    th = max(1, cg_rect.h)
    meta = _WHIM_BY_CG_BASENAME.get(cg_key)
    name_line = meta.display_name if meta else cg_key
    if meta is not None:
        desc_blob = _companion_gallery_desc_short(meta)
    else:
        desc_blob = "奇遇場景；畫面依該格鍵再演繹，氛圍與旅路、魔法基調一致。"
    desc_blob = _gallery_trim_footer_desc_to_two_visible_lines(
        small_font, desc_blob, max_w, prefer_greedy_first_line_wrap=True
    )
    d1, d2 = _gallery_footer_two_lines_from_text(
        small_font, desc_blob, max_w, prefer_greedy_first_line_wrap=True
    )
    cg_surface = load_companion_gallery_cg_fill(asset_root, cg_key, tw, th)
    if cg_surface is not None:
        pygame.draw.rect(canvas, (32, 38, 50), cg_rect)
        canvas.blit(cg_surface, (cg_rect.x, cg_rect.y))
        bw = max(2, cg_rect.h // 200)
        pygame.draw.rect(canvas, (200, 175, 210), cg_rect, width=bw)
    else:
        inner = cg_rect.inflate(-_scale_x(8), -_scale_y(8))
        draw_companion_gallery_placeholder(canvas, inner, name_line)
    _draw_cg_name_overlay_top_left(canvas, cg_rect, small_font, name_line)
    pygame.draw.rect(canvas, (26, 30, 40), bar)
    pygame.draw.line(canvas, (72, 82, 102), (0, bar.y), (CANVAS_WIDTH, bar.y), 2)
    _gallery_fullscreen_draw_footer_dual_desc(
        canvas,
        small_font,
        bar,
        mx,
        max_w,
        lh_s,
        pad_top,
        pad_bt,
        line1=d1,
        line2=d2,
        hint_text=_GALLERY_FS_HINT_RETURN,
    )


def _encounter_gallery_intro_default_zh() -> str:
    """遭遇畫廊缺省簡介（無敵方資料時；單段連續、不分段羅列）。"""
    return (
        "遭遇戰圖為遊戲內設計，外觀未必與劇中一一對應；"
        "魔物擅用地形與視線，魔法使靠距離與詠唱節奏，先讀環境與威脅層次再談反擊，別在迷霧裡先慌了腳步。"
    )


def _encounter_gallery_footer_blob(enemy: EncounterEnemy | None) -> str:
    """
    遭遇畫廊全螢幕底欄：直接使用 ``EncounterEnemy.gallery_intro_zh``（單段連續正文，無換行、不以刪節號硬截）。

    Args:
        enemy: 敵方定義；None 時改用內建缺省文。

    Returns:
        單段中文（交由 ``_gallery_trim_footer_desc_to_two_visible_lines`` 再限兩行可見；必要時自尾端縮短，不出現「…」於原文）。
    """
    default = _encounter_gallery_intro_default_zh()
    if enemy is None:
        return default
    raw = _normalize_footer_blob_continuous_zh(enemy.gallery_intro_zh or "")
    return raw if raw else default


def draw_encounter_cg_fullscreen(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    enemy_id: str,
    asset_root: Path,
    tick: int,
) -> None:
    """
    遭遇敵 CG 全螢幕檢視；名稱置於圖區左上半透明底，底欄兩行連續敘述（第一行貪婪塞滿至行寬，避免上行右側大塊留白）。

    Args:
        canvas: 邏輯畫布。
        small_font: 底欄字與名稱疊字。
        enemy_id: 敵人鍵。
        asset_root: 專案根。
        tick: 影格（占位繪製用）。
    """
    canvas.fill((22, 26, 34))
    mx, max_w, lh_s, _, cg_rect, bar, pad_top, pad_bt = _gallery_fullscreen_layout(
        small_font
    )
    tw = max(1, cg_rect.w)
    th = max(1, cg_rect.h)
    enemy = get_enemy_by_id(enemy_id)
    intro_src = _encounter_gallery_footer_blob(enemy)
    intro_src = _gallery_trim_footer_desc_to_two_visible_lines(
        small_font, intro_src, max_w, prefer_greedy_first_line_wrap=True
    )
    name_zh = enemy.name_zh if enemy else enemy_id
    d1, d2 = _gallery_footer_two_lines_from_text(
        small_font, intro_src, max_w, prefer_greedy_first_line_wrap=True
    )
    cg = encounter_gallery_cg_fill(asset_root, enemy_id, tw, th)
    if cg is not None:
        pygame.draw.rect(canvas, (32, 38, 50), cg_rect)
        canvas.blit(cg, (cg_rect.x, cg_rect.y))
        bw = max(2, cg_rect.h // 200)
        pygame.draw.rect(canvas, (200, 175, 210), cg_rect, width=bw)
    elif enemy is not None:
        pr = pygame.Rect(cg_rect.x, cg_rect.y, tw, th)
        draw_encounter_enemy_placeholder(canvas, pr, enemy, tick)
    else:
        pygame.draw.rect(canvas, (32, 38, 50), cg_rect)
        bw = max(2, cg_rect.h // 200)
        pygame.draw.rect(canvas, (200, 175, 210), cg_rect, width=bw)
    _draw_cg_name_overlay_top_left(canvas, cg_rect, small_font, name_zh)
    pygame.draw.rect(canvas, (26, 30, 40), bar)
    pygame.draw.line(canvas, (72, 82, 102), (0, bar.y), (CANVAS_WIDTH, bar.y), 2)
    _gallery_fullscreen_draw_footer_dual_desc(
        canvas,
        small_font,
        bar,
        mx,
        max_w,
        lh_s,
        pad_top,
        pad_bt,
        line1=d1,
        line2=d2,
        hint_text=_GALLERY_FS_HINT_RETURN,
    )


def draw_reward_cg_fullscreen(
    canvas: pygame.Surface,
    small_font: pygame.font.Font,
    cg_rel_path: str,
    caption_zh: str,
    state: GameState,
    tick: int,
    *,
    reward_token: str | None = None,
    reward_filename_key_order: tuple[str, ...] | None = None,
    reward_note_zh: str | None = None,
) -> None:
    """
    組合獎勵 CG 全畫面檢視（單頁、無敘事切換）；底欄**一行**場景描述（不顯示角色名）。
    CG 區為 cover 縮放、**底對齊並略向置中插值**，在仍偏保留下方字幕的前提下多露一點圖片上方。

    Args:
        canvas: 邏輯畫布。
        small_font: 底部說明。
        cg_rel_path: 圖檔相對路徑。
        caption_zh: 內部顯示用（格內標題等）；全螢幕底欄**不**顯示。
        state: 遊戲狀態（載入失敗時退回立繪）。
        tick: 影格。
        reward_token: 內部規範 token；無館藏註解時供場景後備文用。
        reward_filename_key_order: 與檔名一致之 key 序。
        reward_note_zh: 來自 ``gallery_rewards`` 之館藏註解；None 時改依圖檔路徑查表或泛用文。
    """
    _ = caption_zh
    _ = tick
    canvas.fill((22, 26, 34))
    mx, max_w, lh_s, _, cg_rect, bar, pad_top, pad_bt = _gallery_fullscreen_layout_reward_one_line(
        small_font
    )
    flavor_raw = reward_gallery_footer_source_zh(
        cg_rel_path,
        reward_note_zh,
        reward_token or "",
        filename_key_order=reward_filename_key_order,
    )
    flavor_raw = _gallery_trim_footer_desc_to_one_visible_line(
        small_font, flavor_raw, max_w
    )
    tw = max(1, cg_rect.w)
    th = max(1, cg_rect.h)
    cg_surf = _get_scaled_ending_cg_fill(
        cg_rel_path,
        tw,
        th,
        vertical_align="bottom",
        bottom_toward_center_blend=0.18,
    )
    if cg_surf is not None:
        pygame.draw.rect(canvas, (32, 38, 50), cg_rect)
        canvas.blit(cg_surf, (cg_rect.x, cg_rect.y))
        bw = max(2, cg_rect.h // 200)
        pygame.draw.rect(canvas, (200, 175, 210), cg_rect, width=bw)
    else:
        inner = cg_rect.inflate(-_scale_x(8), -_scale_y(8))
        draw_heroine_portrait(canvas, inner, state, tick)

    pygame.draw.rect(canvas, (26, 30, 40), bar)
    pygame.draw.line(canvas, (72, 82, 102), (0, bar.y), (CANVAS_WIDTH, bar.y), 2)
    _gallery_fullscreen_draw_footer_single_desc(
        canvas,
        small_font,
        bar,
        mx,
        max_w,
        lh_s,
        pad_top,
        pad_bt,
        line1=flavor_raw,
        hint_text=_GALLERY_FS_HINT_RETURN,
    )


def _ending_cg_page_index(ending: Ending) -> int:
    """
    結局翻頁時「CG 頁」之 page_index（接在所有敘事頁之後）。

    敘事為 ``0 .. len(narrative_pages)-1``，下一頁為 CG，索引等於 ``len(narrative_pages)``。

    Args:
        ending: 結局資料。

    Returns:
        CG 頁之索引（單一結局內之翻頁座標，非總頁數）。
    """
    return len(ending.narrative_pages)


def draw_gallery_ending_pages(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    font: pygame.font.Font,
    ending_key: str,
    page_index: int,
    state: GameState,
    tick: int,
) -> None:
    """
    畫廊內全螢幕檢視單一結局：若干敘事頁後接一頁大 CG；左右鍵在 ``0`` 至 CG 頁索引間移動，首尾不相通。

    Args:
        canvas: 邏輯畫布。
        intro_font: 敘事頁標題／內文。
        small_font: 敘事頁頁尾與 CG 頁底部列。
        font: 傳予 ``draw_ending_cg_screen``（簽名保留）。
        ending_key: 合法結局鍵（屬於 ``GALLERY_ENDING_KEYS`` 之子集）。
        page_index: ``0 .. len(narrative_pages)-1`` 為敘事；``len(narrative_pages)`` 為 CG。
        state: 目前遊戲狀態（CG 頁顯示主角名）。
        tick: 影格。
    """
    meta = ENDINGS.get(ending_key)
    if meta is None:
        canvas.fill((22, 26, 34))
        return
    cg_i = _ending_cg_page_index(meta)
    pi = max(0, min(cg_i, page_index))
    if pi < cg_i:
        draw_ending_narrative_screen(
            canvas,
            intro_font,
            small_font,
            meta,
            pi,
            tick,
            from_gallery=True,
        )
    else:
        draw_ending_cg_screen(
            canvas,
            font,
            small_font,
            meta,
            state,
            tick,
            from_gallery=True,
        )


def draw_ending_gallery_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    gallery_page_index: int,
    gallery_slot_index: int,
    gallery_unlocked: set[str],
    gallery_keys: tuple[str, ...],
    section_header: str,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製圖片畫廊子頁（結局 CG）：每頁 3×2 共六張縮圖（末頁可能不足六張）。

    Args:
        canvas: 邏輯畫布。
        menu_font: 標題列字級。
        small_font: 格內名稱與頁尾說明。
        gallery_page_index: 頁碼 0 起。
        gallery_slot_index: 該頁內目前選中格（0～該頁格數−1）。
        gallery_unlocked: 已達成結局 key 集合。
        gallery_keys: 目前分類之結局鍵序（如男線／女線各十人）。
        section_header: 標題列左側分類名（如「通關圖片+結局(男性)」）。
        star_xy: 與標題畫面相同的星空座標。
        tick: 影格（星空閃爍）。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(16)
    lh_label = small_font.get_height()
    gallery_hint_raw = (
        "方向鍵 選擇　PageUp／PageDown 換頁　Enter 全畫面欣賞（已通關）　Esc 返回圖片畫廊"
    )
    gallery_hint_lines = wrap_cjk(
        small_font, gallery_hint_raw, CANVAS_WIDTH - 2 * mx
    )
    if not gallery_hint_lines:
        gallery_hint_lines = [gallery_hint_raw]
    gallery_hint_line_gap = 2
    gallery_hint_block_h = len(gallery_hint_lines) * lh_label + max(
        0, len(gallery_hint_lines) - 1
    ) * gallery_hint_line_gap
    grid_bottom = CANVAS_HEIGHT - _scale_y(8) - gallery_hint_block_h

    pc = _gallery_page_count(gallery_keys)
    pi = max(0, min(gallery_page_index, pc - 1))
    hdr = f"{section_header}　（{pi + 1}／{pc}）"
    y = _scale_y(8)
    for line in wrap_cjk(menu_font, hdr, CANVAS_WIDTH - 2 * mx):
        canvas.blit(menu_font.render(line, True, (255, 230, 190)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(3)

    keys_page = _gallery_keys_on_page(pi, gallery_keys)
    n_cols_ref = 3
    n_rows_ref = 2
    gap_x = _scale_x(6)
    gap_y = _scale_y(4)
    name_gap = _scale_y(2)
    label_line_gap = 1
    label_lines_max = 2
    label_block_h = (
        lh_label * label_lines_max
        + max(0, label_lines_max - 1) * label_line_gap
    )
    avail_h = max(_scale_y(72), grid_bottom - y)
    row_inner_h = (avail_h - (n_rows_ref - 1) * gap_y) // n_rows_ref
    box_h = max(1, row_inner_h - name_gap - label_block_h)
    cell_w = (CANVAS_WIDTH - 2 * mx - (n_cols_ref - 1) * gap_x) // n_cols_ref
    grid_total_w = n_cols_ref * cell_w + (n_cols_ref - 1) * gap_x
    x0 = (CANVAS_WIDTH - grid_total_w) // 2
    row_stride_y = row_inner_h + gap_y

    slot_image_rects: list[tuple[str, pygame.Rect]] = []

    def _draw_one_cell(ek: str, cx: int, cy: int) -> None:
        """邊框僅包住圖片區；名稱繪於框外下方。"""
        box_rect = pygame.Rect(cx, cy, cell_w, box_h)
        slot_image_rects.append((ek, box_rect))
        border_w = max(1, _scale_x(2))

        show_real, meta = _gallery_cell_unlocked_with_file(ek, gallery_unlocked)
        pygame.draw.rect(canvas, (28, 32, 44), box_rect)
        drew_thumb = False
        if show_real and meta is not None:
            cg_fill = _get_scaled_ending_cg_fill(
                meta.cg_path, max(1, box_rect.w), max(1, box_rect.h)
            )
            if cg_fill is not None:
                canvas.blit(cg_fill, box_rect.topleft)
                drew_thumb = True
        if not drew_thumb:
            draw_gallery_cell_locked_cross(canvas, box_rect)

        pygame.draw.rect(canvas, (90, 100, 120), box_rect, width=border_w)

        name_w = max(1, cell_w - _scale_x(2))
        # 未解鎖仍顯示角色名，僅縮圖區不載入 CG（與男女通關圖片分頁一致）。
        disp_name = meta.name if meta is not None else _GALLERY_UNKNOWN_NAME
        name_lines = wrap_cjk(small_font, disp_name, name_w)[:label_lines_max]
        ny_line = box_rect.bottom + name_gap
        for nl in name_lines:
            ns = small_font.render(nl, True, (200, 205, 220))
            nx = cx + (cell_w - ns.get_width()) // 2
            canvas.blit(ns, (nx, ny_line))
            ny_line += lh_label + label_line_gap

    y_top = y
    for idx, ek in enumerate(keys_page):
        row = idx // n_cols_ref
        col = idx % n_cols_ref
        cx = x0 + col * (cell_w + gap_x)
        cy = y_top + row * row_stride_y
        _draw_one_cell(ek, cx, cy)

    n_slots = len(keys_page)
    sel = max(0, min(gallery_slot_index, n_slots - 1))
    if 0 <= sel < len(slot_image_rects):
        _, sel_box = slot_image_rects[sel]
        ow = max(2, _scale_x(3))
        pygame.draw.rect(
            canvas,
            (255, 255, 255),
            sel_box.inflate(_scale_x(3), _scale_y(3)),
            width=ow,
        )

    hy = CANVAS_HEIGHT - _scale_y(8) - gallery_hint_block_h
    for i, hl in enumerate(gallery_hint_lines):
        hs = small_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy))
        hy += lh_label + (
            gallery_hint_line_gap if i + 1 < len(gallery_hint_lines) else 0
        )


def draw_intro_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    page_index: int,
    intro_pages: list[list[str]],
    section_headers: tuple[str, ...],
    tick: int,
) -> None:
    """
    繪製開場前提（含每頁小標）。

    頁尾固定在畫布下方（依換行後實際高度），內文區為 [插圖底, 頁頂間隙)；與換行寬度須與 `main` 建 `intro_pages` 時一致。
    """
    canvas.fill((24, 28, 38))
    art_h = min(230, max(120, int(CANVAS_HEIGHT * _INTRO_ART_HEIGHT_RATIO)))
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_prologue_illustration(canvas, art_rect, page_index, tick)
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    n_pages = len(intro_pages)
    if page_index == 0:
        nav_hint = "→ 下一頁"
    elif page_index >= n_pages - 1:
        nav_hint = "← 上一頁　Enter 開始遊戲"
    else:
        nav_hint = "← 上一頁　→ 下一頁"
    page_line = f"第 {page_index + 1} / {n_pages} 頁"
    footer_lines: list[str] = []
    for block in (nav_hint, page_line):
        footer_lines.extend(wrap_cjk(small_font, block, max_w))
    if not footer_lines:
        footer_lines = [nav_hint, page_line]
    lh_s = small_font.get_height()
    footer_gap = 2
    footer_content_h = len(footer_lines) * lh_s + max(0, len(footer_lines) - 1) * footer_gap
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    body_footer_gap = 8 * CANVAS_HEIGHT // _ORIG_H
    footer_top = CANVAS_HEIGHT - bottom_pad - footer_content_h
    text_limit_y = footer_top - body_footer_gap

    y = art_h + 8 * CANVAS_HEIGHT // _ORIG_H
    fh = intro_font.get_height()

    if page_index < len(section_headers):
        hdr = section_headers[page_index]
        for hl in wrap_cjk(intro_font, hdr, max_w):
            if y + fh > text_limit_y:
                break
            canvas.blit(intro_font.render(hl, True, (255, 214, 170)), (mx, y))
            y += fh + 2
        y += 4 * CANVAS_HEIGHT // _ORIG_H

    for para in intro_pages[page_index]:
        for L in wrap_cjk(intro_font, para, max_w):
            if y + fh > text_limit_y:
                break
            canvas.blit(intro_font.render(L, True, (230, 232, 240)), (mx, y))
            y += fh + 2
        y += 4 * CANVAS_HEIGHT // _ORIG_H

    fy = footer_top
    for i, fl in enumerate(footer_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (footer_gap if i + 1 < len(footer_lines) else 0)


def draw_guardian_intro_screen(
    canvas: pygame.Surface,
    header_font: pygame.font.Font,
    body_font: pygame.font.Font,
    small_font: pygame.font.Font,
    guardian_pages: list[list[str]],
    tick: int,
    *,
    onboarding_font: pygame.font.Font,
    name_entry_step: int,
    name_entry_gender_index: int,
    name_buffer: str,
    ime_composition: str,
) -> None:
    """
    繪製監護人說明：上方插圖＋標題＋內文，底部同一頁完成性別與取名（不另開空白頁）。

    Args:
        canvas: 邏輯畫布。
        header_font: 「監護人須知」標題（粗體，字級略大於內文）。
        body_font: 監護人正文。
        small_font: 底部操作提示。
        guardian_pages: 預先換行後的段落行列表。
        tick: 影格。
        onboarding_font: 底部取名區主字（通常與 ``body_font``／``intro_font`` 同像素）。
        name_entry_step: 0 選性別／1 輸入名字。
        name_entry_gender_index: 0 男孩／1 女孩。
        name_buffer: 已輸入姓名。
        ime_composition: 輸入法組字。
    """
    canvas.fill((26, 30, 42))
    art_h = _guardian_combined_art_h()
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_guardian_illustration(canvas, art_rect, tick)
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    px = _scale_x(24)
    pw = CANVAS_WIDTH - 2 * px
    panel_top = _guardian_panel_top_fixed(small_font, onboarding_font, pw)
    gap_above_panel = 6 * CANVAS_HEIGHT // _ORIG_H
    footer_top = _guardian_fixed_footer_top(small_font, pw, name_entry_step)

    hdr = GUARDIAN_SECTION_HEADERS[0]
    hy0 = art_h + 6 * CANVAS_HEIGHT // _ORIG_H
    for hl in wrap_cjk(header_font, hdr, max_w):
        hs = header_font.render(hl, True, (255, 232, 200))
        canvas.blit(hs, ((CANVAS_WIDTH - hs.get_width()) // 2, hy0))
        hy0 += header_font.get_height() + 3

    y = hy0 + 4 * CANVAS_HEIGHT // _ORIG_H
    bh = body_font.get_height()
    lstep = bh + max(3, bh // 5)
    text_bottom = panel_top - gap_above_panel

    for line in guardian_pages[0]:
        for L in wrap_cjk(body_font, line, max_w):
            if y + bh > text_bottom:
                break
            canvas.blit(body_font.render(L, True, (232, 234, 245)), (mx, y))
            y += lstep
        y += 4 * CANVAS_HEIGHT // _ORIG_H

    pygame.draw.line(
        canvas,
        (56, 62, 78),
        (mx, panel_top - 2),
        (CANVAS_WIDTH - mx, panel_top - 2),
        1,
    )

    py = panel_top + _scale_y(6)
    content_max_y = footer_top - _scale_y(8)
    if name_entry_step == 0:
        for L in wrap_cjk(
            onboarding_font,
            "請選擇孩子的性別（↑↓ 切換，Enter 進入取名）。",
            pw,
        ):
            if py + onboarding_font.get_height() > content_max_y:
                break
            canvas.blit(onboarding_font.render(L, True, (228, 232, 245)), (px, py))
            py += onboarding_font.get_height() + 3
        py += _scale_y(4)
        opt_gap = _scale_y(2)
        for i, lab in enumerate(("男孩", "女孩")):
            disp = f"{i + 1}. {lab}"
            lh = onboarding_font.get_height() + 1
            pad_y = _scale_y(3)
            inner_tw = max(1, pw - 2 * _scale_x(6))
            peek_h = len(wrap_cjk(onboarding_font, disp, inner_tw)) * lh + 2 * pad_y
            # 僅兩個選項：第二項（女孩）務必畫出；第一項空間極度不足時仍可略過
            if i == 0 and py + peek_h > content_max_y:
                break
            py = _blit_event_style_choice_cell(
                canvas,
                px,
                py,
                pw,
                onboarding_font,
                disp,
                i == name_entry_gender_index,
                opt_gap_after=opt_gap,
                compact=True,
            )
    else:
        for L in wrap_cjk(
            onboarding_font,
            "請為孩子取名字（會顯示在養成畫面與結局）。",
            pw,
        ):
            if py + onboarding_font.get_height() > content_max_y:
                break
            canvas.blit(onboarding_font.render(L, True, (228, 232, 245)), (px, py))
            py += onboarding_font.get_height() + 3
        py += _scale_y(4)
        if py + onboarding_font.get_height() <= content_max_y:
            display = name_buffer + ime_composition + "▎"
            canvas.blit(onboarding_font.render(display, True, (255, 220, 180)), (px, py))

    nav_raw = (
        "Enter 確認（至少一字）　Esc 返回標題"
        if name_entry_step == 1
        else "Esc 返回標題"
    )
    nav_lines = wrap_cjk(small_font, nav_raw, pw) or [nav_raw]
    lh_nav = small_font.get_height() + 2
    fy = footer_top
    for i, nl in enumerate(nav_lines):
        canvas.blit(small_font.render(nl, True, (140, 150, 170)), (px, fy))
        fy += lh_nav


# 契約紙上偽古文（語意刻意曖昧，製造「不明文字」感）。
_CONTRACT_RUNE_LINES: tuple[str, ...] = (
    "凡締此紙者，不得在無星之夜私啟其縫；啟則時序洩於指隙。",
    "立約第九印：名先於形，形先於憶；憶不可溯於月缺之晝。",
    "「※」為界，「◇」為扉；扉內無晝夜，亦無回聲。",
    "血脈若繩，三結為環；環斷處唯餘燼與未燼之灰。",
    "守秘者曰：汝所見之字，非字，乃他界之餘燼投影。",
    "若遇「卍」形之影，勿誦其名；名出則契自焚。",
    "第五條隙文：監護之權，自落印瞬起，至月滿十二巡方得議解。",
    "下列空行供真名書寫；真名一成，餘文皆為贅語。",
    "⋄ 契主無面，受者有名；有名者負其重。",
    "凡誦此段者，已默認諸條，毋庸再誓。",
    "附錄：空白處若現墨痕，乃契紙自記，勿拭。",
    "第十一則殘簡：月蝕當夜，紙背會浮現另一套字，讀之則忘本約。",
    "◇◇ 此二符相連時，代表「暫緩」而非「作廢」。",
)


def _contract_visual_seed(name: str) -> int:
    """
    依姓名產生穩定種子（同一姓名在不同次啟動遊戲仍得相同斑駁與段落順序）。

    Args:
        name: 主角姓名。

    Returns:
        非負整數種子。
    """
    raw = hashlib.sha256((name.strip() or ".").encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") % (2**31)


def _blit_parchment_layer(canvas: pygame.Surface, paper: pygame.Rect, rng: random.Random) -> None:
    """
    在 `paper` 範圍內畫漸層羊皮紙底、斑點與邊緣舊化。

    Args:
        canvas: 目標畫布。
        paper: 紙張矩形（邏輯座標）。
        rng: 亂數產生器。
    """
    pw, ph = paper.w, paper.h
    layer = pygame.Surface((pw, ph))
    for yy in range(ph):
        t = yy / max(ph - 1, 1)
        c = (
            int(236 - t * 22 + rng.randint(-3, 3)),
            int(224 - t * 18 + rng.randint(-3, 3)),
            int(198 - t * 16 + rng.randint(-3, 3)),
        )
        c = tuple(max(0, min(255, x)) for x in c)
        pygame.draw.line(layer, c, (0, yy), (pw - 1, yy))
    for _ in range(480):
        x, y = rng.randint(1, pw - 2), rng.randint(1, ph - 2)
        d = rng.randint(-18, 18)
        b = layer.get_at((x, y))
        layer.set_at(
            (x, y),
            (
                max(0, min(255, b[0] + d)),
                max(0, min(255, b[1] + d)),
                max(0, min(255, b[2] + d)),
            ),
        )
    edge = pygame.Surface((pw, ph), pygame.SRCALPHA)
    for _ in range(24):
        side = rng.randint(0, 3)
        if side == 0:
            pygame.draw.rect(edge, (55, 42, 32, rng.randint(10, 35)), (0, 0, rng.randint(4, 14), ph))
        elif side == 1:
            pygame.draw.rect(
                edge,
                (55, 42, 32, rng.randint(10, 35)),
                (pw - rng.randint(4, 14), 0, rng.randint(4, 14), ph),
            )
        elif side == 2:
            pygame.draw.rect(edge, (55, 42, 32, rng.randint(10, 35)), (0, 0, pw, rng.randint(2, 10)))
        else:
            pygame.draw.rect(
                edge,
                (55, 42, 32, rng.randint(10, 35)),
                (0, ph - rng.randint(2, 10), pw, rng.randint(2, 10)),
            )
    layer.blit(edge, (0, 0))
    canvas.blit(layer, paper.topleft)


def _draw_contract_rune_block(
    canvas: pygame.Surface,
    paper: pygame.Rect,
    content_top: int,
    small_font: pygame.font.Font,
    bottom_reserve: int,
    rng: random.Random,
) -> None:
    """
    在紙張上方區域鋪滿換行後的偽契約文（色淡；字級與開場主文一致）。

    Args:
        canvas: 目標畫布。
        paper: 紙張矩形。
        content_top: 偽古文開始的 y（需低於標題列，避免重疊）。
        small_font: 內文字型（與 ``draw_contract_seal_screen`` 之 ``font`` 相同）。
        bottom_reserve: 底部保留給署名與印鑑的像素高度。
        rng: 決定段落順序。
    """
    inner_w = paper.w - _scale_x(20)
    y = content_top
    limit_y = paper.bottom - bottom_reserve
    frags = list(_CONTRACT_RUNE_LINES)
    rng.shuffle(frags)
    rune_col = (88, 78, 70)
    lh = small_font.get_height()
    for frag in frags:
        for line in wrap_cjk(small_font, frag, inner_w):
            if y + lh > limit_y:
                return
            canvas.blit(small_font.render(line, True, rune_col), (paper.x + _scale_x(10), y))
            y += lh + max(4, lh // 5)
        y += _scale_y(1) + 6


def _draw_seal_sigil_patterns(
    surf: pygame.Surface,
    ox: int,
    oy: int,
    side: int,
    rng: random.Random,
    st: float,
) -> None:
    """
    在印面矩形內繪製不可讀的幾何／折線符號（像古契約咒文拓印）。

    Args:
        surf: 帶 alpha 的印面 Surface。
        ox, oy: 印面左上角（於 surf 內座標）。
        side: 印邊長。
        rng: 亂數（已由姓名種子固定，畫面穩定）。
        st: 強度 0～1（線條透明度）。
    """
    if st <= 0:
        return
    a = max(40, int(200 * st))
    light = (255, 232, 216, min(255, a + 30))
    mid = (198, 95, 78, min(255, a))
    dark = (78, 22, 18, min(255, int(140 * st)))
    inset = max(3, side // 8)
    ix0, iy0 = ox + inset, oy + inset
    iw, ih = side - inset * 2, side - inset * 2
    # 內框與斜向刻痕
    pygame.draw.rect(surf, dark, (ix0, iy0, iw, ih), 1)
    for sgn in (-1, 1):
        pygame.draw.line(
            surf,
            mid,
            (ix0, iy0 + ih // 2 + sgn * 2),
            (ix0 + iw, iy0 + ih // 2 - sgn * 2),
            1,
        )
    # 折線符號（多段隨機路徑）
    for _ in range(4):
        x0 = ix0 + rng.randint(2, max(2, iw - 2))
        y0 = iy0 + rng.randint(2, max(2, ih - 2))
        pts: list[tuple[int, int]] = [(x0, y0)]
        for _ in range(rng.randint(3, 6)):
            pts.append(
                (
                    ix0 + rng.randint(2, max(2, iw - 2)),
                    iy0 + rng.randint(2, max(2, ih - 2)),
                )
            )
        if len(pts) >= 2:
            pygame.draw.lines(surf, light, False, pts, 1)
    # 小圓點與短劃（像不明文字筆畫）
    for _ in range(6):
        cx = ix0 + rng.randint(3, iw - 3)
        cy = iy0 + rng.randint(3, ih - 3)
        br = rng.randint(1, 2)
        pygame.draw.circle(surf, light, (cx, cy), br)
    for _ in range(5):
        x1 = ix0 + rng.randint(2, iw - 4)
        y1 = iy0 + rng.randint(2, ih - 4)
        ln = rng.randint(3, max(3, iw // 3))
        if rng.random() < 0.5:
            pygame.draw.line(surf, mid, (x1, y1), (x1 + ln, y1), 1)
        else:
            pygame.draw.line(surf, mid, (x1, y1), (x1, y1 + ln), 1)
    # 中央小菱形
    mx, my = ix0 + iw // 2, iy0 + ih // 2
    d = max(3, iw // 6)
    rh = [(mx, my - d), (mx + d, my), (mx, my + d), (mx - d, my)]
    pygame.draw.polygon(surf, mid, rh, 1)


def _draw_red_ink_seal_imprint(
    canvas: pygame.Surface,
    center_x: int,
    center_y: int,
    rng: random.Random,
    strength: float,
) -> None:
    """
    在紙上繪製方形紅印泥戳章（可漸強顯示），內為程序化偽符號、無可讀單字。

    Args:
        canvas: 目標畫布。
        center_x: 印面中心 x。
        center_y: 印面中心 y。
        rng: 肌理與符號形狀用種子亂數。
        strength: 0～1，控制不透明度與飽和度。
    """
    if strength <= 0:
        return
    st = max(0.0, min(1.0, strength))
    half = max(14, _scale_x(24))
    side = half * 2
    pad = 12
    surf = pygame.Surface((side + pad * 2, side + pad * 2), pygame.SRCALPHA)
    ox, oy = pad, pad
    base_a = int(230 * st)
    # 外緣暈染（印泥滲紙）
    for k in range(3):
        inflate = 6 - k * 2
        a = max(0, int((35 - k * 10) * st))
        pygame.draw.ellipse(
            surf,
            (200, 72, 58, a),
            (ox - inflate, oy - inflate, side + inflate * 2, side + inflate * 2),
        )
    # 印面主體：朱砂／朱泥感（暖橙紅、暗部褐紅，避免洋紅）
    inner = (168, 52, 42, base_a)
    pygame.draw.rect(surf, inner, (ox, oy, side, side))
    pygame.draw.rect(surf, (116, 36, 30, min(255, base_a + 25)), (ox, oy, side, side), 2)
    pygame.draw.rect(surf, (212, 98, 78, int(100 * st)), (ox + 2, oy + 2, side - 4, max(1, side // 5)))
    # 細碎肌理
    for _ in range(int(42 * st)):
        rx = ox + rng.randint(2, side - 3)
        ry = oy + rng.randint(2, side - 3)
        surf.set_at(
            (rx, ry),
            (
                rng.randint(155, 205),
                rng.randint(48, 88),
                rng.randint(30, 50),
                int(140 * st),
            ),
        )
    _draw_seal_sigil_patterns(surf, ox, oy, side, rng, st)
    blit_x = center_x - (side + pad * 2) // 2
    blit_y = center_y - (side + pad * 2) // 2
    canvas.blit(surf, (blit_x, blit_y))


def draw_contract_seal_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    signature_font: pygame.font.Font,
    heroine_name: str,
    anim_frame: int,
    seal_anim_finished: bool,
) -> None:
    """
    繪製古老契約紙、偽古文、署名、蓋印動畫；動畫結束後停格至玩家確認。

    Args:
        canvas: 邏輯畫布。
        font: 標題、偽古文區、真名標籤（與開場前言等主文同字級）。
        small_font: 僅畫布最底操作提示（Enter／Space）。
        signature_font: 真名手寫感署名（大字級、楷體系字型）。
        heroine_name: 已確認的主角姓名。
        anim_frame: 蓋印動畫影格（會夾在相位上限內換算印鑑位置）。
        seal_anim_finished: True 表示動畫已播畢，等待 Enter。
    """
    canvas.fill((22, 18, 16))
    # 單張契約紙：置中、寬高佔畫面主體，底部保留提示列
    _paper_side_mx = max(24, CANVAS_WIDTH // 22)
    _hint_band = small_font.get_height() + 26
    pw = CANVAS_WIDTH - 2 * _paper_side_mx
    ph = CANVAS_HEIGHT - 40 - _hint_band
    px = (CANVAS_WIDTH - pw) // 2
    py = 20 + max(0, (CANVAS_HEIGHT - _hint_band - ph) // 2 - 10)
    paper = pygame.Rect(px, py, pw, ph)

    seed = _contract_visual_seed(heroine_name)
    rng = random.Random(seed)
    _blit_parchment_layer(canvas, paper, rng)

    pygame.draw.rect(canvas, (62, 52, 44), paper, 2)
    pygame.draw.rect(canvas, (42, 36, 30), paper, 1)

    hdr = font.render("古式監護契書", True, (42, 34, 28))
    hdr_y = paper.y + _scale_y(8)
    canvas.blit(hdr, (paper.x + _scale_x(10), hdr_y))

    name_block_h = signature_font.get_height() + font.get_height() + _scale_y(6)
    rune_top = hdr_y + font.get_height() + _scale_y(12)
    _draw_contract_rune_block(
        canvas,
        paper,
        rune_top,
        font,
        bottom_reserve=name_block_h + _scale_y(14),
        rng=rng,
    )

    nm = heroine_name.strip()[:12] or "——"
    name_y = paper.bottom - name_block_h - _scale_y(8)
    lbl = font.render("受監護者之名：", True, (52, 44, 38))
    ns = signature_font.render(nm, True, (34, 28, 24))
    mr = _scale_x(28)
    # 與右側紅印保留距離（略緊以讓簽名更靠右，仍避開印面）
    seal_clearance = _scale_x(64)
    right_x = paper.right - mr - seal_clearance
    canvas.blit(lbl, (right_x - lbl.get_width(), name_y))
    canvas.blit(ns, (right_x - ns.get_width(), name_y + font.get_height() + 2))

    # 印面中心：紙張右側、垂直約中下（加大印面後略內縮避免裁切）
    seal_cx = paper.right - _scale_x(46)
    seal_cy = paper.y + int(paper.h * 0.68)
    stamp_w = _scale_x(58)
    stamp_h = _scale_y(24)
    contact_x0 = seal_cx - stamp_w // 2
    contact_y = seal_cy - stamp_h
    hover_y0 = max(4, paper.y - _scale_y(28))

    pf = min(anim_frame, _CONTRACT_SEAL_PHASE_MAX)
    # 印泥：章壓定瞬間即完整顯現（無漸變「繪製」感）
    imprint_strength = 1.0 if (seal_anim_finished or pf >= 38) else 0.0
    if imprint_strength > 0:
        _draw_red_ink_seal_imprint(canvas, seal_cx, seal_cy, rng, imprint_strength)

    # 木章本體：落下 → 加壓 → 向右上方移出畫面
    stamp_x0 = contact_x0
    stamp_y = contact_y
    show_stamp = True
    if pf < 26:
        t = pf / 25.0 if pf > 0 else 0.0
        stamp_y = int(hover_y0 + (contact_y - hover_y0) * min(1.0, t))
    elif pf < 38:
        stamp_y = contact_y + min(_scale_y(6), _scale_y(1) * (pf - 26))
    elif pf < 48:
        stamp_y = contact_y
    elif pf < 79:
        t = min(1.0, (pf - 48) / 30.0)
        stamp_x0 = int(contact_x0 + (CANVAS_WIDTH + stamp_w * 2) * t)
        stamp_y = int(contact_y - _scale_y(8) - _scale_y(36) * t)
    else:
        show_stamp = False

    if show_stamp:
        pygame.draw.rect(canvas, (64, 46, 40), (stamp_x0, stamp_y, stamp_w, stamp_h))
        pygame.draw.rect(canvas, (36, 26, 22), (stamp_x0, stamp_y, stamp_w, stamp_h), 1)
        knob_y = stamp_y - _scale_y(10)
        pygame.draw.rect(
            canvas,
            (82, 62, 54),
            (stamp_x0 + stamp_w // 2 - _scale_x(7), knob_y, _scale_x(14), _scale_y(10)),
        )

    # 底部提示：略靠下、小字、灰色；保留少量下緣避免裁切
    hint_base_y = CANVAS_HEIGHT - _scale_y(10) - small_font.get_height()
    if seal_anim_finished:
        line = "按下 Enter 繼續"
        hx = (CANVAS_WIDTH - small_font.size(line)[0]) // 2
        for dx, dy, col in ((1, 1, (125, 128, 136)), (0, 0, (210, 214, 224))):
            canvas.blit(small_font.render(line, True, col), (hx + dx, hint_base_y + dy))
    elif anim_frame < _CONTRACT_SEAL_ANIM_DONE_AT // 3:
        line = "Space 可快轉至蓋印結束"
        ht = small_font.render(line, True, (130, 134, 142))
        canvas.blit(ht, ((CANVAS_WIDTH - ht.get_width()) // 2, hint_base_y - _scale_y(2)))


def _draw_slot_choice_list(
    canvas: pygame.Surface,
    row_font: pygame.font.Font,
    mx: int,
    y: int,
    slot_cursor: int,
    *,
    hub_menu_style: bool = False,
) -> int:
    """
    繪製五格欄位列表：每格單行；「欄位 n」於固定寬欄內**左對齊**，姓名與「（空）」自
    ``row_text_left + slot_label_w + col_gap`` 起算；有進度時**名字（含「（男）／（女）」）**、
    **年紀**、**記錄時間**各占固定欄寬，欄內皆**靠左對齊**（過寬則單行截斷加「…」）。
    欄與欄之間僅留窄間距，並優先保留時間欄寬（對齊 ``save_slots`` 之本機日期時間字串）。
    標題選單（hub）時「▶／空白」與圖片畫廊相同自 ``mx`` 左緣起畫，其後預留 ``prefix_col_w``
    再接欄位標籤。

    Args:
        canvas: 畫布。
        row_font: 欄位列內文（與一般 UI 主字同級，較舊版小字更易讀）。
        mx: 左邊 x。
        y: 起始 y。
        slot_cursor: 目前游標 1～5。
        hub_menu_style: 為 True 時前綴「▶／空白」與選取色與「圖片畫廊／遊戲設定」選單列一致。

    Returns:
        列表繪製後下一個可用的 y。
    """
    row_gap = _scale_y(5) if hub_menu_style else _scale_y(6)
    row_h = row_font.get_height() + row_gap
    col_gap = _scale_x(6)
    pw_sel = row_font.size("▶ ")[0]
    pw_unsel = row_font.size("  ")[0]
    prefix_col_w = max(pw_sel, pw_unsel) if hub_menu_style else 0
    row_text_left = mx + prefix_col_w
    slot_label_w = max(
        row_font.size(f"欄位 {k}")[0] for k in range(1, SLOT_COUNT + 1)
    )
    x_name_col = row_text_left + slot_label_w + col_gap
    right_edge = CANVAS_WIDTH - mx - _scale_x(8)
    avail = max(1, right_edge - x_name_col)
    inner = max(1, avail - 2 * col_gap)
    time_need = row_font.size("2099-12-31 23:59:59")[0] + _scale_x(2)
    name_col_w = max(_scale_x(40), inner * 36 // 100)
    age_col_w = max(_scale_x(30), inner * 18 // 100)
    if name_col_w + age_col_w >= inner:
        name_col_w = inner * 54 // 100
        age_col_w = inner * 22 // 100
    when_col_w = max(0, inner - name_col_w - age_col_w)
    if when_col_w < time_need:
        deficit = time_need - when_col_w
        take_n = min(deficit, max(0, name_col_w - _scale_x(36)))
        name_col_w -= take_n
        deficit -= take_n
        if deficit > 0:
            take_a = min(deficit, max(0, age_col_w - _scale_x(26)))
            age_col_w -= take_a
            deficit -= take_a
        when_col_w = max(0, inner - name_col_w - age_col_w)
    x_age_col = x_name_col + name_col_w + col_gap
    x_when_col = x_age_col + age_col_w + col_gap

    for i in range(1, SLOT_COUNT + 1):
        summ = slot_summary(i, _GAME_USERDATA_ROOT)
        sel = i == slot_cursor
        if summ.get("empty"):
            if hub_menu_style:
                col = (155, 162, 178) if sel else (105, 112, 128)
            else:
                col = (150, 165, 185) if sel else (120, 130, 150)
        else:
            if hub_menu_style:
                col = (255, 230, 160) if sel else (190, 200, 220)
            else:
                col = (255, 238, 210) if sel else (205, 215, 230)

        if hub_menu_style:
            prefix = "▶ " if sel else "  "
            pr_surf = row_font.render(prefix, True, col)
            canvas.blit(pr_surf, (mx, y))

        label_s = row_font.render(f"欄位 {i}", True, col)
        label_x = row_text_left
        canvas.blit(label_s, (label_x, y))

        if summ.get("empty"):
            canvas.blit(row_font.render("（空）", True, col), (x_name_col, y))
            y += row_h
            continue

        nm = (summ.get("heroine_name") or "").strip() or "孩子"
        gender_zh = str(summ.get("gender_zh", "女"))
        tag_s = row_font.render(f"（{gender_zh}）", True, col)
        gap_nm_tag = _scale_x(2)
        age_p = str(summ.get("age_phrase", ""))
        when = str(summ.get("saved_at_local", ""))
        name_slot_w = max(1, name_col_w)
        tag_room = tag_s.get_width() + gap_nm_tag
        name_max = max(8, name_slot_w - tag_room)
        nm_fit = _fit_one_line_cjk(row_font, nm, name_max)
        nm_surf = row_font.render(nm_fit, True, col)
        canvas.blit(nm_surf, (x_name_col, y))
        canvas.blit(tag_s, (x_name_col + nm_surf.get_width() + gap_nm_tag, y))
        age_fit = _fit_one_line_cjk(row_font, age_p, max(8, age_col_w))
        when_fit = _fit_one_line_cjk(row_font, when, max(8, right_edge - x_when_col))
        canvas.blit(row_font.render(age_fit, True, col), (x_age_col, y))
        canvas.blit(row_font.render(when_fit, True, col), (x_when_col, y))
        y += row_h
    return y


def draw_save_slot_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    slot_cursor: int,
) -> None:
    """繪製儲存欄位選擇（遊玩中按 S 進入）。"""
    canvas.fill((20, 24, 32))
    mx = _scale_x(24)
    y = _scale_y(24)
    canvas.blit(font.render("選擇儲存欄位（↑↓ + Enter，Esc 取消）", True, (240, 236, 230)), (mx, y))
    y += font.get_height() + _scale_y(16)
    _draw_slot_choice_list(canvas, font, mx, y, slot_cursor)


def draw_slot_select_screen(
    canvas: pygame.Surface,
    menu_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    slot_cursor: int,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製讀檔欄位選擇（標題選單「讀取進度」）。

    版面與字級與「圖片畫廊」「遊戲設定」一致：星空底、左緣 ``_scale_x(20)``、標題色 (255,200,160)、
    欄位列用 ``menu_font``、頁尾說明用 ``hint_font`` 與 (130,138,155)。
    """
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)
    mx = _scale_x(20)
    tw = CANVAS_WIDTH - 2 * mx
    y = _scale_y(14)
    for line in wrap_cjk(menu_font, "讀取進度", tw):
        canvas.blit(menu_font.render(line, True, (255, 200, 160)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(10)
    hint_raw = "↑↓ 選擇　Enter 讀取　數字鍵 1～5 快捷　Esc 返回標題"
    hint_lines = wrap_cjk(hint_font, hint_raw, tw) or [hint_raw]
    lh_hint = hint_font.get_height()
    hint_gap = 2
    hint_h = len(hint_lines) * lh_hint + max(0, len(hint_lines) - 1) * hint_gap
    bottom_pad = _scale_y(8)
    _draw_slot_choice_list(
        canvas, menu_font, mx, y, slot_cursor, hub_menu_style=True
    )
    hy = CANVAS_HEIGHT - bottom_pad - hint_h
    for i, hl in enumerate(hint_lines):
        hs = hint_font.render(hl, True, (130, 138, 155))
        canvas.blit(hs, (mx, hy))
        hy += lh_hint + (hint_gap if i + 1 < len(hint_lines) else 0)


def draw_incident_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    event: IncidentEvent,
    option_index: int,
) -> None:
    """
    培養中突發事件：標題、內文、三選一（選中項以與培養格相同的亮色底與邊框標示；底列為操作說明）。

    Args:
        canvas: 邏輯畫布。
        font: 「突發事件」與事件標題列。
        small_font: 事件內文、三選一選項與底列操作提示。
        event: 目前事件。
        option_index: 選項游標 0～2。
    """
    canvas.fill((22, 26, 38))
    mx = _scale_x(20)
    y = _scale_y(18)
    illu_side = min(_scale_x(136), _scale_y(136))
    illu_gap = _scale_x(10)
    bottom_pad = _scale_y(16)
    hint_h = small_font.get_height()
    hint_gap = _scale_y(8)
    # 說明文字距畫布底較近（與插圖留白分開計算）。
    hint_bottom_pad = _scale_y(5)
    # 底列保留給操作說明，插圖上移避免與文字重疊或被誤認為遮擋。
    illu_y = CANVAS_HEIGHT - bottom_pad - illu_side - hint_h - hint_gap
    illu_x = CANVAS_WIDTH - mx - illu_side
    illu_rect = pygame.Rect(illu_x, illu_y, illu_side, illu_side)
    max_w = max(1, CANVAS_WIDTH - 2 * mx - illu_side - illu_gap)
    canvas.blit(font.render("突發事件", True, (255, 210, 175)), (mx, y))
    y += font.get_height() + _scale_y(6)
    canvas.blit(font.render(event.title, True, (245, 240, 230)), (mx, y))
    y += font.get_height() + _scale_y(10)
    for line in wrap_cjk(small_font, event.body, max_w):
        canvas.blit(small_font.render(line, True, (205, 212, 225)), (mx, y))
        y += small_font.get_height() + 2
    y += _scale_y(14)
    opt_gap = _scale_y(4)
    for i, opt in enumerate(event.options):
        label = f"{i + 1}. {opt.label}"
        y = _blit_event_style_choice_cell(
            canvas,
            mx,
            y,
            max_w,
            small_font,
            label,
            i == option_index,
            opt_gap_after=opt_gap,
        )
    draw_incident_illustration(canvas, illu_rect, event.id)
    hint = "【↑↓】選擇選項　【Enter】確認"
    hint_y = CANVAS_HEIGHT - hint_bottom_pad - hint_h
    canvas.blit(
        small_font.render(hint, True, (150, 162, 178)),
        (mx, hint_y),
    )


def draw_incident_aftermath_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    event: IncidentEvent,
    chosen_index: int,
    aftermath_page_index: int,
    stat_effect_full_line: str,
    _tick: int,
) -> None:
    """
    突發事件餘韻：上方放大事件插圖、標題式結語與段落（**單頁**；Enter 返回養成）。

    @param canvas - 邏輯畫布
    @param intro_font - 標題／餘韻正文
    @param small_font - 頁尾操作說明
    @param event - 目前突發事件
    @param chosen_index - 玩家已選選項 0～2
    @param aftermath_page_index - 保留 0（單頁；與繪製分頁索引簽名相容）
    @param stat_effect_full_line - 含「數值變化：」前綴之五維說明（第一頁頁尾 Enter 上方，比照培養回饋）
    @param _tick - 影格（與重大事件結語簽名一致，供日後插圖動效擴充）
    """
    canvas.fill((24, 28, 38))
    art_h = _resolution_art_h_aftermath_compact()
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_incident_illustration(canvas, art_rect, event.id)
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    text_limit_y_full, _ = _resolution_text_limit_y(small_font, max_w)

    pages = _incident_aftermath_paragraph_pages(
        event,
        chosen_index,
        intro_font,
        small_font,
        stat_bottom_line=stat_effect_full_line,
    )
    if not pages:
        pages = [()]
    pi = max(0, min(aftermath_page_index, len(pages) - 1))
    page_paras = pages[pi]
    nav_raw = (
        "【Enter】下一頁"
        if pi < len(pages) - 1
        else "【Enter】返回養成"
    )
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    footer_top = _aftermath_footer_top_for_nav_raw(small_font, max_w, nav_raw)
    para_limit_y = (
        _aftermath_narrative_bottom_y_page0_with_bottom_stat(
            small_font, intro_font, max_w, stat_effect_full_line
        )
        if pi == 0
        else text_limit_y_full
    )

    y = art_h + 8 * CANVAS_HEIGHT // _ORIG_H
    fh = intro_font.get_height()
    opt = event.options[chosen_index]
    hdr = f"餘韻　—　{opt.label}" if pi == 0 else "餘韻　（續）"
    for hl in wrap_cjk(intro_font, hdr, max_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(hl, True, (255, 214, 170)), (mx, y))
        y += fh + 2
    y += 4 * CANVAS_HEIGHT // _ORIG_H

    _pgap = _aftermath_para_gap_px()
    for para in page_paras:
        for L in wrap_cjk(intro_font, para, max_w):
            if y + fh > para_limit_y:
                break
            canvas.blit(intro_font.render(L, True, (230, 232, 240)), (mx, y))
            y += fh + 2
        y += _pgap

    if pi == 0 and stat_effect_full_line.strip():
        gap_stat_above_nav = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y)
        fh_stat = intro_font.get_height() + 2
        stat_lines = wrap_cjk(intro_font, stat_effect_full_line, max_w)
        stat_block_h = len(stat_lines) * fh_stat
        sy = footer_top - gap_stat_above_nav - stat_block_h
        for i, sl in enumerate(stat_lines):
            canvas.blit(
                intro_font.render(sl, True, _EVENT_AFTERMATH_STAT_COLOR_ON_DARK),
                (mx, sy + i * fh_stat),
            )

    fy = footer_top
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def _major_option_effect_line(opt: MajorEventOption) -> str:
    """
    重大事件選項的五維與隱藏增量說明（單行）。

    Args:
        opt: 選項。

    Returns:
        例如「智力+18  務實+12（真理探求+8）」。
    """
    base = format_major_deltas_brief(opt.deltas)
    ex = format_major_extra_brief(opt.extra_deltas)
    if ex:
        return f"{base}（{ex}）"
    return base


def draw_major_event_preamble_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    event: MajorEvent,
    tick: int,
) -> None:
    """
    重大事件前言：上方插圖、標題與背景敘述（插圖較開場略矮，段落間距較緊，以容納長篇內文）。

    Args:
        canvas: 邏輯畫布。
        intro_font: 標題／內文。
        small_font: 頁尾操作說明。
        event: 目前重大事件。
        tick: 影格。
    """
    canvas.fill((24, 28, 38))
    # 插圖低於開場前言比例，多留垂直空間；避免 8 歲等長篇前言底部被頁尾裁切
    art_h = min(200, max(104, int(CANVAS_HEIGHT * 0.32)))
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_major_event_illustration(
        canvas,
        art_rect,
        age_year=event.age_year,
        is_resolution=False,
        choice_index=0,
        tick=tick,
    )
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    nav_raw = "【Enter】繼續"
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    footer_top = CANVAS_HEIGHT - bottom_pad - nav_content_h
    text_limit_y = footer_top - 4 * CANVAS_HEIGHT // _ORIG_H

    y = art_h + 4 * CANVAS_HEIGHT // _ORIG_H
    fh = intro_font.get_height()
    for hl in wrap_cjk(intro_font, f"重大事件　{event.preamble_title}", max_w):
        if y + fh > text_limit_y:
            break
        canvas.blit(intro_font.render(hl, True, (255, 214, 170)), (mx, y))
        y += fh + 2
    y += 4 * CANVAS_HEIGHT // _ORIG_H

    for para in event.preamble_body:
        for L in wrap_cjk(intro_font, para, max_w):
            if y + fh > text_limit_y:
                break
            canvas.blit(intro_font.render(L, True, (230, 232, 240)), (mx, y))
            y += fh + 2
        y += 6 * CANVAS_HEIGHT // _ORIG_H

    fy = footer_top
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def draw_major_event_choice_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    event: MajorEvent,
    option_index: int,
    tick: int,
) -> None:
    """
    重大事件三選一：上方縮圖、標題、選項（僅文案；確認後數值於餘韻第一頁頁尾 Enter 上方「數值變化」列顯示）。

    Args:
        canvas: 邏輯畫布。
        font: 標題用。
        small_font: 內文與選項。
        event: 目前重大事件。
        option_index: 游標 0～2。
        tick: 影格。
    """
    canvas.fill((22, 26, 38))
    art_h = min(100, max(64, int(CANVAS_HEIGHT * 0.15)))
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_major_event_illustration(
        canvas,
        art_rect,
        age_year=event.age_year,
        is_resolution=False,
        choice_index=0,
        tick=tick,
    )
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    y = art_h + _scale_y(6)
    max_w = CANVAS_WIDTH - 2 * mx
    canvas.blit(font.render("重大事件", True, (255, 210, 175)), (mx, y))
    y += font.get_height() + _scale_y(2)
    for tl in wrap_cjk(font, event.title, max_w):
        canvas.blit(font.render(tl, True, (245, 240, 230)), (mx, y))
        y += font.get_height() + 2
    y += _scale_y(6)

    opt_gap = _scale_y(3)
    hint_h = small_font.get_height()
    hint_bottom_pad = _scale_y(5)
    hint_y = CANVAS_HEIGHT - hint_bottom_pad - hint_h

    for i, opt in enumerate(event.options):
        label = f"{i + 1}. {opt.label}"
        y = _blit_event_style_choice_cell(
            canvas,
            mx,
            y,
            max_w,
            small_font,
            label,
            i == option_index,
            opt_gap_after=opt_gap,
        )

    hint = "【↑↓】選擇選項　【Enter】確認所選"
    canvas.blit(
        small_font.render(hint, True, (150, 162, 178)),
        (mx, hint_y),
    )


def draw_major_event_resolution_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    event: MajorEvent,
    chosen_index: int,
    aftermath_page_index: int,
    stat_effect_full_line: str,
    tick: int,
) -> None:
    """
    重大事件結語：依選項顯示插圖、世界影響敘述，以及頁尾 Enter 上方之「數值變化」（**單頁**；Enter 返回養成）。

    Args:
        canvas: 邏輯畫布。
        intro_font: 正文。
        small_font: 頁尾。
        event: 目前重大事件。
        chosen_index: 已選選項 0～2。
        aftermath_page_index: 保留 0（單頁；與繪製分頁索引簽名相容）。
        stat_effect_full_line: 含「數值變化：」前綴之五維與隱藏增量說明（頁尾 Enter 上方）。
        tick: 影格。
    """
    canvas.fill((24, 28, 38))
    art_h = _resolution_art_h_aftermath_compact()
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    draw_major_event_illustration(
        canvas,
        art_rect,
        age_year=event.age_year,
        is_resolution=True,
        choice_index=chosen_index,
        tick=tick,
    )
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    text_limit_y_full, _ = _resolution_text_limit_y(small_font, max_w)

    pages = _major_resolution_paragraph_pages(
        event,
        chosen_index,
        intro_font,
        small_font,
        stat_bottom_line=stat_effect_full_line,
    )
    if not pages:
        pages = [()]
    pi = max(0, min(aftermath_page_index, len(pages) - 1))
    page_paras = pages[pi]
    nav_raw = (
        "【Enter】下一頁"
        if pi < len(pages) - 1
        else "【Enter】返回養成"
    )
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    footer_top = _aftermath_footer_top_for_nav_raw(small_font, max_w, nav_raw)
    para_limit_y = (
        _aftermath_narrative_bottom_y_page0_with_bottom_stat(
            small_font, intro_font, max_w, stat_effect_full_line
        )
        if pi == 0
        else text_limit_y_full
    )

    y = art_h + 8 * CANVAS_HEIGHT // _ORIG_H
    fh = intro_font.get_height()
    hdr = f"餘韻　—　{event.options[chosen_index].label}" if pi == 0 else "餘韻　（續）"
    for hl in wrap_cjk(intro_font, hdr, max_w):
        if y + fh > para_limit_y:
            break
        canvas.blit(intro_font.render(hl, True, (255, 214, 170)), (mx, y))
        y += fh + 2
    y += 4 * CANVAS_HEIGHT // _ORIG_H

    _pgap_m = _aftermath_para_gap_px()
    for para in page_paras:
        for L in wrap_cjk(intro_font, para, max_w):
            if y + fh > para_limit_y:
                break
            canvas.blit(intro_font.render(L, True, (230, 232, 240)), (mx, y))
            y += fh + 2
        y += _pgap_m

    if pi == 0 and stat_effect_full_line.strip():
        gap_stat_above_nav = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y)
        fh_stat = intro_font.get_height() + 2
        stat_lines = wrap_cjk(intro_font, stat_effect_full_line, max_w)
        stat_block_h = len(stat_lines) * fh_stat
        sy = footer_top - gap_stat_above_nav - stat_block_h
        for i, sl in enumerate(stat_lines):
            canvas.blit(
                intro_font.render(sl, True, _EVENT_AFTERMATH_STAT_COLOR_ON_DARK),
                (mx, sy + i * fh_stat),
            )

    fy = footer_top
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def _play_stats_table_min_body_h(small_font: pygame.font.Font) -> int:
    """
    左欄五維表本體（表頭列＋五筆數值）所需之最小高度。

    Args:
        small_font: 狀態表用字型。

    Returns:
        像素高度（含上下微邊距）。
    """
    return _scale_y(6) + 6 * small_font.get_height()


def _draw_play_stats_table(
    canvas: pygame.Surface,
    rect: pygame.Rect,
    state: GameState,
    small_font: pygame.font.Font,
) -> None:
    """
    左欄五維表格。

    空間不足時縮小列高，仍會畫滿五維（含「務實」）；文字於列內垂直置中。

    Args:
        canvas: 畫布。
        rect: 表格矩形（須落在左欄面板內）。
        state: 遊戲狀態。
        small_font: 小字。
    """
    pad_i = _scale_x(8)
    pad_t = _scale_y(3)
    pad_b = _scale_y(3)
    inner_h = max(1, rect.height - pad_t - pad_b)
    n_bands = 6
    row_h = max(1, inner_h // n_bands)
    fh = small_font.get_height()

    def _ty(y0: int) -> int:
        return y0 + max(0, (row_h - fh) // 2)

    y = rect.y + pad_t
    c_hdr = (175, 182, 200)
    canvas.blit(
        small_font.render("項目", True, c_hdr), (rect.x + pad_i, _ty(y))
    )
    nh = small_font.render("數值", True, c_hdr)
    canvas.blit(nh, (rect.right - pad_i - nh.get_width(), _ty(y)))
    y += row_h
    pygame.draw.line(
        canvas, (68, 76, 94), (rect.x + 4, y - 1), (rect.right - 4, y - 1), 1
    )
    rows: list[tuple[str, int, tuple[int, int, int]]] = [
        ("智力", state.int_stat, (200, 220, 255)),
        ("力量", state.str_stat, (255, 200, 200)),
        ("社交", state.social, (200, 230, 255)),
        ("信仰", state.fth_stat, (220, 255, 200)),
        ("務實", state.pragmatic, (190, 205, 220)),
    ]
    for label, val, col in rows:
        canvas.blit(
            small_font.render(label, True, col), (rect.x + pad_i, _ty(y))
        )
        vs = small_font.render(str(val), True, col)
        canvas.blit(vs, (rect.right - pad_i - vs.get_width(), _ty(y)))
        y += row_h
        pygame.draw.line(
            canvas, (44, 50, 64), (rect.x + 6, y - 1), (rect.right - 6, y - 1), 1
        )


def draw_ending_narrative_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    ending: Ending,
    narrative_index: int,
    tick: int,
    *,
    from_gallery: bool = False,
) -> None:
    """
    結局敘事頁（版面近似開場前言：上緣插圖、標題、內文；與結局 CG 併為多頁，以左右鍵切換）。

    Args:
        canvas: 邏輯畫布。
        intro_font: 標題／正文。
        small_font: 頁尾說明。
        ending: 結局資料。
        narrative_index: 對應 ``narrative_pages`` 之索引（若越界則夾在合法範圍內）。
        tick: 影格（插圖動效）。
        from_gallery: 若 True，頁尾改為返回畫廊之說明。
    """
    canvas.fill((24, 28, 38))
    art_h = min(230, max(120, int(CANVAS_HEIGHT * _INTRO_ART_HEIGHT_RATIO)))
    art_rect = pygame.Rect(0, 0, CANVAS_WIDTH, art_h)
    n_narr = len(ending.narrative_pages)
    ni = max(0, min(narrative_index, n_narr - 1)) if n_narr > 0 else 0
    draw_prologue_illustration(canvas, art_rect, ni, tick)
    pygame.draw.line(canvas, (70, 76, 92), (0, art_h), (CANVAS_WIDTH, art_h), 2)

    mx = _scale_x(20)
    max_w = CANVAS_WIDTH - 2 * mx - _TEXT_PAD_X
    nav_raw = (
        "【←／→】切換頁面　【Enter】返回畫廊"
        if from_gallery
        else "【←／→】切換頁面"
    )
    nav_lines = wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    bottom_pad = 8 * CANVAS_HEIGHT // _ORIG_H
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    footer_top = CANVAS_HEIGHT - bottom_pad - nav_content_h
    text_limit_y = footer_top - 8 * CANVAS_HEIGHT // _ORIG_H

    y = art_h + 8 * CANVAS_HEIGHT // _ORIG_H
    fh = intro_font.get_height()
    hdr = f"結局敘事　{ending.name}"
    for hl in wrap_cjk(intro_font, hdr, max_w):
        if y + fh > text_limit_y:
            break
        canvas.blit(intro_font.render(hl, True, (255, 214, 170)), (mx, y))
        y += fh + 2
    y += 4 * CANVAS_HEIGHT // _ORIG_H

    body = ending.narrative_pages[ni]
    for L in wrap_cjk(intro_font, body, max_w):
        if y + fh > text_limit_y:
            break
        canvas.blit(intro_font.render(L, True, (230, 232, 240)), (mx, y))
        y += fh + 2

    fy = footer_top
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)


def draw_ending_cg_screen(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    ending: Ending,
    state: GameState,
    tick: int,
    *,
    from_gallery: bool = False,
) -> None:
    """
    結局 CG 全畫面（第三頁）：CG／立繪佔絕大多數高度；底部僅留窄條放稱號、一句餘韻與操作說明。

    Args:
        canvas: 邏輯畫布。
        font: 未使用（保留簽名與呼叫端一致）。
        small_font: 底部文字列與提示。
        ending: 結局資料。
        state: 遊戲狀態（主角名）。
        tick: 影格。
        from_gallery: 若 True，Enter 提示改為返回畫廊。
    """
    _ = tick
    _ = font
    canvas.fill((22, 26, 34))
    display_name = (state.heroine_name or "").strip() or "……"
    mx, max_w, lh_s, _, cg_rect, bar, pad_top, pad_bt = _gallery_fullscreen_layout(
        small_font
    )
    hint_raw = (
        "【←／→】切換頁面　【Enter】返回畫廊"
        if from_gallery
        else "【←／→】切換頁面　【Enter】返回標題"
    )
    tw = max(1, cg_rect.w)
    th = max(1, cg_rect.h)
    cg_surf = _get_scaled_ending_cg_fill(ending.cg_path, tw, th)
    if cg_surf is not None:
        pygame.draw.rect(canvas, (32, 38, 50), cg_rect)
        canvas.blit(cg_surf, (cg_rect.x, cg_rect.y))
        bw = max(2, cg_rect.h // 200)
        pygame.draw.rect(canvas, (200, 175, 210), cg_rect, width=bw)
    else:
        inner = cg_rect.inflate(-_scale_x(8), -_scale_y(8))
        draw_heroine_portrait(canvas, inner, state, tick)

    pygame.draw.rect(canvas, (26, 30, 40), bar)
    pygame.draw.line(canvas, (72, 82, 102), (0, bar.y), (CANVAS_WIDTH, bar.y), 2)
    _gallery_fullscreen_draw_footer(
        canvas,
        small_font,
        bar,
        mx,
        max_w,
        lh_s,
        pad_top,
        pad_bt,
        line1=f"{display_name}　{ending.name} — {ending.title}",
        line2=ending.quote,
        hint_text=hint_raw,
    )


def draw_playing_hud(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    state: GameState,
    tick: int,
    training_menu_index: int,
) -> None:
    """
    遊玩畫面：左欄、立繪／結局 CG、底部列（外緣預設貼齊邏輯畫布，見 `_PLAY_HUD_*` 常數）。
    狀態列與立繪底標為「姓名　男／女　年齡　階段」。

    Args:
        canvas: 邏輯畫布。
        font: UI 字。
        small_font: 小字。
        state: 狀態。
        tick: 影格。
        training_menu_index: 底部培養選單游標（0～7）。
    """
    canvas.fill((22, 26, 34))
    px = _scale_x(_PLAY_HUD_EDGE_PAD_LOGICAL_X)
    py = _scale_y(_PLAY_HUD_EDGE_PAD_LOGICAL_Y)
    gap = _scale_x(_PLAY_HUD_STATS_PORTRAIT_GAP_LOGICAL_X)
    lh = font.get_height() + 3
    lh_s = small_font.get_height() + 2

    min_portrait_w = (CANVAS_WIDTH * _PLAY_PORTRAIT_MIN_FRAC_NUM) // _PLAY_PORTRAIT_MIN_FRAC_DEN
    stats_w = min(
        _PLAY_STATS_PANEL_MAX_W, CANVAS_WIDTH - 2 * px - gap - min_portrait_w
    )
    stats_w = max(stats_w, _scale_x(72))
    portrait_w = CANVAS_WIDTH - 2 * px - gap - stats_w
    if portrait_w < min_portrait_w:
        portrait_w = min_portrait_w
        stats_w = max(CANVAS_WIDTH - 2 * px - gap - portrait_w, _scale_x(72))

    # 培養中底部略增，保留最底註釋列；結局等仍用較矮列
    action_h = (
        _PLAY_ACTION_BAR_TRAINING_H if state.time_left > 0 else _PLAY_ACTION_BAR_H
    )
    bar_y = CANVAS_HEIGHT - action_h - py
    action_top = bar_y - _PLAY_BAR_TOP_SPACER
    main_h = max(_scale_y(40), action_top - py)

    stats_rect = pygame.Rect(px, py, stats_w, main_h)
    portrait_rect = pygame.Rect(stats_rect.right + gap, py, portrait_w, main_h)

    pygame.draw.rect(canvas, (28, 33, 44), stats_rect)
    pygame.draw.rect(canvas, (88, 98, 124), stats_rect, width=2)
    pygame.draw.rect(canvas, (40, 46, 60), stats_rect.inflate(-4, -4), width=1)

    hx = stats_rect.x + _scale_x(4)
    hy = stats_rect.y + _scale_y(6)
    stats_inner_w = stats_rect.w - _scale_x(8)

    am = state.age_months
    ay = am // 12
    mo = am % 12
    display_name = (state.heroine_name or "").strip() or "……"
    _pg = getattr(state, "protagonist_gender", "female")
    phase_cn = _play_phase_display_zh(state.phase, _pg)
    gender_cn = "男" if _pg == "male" else "女"
    name_age_phase = f"{display_name}　{gender_cn}　{ay} 歲 {mo} 個月　{phase_cn}"

    header_lines: list[tuple[str, tuple[int, int, int]]] = []
    for text, col in (("狀態", (200, 190, 220)), (name_age_phase, (255, 228, 210))):
        for L in wrap_cjk(small_font, text, stats_inner_w):
            header_lines.append((L, col))
    min_body = _play_stats_table_min_body_h(small_font)
    ideal_table_top = stats_rect.y + len(header_lines) * lh_s + _scale_y(8)
    max_table_top = stats_rect.bottom - min_body - 8
    max_table_top = max(max_table_top, stats_rect.y + _scale_y(8))
    table_top = max(stats_rect.y + _scale_y(8), min(ideal_table_top, max_table_top))

    for L, col in header_lines:
        if hy + lh_s > table_top - _scale_y(2):
            break
        canvas.blit(small_font.render(L, True, col), (hx, hy))
        hy += lh_s

    table_body_h = max(1, stats_rect.bottom - table_top - 8)
    table_rect = pygame.Rect(
        stats_rect.x + 4,
        table_top,
        stats_rect.w - 8,
        table_body_h,
    )
    pygame.draw.rect(canvas, (30, 35, 46), table_rect)
    pygame.draw.rect(canvas, (82, 92, 112), table_rect, width=1)
    _draw_play_stats_table(canvas, table_rect, state, small_font)

    draw_heroine_portrait(canvas, portrait_rect, state, tick)

    cap_lines = wrap_cjk(small_font, name_age_phase, portrait_rect.w - _scale_x(8))
    lh_cap = small_font.get_height() + 2
    label_h = len(cap_lines) * lh_cap + _scale_y(10)
    band = pygame.Surface((portrait_rect.w, label_h), pygame.SRCALPHA)
    band.fill((16, 20, 28, 210))
    canvas.blit(band, (portrait_rect.x, portrait_rect.bottom - label_h))
    cap_y = portrait_rect.bottom - label_h + _scale_y(4)
    for nl in cap_lines:
        canvas.blit(
            small_font.render(nl, True, (255, 230, 210)),
            (portrait_rect.x + _scale_x(6), cap_y),
        )
        cap_y += lh_cap

    bar_rect = pygame.Rect(px, bar_y, CANVAS_WIDTH - 2 * px, action_h)
    pygame.draw.rect(canvas, (26, 30, 40), bar_rect)
    pygame.draw.rect(canvas, (72, 82, 102), bar_rect, width=2)

    bx = bar_rect.x + _scale_x(6)
    by = bar_rect.y + _scale_y(6)
    bar_max_w = bar_rect.w - _scale_x(12)

    if state.time_left > 0:
        n_act = len(TRAINING_ACTIONS)
        cur = max(0, min(n_act - 1, training_menu_index))
        footer_font = _get_play_footer_font()
        lh_f = footer_font.get_height() + 1
        lh_e = lh_f
        bar_ipad = _scale_x(6)
        inner_w = max(1, bar_rect.w - 2 * bar_ipad)
        btn_col_gap = _scale_x(6)
        btn_cell_w = max(_scale_x(36), (inner_w - 3 * btn_col_gap) // 4)
        footer_one = _fit_one_line_cjk(
            footer_font,
            "【↑↓←→】選擇培養　【Enter】確認所選培養並結算本季（扣 1 季）　【S】選擇欄位儲存　【Esc】返回標題",
            bar_max_w,
        )
        grid_top = bar_rect.y + _scale_y(5)
        bottom_pad = _scale_y(1)
        hint_y = bar_rect.bottom - bottom_pad - footer_font.get_height()
        gap_above_footer = _scale_y(2)
        avail_grid_h = hint_y - gap_above_footer - grid_top
        avail_grid_h = max(_scale_y(20), avail_grid_h)
        btn_row_gap = _scale_y(3)
        btn_cell_h = max(1, (avail_grid_h - btn_row_gap) // 2)
        txt_pad = _scale_x(4)
        max_tw = max(20, btn_cell_w - 2 * txt_pad)
        for idx, act in enumerate(TRAINING_ACTIONS):
            row = idx // 4
            col = idx % 4
            cx0 = bar_rect.x + bar_ipad + col * (btn_cell_w + btn_col_gap)
            cy0 = grid_top + row * (btn_cell_h + btn_row_gap)
            cell = pygame.Rect(cx0, cy0, btn_cell_w, btn_cell_h)
            sel = idx == cur
            fill = (58, 74, 102) if sel else (36, 40, 52)
            border = (140, 165, 205) if sel else (70, 78, 96)
            bw = 2 if sel else 1
            rad = max(3, min(btn_cell_h // 8, btn_cell_w // 8))
            pygame.draw.rect(canvas, fill, cell, border_radius=rad)
            pygame.draw.rect(canvas, border, cell, width=bw, border_radius=rad)
            title_one = _fit_one_line_cjk(small_font, act.title, max_tw)
            effect_one = _fit_one_line_cjk(
                footer_font, format_action_stat_effects_line(act), max_tw
            )
            total_th = lh_s + lh_e
            ty0 = cy0 + max(txt_pad, (btn_cell_h - total_th) // 2)
            title_col = (248, 250, 255) if sel else (210, 216, 228)
            effect_col = (190, 210, 235) if sel else (145, 162, 182)
            ty = ty0
            ts = small_font.render(title_one, True, title_col)
            canvas.blit(ts, (cx0 + (btn_cell_w - ts.get_width()) // 2, ty))
            ty += lh_s
            es = footer_font.render(effect_one, True, effect_col)
            canvas.blit(es, (cx0 + (btn_cell_w - es.get_width()) // 2, ty))
        foot_col = (150, 162, 178)
        canvas.blit(footer_font.render(footer_one, True, foot_col), (bx, hint_y))
    else:
        done_hint = "養成時程已結束——即將進入結局敘事。"
        for L in wrap_cjk(small_font, done_hint, bar_max_w):
            canvas.blit(small_font.render(L, True, (180, 188, 205)), (bx, by))
            by += lh_s


def draw_toast(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    message: str,
    *,
    centered: bool = False,
) -> None:
    """短提示（預設下方；`centered=True` 時顯示於中央）。"""
    if not message:
        return
    if centered:
        pad_x = _scale_x(22)
        pad_y = _scale_y(18)
        max_tw = max(_scale_x(280), CANVAS_WIDTH * 3 // 5)
        line_gap = 8
    else:
        pad_x = _scale_x(10)
        pad_y = _scale_y(6)
        max_tw = CANVAS_WIDTH - _scale_x(32) - _TEXT_PAD_X
        line_gap = 4
    lines = wrap_cjk(font, message, max_tw)
    line_h = font.get_height() + line_gap
    total_h = len(lines) * line_h
    max_line_w = max((font.size(L)[0] for L in lines), default=0)
    bx0 = (CANVAS_WIDTH - max_line_w) // 2
    by = (
        (CANVAS_HEIGHT - total_h) // 2
        if centered
        else CANVAS_HEIGHT - _scale_y(20) - total_h
    )
    bg = pygame.Surface((max_line_w + pad_x * 2, total_h + pad_y), pygame.SRCALPHA)
    bg.fill((255, 248, 220, 230))
    canvas.blit(bg, (bx0 - pad_x, by - pad_y // 2))
    cy = by
    for L in lines:
        surf = font.render(L, True, (40, 36, 30))
        canvas.blit(surf, ((CANVAS_WIDTH - surf.get_width()) // 2, cy))
        cy += line_h


def _split_training_feedback_body(body: str) -> tuple[str, str]:
    """
    將括號前內文拆成「行動名：」與敘事，便於左欄分層著色與縮排。

    Args:
        body: 全形 ``（`` 之前的字串。

    Returns:
        ``(action_lead, narrative)``。若無 ``：`` 或冒號後為空，則 ``action_lead`` 為空字串、
        ``narrative`` 為整段 ``body``（去首尾空白）。
    """
    idx = body.find("：")
    if idx <= 0:
        return "", body.strip()
    lead = body[: idx + 1].strip()
    narrative = body[idx + 1 :].strip()
    if not narrative:
        return "", body.strip()
    return lead, narrative


def draw_training_feedback_modal(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    message: str,
    action_key: int,
    now_ms: int,
    gender_key: str,
) -> None:
    """
    培養結算畫面（**顯示規格**；換圖不需改此函式，除非要改版面）。

    **字串**：須為 ``format_training_feedback_modal_message`` 產生之格式；以最後一組全形
    ``（…）`` 拆出數值列，顯示時加上 ``_TRAINING_FEEDBACK_MODAL_STAT_PREFIX``。

    **繪製順序（下→上）**：
        1. 全寬米色底框（內容區高 = 圖高 + 2×垂直 inset；圖距右緣可另用較小 inset 略靠右）
        2. 左欄文字（標題 → 行動引導「◯◯：」→ 縮排敘事 → 數值 → Enter 說明；段落間距見常數；寬度預留右側插圖）
        3. 右側前景插圖（固定 ``_TRAINING_FEEDBACK_MODAL_FX_LOGICAL_*`` 矩形內 ``contain``）

    Args:
        canvas: 邏輯畫布。
        font: 標題與內文（建議與遊玩畫面 ``small_font``／``_make_small_font`` 同級）。
        small_font: 底部 Enter 提示（建議 ``_get_play_footer_font``，與培養列底註同級）。
        message: 完整回饋字串。
        action_key: 培養 1～8。
        now_ms: 毫秒時間（向量圖示動態用）。
        gender_key: 主角性別。
    """
    if not message:
        return
    body = message
    stat_line = ""
    lpar = message.rfind("（")
    rpar = message.rfind("）")
    if 0 <= lpar < rpar:
        body = message[:lpar].strip()
        stat_line = message[lpar + 1 : rpar].strip()

    inner_pad_l = _scale_x(_TRAINING_FEEDBACK_MODAL_INNER_PAD_LEFT_LOGICAL_X)
    inner_pad_r = _scale_x(_TRAINING_FEEDBACK_MODAL_INNER_PAD_RIGHT_LOGICAL_X)
    inner_pad_y = _scale_y(_TRAINING_FEEDBACK_MODAL_INNER_PAD_LOGICAL_Y)
    panel_w = CANVAS_WIDTH
    content_w = max(1, panel_w - inner_pad_l - inner_pad_r)

    fx_w = _scale_x(_TRAINING_FEEDBACK_MODAL_FX_LOGICAL_W)
    fx_h = _scale_y(_TRAINING_FEEDBACK_MODAL_FX_LOGICAL_H)
    fx_inset_y = _scale_x(_TRAINING_FEEDBACK_MODAL_FX_INSET_LOGICAL_X)
    fx_inset_r = _scale_x(_TRAINING_FEEDBACK_MODAL_FX_INSET_RIGHT_LOGICAL_X)
    panel_inner_h = fx_h + 2 * fx_inset_y
    panel_h = panel_inner_h + 2 * inner_pad_y
    px = 0
    py = (CANVAS_HEIGHT - panel_h) // 2

    text_fx_gap = _scale_x(_TRAINING_FEEDBACK_MODAL_TEXT_FX_GAP_LOGICAL_X)
    text_col_cap = _scale_x(_TRAINING_FEEDBACK_MODAL_TEXT_COL_LOGICAL_W)
    text_col_w = max(
        1,
        min(
            text_col_cap,
            content_w - fx_inset_r - fx_w - text_fx_gap,
        ),
    )

    line_gap = _scale_y(_TRAINING_FEEDBACK_MODAL_LINE_GAP_LOGICAL_Y)
    lh = font.get_height() + line_gap
    stat_line_gap = _scale_y(_TRAINING_FEEDBACK_MODAL_STAT_LINE_GAP_LOGICAL_Y)

    action_lead, narrative = _split_training_feedback_body(body)
    body_indent_px = (
        _scale_x(_TRAINING_FEEDBACK_MODAL_TEXT_BODY_INDENT_LOGICAL_X)
        if action_lead
        else 0
    )
    body_wrap_w = max(1, text_col_w - body_indent_px) if action_lead else text_col_w
    body_lines = wrap_cjk(
        font,
        narrative if action_lead else body.strip(),
        body_wrap_w,
    )
    body_tx = px + inner_pad_l + body_indent_px

    shell = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    shell.fill(_TRAINING_FEEDBACK_MODAL_SHELL_FILL)
    pygame.draw.rect(
        shell,
        _TRAINING_FEEDBACK_MODAL_SHELL_STROKE,
        shell.get_rect(),
        width=3,
        border_radius=16,
    )
    pygame.draw.rect(
        shell,
        _TRAINING_FEEDBACK_MODAL_SHELL_INNER_GLOW,
        shell.get_rect().inflate(-10, -10),
        width=1,
        border_radius=12,
    )
    canvas.blit(shell, (px, py))

    text_clip = pygame.Rect(px + inner_pad_l, py + inner_pad_y, text_col_w, panel_inner_h)
    prev_clip = canvas.get_clip()
    canvas.set_clip(prev_clip.clip(text_clip))
    try:
        tx = px + inner_pad_l
        ty = py + inner_pad_y
        canvas.blit(
            font.render(_TRAINING_FEEDBACK_MODAL_HEADER, True, _TRAINING_FEEDBACK_MODAL_COLOR_HEADER),
            (tx, ty),
        )
        ty += font.get_height() + _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_AFTER_HEADER_LOGICAL_Y)
        if action_lead:
            gap_after_lead = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_AFTER_ACTION_LEAD_LOGICAL_Y)
            lead_lines = wrap_cjk(font, action_lead, text_col_w)
            for i, ll in enumerate(lead_lines):
                canvas.blit(
                    font.render(ll, True, _TRAINING_FEEDBACK_MODAL_COLOR_ACTION_LEAD),
                    (tx, ty),
                )
                ty += font.get_height()
                if i + 1 < len(lead_lines):
                    ty += line_gap
            ty += gap_after_lead
        for line in body_lines:
            surf = font.render(line, True, _TRAINING_FEEDBACK_MODAL_COLOR_BODY)
            canvas.blit(surf, (body_tx, ty))
            ty += lh
        if stat_line:
            ty += _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_STAT_LOGICAL_Y)
            stat_full = _TRAINING_FEEDBACK_MODAL_STAT_PREFIX + stat_line
            stat_lines = wrap_cjk(font, stat_full, text_col_w)
            for si, sline in enumerate(stat_lines):
                canvas.blit(
                    font.render(sline, True, _TRAINING_FEEDBACK_MODAL_COLOR_STAT),
                    (tx, ty),
                )
                ty += font.get_height()
                if si < len(stat_lines) - 1:
                    ty += stat_line_gap
        gap_before_hint = _scale_y(_TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y)
        hint_bottom_inset = _scale_y(_TRAINING_FEEDBACK_MODAL_HINT_BOTTOM_INSET_LOGICAL_Y)
        hint_surf = small_font.render(
            _TRAINING_FEEDBACK_MODAL_HINT,
            True,
            _TRAINING_FEEDBACK_MODAL_COLOR_HINT,
        )
        hint_h = hint_surf.get_height()
        inner_bottom = py + inner_pad_y + panel_inner_h
        desired_hint_ty = inner_bottom - hint_bottom_inset - hint_h
        if ty + gap_before_hint <= desired_hint_ty:
            ty = desired_hint_ty
        else:
            ty += gap_before_hint
        canvas.blit(hint_surf, (tx, ty))
    finally:
        canvas.set_clip(prev_clip)

    # 前景插圖：上／下距離 ``fx_inset_y``；距內容區右緣 ``fx_inset_r``（右緣 = 左內距 + content_w）。
    content_right = px + inner_pad_l + content_w
    fx_x = max(0, content_right - fx_inset_r - fx_w)
    inner_top = py + inner_pad_y
    fx_y = inner_top + fx_inset_y
    draw_training_feedback_fx_into_rect(
        canvas,
        pygame.Rect(fx_x, fx_y, fx_w, fx_h),
        action_key,
        now_ms,
        gender_key=gender_key,
        image_fit="contain",
        image_margin=0,
    )


def draw_training_feedback_overlay(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    message: str,
    action_key: int,
    now_ms: int,
    *,
    gender_key: str = "female",
) -> None:
    """
    培養結算回饋：尺寸與位置對齊底部 8 項培養選單區（左文右插圖）。
    """
    if not message:
        return

    # 與 draw_playing_hud 的底部培養列採同一幾何，讓回饋「剛好蓋住」8 選項區。
    px = _scale_x(_PLAY_HUD_EDGE_PAD_LOGICAL_X)
    py = _scale_y(_PLAY_HUD_EDGE_PAD_LOGICAL_Y)
    action_h = _PLAY_ACTION_BAR_TRAINING_H
    bar_y = CANVAS_HEIGHT - action_h - py
    band = pygame.Rect(px, bar_y, CANVAS_WIDTH - 2 * px, action_h)

    panel = pygame.Surface((band.w, band.h), pygame.SRCALPHA)
    panel.fill((255, 248, 220, 245))
    pygame.draw.rect(panel, (96, 104, 124), panel.get_rect(), width=2)
    canvas.blit(panel, band.topleft)

    # 右側正方形插圖區（與獨立回饋面板同級，至少約兩倍於舊版）
    pad_x = _scale_x(22)
    pad_y = _scale_y(20)
    fx_side = max(_scale_y(176), min(band.h - pad_y * 2, band.w * 2 // 5))
    fx_rect = pygame.Rect(
        band.right - pad_x - fx_side,
        band.y + (band.h - fx_side) // 2,
        fx_side,
        fx_side,
    )
    draw_training_feedback_fx(canvas, action_key, now_ms, fx_rect, gender_key=gender_key)

    # 左側文字區（靠左，但整塊位於畫面中段）
    tx = band.x + pad_x
    tw = max(_scale_x(220), fx_rect.x - tx - _scale_x(18))
    ty = band.y + pad_y
    header = "本季培養回饋"
    hs = font.render(header, True, (52, 56, 70))
    canvas.blit(hs, (tx, ty))
    ty += font.get_height() + _scale_y(8)

    body = message
    stat_line = ""
    lpar = message.rfind("（")
    rpar = message.rfind("）")
    if 0 <= lpar < rpar:
        body = message[:lpar].strip()
        stat_line = message[lpar + 1 : rpar].strip()

    body_lines = wrap_cjk(font, body, tw)[:3]
    for line in body_lines:
        surf = font.render(line, True, (36, 38, 48))
        canvas.blit(surf, (tx, ty))
        ty += font.get_height() + _scale_y(2)

    if stat_line:
        ty += _scale_y(6)
        ss = font.render("數值變化：" + stat_line, True, (28, 70, 116))
        canvas.blit(ss, (tx, ty))


def main() -> None:
    """程式進入點。"""
    pygame.init()
    pygame.font.init()
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
        pygame.mixer.music.set_volume(1.0)
    except pygame.error:
        pass

    canvas_w, canvas_h = CANVAS_WIDTH, CANVAS_HEIGHT
    win_w = max(canvas_w, canvas_w * INITIAL_WINDOW_SCALE)
    win_h = max(canvas_h, canvas_h * INITIAL_WINDOW_SCALE)
    screen = pygame.display.set_mode((win_w, win_h), WINDOW_FLAGS)
    pygame.display.set_caption(GAME_TITLE)

    canvas = pygame.Surface((canvas_w, canvas_h))
    clock = pygame.time.Clock()
    font = _make_ui_font()
    title_main = _make_title_screen_main_font()
    title_sub = _make_title_screen_sub_font()
    small_font = _make_small_font()
    intro_font = _make_intro_font()
    title_menu_font = _make_title_menu_font()
    title_hint_font = _make_title_hint_font()
    frieren_quiz_font = _make_frieren_quiz_font()
    frieren_quiz_seal_font = _make_frieren_quiz_seal_font()
    guardian_header_font = _make_guardian_header_font()
    guardian_body_font = _make_guardian_body_font()
    contract_signature_font = _make_contract_signature_font()
    event_alert_title_font = _make_event_alert_title_font()
    event_alert_teaser_font = _make_event_alert_teaser_font()

    margin_x = _scale_x(28)
    max_text_w = canvas_w - 2 * margin_x - _TEXT_PAD_X
    # 與 `draw_intro_screen` 使用相同邊距與字型換行，避免量測與繪製不一致
    intro_text_w = canvas_w - 2 * _scale_x(20) - _TEXT_PAD_X
    intro_pages = [wrap_cjk(intro_font, section, intro_text_w) for section in PROLOGUE_SECTIONS]
    guardian_text_w = canvas_w - 2 * _scale_x(20) - _TEXT_PAD_X
    guardian_pages = [wrap_cjk(guardian_body_font, section, guardian_text_w) for section in GUARDIAN_INTRO_SECTIONS]

    state = GameState()
    gallery_unlocked = load_gallery_unlocked(_GAME_USERDATA_ROOT)
    enemy_gallery_unlocked = load_enemy_gallery_unlocked(_GAME_USERDATA_ROOT)
    companion_gallery_unlocked = load_companion_gallery_unlocked(
        _GAME_USERDATA_ROOT, _GAME_ASSET_ROOT
    )
    whim_gallery_unlocked = load_whim_gallery_unlocked(_GAME_USERDATA_ROOT)
    save_gallery_unlocked(
        _GAME_USERDATA_ROOT, gallery_unlocked, asset_root=_GAME_ASSET_ROOT
    )
    gallery_hub_index = 0
    gallery_active_keys: tuple[str, ...] = GALLERY_MALE_ENDING_KEYS
    gallery_section_label = _GALLERY_HUB_MENU_ITEMS[0]
    gallery_page_index = 0
    gallery_slot_index = 0
    gallery_view_key: str | None = None
    gallery_view_companion_key: str | None = None
    gallery_view_reward_slot: (
        tuple[str, str, tuple[str, ...], str | None] | None
    ) = None
    gallery_grid_mode: str = "ending"
    gallery_view_page_index = 0
    gallery_view_encounter_id: str | None = None
    screen_mode = Screen.TITLE
    title_menu_index = 0
    cheat_menu_index = 0
    cheat_menu_extras_unlocked = False
    cheat_secret_step = 0
    cheat_gallery_all_on = False
    cheat_bootstrap_on = False
    cheat_gallery_unlock_snapshot: set[str] | None = None
    cheat_gallery_keys_earned_while_cheat: set[str] = set()
    cheat_bgm_muted = False
    cheat_menu_modal: str | None = None
    cheat_hint_page_index = 0
    cheat_hint_gender: str | None = None
    cheat_hint_gender_menu_index = 0
    slot_cursor = 1
    intro_page_index = 0
    name_buffer = ""
    ime_composition = ""
    name_input_active = False
    name_entry_step = 0
    name_entry_gender_index = 0
    toast_message = ""
    toast_until = 0
    training_fx_action_key: int | None = None
    training_fx_pending_quarter: bool = False
    training_fx_pre_years: int = 0
    tick = 0
    current_save_slot = 1
    contract_seal_anim_frame = 0
    adopter_quiz_q_index = 0
    adopter_quiz_choice = 0
    adopter_quiz_answers: list[int] = [0, 0, 0, 0, 0]
    adopter_quiz_show_result = False
    adopter_quiz_judgment_zh = ""
    adopter_quiz_merged: dict[str, int] = {}
    training_menu_index = 0
    active_incident: IncidentEvent | None = None
    incident_option_index = 0
    incident_pending_year: int | None = None
    incident_phase: int = 0
    incident_chosen_index: int | None = None
    active_major_event: MajorEvent | None = None
    major_event_phase: int = 0
    major_event_option_index: int = 0
    major_event_pending_year: int | None = None
    major_event_chosen: int | None = None
    ending_cached: Ending | None = None
    ending_page_index: int | None = None
    pending_play_transition: Screen | None = None
    event_alert_next: Screen | None = None
    event_alert_major_age: int | None = None
    event_alert_is_encounter: bool = False
    event_alert_is_whim: bool = False
    encounter_alert_age: int | None = None
    active_encounter_enemy: EncounterEnemy | None = None
    encounter_battle_outcome: BattleOutcome | None = None
    encounter_frame_index: int = 0
    encounter_phase: int = 0
    encounter_applied: bool = False
    encounter_pending_year: int | None = None
    aftermath_page_index: int = 0

    # --- 奇遇事件（WHIM_EVENT）---
    whim_phase: int = 0
    whim_option_index: int = 0
    whim_chosen_index: int | None = None
    whim_is_correct: bool | None = None
    whim_active_slot_index: int | None = None
    active_whim_encounter: WhimEncounter | None = None
    active_whim_question: WhimQuestion | None = None
    whim_aftermath_page_index: int = 0
    whim_stat_effect_full_line: str = ""
    # 測驗畫面選項隨機排列：顯示槽 0～2 → 題庫 options 索引；正解槽 = perm.index(correct_index)
    whim_option_perm: tuple[int, int, int] | None = None
    whim_correct_slot: int = 0

    # --- 芙莉蓮測驗（標題→遊戲設定）---
    frieren_quiz_phase: FrierenQuizPhase = FrierenQuizPhase.CONFIRM
    frieren_quiz_session_indices: list[int] = []
    frieren_quiz_round_idx: int = 0
    frieren_quiz_score: int = 0
    frieren_quiz_active_question: WhimQuestion | None = None
    frieren_quiz_perm: tuple[int, int, int] | None = None
    frieren_quiz_option_index: int = 0
    frieren_quiz_feedback_correct: bool | None = None
    frieren_quiz_chosen_slot: int | None = None
    frieren_quiz_perm_feedback: tuple[int, int, int] | None = None
    frieren_quiz_cert_earned: bool = load_frieren_quiz_certificate_earned(
        _GAME_USERDATA_ROOT
    )
    frieren_quiz_cert_just_earned: bool = False

    def _frieren_quiz_load_current_question() -> None:
        """自 ``frieren_quiz_session_indices`` 載入本題並重排選項。"""
        nonlocal frieren_quiz_active_question, frieren_quiz_perm, frieren_quiz_option_index
        if not frieren_quiz_session_indices:
            return
        qi = frieren_quiz_session_indices[frieren_quiz_round_idx]
        frieren_quiz_active_question = WHIM_QUESTIONS[qi]
        pl = [0, 1, 2]
        random.shuffle(pl)
        frieren_quiz_perm = (pl[0], pl[1], pl[2])
        frieren_quiz_option_index = 0

    def _frieren_quiz_begin_session() -> None:
        """開始一輪 10 題（題號不重複）。"""
        nonlocal frieren_quiz_session_indices, frieren_quiz_round_idx, frieren_quiz_score
        nonlocal frieren_quiz_feedback_correct, frieren_quiz_chosen_slot
        nonlocal frieren_quiz_perm_feedback, frieren_quiz_phase, frieren_quiz_cert_just_earned
        frieren_quiz_cert_just_earned = False
        pool = list(range(len(WHIM_QUESTIONS)))
        random.shuffle(pool)
        frieren_quiz_session_indices = pool[:FRIEREN_QUIZ_NUM_QUESTIONS]
        frieren_quiz_round_idx = 0
        frieren_quiz_score = 0
        frieren_quiz_feedback_correct = None
        frieren_quiz_chosen_slot = None
        frieren_quiz_perm_feedback = None
        frieren_quiz_phase = FrierenQuizPhase.QUESTION
        _frieren_quiz_load_current_question()

    n_stars = 48
    star_xy: list[tuple[int, int]] = [
        (
            (i * 47 + 13) % (canvas_w - _scale_x(40)) + _scale_x(20),
            (i * 71 + 29) % (canvas_h - _scale_y(70)) + _scale_y(24),
        )
        for i in range(n_stars)
    ]

    def goto_after_load() -> None:
        """讀檔後決定下一畫面。"""
        nonlocal screen_mode, intro_page_index, guardian_page_index, name_buffer, ime_composition, name_input_active, name_entry_step, name_entry_gender_index, training_menu_index, ending_cached, ending_page_index, training_fx_action_key, training_fx_pending_quarter, training_fx_pre_years
        nonlocal adopter_quiz_q_index, adopter_quiz_choice, adopter_quiz_answers, adopter_quiz_show_result, adopter_quiz_judgment_zh, adopter_quiz_merged
        ime_composition = ""
        training_fx_action_key = None
        training_fx_pending_quarter = False
        training_fx_pre_years = 0
        state.refresh_life_phase()
        if not state.intro_done:
            intro_page_index = 0
            screen_mode = Screen.INTRO
        elif state.onboarding_complete:
            training_menu_index = 0
            if state.time_left <= 0:
                ending_cached = resolve_ending(state)
                ending_page_index = 0
                screen_mode = Screen.ENDING
            else:
                _ensure_whim_schedule_at_play_entry(state, random)
                ending_cached = None
                ending_page_index = None
                screen_mode = Screen.PLAY
        elif state.heroine_name.strip() and not state.onboarding_complete:
            name_buffer = state.heroine_name.strip()
            name_input_active = False
            name_entry_step = 1
            name_entry_gender_index = (
                0 if getattr(state, "protagonist_gender", "male") == "male" else 1
            )
            adopter_quiz_q_index = 0
            adopter_quiz_choice = 0
            adopter_quiz_answers = [0, 0, 0, 0, 0]
            adopter_quiz_show_result = False
            adopter_quiz_judgment_zh = ""
            adopter_quiz_merged = {}
            screen_mode = Screen.ADOPTER_QUESTIONNAIRE
        elif state.guardian_intro_done and not state.heroine_name.strip():
            name_buffer = ""
            name_input_active = False
            name_entry_step = 0
            name_entry_gender_index = 0
            screen_mode = Screen.GUARDIAN_INTRO
        else:
            guardian_page_index = 0
            name_buffer = ""
            name_input_active = False
            name_entry_step = 0
            name_entry_gender_index = 0
            screen_mode = Screen.GUARDIAN_INTRO

    guardian_page_index = 0

    bgm_loaded_fs: str | None = None

    def sync_bgm() -> None:
        """
        若與目前畫面／階段對應之 BGM 與正在播放者不同則載入並循環播放；
        作弊靜音時暫停、解除靜音時恢復。
        """
        nonlocal bgm_loaded_fs
        if pygame.mixer.get_init() is None:
            return
        target = _bgm_track_for_screen(
            screen_mode,
            state,
            event_alert_next=event_alert_next,
        )
        if not target.is_file():
            if bgm_loaded_fs is not None:
                try:
                    pygame.mixer.music.stop()
                except pygame.error:
                    pass
                bgm_loaded_fs = None
            return
        fs = os.fsdecode(target.resolve())
        if bgm_loaded_fs != fs:
            try:
                pygame.mixer.music.load(fs)
                pygame.mixer.music.play(-1)
                bgm_loaded_fs = fs
            except pygame.error:
                bgm_loaded_fs = None
                return
        try:
            if cheat_bgm_muted:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
        except pygame.error:
            pass

    def _finalize_pending_training_quarter(pre_years: int) -> None:
        """
        培養回饋關閉後才扣 1 季並檢查滿歲事件；回饋顯示期間 HUD 仍維持扣季前時間點。

        Args:
            pre_years: 執行培養指令前之滿歲年數（``state.age_months // 12``）。
        """
        nonlocal state, pending_play_transition, ending_cached, ending_page_index
        nonlocal active_major_event, major_event_phase, major_event_option_index
        nonlocal major_event_pending_year, major_event_chosen, aftermath_page_index
        nonlocal active_encounter_enemy, encounter_pending_year, encounter_battle_outcome
        nonlocal encounter_frame_index, encounter_phase, encounter_applied
        nonlocal event_alert_next, event_alert_major_age, event_alert_is_encounter, event_alert_is_whim
        nonlocal encounter_alert_age, active_incident, incident_pending_year
        nonlocal incident_option_index, incident_phase, incident_chosen_index, screen_mode
        nonlocal whim_phase, whim_option_index, whim_chosen_index, whim_is_correct
        nonlocal whim_active_slot_index, active_whim_encounter, active_whim_question
        nonlocal whim_aftermath_page_index, whim_stat_effect_full_line
        nonlocal whim_option_perm, whim_correct_slot
        state.spend_time(1)
        state.refresh_life_phase()
        post_years = state.age_months // 12
        if post_years > pre_years:
            if (
                post_years in MAJOR_TRIGGER_YEARS
                and post_years not in state.major_years_fired
            ):
                me = major_event_for_age(post_years)
                if me is not None:
                    active_major_event = me
                    major_event_phase = 0
                    major_event_option_index = 0
                    major_event_pending_year = post_years
                    major_event_chosen = None
                    aftermath_page_index = 0
                    pending_play_transition = Screen.EVENT_ALERT
                    event_alert_next = Screen.MAJOR_EVENT
                    event_alert_major_age = post_years
                    event_alert_is_encounter = False
                    event_alert_is_whim = False
                    encounter_alert_age = None
            elif (
                post_years in ENCOUNTER_TRIGGER_YEARS
                and post_years not in state.encounter_years_fired
            ):
                enc_enemy = pick_random_encounter(post_years, random)
                if enc_enemy is not None:
                    active_encounter_enemy = enc_enemy
                    encounter_pending_year = post_years
                    encounter_battle_outcome = simulate_encounter(
                        enc_enemy, state, random
                    )
                    encounter_frame_index = 0
                    encounter_phase = 0
                    encounter_applied = False
                    pending_play_transition = Screen.EVENT_ALERT
                    event_alert_next = Screen.ENCOUNTER_BATTLE
                    event_alert_major_age = None
                    event_alert_is_encounter = True
                    event_alert_is_whim = False
                    encounter_alert_age = post_years
            elif (
                post_years in INCIDENT_TRIGGER_YEARS
                and post_years not in state.incident_years_fired
            ):
                inc = pick_random_incident(
                    post_years,
                    random,
                    frozenset(state.incident_ids_fired),
                )
                if inc is not None:
                    active_incident = inc
                    incident_pending_year = post_years
                    incident_option_index = 0
                    incident_phase = 0
                    incident_chosen_index = None
                    aftermath_page_index = 0
                    pending_play_transition = Screen.EVENT_ALERT
                    event_alert_next = Screen.INCIDENT
                    event_alert_major_age = None
                    event_alert_is_encounter = False
                    event_alert_is_whim = False
                    encounter_alert_age = None

        # 奇遇事件：僅在本局排程的培養季槽位觸發（與年底事件避免重疊）。
        if pending_play_transition is None:
            whim_i = whim_active_index_for_completed_quarters(state)
            if whim_i is not None:
                active_whim_slot_index = whim_i
                npc_key = (
                    state.whim_npc_keys[whim_i]
                    if whim_i < len(state.whim_npc_keys)
                    else ""
                )
                active_whim_encounter = (
                    whim_encounter_by_key(npc_key) if npc_key else None
                )
                active_whim_question = whim_resolved_question_for_index(
                    state, whim_i
                )
                if active_whim_encounter is not None and active_whim_question is not None:
                    whim_phase = 0
                    whim_option_index = 0
                    whim_chosen_index = None
                    whim_is_correct = None
                    whim_aftermath_page_index = 0
                    whim_stat_effect_full_line = ""
                    whim_option_perm = None
                    pending_play_transition = Screen.EVENT_ALERT
                    event_alert_next = Screen.WHIM_EVENT
                    event_alert_major_age = None
                    event_alert_is_encounter = False
                    event_alert_is_whim = True
                    encounter_alert_age = None
        if (
            state.time_left <= 0
            and screen_mode is Screen.PLAY
            and pending_play_transition != Screen.EVENT_ALERT
        ):
            ending_cached = resolve_ending(state)
            ending_page_index = 0
            pending_play_transition = Screen.ENDING

    running = True
    while running:
        tick += 1
        now_ms = pygame.time.get_ticks()
        if not (
            screen_mode is Screen.GUARDIAN_INTRO and name_entry_step == 1
        ):
            ime_composition = ""
        if screen_mode is Screen.PLAY and name_input_active:
            pygame.key.stop_text_input()
            name_input_active = False
        if (
            screen_mode is Screen.GUARDIAN_INTRO
            and name_entry_step == 1
            and not name_input_active
        ):
            pygame.key.start_text_input()
            name_input_active = True
        if (
            screen_mode is Screen.GUARDIAN_INTRO
            and name_entry_step == 0
            and name_input_active
        ):
            pygame.key.stop_text_input()
            name_input_active = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(event.w, 320), max(event.h, 240)), WINDOW_FLAGS)
            elif event.type == pygame.TEXTINPUT:
                if (
                    screen_mode is Screen.GUARDIAN_INTRO
                    and name_entry_step == 1
                    and event.text
                    and event.text.isprintable()
                ):
                    if len(name_buffer) < 12:
                        name_buffer += event.text
            elif _PYGAME_TEXTEDITING is not None and event.type == _PYGAME_TEXTEDITING:
                if screen_mode is Screen.GUARDIAN_INTRO and name_entry_step == 1:
                    ime_composition = getattr(event, "text", "") or ""
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if screen_mode is Screen.CONTRACT_SEAL:
                        contract_seal_anim_frame = _CONTRACT_SEAL_ANIM_DONE_AT
                    elif screen_mode is Screen.GUARDIAN_INTRO:
                        pygame.key.stop_text_input()
                        name_input_active = False
                        name_entry_step = 0
                        name_entry_gender_index = 0
                        name_buffer = ""
                        ime_composition = ""
                        adopter_quiz_q_index = 0
                        adopter_quiz_choice = 0
                        adopter_quiz_answers = [0, 0, 0, 0, 0]
                        adopter_quiz_show_result = False
                        adopter_quiz_judgment_zh = ""
                        adopter_quiz_merged = {}
                        screen_mode = Screen.TITLE
                    elif screen_mode is Screen.INTRO:
                        screen_mode = Screen.TITLE
                    elif screen_mode is Screen.SLOT_SELECT:
                        screen_mode = Screen.TITLE
                    elif screen_mode is Screen.SAVE_SLOT:
                        screen_mode = Screen.PLAY
                    elif screen_mode is Screen.ENDING:
                        ending_cached = None
                        ending_page_index = None
                        screen_mode = Screen.TITLE
                    elif screen_mode is Screen.GALLERY:
                        if (
                            gallery_view_key is not None
                            or gallery_view_reward_slot is not None
                            or gallery_view_encounter_id is not None
                            or gallery_view_companion_key is not None
                        ):
                            gallery_view_key = None
                            gallery_view_reward_slot = None
                            gallery_view_encounter_id = None
                            gallery_view_companion_key = None
                            gallery_view_page_index = 0
                        else:
                            screen_mode = Screen.GALLERY_HUB
                    elif screen_mode is Screen.GALLERY_HUB:
                        screen_mode = Screen.TITLE
                    elif screen_mode is Screen.CHEAT_GALLERY_HINTS:
                        if cheat_hint_gender is None:
                            cheat_hint_page_index = 0
                            cheat_hint_gender_menu_index = 0
                            screen_mode = Screen.CHEAT_MENU
                        else:
                            cheat_hint_gender = None
                            cheat_hint_page_index = 0
                    elif screen_mode is Screen.FRIEREN_QUIZ:
                        screen_mode = Screen.CHEAT_MENU
                    elif screen_mode is Screen.CHEAT_MENU:
                        if cheat_menu_modal is not None:
                            cheat_menu_modal = None
                        else:
                            screen_mode = Screen.TITLE
                    elif screen_mode is Screen.INCIDENT:
                        pass
                    elif screen_mode is Screen.ENCOUNTER_BATTLE:
                        pass
                    elif screen_mode is Screen.MAJOR_EVENT:
                        pass
                    elif screen_mode is Screen.EVENT_ALERT:
                        pass
                    elif screen_mode is Screen.WHIM_EVENT:
                        pass
                    elif screen_mode is Screen.ADOPTER_QUESTIONNAIRE:
                        if adopter_quiz_show_result:
                            pass
                        elif adopter_quiz_q_index > 0:
                            adopter_quiz_q_index -= 1
                            adopter_quiz_choice = adopter_quiz_answers[
                                adopter_quiz_q_index
                            ]
                        else:
                            name_buffer = state.heroine_name
                            name_entry_step = 1
                            ime_composition = ""
                            name_input_active = False
                            screen_mode = Screen.GUARDIAN_INTRO
                    elif screen_mode is Screen.PLAY:
                        if training_fx_action_key is not None:
                            if training_fx_pending_quarter:
                                _finalize_pending_training_quarter(training_fx_pre_years)
                                training_fx_pending_quarter = False
                                training_fx_pre_years = 0
                            training_fx_action_key = None
                            toast_message = ""
                            if pending_play_transition is not None:
                                screen_mode = pending_play_transition
                                pending_play_transition = None
                                sync_bgm()
                        else:
                            screen_mode = Screen.TITLE
                    else:
                        running = False
                elif screen_mode is Screen.TITLE:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        title_menu_index = (title_menu_index - 1) % len(TITLE_MENU_ITEMS)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        title_menu_index = (title_menu_index + 1) % len(TITLE_MENU_ITEMS)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if title_menu_index == 0:
                            if cheat_bootstrap_on:
                                state = _make_cheat_bootstrap_state()
                                current_save_slot = 1
                                training_menu_index = 0
                                active_incident = None
                                incident_option_index = 0
                                incident_pending_year = None
                                incident_phase = 0
                                incident_chosen_index = None
                                active_major_event = None
                                major_event_phase = 0
                                major_event_option_index = 0
                                major_event_pending_year = None
                                major_event_chosen = None
                                event_alert_next = None
                                event_alert_major_age = None
                                event_alert_is_encounter = False
                                encounter_alert_age = None
                                active_encounter_enemy = None
                                encounter_battle_outcome = None
                                encounter_frame_index = 0
                                encounter_phase = 0
                                encounter_applied = False
                                encounter_pending_year = None
                                aftermath_page_index = 0
                                ending_cached = None
                                ending_page_index = None
                                training_fx_action_key = None
                                training_fx_pending_quarter = False
                                training_fx_pre_years = 0
                                contract_seal_anim_frame = 0
                                adopter_quiz_q_index = 0
                                adopter_quiz_choice = 0
                                adopter_quiz_answers = [0, 0, 0, 0, 0]
                                adopter_quiz_show_result = False
                                adopter_quiz_judgment_zh = ""
                                adopter_quiz_merged = {}
                                toast_message = "作弊開局：已進入養成"
                                toast_until = now_ms + 2200
                                screen_mode = Screen.PLAY
                            else:
                                state = GameState()
                                current_save_slot = 1
                                intro_page_index = 0
                                contract_seal_anim_frame = 0
                                adopter_quiz_q_index = 0
                                adopter_quiz_choice = 0
                                adopter_quiz_answers = [0, 0, 0, 0, 0]
                                adopter_quiz_show_result = False
                                adopter_quiz_judgment_zh = ""
                                adopter_quiz_merged = {}
                                training_menu_index = 0
                                active_incident = None
                                incident_option_index = 0
                                incident_pending_year = None
                                incident_phase = 0
                                incident_chosen_index = None
                                active_major_event = None
                                major_event_phase = 0
                                major_event_option_index = 0
                                major_event_pending_year = None
                                major_event_chosen = None
                                event_alert_next = None
                                event_alert_major_age = None
                                event_alert_is_encounter = False
                                encounter_alert_age = None
                                active_encounter_enemy = None
                                encounter_battle_outcome = None
                                encounter_frame_index = 0
                                encounter_phase = 0
                                encounter_applied = False
                                encounter_pending_year = None
                                aftermath_page_index = 0
                                ending_cached = None
                                ending_page_index = None
                                training_fx_action_key = None
                                training_fx_pending_quarter = False
                                training_fx_pre_years = 0
                                screen_mode = Screen.INTRO
                        elif title_menu_index == 1:
                            slot_cursor = 1
                            screen_mode = Screen.SLOT_SELECT
                        elif title_menu_index == 2:
                            gallery_hub_index = 0
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            gallery_view_key = None
                            gallery_view_reward_slot = None
                            gallery_grid_mode = "ending"
                            gallery_view_page_index = 0
                            screen_mode = Screen.GALLERY_HUB
                        elif title_menu_index == 3:
                            cheat_menu_index = 0
                            cheat_secret_step = 0
                            cheat_menu_modal = None
                            screen_mode = Screen.CHEAT_MENU
                        elif title_menu_index == 4:
                            running = False
                elif screen_mode is Screen.CHEAT_MENU:
                    if cheat_menu_modal is not None:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if cheat_menu_modal == _CHEAT_MODAL_CONFIRM_GALLERY:
                                cheat_gallery_unlock_snapshot = set(gallery_unlocked)
                                cheat_gallery_keys_earned_while_cheat.clear()
                                gallery_unlocked.update(GALLERY_ENDING_KEYS)
                                save_gallery_unlocked(
                                    _GAME_USERDATA_ROOT,
                                    gallery_unlocked,
                                    asset_root=_GAME_ASSET_ROOT,
                                )
                                cheat_gallery_all_on = True
                                toast_message = "已開啟：解鎖畫廊全部結局CG圖"
                                toast_until = now_ms + 2200
                            elif cheat_menu_modal == _CHEAT_MODAL_CONFIRM_BOOTSTRAP:
                                cheat_bootstrap_on = True
                                toast_message = "已開啟作弊開局：請從標題選「新遊戲」"
                                toast_until = now_ms + 2200
                            elif cheat_menu_modal == _CHEAT_MODAL_CONFIRM_CLEAR_GALLERY:
                                clear_all_gallery_unlock_data(_GAME_USERDATA_ROOT)
                                gallery_unlocked.clear()
                                enemy_gallery_unlocked.clear()
                                enemy_gallery_unlocked.update(
                                    load_enemy_gallery_unlocked(_GAME_USERDATA_ROOT)
                                )
                                companion_gallery_unlocked.clear()
                                companion_gallery_unlocked.update(
                                    load_companion_gallery_unlocked(
                                        _GAME_USERDATA_ROOT, _GAME_ASSET_ROOT
                                    )
                                )
                                whim_gallery_unlocked.clear()
                                whim_gallery_unlocked.update(
                                    load_whim_gallery_unlocked(_GAME_USERDATA_ROOT)
                                )
                                cheat_gallery_all_on = False
                                cheat_gallery_unlock_snapshot = None
                                cheat_gallery_keys_earned_while_cheat.clear()
                                toast_message = (
                                    "已清空圖片畫廊解鎖紀錄（通關／夥伴／強敵／獎勵等；養成存檔未刪）"
                                )
                                toast_until = now_ms + 2200
                            elif cheat_menu_modal == _CHEAT_MODAL_CONFIRM_CLEAR_SAVES:
                                _delete_all_save_slot_files(_GAME_USERDATA_ROOT)
                                toast_message = "已清空所有存檔（五格）"
                                toast_until = now_ms + 2200
                            elif cheat_menu_modal == _CHEAT_MODAL_CONFIRM_UNLOCK_COMPANION_ENEMY:
                                cheat_unlock_companion_enemy_gallery_cg(
                                    _GAME_USERDATA_ROOT, _GAME_ASSET_ROOT
                                )
                                enemy_gallery_unlocked.clear()
                                enemy_gallery_unlocked.update(
                                    load_enemy_gallery_unlocked(_GAME_USERDATA_ROOT)
                                )
                                companion_gallery_unlocked.clear()
                                companion_gallery_unlocked.update(
                                    load_companion_gallery_unlocked(
                                        _GAME_USERDATA_ROOT, _GAME_ASSET_ROOT
                                    )
                                )
                                toast_message = (
                                    "已解鎖：同行的夥伴(奇遇)、遭遇的強敵(遭遇戰)（全部 CG）"
                                )
                                toast_until = now_ms + 2400
                            cheat_menu_modal = None
                    else:
                        vis = _cheat_menu_visible_item_indices(cheat_menu_extras_unlocked)
                        n_vis = len(vis)
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            item_i = vis[cheat_menu_index]
                            if item_i == 0:
                                frieren_quiz_phase = FrierenQuizPhase.CONFIRM
                                screen_mode = Screen.FRIEREN_QUIZ
                            elif item_i == 1:
                                cheat_hint_page_index = 0
                                cheat_hint_gender = None
                                cheat_hint_gender_menu_index = 0
                                screen_mode = Screen.CHEAT_GALLERY_HINTS
                            elif item_i == 2:
                                cheat_bgm_muted = not cheat_bgm_muted
                                toast_message = (
                                    "背景音樂：關"
                                    if cheat_bgm_muted
                                    else "背景音樂：開"
                                )
                                toast_until = now_ms + 1600
                            elif item_i == 3:
                                cheat_menu_modal = _CHEAT_MODAL_CONFIRM_CLEAR_GALLERY
                            elif item_i == 4:
                                cheat_menu_modal = _CHEAT_MODAL_CONFIRM_CLEAR_SAVES
                            elif item_i == 5:
                                if cheat_bootstrap_on:
                                    cheat_bootstrap_on = False
                                    toast_message = "已關閉：作弊開局"
                                    toast_until = now_ms + 2200
                                else:
                                    cheat_menu_modal = _CHEAT_MODAL_CONFIRM_BOOTSTRAP
                            elif item_i == 6:
                                if cheat_gallery_all_on:
                                    snap = (
                                        cheat_gallery_unlock_snapshot
                                        if cheat_gallery_unlock_snapshot is not None
                                        else load_gallery_unlocked(_GAME_USERDATA_ROOT)
                                    )
                                    restored = (
                                        set(snap) | cheat_gallery_keys_earned_while_cheat
                                    ) & set(GALLERY_ENDING_KEYS)
                                    gallery_unlocked.clear()
                                    gallery_unlocked.update(restored)
                                    save_gallery_unlocked(
                                        _GAME_USERDATA_ROOT,
                                        gallery_unlocked,
                                        asset_root=_GAME_ASSET_ROOT,
                                    )
                                    cheat_gallery_all_on = False
                                    cheat_gallery_unlock_snapshot = None
                                    cheat_gallery_keys_earned_while_cheat.clear()
                                    toast_message = "已關閉：畫廊全解鎖作弊（保留實際破關解鎖）"
                                    toast_until = now_ms + 2200
                                else:
                                    cheat_menu_modal = _CHEAT_MODAL_CONFIRM_GALLERY
                            elif item_i == 7:
                                cheat_menu_modal = (
                                    _CHEAT_MODAL_CONFIRM_UNLOCK_COMPANION_ENEMY
                                )
                        else:
                            if cheat_menu_extras_unlocked:
                                nav = _cheat_menu_navigate_grid(
                                    cheat_menu_index, vis, event.key
                                )
                                if nav is not None:
                                    cheat_menu_index = nav
                            else:
                                if event.key in (pygame.K_UP, pygame.K_w):
                                    cheat_menu_index = (cheat_menu_index - 1) % n_vis
                                elif event.key in (pygame.K_DOWN, pygame.K_s):
                                    cheat_menu_index = (cheat_menu_index + 1) % n_vis
                                else:
                                    d: str | None = None
                                    if event.key == pygame.K_LEFT:
                                        d = "left"
                                    elif event.key == pygame.K_RIGHT:
                                        d = "right"
                                    if d is not None:
                                        if d == _CHEAT_SECRET_SEQUENCE[cheat_secret_step]:
                                            cheat_secret_step += 1
                                            if cheat_secret_step >= len(
                                                _CHEAT_SECRET_SEQUENCE
                                            ):
                                                cheat_menu_extras_unlocked = True
                                                cheat_secret_step = 0
                                        else:
                                            cheat_secret_step = 0
                elif screen_mode is Screen.FRIEREN_QUIZ:
                    if frieren_quiz_phase is FrierenQuizPhase.CONFIRM:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            _frieren_quiz_begin_session()
                        elif event.key == pygame.K_ESCAPE:
                            screen_mode = Screen.CHEAT_MENU
                    elif frieren_quiz_phase is FrierenQuizPhase.QUESTION:
                        if event.key == pygame.K_ESCAPE:
                            screen_mode = Screen.CHEAT_MENU
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            frieren_quiz_option_index = (frieren_quiz_option_index - 1) % 3
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            frieren_quiz_option_index = (frieren_quiz_option_index + 1) % 3
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if (
                                frieren_quiz_active_question is None
                                or frieren_quiz_perm is None
                            ):
                                pass
                            else:
                                q = frieren_quiz_active_question
                                perm = frieren_quiz_perm
                                slot = frieren_quiz_option_index
                                correct_slot = perm.index(q.correct_index)
                                frieren_quiz_feedback_correct = slot == correct_slot
                                frieren_quiz_chosen_slot = slot
                                frieren_quiz_perm_feedback = perm
                                if frieren_quiz_feedback_correct:
                                    frieren_quiz_score += 10
                                frieren_quiz_phase = FrierenQuizPhase.FEEDBACK
                    elif frieren_quiz_phase is FrierenQuizPhase.FEEDBACK:
                        if event.key == pygame.K_ESCAPE:
                            screen_mode = Screen.CHEAT_MENU
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            frieren_quiz_round_idx += 1
                            if frieren_quiz_round_idx >= FRIEREN_QUIZ_NUM_QUESTIONS:
                                total_pts = FRIEREN_QUIZ_NUM_QUESTIONS * 10
                                if (
                                    frieren_quiz_score >= total_pts
                                    and not frieren_quiz_cert_earned
                                ):
                                    save_frieren_quiz_certificate_earned(
                                        _GAME_USERDATA_ROOT
                                    )
                                    frieren_quiz_cert_earned = True
                                    frieren_quiz_cert_just_earned = True
                                frieren_quiz_phase = FrierenQuizPhase.RESULTS
                            else:
                                frieren_quiz_phase = FrierenQuizPhase.QUESTION
                                _frieren_quiz_load_current_question()
                    elif frieren_quiz_phase is FrierenQuizPhase.RESULTS:
                        if event.key in (
                            pygame.K_RETURN,
                            pygame.K_KP_ENTER,
                            pygame.K_ESCAPE,
                        ):
                            screen_mode = Screen.CHEAT_MENU
                elif screen_mode is Screen.CHEAT_GALLERY_HINTS:
                    if cheat_hint_gender is None:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            cheat_hint_gender_menu_index = (
                                cheat_hint_gender_menu_index - 1
                            ) % 2
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            cheat_hint_gender_menu_index = (
                                cheat_hint_gender_menu_index + 1
                            ) % 2
                        elif event.key in (
                            pygame.K_RETURN,
                            pygame.K_KP_ENTER,
                            pygame.K_SPACE,
                        ):
                            cheat_hint_gender = (
                                _CHEAT_HINT_GENDER_MALE
                                if cheat_hint_gender_menu_index == 0
                                else _CHEAT_HINT_GENDER_FEMALE
                            )
                            cheat_hint_page_index = 0
                    else:
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            if cheat_hint_page_index > 0:
                                cheat_hint_page_index -= 1
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            npg = _cheat_gallery_hint_num_pages(cheat_hint_gender)
                            if cheat_hint_page_index < npg - 1:
                                cheat_hint_page_index += 1
                elif screen_mode is Screen.INTRO:
                    if event.key == pygame.K_LEFT:
                        intro_page_index = max(0, intro_page_index - 1)
                    elif event.key == pygame.K_RIGHT:
                        intro_page_index = min(len(intro_pages) - 1, intro_page_index + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if intro_page_index >= len(intro_pages) - 1:
                            state.intro_done = True
                            screen_mode = Screen.GUARDIAN_INTRO
                elif screen_mode is Screen.GUARDIAN_INTRO:
                    if name_entry_step == 0:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            name_entry_gender_index = 1 - name_entry_gender_index
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            name_entry_gender_index = 1 - name_entry_gender_index
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            name_entry_step = 1
                            name_buffer = ""
                            ime_composition = ""
                    else:
                        if event.key == pygame.K_BACKSPACE:
                            name_buffer = name_buffer[:-1]
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            nm = name_buffer.strip()
                            if nm:
                                state.protagonist_gender = (
                                    "male" if name_entry_gender_index == 0 else "female"
                                )
                                state.heroine_name = nm
                                state.guardian_intro_done = True
                                pygame.key.stop_text_input()
                                name_input_active = False
                                contract_seal_anim_frame = 0
                                adopter_quiz_q_index = 0
                                adopter_quiz_choice = 0
                                adopter_quiz_answers = [0, 0, 0, 0, 0]
                                adopter_quiz_show_result = False
                                adopter_quiz_judgment_zh = ""
                                adopter_quiz_merged = {}
                                screen_mode = Screen.ADOPTER_QUESTIONNAIRE
                elif screen_mode is Screen.ADOPTER_QUESTIONNAIRE:
                    if adopter_quiz_show_result:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            contract_seal_anim_frame = 0
                            screen_mode = Screen.CONTRACT_SEAL
                    else:
                        n_opts = 4
                        if event.key in (pygame.K_UP, pygame.K_w):
                            adopter_quiz_choice = (adopter_quiz_choice - 1) % n_opts
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            adopter_quiz_choice = (adopter_quiz_choice + 1) % n_opts
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            adopter_quiz_answers[adopter_quiz_q_index] = adopter_quiz_choice
                            if adopter_quiz_q_index < ADOPTER_QUESTIONNAIRE_COUNT - 1:
                                adopter_quiz_q_index += 1
                                adopter_quiz_choice = adopter_quiz_answers[
                                    adopter_quiz_q_index
                                ]
                            else:
                                jm, merged = finalize_adopter_questionnaire(
                                    tuple(adopter_quiz_answers), state
                                )
                                adopter_quiz_judgment_zh = jm
                                adopter_quiz_merged = merged
                                adopter_quiz_show_result = True
                elif screen_mode is Screen.CONTRACT_SEAL:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if contract_seal_anim_frame >= _CONTRACT_SEAL_ANIM_DONE_AT:
                            state.onboarding_complete = True
                            _ensure_whim_schedule_at_play_entry(state, random)
                            screen_mode = Screen.PLAY
                    elif event.key == pygame.K_SPACE:
                        if contract_seal_anim_frame < _CONTRACT_SEAL_ANIM_DONE_AT:
                            contract_seal_anim_frame = _CONTRACT_SEAL_ANIM_DONE_AT
                elif screen_mode is Screen.SLOT_SELECT:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        slot_cursor = max(1, slot_cursor - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        slot_cursor = min(SLOT_COUNT, slot_cursor + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        try:
                            state = load_from_slot(slot_cursor, _GAME_USERDATA_ROOT)
                            current_save_slot = slot_cursor
                            goto_after_load()
                        except FileNotFoundError:
                            toast_message = "此欄位沒有存檔"
                            toast_until = now_ms + 2000
                        except (OSError, ValueError, KeyError) as e:
                            toast_message = f"讀檔失敗：{e}"
                            toast_until = now_ms + 2500
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        slot_cursor = event.key - pygame.K_0
                        try:
                            state = load_from_slot(slot_cursor, _GAME_USERDATA_ROOT)
                            current_save_slot = slot_cursor
                            goto_after_load()
                        except FileNotFoundError:
                            toast_message = "此欄位沒有存檔"
                            toast_until = now_ms + 2000
                        except (OSError, ValueError, KeyError) as e:
                            toast_message = f"讀檔失敗：{e}"
                            toast_until = now_ms + 2500
                elif screen_mode is Screen.SAVE_SLOT:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        slot_cursor = max(1, slot_cursor - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        slot_cursor = min(SLOT_COUNT, slot_cursor + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        try:
                            save_to_slot(state, slot_cursor, _GAME_USERDATA_ROOT)
                            current_save_slot = slot_cursor
                            toast_message = f"已儲存至欄位 {slot_cursor}"
                            toast_until = now_ms + 2000
                            screen_mode = Screen.PLAY
                        except OSError as e:
                            toast_message = f"存檔失敗：{e}"
                            toast_until = now_ms + 2500
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        slot_cursor = event.key - pygame.K_0
                        try:
                            save_to_slot(state, slot_cursor, _GAME_USERDATA_ROOT)
                            current_save_slot = slot_cursor
                            toast_message = f"已儲存至欄位 {slot_cursor}"
                            toast_until = now_ms + 2000
                            screen_mode = Screen.PLAY
                        except OSError as e:
                            toast_message = f"存檔失敗：{e}"
                            toast_until = now_ms + 2500
                elif screen_mode is Screen.MAJOR_EVENT:
                    me = active_major_event
                    if me is None:
                        screen_mode = Screen.PLAY
                    elif major_event_phase == 0:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            major_event_phase = 1
                            major_event_option_index = 0
                    elif major_event_phase == 1:
                        if event.key == pygame.K_UP:
                            major_event_option_index = (major_event_option_index - 1) % 3
                        elif event.key == pygame.K_DOWN:
                            major_event_option_index = (major_event_option_index + 1) % 3
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            opt = me.options[major_event_option_index]
                            state.apply_deltas(opt.deltas)
                            state.apply_deltas(opt.extra_deltas)
                            for flg in opt.flags_add:
                                state.add_flag(flg)
                            if state.protagonist_gender == "male":
                                for flg in opt.flags_add_if_male:
                                    state.add_flag(flg)
                            major_event_chosen = major_event_option_index
                            major_event_phase = 2
                            aftermath_page_index = 0
                    elif major_event_phase == 2:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            aftermath_page_index = 0
                            if (
                                major_event_pending_year is not None
                                and major_event_pending_year not in state.major_years_fired
                            ):
                                state.major_years_fired.append(major_event_pending_year)
                            active_major_event = None
                            major_event_phase = 0
                            major_event_option_index = 0
                            major_event_pending_year = None
                            major_event_chosen = None
                            screen_mode = Screen.PLAY
                elif screen_mode is Screen.INCIDENT:
                    if active_incident is None:
                        screen_mode = Screen.PLAY
                    elif incident_phase == 0:
                        if event.key == pygame.K_UP:
                            incident_option_index = (incident_option_index - 1) % 3
                        elif event.key == pygame.K_DOWN:
                            incident_option_index = (incident_option_index + 1) % 3
                        elif pygame.K_1 <= event.key <= pygame.K_3:
                            incident_option_index = int(event.key - pygame.K_1)
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            opt = active_incident.options[incident_option_index]
                            state.apply_deltas(opt.deltas)
                            if incident_pending_year is not None:
                                state.incident_years_fired.append(incident_pending_year)
                            if active_incident.id not in state.incident_ids_fired:
                                state.incident_ids_fired.append(active_incident.id)
                            if opt.aftermath:
                                incident_chosen_index = incident_option_index
                                incident_phase = 1
                                aftermath_page_index = 0
                            else:
                                toast_message = (
                                    "突發事件　"
                                    + format_incident_deltas_brief(opt.deltas)
                                )
                                toast_until = now_ms + _TOAST_DURATION_PLAY_EVENT_MS
                                active_incident = None
                                incident_pending_year = None
                                incident_phase = 0
                                incident_chosen_index = None
                                screen_mode = Screen.PLAY
                    elif incident_phase == 1:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            aftermath_page_index = 0
                            active_incident = None
                            incident_pending_year = None
                            incident_phase = 0
                            incident_chosen_index = None
                            incident_option_index = 0
                            screen_mode = Screen.PLAY
                elif screen_mode is Screen.ENCOUNTER_BATTLE:
                    if active_encounter_enemy is None or encounter_battle_outcome is None:
                        screen_mode = Screen.PLAY
                    elif encounter_phase == 0:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            nfr = len(encounter_battle_outcome.frames) - 1
                            # 禁止 Enter 快轉到最後一幀：結算與勝負早已在進場前決定，
                            # 快轉僅造成「秒結束＋同幀連按跳過餘韻」等不良體感；須待自動播映抵達末幀。
                            if encounter_frame_index >= nfr:
                                if not encounter_applied:
                                    if encounter_pending_year is not None:
                                        state.encounter_years_fired.append(
                                            encounter_pending_year
                                        )
                                    bo = encounter_battle_outcome
                                    state.apply_deltas(bo.participation_deltas)
                                    if bo.win:
                                        state.apply_deltas(bo.treasure_deltas)
                                        register_enemy_gallery_unlock(
                                            _GAME_USERDATA_ROOT,
                                            enemy_gallery_unlocked,
                                            active_encounter_enemy.id,
                                        )
                                    encounter_applied = True
                                encounter_phase = 1
                                break
                    elif encounter_phase == 1:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            active_encounter_enemy = None
                            encounter_battle_outcome = None
                            encounter_frame_index = 0
                            encounter_phase = 0
                            encounter_applied = False
                            encounter_pending_year = None
                            screen_mode = Screen.PLAY
                            break
                elif screen_mode is Screen.WHIM_EVENT:
                    if active_whim_encounter is None or active_whim_question is None:
                        screen_mode = Screen.PLAY
                    elif whim_phase == 0:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            perm_list = [0, 1, 2]
                            random.shuffle(perm_list)
                            whim_option_perm = (perm_list[0], perm_list[1], perm_list[2])
                            whim_correct_slot = whim_option_perm.index(
                                active_whim_question.correct_index
                            )
                            whim_phase = 1
                            whim_option_index = 0
                    elif whim_phase == 1:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            whim_option_index = (whim_option_index - 1) % 3
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            whim_option_index = (whim_option_index + 1) % 3
                        elif pygame.K_1 <= event.key <= pygame.K_3:
                            whim_option_index = int(event.key - pygame.K_1)
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            chosen = whim_option_index
                            is_correct = chosen == whim_correct_slot
                            whim_chosen_index = chosen
                            whim_is_correct = is_correct
                            deltas = (
                                active_whim_encounter.deltas_correct
                                if is_correct
                                else active_whim_encounter.deltas_wrong
                            )
                            state.apply_deltas(deltas)
                            whim_stat_effect_full_line = (
                                _TRAINING_FEEDBACK_MODAL_STAT_PREFIX
                                + format_whim_deltas_line(deltas)
                            )
                            if is_correct:
                                register_whim_gallery_unlock(
                                    _GAME_USERDATA_ROOT,
                                    whim_gallery_unlocked,
                                    active_whim_encounter.cg_basename,
                                )
                            whim_phase = 2
                    elif whim_phase == 2:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if (
                                whim_active_slot_index is not None
                                and 0
                                <= whim_active_slot_index
                                < len(state.whim_fired)
                            ):
                                state.whim_fired[whim_active_slot_index] = True
                            active_whim_encounter = None
                            active_whim_question = None
                            whim_active_slot_index = None
                            whim_phase = 0
                            whim_option_index = 0
                            whim_chosen_index = None
                            whim_is_correct = None
                            whim_aftermath_page_index = 0
                            whim_stat_effect_full_line = ""
                            whim_option_perm = None
                            screen_mode = Screen.PLAY
                            sync_bgm()
                elif screen_mode is Screen.EVENT_ALERT:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        nxt = event_alert_next
                        event_alert_next = None
                        event_alert_major_age = None
                        event_alert_is_encounter = False
                        event_alert_is_whim = False
                        encounter_alert_age = None
                        screen_mode = nxt if nxt is not None else Screen.PLAY
                        sync_bgm()
                elif screen_mode is Screen.PLAY:
                    training_feedback_active = training_fx_action_key is not None
                    if (
                        pending_play_transition is not None
                        and not training_feedback_active
                    ):
                        screen_mode = pending_play_transition
                        pending_play_transition = None
                        sync_bgm()
                        continue
                    if event.key == pygame.K_s and not training_feedback_active:
                        slot_cursor = current_save_slot
                        screen_mode = Screen.SAVE_SLOT
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if training_fx_action_key is not None:
                            if training_fx_pending_quarter:
                                _finalize_pending_training_quarter(training_fx_pre_years)
                                training_fx_pending_quarter = False
                                training_fx_pre_years = 0
                            training_fx_action_key = None
                            toast_message = ""
                            if pending_play_transition is not None:
                                screen_mode = pending_play_transition
                                pending_play_transition = None
                                sync_bgm()
                            continue
                        if state.time_left > 0:
                            act = TRAINING_ACTIONS[training_menu_index]
                            if state.can_spend(1):
                                pre_years = state.age_months // 12
                                state.apply_deltas(act.deltas)
                                toast_message = format_training_feedback_modal_message(
                                    act,
                                    gender_key=state.protagonist_gender,
                                )
                                toast_until = 0
                                training_fx_action_key = act.key_num
                                training_fx_pending_quarter = True
                                training_fx_pre_years = pre_years
                    elif state.time_left > 0:
                        if event.key in (
                            pygame.K_UP,
                            pygame.K_DOWN,
                            pygame.K_LEFT,
                            pygame.K_RIGHT,
                        ):
                            if not training_feedback_active:
                                training_menu_index = _training_menu_navigate(
                                    training_menu_index, event.key
                                )
                elif screen_mode is Screen.ENDING:
                    if ending_cached is None:
                        screen_mode = Screen.TITLE
                    elif event.key == pygame.K_LEFT:
                        if ending_page_index is not None:
                            ending_page_index = max(0, ending_page_index - 1)
                    elif event.key == pygame.K_RIGHT:
                        if ending_page_index is not None and ending_cached is not None:
                            _mx = _ending_cg_page_index(ending_cached)
                            ending_page_index = min(_mx, ending_page_index + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if (
                            ending_cached is not None
                            and ending_page_index
                            == _ending_cg_page_index(ending_cached)
                        ):
                            ec = ending_cached
                            if ec is not None:
                                register_gallery_unlock(
                                    _GAME_USERDATA_ROOT,
                                    gallery_unlocked,
                                    ec.key,
                                    asset_root=_GAME_ASSET_ROOT,
                                )
                                if cheat_gallery_all_on:
                                    cheat_gallery_keys_earned_while_cheat.add(ec.key)
                            ending_page_index = None
                            ending_cached = None
                            screen_mode = Screen.TITLE
                elif screen_mode is Screen.GALLERY_HUB:
                    n_hub = len(_GALLERY_HUB_MENU_ITEMS)
                    if event.key in (pygame.K_UP, pygame.K_w):
                        gallery_hub_index = (gallery_hub_index - 1) % n_hub
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        gallery_hub_index = (gallery_hub_index + 1) % n_hub
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if gallery_hub_index == 0:
                            gallery_grid_mode = "ending"
                            gallery_view_reward_slot = None
                            gallery_view_encounter_id = None
                            gallery_view_companion_key = None
                            gallery_active_keys = GALLERY_MALE_ENDING_KEYS
                            gallery_section_label = _GALLERY_HUB_MENU_ITEMS[0]
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            screen_mode = Screen.GALLERY
                        elif gallery_hub_index == 1:
                            gallery_grid_mode = "ending"
                            gallery_view_reward_slot = None
                            gallery_view_encounter_id = None
                            gallery_view_companion_key = None
                            gallery_active_keys = GALLERY_FEMALE_ENDING_KEYS
                            gallery_section_label = _GALLERY_HUB_MENU_ITEMS[1]
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            screen_mode = Screen.GALLERY
                        elif gallery_hub_index == 2:
                            gallery_grid_mode = "companion"
                            gallery_view_key = None
                            gallery_view_reward_slot = None
                            gallery_view_encounter_id = None
                            gallery_view_companion_key = None
                            gallery_view_page_index = 0
                            gallery_section_label = _GALLERY_HUB_MENU_ITEMS[2]
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            screen_mode = Screen.GALLERY
                        elif gallery_hub_index == 3:
                            gallery_grid_mode = "encounter"
                            gallery_view_key = None
                            gallery_view_reward_slot = None
                            gallery_view_encounter_id = None
                            gallery_view_companion_key = None
                            gallery_view_page_index = 0
                            gallery_section_label = _GALLERY_HUB_MENU_ITEMS[3]
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            screen_mode = Screen.GALLERY
                        elif gallery_hub_index == 4:
                            gallery_grid_mode = "reward"
                            gallery_view_key = None
                            gallery_view_companion_key = None
                            gallery_view_page_index = 0
                            gallery_view_encounter_id = None
                            gallery_section_label = _GALLERY_HUB_MENU_ITEMS[4]
                            gallery_page_index = 0
                            gallery_slot_index = 0
                            screen_mode = Screen.GALLERY
                elif screen_mode is Screen.GALLERY:
                    if gallery_view_reward_slot is not None:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            gallery_view_reward_slot = None
                    elif gallery_view_encounter_id is not None:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            gallery_view_encounter_id = None
                    elif gallery_view_key is not None:
                        _gv_meta = ENDINGS.get(gallery_view_key)
                        _gv_max = (
                            _ending_cg_page_index(_gv_meta)
                            if _gv_meta is not None
                            else 0
                        )
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            gallery_view_page_index = max(
                                0, gallery_view_page_index - 1
                            )
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            gallery_view_page_index = min(
                                _gv_max, gallery_view_page_index + 1
                            )
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            gallery_view_key = None
                            gallery_view_page_index = 0
                    elif gallery_view_companion_key is not None:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            gallery_view_companion_key = None
                    elif gallery_grid_mode == "reward":
                        reward_slots_nav = sorted_reward_gallery_slots_for_display(
                            all_reward_gallery_slots(
                                gallery_unlocked, _GAME_ASSET_ROOT
                            )
                        )
                        keys_here = _gallery_keys_on_page(
                            gallery_page_index, reward_slots_nav
                        )
                        n_sp = len(keys_here)
                        g_pc = _gallery_page_count(reward_slots_nav)
                        if event.key == pygame.K_PAGEUP:
                            if gallery_page_index > 0:
                                gallery_page_index -= 1
                                keys_prev = _gallery_keys_on_page(
                                    gallery_page_index, reward_slots_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_prev) - 1)
                                )
                        elif event.key == pygame.K_PAGEDOWN:
                            if gallery_page_index < g_pc - 1:
                                gallery_page_index += 1
                                keys_next = _gallery_keys_on_page(
                                    gallery_page_index, reward_slots_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_next) - 1)
                                )
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            n = _gallery_neighbor_slot(gallery_slot_index, "up", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            n = _gallery_neighbor_slot(gallery_slot_index, "down", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            n = _gallery_neighbor_slot(gallery_slot_index, "left", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            n = _gallery_neighbor_slot(
                                gallery_slot_index, "right", n_sp
                            )
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if 0 <= gallery_slot_index < n_sp:
                                sel_slot = keys_here[gallery_slot_index]
                                if (
                                    isinstance(sel_slot, tuple)
                                    and len(sel_slot) == 5
                                    and isinstance(sel_slot[0], str)
                                    and isinstance(sel_slot[1], str)
                                    and isinstance(sel_slot[2], tuple)
                                    and (
                                        sel_slot[3] is None
                                        or isinstance(sel_slot[3], str)
                                    )
                                    and isinstance(sel_slot[4], bool)
                                ):
                                    _r_rel = sel_slot[1]
                                    _r_revealed = sel_slot[4]
                                    if not _r_revealed:
                                        toast_message = (
                                            "尚未達成此格所列全部角色結局，解鎖後即可欣賞 CG"
                                        )
                                        toast_until = now_ms + 2200
                                    elif _reward_can_open_fullscreen(_r_rel):
                                        gallery_view_reward_slot = (
                                            sel_slot[0],
                                            sel_slot[1],
                                            sel_slot[2],
                                            sel_slot[3],
                                        )
                    elif gallery_grid_mode == "encounter":
                        enc_nav = ENCOUNTER_GALLERY_ORDER
                        keys_here = _gallery_keys_on_page(
                            gallery_page_index, enc_nav
                        )
                        n_sp = len(keys_here)
                        g_pc = _gallery_page_count(enc_nav)
                        if event.key == pygame.K_PAGEUP:
                            if gallery_page_index > 0:
                                gallery_page_index -= 1
                                keys_prev = _gallery_keys_on_page(
                                    gallery_page_index, enc_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_prev) - 1)
                                )
                        elif event.key == pygame.K_PAGEDOWN:
                            if gallery_page_index < g_pc - 1:
                                gallery_page_index += 1
                                keys_next = _gallery_keys_on_page(
                                    gallery_page_index, enc_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_next) - 1)
                                )
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            n = _gallery_neighbor_slot(gallery_slot_index, "up", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            n = _gallery_neighbor_slot(gallery_slot_index, "down", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            n = _gallery_neighbor_slot(gallery_slot_index, "left", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            n = _gallery_neighbor_slot(
                                gallery_slot_index, "right", n_sp
                            )
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if 0 <= gallery_slot_index < n_sp:
                                eid = keys_here[gallery_slot_index]
                                if eid not in enemy_gallery_unlocked:
                                    toast_message = "戰勝該敵後解鎖此 CG"
                                    toast_until = now_ms + 2200
                                else:
                                    gallery_view_encounter_id = eid
                    elif gallery_grid_mode == "companion":
                        comp_nav = companion_gallery_key_order(_GAME_ASSET_ROOT)
                        keys_here = _gallery_keys_on_page(
                            gallery_page_index, comp_nav
                        )
                        n_sp = len(keys_here)
                        g_pc = _gallery_page_count(comp_nav)
                        if event.key == pygame.K_PAGEUP:
                            if gallery_page_index > 0:
                                gallery_page_index -= 1
                                keys_prev = _gallery_keys_on_page(
                                    gallery_page_index, comp_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_prev) - 1)
                                )
                        elif event.key == pygame.K_PAGEDOWN:
                            if gallery_page_index < g_pc - 1:
                                gallery_page_index += 1
                                keys_next = _gallery_keys_on_page(
                                    gallery_page_index, comp_nav
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_next) - 1)
                                )
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            n = _gallery_neighbor_slot(gallery_slot_index, "up", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            n = _gallery_neighbor_slot(gallery_slot_index, "down", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            n = _gallery_neighbor_slot(gallery_slot_index, "left", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            n = _gallery_neighbor_slot(
                                gallery_slot_index, "right", n_sp
                            )
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if 0 <= gallery_slot_index < n_sp:
                                cg_key = keys_here[gallery_slot_index]
                                if cg_key not in companion_gallery_unlocked:
                                    toast_message = "尚未解鎖此夥伴 CG"
                                    toast_until = now_ms + 2200
                                else:
                                    gallery_view_companion_key = cg_key
                    else:
                        keys_here = _gallery_keys_on_page(
                            gallery_page_index, gallery_active_keys
                        )
                        n_sp = len(keys_here)
                        g_pc = _gallery_page_count(gallery_active_keys)
                        if event.key == pygame.K_PAGEUP:
                            if gallery_page_index > 0:
                                gallery_page_index -= 1
                                keys_prev = _gallery_keys_on_page(
                                    gallery_page_index, gallery_active_keys
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_prev) - 1)
                                )
                        elif event.key == pygame.K_PAGEDOWN:
                            if gallery_page_index < g_pc - 1:
                                gallery_page_index += 1
                                keys_next = _gallery_keys_on_page(
                                    gallery_page_index, gallery_active_keys
                                )
                                gallery_slot_index = min(
                                    gallery_slot_index, max(0, len(keys_next) - 1)
                                )
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            n = _gallery_neighbor_slot(gallery_slot_index, "up", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            n = _gallery_neighbor_slot(gallery_slot_index, "down", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            n = _gallery_neighbor_slot(gallery_slot_index, "left", n_sp)
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            n = _gallery_neighbor_slot(
                                gallery_slot_index, "right", n_sp
                            )
                            if n is not None:
                                gallery_slot_index = n
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if 0 <= gallery_slot_index < n_sp:
                                ek = keys_here[gallery_slot_index]
                                if _gallery_can_open_fullscreen(ek, gallery_unlocked):
                                    gallery_view_key = ek
                                    gallery_view_page_index = 0
                                else:
                                    toast_message = "尚未解鎖此通關 CG"
                                    toast_until = now_ms + 2200

        # 最後一季按下訓練後，同一幀內 time_left 已歸零但仍在 PLAY，且可能尚有培養回饋（training_fx）或
        # 已排程之 EVENT_ALERT／ENDING（pending_play_transition）。若此處不等待，會搶先進 ENDING，導致
        # 「16→17 那次回饋」與 17 歲重大事件整段被跳過。
        if (
            screen_mode is Screen.PLAY
            and state.time_left <= 0
            and ending_page_index is None
            and state.onboarding_complete
            and training_fx_action_key is None
            and pending_play_transition is None
        ):
            ending_cached = resolve_ending(state)
            ending_page_index = 0
            screen_mode = Screen.ENDING

        if (
            screen_mode is Screen.ENCOUNTER_BATTLE
            and encounter_phase == 0
            and encounter_battle_outcome is not None
        ):
            nfr = len(encounter_battle_outcome.frames) - 1
            if (
                encounter_frame_index < nfr
                and tick % ENCOUNTER_BATTLE_TICKS_PER_STEP == 0
            ):
                encounter_frame_index += 1

        sync_bgm()

        if screen_mode is Screen.TITLE:
            draw_title_screen(
                canvas,
                title_main,
                title_sub,
                title_menu_font,
                title_hint_font,
                title_menu_index,
                star_xy,
                tick,
            )
        elif screen_mode is Screen.CHEAT_MENU:
            draw_cheat_menu_screen(
                canvas,
                title_menu_font,
                title_hint_font,
                cheat_menu_index,
                cheat_menu_extras_unlocked,
                cheat_gallery_all_on,
                cheat_bootstrap_on,
                not cheat_bgm_muted,
                cheat_menu_modal,
                star_xy,
                tick,
            )
        elif screen_mode is Screen.FRIEREN_QUIZ:
            if frieren_quiz_phase is FrierenQuizPhase.CONFIRM:
                draw_frieren_quiz_confirm(
                    canvas,
                    menu_font=frieren_quiz_font,
                    small_font=frieren_quiz_font,
                    hint_font=title_hint_font,
                    star_xy=star_xy,
                    tick=tick,
                )
            else:
                q_round_1 = (
                    frieren_quiz_round_idx + 1
                    if frieren_quiz_phase
                    in (FrierenQuizPhase.QUESTION, FrierenQuizPhase.FEEDBACK)
                    else FRIEREN_QUIZ_NUM_QUESTIONS
                )
                draw_frieren_quiz_screen(
                    canvas,
                    menu_font=frieren_quiz_font,
                    small_font=frieren_quiz_font,
                    intro_font=frieren_quiz_font,
                    hint_font=title_hint_font,
                    seal_font=frieren_quiz_seal_font,
                    phase=frieren_quiz_phase,
                    question=frieren_quiz_active_question,
                    perm=frieren_quiz_perm,
                    option_index=frieren_quiz_option_index,
                    q_round_1based=q_round_1,
                    score=frieren_quiz_score,
                    feedback_correct=frieren_quiz_feedback_correct,
                    chosen_slot=frieren_quiz_chosen_slot,
                    perm_for_feedback=frieren_quiz_perm_feedback,
                    certificate_earned_before=frieren_quiz_cert_earned,
                    certificate_just_earned=frieren_quiz_cert_just_earned,
                    star_xy=star_xy,
                    tick=tick,
                )
        elif screen_mode is Screen.CHEAT_GALLERY_HINTS:
            draw_cheat_ending_hints_screen(
                canvas,
                title_menu_font,
                small_font,
                star_xy,
                tick,
                cheat_hint_page_index,
                cheat_hint_gender,
                cheat_hint_gender_menu_index,
            )
        elif screen_mode is Screen.GALLERY_HUB:
            draw_gallery_hub_screen(
                canvas,
                title_menu_font,
                title_hint_font,
                gallery_hub_index,
                star_xy,
                tick,
            )
        elif screen_mode is Screen.GALLERY:
            if gallery_view_reward_slot is not None:
                _rv_tok, _rv_rel, _rv_ko, _rv_note = gallery_view_reward_slot
                if _resolve_ending_cg_disk_path(_rv_rel) is None:
                    gallery_view_reward_slot = None
                else:
                    draw_reward_cg_fullscreen(
                        canvas,
                        small_font,
                        _rv_rel,
                        reward_token_label_zh(
                            _rv_tok,
                            filename_key_order=_rv_ko,
                        ),
                        state,
                        tick,
                        reward_token=_rv_tok,
                        reward_filename_key_order=_rv_ko,
                        reward_note_zh=_rv_note,
                    )
            elif gallery_view_encounter_id is not None:
                draw_encounter_cg_fullscreen(
                    canvas,
                    small_font,
                    gallery_view_encounter_id,
                    _GAME_ASSET_ROOT,
                    tick,
                )
            elif gallery_view_key is not None:
                draw_gallery_ending_pages(
                    canvas,
                    intro_font,
                    small_font,
                    font,
                    gallery_view_key,
                    gallery_view_page_index,
                    state,
                    tick,
                )
            elif gallery_view_companion_key is not None:
                draw_companion_cg_fullscreen(
                    canvas,
                    small_font,
                    gallery_view_companion_key,
                    _GAME_ASSET_ROOT,
                    tick,
                )
            elif gallery_grid_mode == "reward":
                _rslots = sorted_reward_gallery_slots_for_display(
                    all_reward_gallery_slots(
                        gallery_unlocked, _GAME_ASSET_ROOT
                    )
                )
                draw_reward_gallery_screen(
                    canvas,
                    title_menu_font,
                    small_font,
                    gallery_page_index,
                    gallery_slot_index,
                    _rslots,
                    gallery_section_label,
                    star_xy,
                    tick,
                )
            elif gallery_grid_mode == "encounter":
                draw_encounter_gallery_screen(
                    canvas,
                    title_menu_font,
                    small_font,
                    gallery_page_index,
                    gallery_slot_index,
                    enemy_gallery_unlocked,
                    gallery_section_label,
                    _GAME_ASSET_ROOT,
                    star_xy,
                    tick,
                )
            elif gallery_grid_mode == "companion":
                draw_companion_gallery_screen(
                    canvas,
                    title_menu_font,
                    small_font,
                    gallery_page_index,
                    gallery_slot_index,
                    companion_gallery_unlocked,
                    companion_gallery_key_order(_GAME_ASSET_ROOT),
                    gallery_section_label,
                    _GAME_ASSET_ROOT,
                    star_xy,
                    tick,
                )
            else:
                draw_ending_gallery_screen(
                    canvas,
                    title_menu_font,
                    small_font,
                    gallery_page_index,
                    gallery_slot_index,
                    gallery_unlocked,
                    gallery_active_keys,
                    gallery_section_label,
                    star_xy,
                    tick,
                )
        elif screen_mode is Screen.INTRO:
            draw_intro_screen(
                canvas,
                intro_font,
                small_font,
                intro_page_index,
                intro_pages,
                PROLOGUE_SECTION_HEADERS,
                tick,
            )
        elif screen_mode is Screen.GUARDIAN_INTRO:
            draw_guardian_intro_screen(
                canvas,
                guardian_header_font,
                guardian_body_font,
                small_font,
                guardian_pages,
                tick,
                onboarding_font=intro_font,
                name_entry_step=name_entry_step,
                name_entry_gender_index=name_entry_gender_index,
                name_buffer=name_buffer,
                ime_composition=ime_composition,
            )
        elif screen_mode is Screen.ADOPTER_QUESTIONNAIRE:
            if adopter_quiz_show_result:
                draw_adopter_questionnaire_result_screen(
                    canvas,
                    intro_font,
                    small_font,
                    adopter_quiz_judgment_zh,
                    adopter_quiz_merged,
                    star_xy,
                    tick,
                )
            else:
                draw_adopter_questionnaire_screen(
                    canvas,
                    intro_font,
                    intro_font,
                    adopter_quiz_q_index,
                    adopter_quiz_choice,
                    star_xy,
                    tick,
                )
        elif screen_mode is Screen.CONTRACT_SEAL:
            draw_contract_seal_screen(
                canvas,
                intro_font,
                small_font,
                contract_signature_font,
                state.heroine_name,
                contract_seal_anim_frame,
                contract_seal_anim_frame >= _CONTRACT_SEAL_ANIM_DONE_AT,
            )
        elif screen_mode is Screen.SLOT_SELECT:
            draw_slot_select_screen(
                canvas,
                title_menu_font,
                title_hint_font,
                slot_cursor,
                star_xy,
                tick,
            )
        elif screen_mode is Screen.SAVE_SLOT:
            draw_save_slot_screen(canvas, font, small_font, slot_cursor)
        elif screen_mode is Screen.EVENT_ALERT:
            draw_event_alert_screen(
                canvas,
                event_alert_title_font,
                event_alert_teaser_font,
                small_font,
                event_alert_major_age,
                tick,
                event_alert_is_encounter=event_alert_is_encounter,
                event_alert_is_whim=event_alert_is_whim,
                encounter_alert_age=encounter_alert_age,
                protagonist_gender=getattr(
                    state, "protagonist_gender", "female"
                ),
            )
        elif (
            screen_mode is Screen.WHIM_EVENT
            and active_whim_encounter is not None
            and active_whim_question is not None
        ):
            draw_whim_event_screen(
                canvas,
                title_font=font,
                intro_font=intro_font,
                small_font=small_font,
                font=font,
                tick=tick,
                phase=whim_phase,
                encounter=active_whim_encounter,
                question=active_whim_question,
                option_index=whim_option_index,
                chosen_index=whim_chosen_index,
                is_correct=whim_is_correct,
                aftermath_page_index=whim_aftermath_page_index,
                stat_effect_full_line=whim_stat_effect_full_line,
                asset_root=_GAME_ASSET_ROOT,
                protagonist_gender=getattr(
                    state, "protagonist_gender", "female"
                ),
                option_perm=whim_option_perm,
            )
        elif screen_mode is Screen.INCIDENT and active_incident is not None:
            if incident_phase == 1 and incident_chosen_index is not None:
                _ix_af = incident_chosen_index
                _inc_stat_line = _TRAINING_FEEDBACK_MODAL_STAT_PREFIX + format_incident_deltas_brief(
                    active_incident.options[_ix_af].deltas
                )
                draw_incident_aftermath_screen(
                    canvas,
                    intro_font,
                    small_font,
                    active_incident,
                    incident_chosen_index,
                    aftermath_page_index,
                    _inc_stat_line,
                    tick,
                )
            else:
                draw_incident_screen(
                    canvas, font, small_font, active_incident, incident_option_index
                )
        elif (
            screen_mode is Screen.ENCOUNTER_BATTLE
            and active_encounter_enemy is not None
            and encounter_battle_outcome is not None
        ):
            en = active_encounter_enemy
            bo = encounter_battle_outcome
            if encounter_phase == 0:
                draw_encounter_battle_screen(
                    canvas,
                    font,
                    small_font,
                    state,
                    en,
                    bo,
                    encounter_frame_index,
                    _GAME_ASSET_ROOT,
                    tick,
                )
            else:
                paras = en.aftermath_win if bo.win else en.aftermath_lose
                pl = format_encounter_deltas_brief(bo.participation_deltas)
                tr = (
                    format_encounter_deltas_brief(bo.treasure_deltas)
                    if bo.win and bo.treasure_deltas
                    else ""
                )
                stat_part = _TRAINING_FEEDBACK_MODAL_STAT_PREFIX + pl
                stat_tr = ("寶物加成：" + tr) if tr else ""
                _has_tr = bool(bo.win and bo.treasure_deltas)
                draw_encounter_aftermath_screen(
                    canvas,
                    intro_font,
                    small_font,
                    en,
                    bo.win,
                    paras,
                    stat_part,
                    stat_tr,
                    aftermath_has_treasure=_has_tr,
                    aftermath_treasure_name_zh=(
                        en.treasure_name_zh if _has_tr else None
                    ),
                    protagonist_gender=getattr(
                        state, "protagonist_gender", "female"
                    ),
                    tick=tick,
                )
        elif screen_mode is Screen.MAJOR_EVENT and active_major_event is not None:
            me = active_major_event
            if major_event_phase == 0:
                draw_major_event_preamble_screen(
                    canvas, intro_font, small_font, me, tick
                )
            elif major_event_phase == 1:
                draw_major_event_choice_screen(
                    canvas, font, small_font, me, major_event_option_index, tick
                )
            elif major_event_chosen is not None:
                _ch_af = major_event_chosen
                _maj_stat_line = _TRAINING_FEEDBACK_MODAL_STAT_PREFIX + _major_option_effect_line(
                    me.options[_ch_af]
                )
                draw_major_event_resolution_screen(
                    canvas,
                    intro_font,
                    small_font,
                    me,
                    major_event_chosen,
                    aftermath_page_index,
                    _maj_stat_line,
                    tick,
                )
        elif screen_mode is Screen.ENDING and ending_cached is not None:
            ep = 0 if ending_page_index is None else ending_page_index
            _cg_i = _ending_cg_page_index(ending_cached)
            if ep >= _cg_i:
                draw_ending_cg_screen(
                    canvas, font, small_font, ending_cached, state, tick
                )
            else:
                draw_ending_narrative_screen(
                    canvas,
                    intro_font,
                    small_font,
                    ending_cached,
                    ep,
                    tick,
                )
        elif screen_mode is Screen.PLAY:
            draw_playing_hud(canvas, font, small_font, state, tick, training_menu_index)

        _fx_gender = getattr(state, "protagonist_gender", "female")
        if (
            screen_mode is Screen.PLAY
            and training_fx_action_key is not None
            and toast_message
        ):
            draw_training_feedback_modal(
                canvas,
                small_font,
                _get_play_footer_font(),
                toast_message,
                training_fx_action_key,
                now_ms,
                _fx_gender,
            )
        elif toast_message and toast_until > 0 and now_ms < toast_until:
            draw_toast(canvas, small_font, toast_message)
        elif toast_message and toast_until > 0 and now_ms >= toast_until:
            toast_message = ""

        if screen_mode is Screen.GUARDIAN_INTRO and name_entry_step == 1:
            _set_text_input_rect_for_screen(
                screen,
                _guardian_panel_name_field_rect(small_font, intro_font, name_entry_step),
            )

        if screen_mode is Screen.CONTRACT_SEAL and contract_seal_anim_frame < _CONTRACT_SEAL_ANIM_DONE_AT:
            contract_seal_anim_frame += 1

        sw, sh = screen.get_size()
        sx = sw / CANVAS_WIDTH
        sy = sh / CANVAS_HEIGHT
        scale = min(sx, sy)
        nw = int(CANVAS_WIDTH * scale)
        nh = int(CANVAS_HEIGHT * scale)
        scaled = pygame.transform.scale(canvas, (nw, nh))
        screen.fill((10, 10, 14))
        screen.blit(scaled, ((sw - nw) // 2, (sh - nh) // 2))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()