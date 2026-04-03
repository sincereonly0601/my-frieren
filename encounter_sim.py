"""
遭遇戰：由養成數值推導戰鬥面板，並以全自動回合結算勝負與動畫影格。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from encounter_defs import EncounterEnemy, ENCOUNTER_PARTICIPATION_DELTAS
from game_state import GameState

# --- 遭遇戰平衡常數（集中於此檔調參）---
# 敵人資料表 ``base_hp``／``base_atk``／``base_def`` 先乘此係數再進入後續公式（拉高面板顯示與威脅感）。
_ENCOUNTER_BASE_STAT_MULT: float = 1.15
# 雙方生命上限同乘，拉長交鋒；數值僅影響戰鬥播映，不改養成欄位。
_COMBAT_HP_POOL_SCALE: float = 3.0
# 敵方生命在共用放大後再乘（愈高愈耐打、愈易逼出敗北／超時）。
_ENEMY_HP_STRESS_MULT: float = 1.88
# 敵方攻／防加壓（相對於原 base × difficulty 係數）。
_ENEMY_ATK_STRESS_MULT: float = 2.02
_ENEMY_DEF_STRESS_MULT: float = 1.60
# 依敵人所屬池（6／11／16 歲）再乘算最終攻防血（與上列 ``_ENCOUNTER_BASE_STAT_MULT`` 一併校準勝率）。
_ENEMY_TIER_PANEL_MULT: dict[str, float] = {
    "monster": 1.556,
    "elite": 2.313,
    "boss": 2.505,
}
# 各池最終敵方攻防血再乘此係數（<1 ＝ 變簡單；愈接近 1 愈難）。
# ``player_combat_stats`` 改為七維參與後我方面板整體偏高，此處再拉高約一成餘，避免遭遇戰過於碾壓。
_ENCOUNTER_ENEMY_EASE_BY_TIER: dict[str, float] = {
    "monster": 0.34,
    "elite": 0.46,
    "boss": 0.46,
}
# 敵方最終攻／防／生命上限於上列係數全部疊算後再乘（1.0 ＝不變；>1 整體加難）。
_ENCOUNTER_ENEMY_FINAL_POWER_MULT: float = 1.22
# 於 ``_ENCOUNTER_ENEMY_FINAL_POWER_MULT`` 之後再乘；同時放大敵方攻／防／生命上限（整體強度倍率）。
_ENCOUNTER_ENEMY_OVERALL_MULT: float = 1.14
# 敵方最終攻／防／生命上限於 ``fpm * ovm`` 之後再乘（1.2 ＝在調整前平衡上整體加難兩成）。
_ENCOUNTER_ENEMY_DIFFICULTY_MULT: float = 1.12
# 傷害公式中防禦折減係數（愈大則單發傷害愈低、戰線愈長）。
_DAMAGE_DEF_FACTOR: float = 0.36
# 單回合：我方先攻 → 敵方還擊；此為「我方先攻次數」上限。
_MAX_ENCOUNTER_ROUNDS: int = 64
_PROB_PLAYER_ULTIMATE: float = 0.09
# 敵方大招機率底＋每點 difficulty 加成（上限仍低於 1）。
_ENEMY_ULT_BASE: float = 0.125
_ENEMY_ULT_PER_DIFF: float = 0.041


@dataclass(frozen=True)
class BattleFrame:
    """
    單一戰鬥播映影格（供 UI 顯示血條與字幕）。

    Attributes:
        player_hp: 我方剩餘生命。
        enemy_hp: 敵方剩餘生命。
        player_hp_max: 我方生命上限。
        enemy_hp_max: 敵方生命上限。
        banner_zh: 本回合說明（一句）。
    """

    player_hp: int
    enemy_hp: int
    player_hp_max: int
    enemy_hp_max: int
    banner_zh: str


@dataclass(frozen=True)
class BattleOutcome:
    """
    遭遇戰完整結算結果。

    Attributes:
        win: 是否勝利。
        frames: 依序播放之影格（每回合通常兩格：我方行動 → 敵方還擊）。
        participation_deltas: 勝敗皆套用。
        treasure_deltas: 僅勝利時非空；敗北為空字典。
        player_atk: 結算用我方攻擊面板。
        player_def: 結算用我方防禦面板。
        enemy_atk: 結算用敵方攻擊面板。
        enemy_def: 結算用敵方防禦面板。
    """

    win: bool
    frames: tuple[BattleFrame, ...]
    participation_deltas: dict[str, int]
    treasure_deltas: dict[str, int]
    player_atk: int
    player_def: int
    enemy_atk: int
    enemy_def: int


def player_combat_stats(state: GameState) -> tuple[int, int, int]:
    """
    由養成數值推算戰鬥用生命、攻擊、防禦。

    僅五維（智力／力量／社交／信仰／務實）參與戰鬥面板換算。

    - 生命：力量／信仰／務實為體幹；智力與社交折半加總。
    - 攻擊：智力為魔式主軸（係數 5/3）；力量為直擊補正；信仰與務實合計取三分之一作穩定輸出。
    - 防禦：務實為戰術根底；信仰折半；智力與社交合取三分之一（術式與協調）；力量折半（肉體耐打）。

    Args:
        state: 目前遊戲狀態。

    Returns:
        ``(max_hp, atk, defense)`` 皆為正整數。
    """
    i = state.int_stat
    s = state.str_stat
    f = state.fth_stat
    p = state.pragmatic
    soc = state.social

    hp = 32 + s + f + p + (i + soc) // 2
    atk = 8 + (i * 5 // 3) + s + (f + p) // 3
    defense = 4 + p + f // 2 + (i + soc) // 3 + s // 2

    hp = max(24, hp)
    atk = max(6, atk)
    defense = max(3, defense)
    return hp, atk, defense


def _roll_damage(
    rng: random.Random,
    atk: int,
    defense: int,
    *,
    ultimate: bool,
) -> int:
    """
    依攻防與是否大招計算單次傷害（含亂數）。

    Args:
        rng: 亂數來源。
        atk: 攻擊方面板攻擊。
        defense: 守備方面板防禦。
        ultimate: 是否為大招（傷害區間較寬、期望較高）。

    Returns:
        至少為 1 的整數傷害。
    """
    base = atk - int(defense * _DAMAGE_DEF_FACTOR)
    base = max(2, base)
    if ultimate:
        base = int(base * rng.uniform(2.0, 2.75))
    else:
        base = int(base * rng.uniform(0.85, 1.15))
    return max(1, base)


def _protagonist_you_zh(state: GameState) -> str:
    """
    戰報第二人稱：女性路線為「妳」，男性路線為「你」。

    Args:
        state: 遊戲狀態（讀 ``protagonist_gender``）。

    Returns:
        單一字元稱謂字串。
    """
    return "你" if getattr(state, "protagonist_gender", "female") == "male" else "妳"


def _player_move_name(rng: random.Random, ultimate: bool) -> str:
    """我方招式顯示名。"""
    if ultimate:
        return rng.choice(
            (
                "殺戮魔彈（節制詠唱）",
                "索利泰爾式連射",
                "障壁內爆",
                "拘束術式・改",
                "魔力收束・極",
            )
        )
    return rng.choice(
        (
            "普通魔彈",
            "障壁推移",
            "光術收束・刺眼一閃",
            "魔力貫穿・直線轟擊",
            "飛行術式・低空掠擊",
            "治癒術・止血優先",
        )
    )


def simulate_encounter(
    enemy: EncounterEnemy,
    state: GameState,
    rng: random.Random,
) -> BattleOutcome:
    """
    模擬一場全自動遭遇戰直到一方倒地或達回合上限。

    雙方每回合我方先攻、敵方還擊；不定期觸發大招。生命上限經池化放大以拉長戰線，
    敵方並有額外生命／攻防加壓與依池別（魔物／強敵／頭目）之面板係數；再經
    ``_ENCOUNTER_ENEMY_EASE_BY_TIER``、``_ENCOUNTER_ENEMY_FINAL_POWER_MULT``、
    ``_ENCOUNTER_ENEMY_OVERALL_MULT`` 與 ``_ENCOUNTER_ENEMY_DIFFICULTY_MULT`` 調整敵方最終面板
    （需與 ``player_combat_stats`` 一併校準）。
    防禦在傷害式中有折減。若達回合上限仍雙方存活，判敗並補上一則說明影格。

    Args:
        enemy: 敵人資料。
        state: 遊戲狀態（讀取數值；不修改）。
        rng: 亂數來源。

    Returns:
        勝負、影格序列與獎勵增量。
    """
    php_max, patk, pdef = player_combat_stats(state)
    tier_mul = 1.0 + 0.065 * int(enemy.difficulty)
    bsm = _ENCOUNTER_BASE_STAT_MULT
    ehp_raw = max(20, int(enemy.base_hp * bsm * tier_mul))
    eatk_raw = max(6, int(enemy.base_atk * bsm * tier_mul))
    edef_raw = max(3, int(enemy.base_def * bsm * tier_mul))
    eatk = max(6, int(eatk_raw * _ENEMY_ATK_STRESS_MULT))
    edef = max(3, int(edef_raw * _ENEMY_DEF_STRESS_MULT))
    php_max = max(
        1,
        int(round(php_max * _COMBAT_HP_POOL_SCALE)),
    )
    ehp_max = max(
        1,
        int(round(ehp_raw * _COMBAT_HP_POOL_SCALE * _ENEMY_HP_STRESS_MULT)),
    )
    tier_mul_panel = float(_ENEMY_TIER_PANEL_MULT.get(enemy.tier, 1.0))
    eatk = max(6, int(round(eatk * tier_mul_panel)))
    edef = max(3, int(round(edef * tier_mul_panel)))
    ehp_max = max(1, int(round(ehp_max * tier_mul_panel)))
    ease = float(_ENCOUNTER_ENEMY_EASE_BY_TIER.get(enemy.tier, 1.0))
    eatk = max(6, int(round(eatk * ease)))
    edef = max(3, int(round(edef * ease)))
    ehp_max = max(1, int(round(ehp_max * ease)))
    fpm = _ENCOUNTER_ENEMY_FINAL_POWER_MULT
    ovm = _ENCOUNTER_ENEMY_OVERALL_MULT
    diffm = _ENCOUNTER_ENEMY_DIFFICULTY_MULT
    eatk = max(6, int(round(eatk * fpm * ovm * diffm)))
    edef = max(3, int(round(edef * fpm * ovm * diffm)))
    ehp_max = max(1, int(round(ehp_max * fpm * ovm * diffm)))

    php = php_max
    ehp = ehp_max
    pyou = _protagonist_you_zh(state)
    frames: list[BattleFrame] = []
    frames.append(
        BattleFrame(
            php,
            ehp,
            php_max,
            ehp_max,
            "── 交鋒開始 ──",
        )
    )

    for _ in range(_MAX_ENCOUNTER_ROUNDS):
        if php <= 0 or ehp <= 0:
            break
        pu = rng.random() < _PROB_PLAYER_ULTIMATE
        eu = rng.random() < min(
            0.92,
            _ENEMY_ULT_BASE + _ENEMY_ULT_PER_DIFF * int(enemy.difficulty),
        )

        pm = _player_move_name(rng, pu)
        em = enemy.ultimate_zh if eu else rng.choice(enemy.move_names)

        dmg_e = _roll_damage(rng, patk, edef, ultimate=pu)
        dmg_p = _roll_damage(rng, eatk, pdef, ultimate=eu)

        ehp -= dmg_e
        frames.append(
            BattleFrame(
                max(0, php),
                max(0, ehp),
                php_max,
                ehp_max,
                f"【我方】{pyou}詠出「{pm}」，{enemy.name_zh} 受創 {dmg_e}。",
            )
        )
        if php <= 0 or ehp <= 0:
            break

        php -= dmg_p
        frames.append(
            BattleFrame(
                max(0, php),
                max(0, ehp),
                php_max,
                ehp_max,
                f"【敵方】{enemy.name_zh} 以「{em}」還擊，{pyou}受創 {dmg_p}。",
            )
        )
        if php <= 0 or ehp <= 0:
            break

    if php > 0 and ehp > 0:
        frames.append(
            BattleFrame(
                php,
                ehp,
                php_max,
                ehp_max,
                "── 鏖戰未絕，魔力與體勢先一步見底——此役判為落敗。 ──",
            )
        )

    if php <= 0 and ehp <= 0:
        win = rng.random() < 0.48
        frames.append(
            BattleFrame(
                0,
                0,
                php_max,
                ehp_max,
                "煙塵散去──"
                + (
                    f"{pyou}仍站著。"
                    if win
                    else f"{pyou}先跪倒；對方亦踉蹌，但戰果歸敵。"
                ),
            )
        )
    else:
        win = ehp <= 0 and php > 0

    if win:
        treasure = dict(enemy.treasure_deltas)
    else:
        treasure = {}

    return BattleOutcome(
        win=win,
        frames=tuple(frames),
        participation_deltas=dict(ENCOUNTER_PARTICIPATION_DELTAS),
        treasure_deltas=treasure,
        player_atk=patk,
        player_def=pdef,
        enemy_atk=eatk,
        enemy_def=edef,
    )
