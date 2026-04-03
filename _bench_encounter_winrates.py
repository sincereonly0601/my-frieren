"""
蒙地卡羅估算遭遇戰勝率（呼叫與遊戲相同之 ``simulate_encounter``）。

假設：滿 6／11／16 歲觸發時，以對應季數與數種養成分佈建立 ``GameState``。
"""

from __future__ import annotations

import random
from collections import defaultdict
from encounter_defs import ENCOUNTER_BY_ID, EncounterEnemy
from encounter_sim import simulate_encounter
from game_state import GameState, START_AGE_MONTHS, TOTAL_TRAINING_QUARTERS

_STAT_KEYS: tuple[str, ...] = (
    "int_stat",
    "str_stat",
    "fth_stat",
    "pragmatic",
    "romantic",
    "solitude",
    "social",
)


def _time_left_at_age_years(age_years: int) -> int:
    """滿 ``age_years`` 歲當下（以 age_months 對齊）之剩餘季數。"""
    age_months = age_years * 12
    spent = (age_months - START_AGE_MONTHS) // 3
    return TOTAL_TRAINING_QUARTERS - spent


def _state_with_total_stats(age_years: int, total: int, rng: random.Random) -> GameState:
    """
    建立指定年齡、七維總和為 ``total`` 之狀態（隨機分配，每維至少 0）。
    """
    tl = _time_left_at_age_years(age_years)
    base = GameState(time_left=tl)
    parts = [0] * 7
    for _ in range(total):
        parts[rng.randrange(7)] += 1
    for k, v in zip(_STAT_KEYS, parts):
        setattr(base, k, v)
    return base


def _state_even(age_years: int, per_stat: int) -> GameState:
    """七維皆為 ``per_stat``。"""
    tl = _time_left_at_age_years(age_years)
    g = GameState(time_left=tl)
    for k in _STAT_KEYS:
        setattr(g, k, per_stat)
    return g


def _enemies_by_tier() -> dict[str, list[EncounterEnemy]]:
    out: dict[str, list[EncounterEnemy]] = defaultdict(list)
    for e in ENCOUNTER_BY_ID.values():
        out[e.tier].append(e)
    return dict(out)


def main() -> None:
    rng_master = random.Random(20260327)
    tiers_age = {"monster": 6, "elite": 11, "boss": 16}
    by_tier = _enemies_by_tier()

    # 參考建置：偏弱／中庸／偏強（七維總和；同齡隨機分配跑一輪、全均等跑一輪）
    total_profiles: list[tuple[str, int]] = [
        ("弱(總和約80)", 80),
        ("中(總和約180)", 180),
        ("強(總和約320)", 320),
    ]
    even_profiles: list[tuple[str, int]] = [
        ("七維均等10", 10),
        ("七維均等25", 25),
        ("七維均等45", 45),
    ]

    trials_random = 4000
    trials_even = 2000

    print("=== 遭遇戰勝率蒙地卡羅（與主程式相同 simulate_encounter）===\n")
    print("年齡對應池：6 歲→魔物、11 歲→強敵、16 歲→頭目。\n")

    for tier, age in tiers_age.items():
        enemies = by_tier[tier]
        print(f"--- {tier}（滿 {age} 歲池，共 {len(enemies)} 名敵人）---")

        for label, total in total_profiles:
            wins = 0
            for _ in range(trials_random):
                st = _state_with_total_stats(age, total, rng_master)
                e = rng_master.choice(enemies)
                r = random.Random(rng_master.randrange(1 << 30))
                if simulate_encounter(e, st, r).win:
                    wins += 1
            wr = 100.0 * wins / trials_random
            print(
                f"  七維隨機分配·{label}（總和={total}）："
                f"平均勝率 {wr:.1f}%（{trials_random} 場／每場隨機抽池內敵人）"
            )

        for label, per in even_profiles:
            wins_e = 0
            st = _state_even(age, per)
            for _ in range(trials_even):
                e = rng_master.choice(enemies)
                r = random.Random(rng_master.randrange(1 << 30))
                if simulate_encounter(e, st, r).win:
                    wins_e += 1
            wr_e = 100.0 * wins_e / trials_even
            print(
                f"  七維均等·{label}（每維={per}）："
                f"平均勝率 {wr_e:.1f}%（{trials_even} 場）"
            )

        # 每名敵人：中庸總和 180、隨機分配
        print("  單敵（總和180 隨機分配，每敵 800 場）：")
        for e in sorted(enemies, key=lambda x: x.id):
            w = 0
            for _ in range(800):
                st = _state_with_total_stats(age, 180, rng_master)
                r = random.Random(rng_master.randrange(1 << 30))
                if simulate_encounter(e, st, r).win:
                    w += 1
            print(f"    {e.id:28} {e.name_zh:12} 勝率 {100.0 * w / 800:.1f}%")
        print()

    print("--- 補充：頭目池（16 歲）較高七維總和（隨機分配，每組 5000 場）---")
    rng2 = random.Random(4242)
    bosses = by_tier["boss"]
    for total in (400, 500, 600, 700, 800):
        wins = 0
        trials = 5000
        for _ in range(trials):
            st = _state_with_total_stats(16, total, rng2)
            e = rng2.choice(bosses)
            r = random.Random(rng2.randrange(1 << 30))
            if simulate_encounter(e, st, r).win:
                wins += 1
        print(f"  總和={total}: 平均勝率 {100.0 * wins / trials:.1f}%")


if __name__ == "__main__":
    main()
