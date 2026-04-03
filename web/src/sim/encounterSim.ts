/**
 * 遭遇戰自動結算（與桌面 `encounter_sim.py` 公式對齊）。
 */

import type { GameStateStored } from "../save/idbSave";
import type { EncounterEnemyJson } from "./types";
import type { SimRng } from "./rng";

const ENCOUNTER_BASE_STAT_MULT = 1.15;
const COMBAT_HP_POOL_SCALE = 3.0;
const ENEMY_HP_STRESS_MULT = 1.88;
const ENEMY_ATK_STRESS_MULT = 2.02;
const ENEMY_DEF_STRESS_MULT = 1.6;
const ENEMY_TIER_PANEL_MULT: Record<string, number> = {
  monster: 1.556,
  elite: 2.313,
  boss: 2.505,
};
const ENCOUNTER_ENEMY_EASE_BY_TIER: Record<string, number> = {
  monster: 0.438,
  elite: 0.478,
  boss: 0.428,
};
const ENCOUNTER_ENEMY_FINAL_POWER_MULT = 1.22;
const ENCOUNTER_ENEMY_OVERALL_MULT = 1.14;
/** 敵方最終攻／防／生命在 `fpm * ovm` 之後再乘（1.12 ＝較原本再小幅加壓；與 `encounter_sim.py` 一致） */
const ENCOUNTER_ENEMY_DIFFICULTY_MULT = 1.12;
const DAMAGE_DEF_FACTOR = 0.36;
const MAX_ENCOUNTER_ROUNDS = 64;
const PROB_PLAYER_ULTIMATE = 0.09;
const ENEMY_ULT_BASE = 0.125;
const ENEMY_ULT_PER_DIFF = 0.041;

/** 與桌面 `ENCOUNTER_PARTICIPATION_DELTAS` 一致 */
export const ENCOUNTER_PARTICIPATION_DELTAS: Record<string, number> = {
  int_stat: 2,
  str_stat: 2,
  fth_stat: 2,
  pragmatic: 2,
  social: 2,
};

export type BattleFrame = {
  player_hp: number;
  enemy_hp: number;
  player_hp_max: number;
  enemy_hp_max: number;
  banner_zh: string;
};

export type BattleOutcome = {
  win: boolean;
  frames: BattleFrame[];
  participation_deltas: Record<string, number>;
  treasure_deltas: Record<string, number>;
  player_atk: number;
  player_def: number;
  enemy_atk: number;
  enemy_def: number;
};

/**
 * 由養成數值推算戰鬥用生命、攻擊、防禦（與 `player_combat_stats` 一致）。
 *
 * @param state - 遊戲狀態
 */
export function playerCombatStats(state: GameStateStored): [number, number, number] {
  const i = state.int_stat;
  const s = state.str_stat;
  const f = state.fth_stat;
  const p = state.pragmatic;
  const soc = state.social;

  let hp = 32 + s + f + p + Math.floor((i + soc) / 2);
  let atk = 8 + Math.floor((i * 5) / 3) + s + Math.floor((f + p) / 3);
  let defense = 4 + p + Math.floor(f / 2) + Math.floor((i + soc) / 3) + Math.floor(s / 2);

  hp = Math.max(24, hp);
  atk = Math.max(6, atk);
  defense = Math.max(3, defense);
  return [hp, atk, defense];
}

function rollDamage(
  rng: SimRng,
  atk: number,
  defense: number,
  ultimate: boolean,
): number {
  let base = atk - Math.floor(defense * DAMAGE_DEF_FACTOR);
  base = Math.max(2, base);
  if (ultimate) {
    base = Math.floor(base * rng.uniform(2.0, 2.75));
  } else {
    base = Math.floor(base * rng.uniform(0.85, 1.15));
  }
  return Math.max(1, base);
}

function protagonistYouZh(state: GameStateStored): string {
  return state.protagonist_gender === "male" ? "你" : "妳";
}

function playerMoveName(rng: SimRng, ultimate: boolean): string {
  if (ultimate) {
    return rng.choice([
      "殺戮魔彈（節制詠唱）",
      "索利泰爾式連射",
      "障壁內爆",
      "拘束術式・改",
      "魔力收束・極",
    ]);
  }
  return rng.choice([
    "普通魔彈",
    "障壁推移",
    "光術收束・刺眼一閃",
    "魔力貫穿・直線轟擊",
    "飛行術式・低空掠擊",
    "治癒術・止血優先",
  ]);
}

/**
 * 模擬一場全自動遭遇戰（與桌面 `simulate_encounter` 一致）。
 *
 * @param enemy - 敵方資料
 * @param state - 養成狀態（僅讀取）
 * @param rng - 亂數源
 */
export function simulateEncounter(
  enemy: EncounterEnemyJson,
  state: GameStateStored,
  rng: SimRng,
): BattleOutcome {
  let [phpMax, patk, pdef] = playerCombatStats(state);
  const tierMul = 1.0 + 0.065 * enemy.difficulty;
  const bsm = ENCOUNTER_BASE_STAT_MULT;
  let ehpRaw = Math.max(20, Math.floor(enemy.base_hp * bsm * tierMul));
  let eatkRaw = Math.max(6, Math.floor(enemy.base_atk * bsm * tierMul));
  let edefRaw = Math.max(3, Math.floor(enemy.base_def * bsm * tierMul));
  let eatk = Math.max(6, Math.floor(eatkRaw * ENEMY_ATK_STRESS_MULT));
  let edef = Math.max(3, Math.floor(edefRaw * ENEMY_DEF_STRESS_MULT));
  phpMax = Math.max(1, Math.round(phpMax * COMBAT_HP_POOL_SCALE));
  let ehpMax = Math.max(
    1,
    Math.round(ehpRaw * COMBAT_HP_POOL_SCALE * ENEMY_HP_STRESS_MULT),
  );
  const tierMulPanel = ENEMY_TIER_PANEL_MULT[enemy.tier] ?? 1.0;
  eatk = Math.max(6, Math.round(eatk * tierMulPanel));
  edef = Math.max(3, Math.round(edef * tierMulPanel));
  ehpMax = Math.max(1, Math.round(ehpMax * tierMulPanel));
  const ease = ENCOUNTER_ENEMY_EASE_BY_TIER[enemy.tier] ?? 1.0;
  eatk = Math.max(6, Math.round(eatk * ease));
  edef = Math.max(3, Math.round(edef * ease));
  ehpMax = Math.max(1, Math.round(ehpMax * ease));
  const fpm = ENCOUNTER_ENEMY_FINAL_POWER_MULT;
  const ovm = ENCOUNTER_ENEMY_OVERALL_MULT;
  const diffm = ENCOUNTER_ENEMY_DIFFICULTY_MULT;
  eatk = Math.max(6, Math.round(eatk * fpm * ovm * diffm));
  edef = Math.max(3, Math.round(edef * fpm * ovm * diffm));
  ehpMax = Math.max(1, Math.round(ehpMax * fpm * ovm * diffm));

  let php = phpMax;
  let ehp = ehpMax;
  const pyou = protagonistYouZh(state);
  const frames: BattleFrame[] = [];
  frames.push({
    player_hp: php,
    enemy_hp: ehp,
    player_hp_max: phpMax,
    enemy_hp_max: ehpMax,
    banner_zh: "── 交鋒開始 ──",
  });

  for (let round = 0; round < MAX_ENCOUNTER_ROUNDS; round++) {
    if (php <= 0 || ehp <= 0) {
      break;
    }
    const pu = rng.random() < PROB_PLAYER_ULTIMATE;
    const eu = rng.random() < Math.min(0.92, ENEMY_ULT_BASE + ENEMY_ULT_PER_DIFF * enemy.difficulty);

    const pm = playerMoveName(rng, pu);
    const em = eu ? enemy.ultimate_zh : rng.choice(enemy.move_names);

    const dmgE = rollDamage(rng, patk, edef, pu);
    const dmgP = rollDamage(rng, eatk, pdef, eu);

    ehp -= dmgE;
    frames.push({
      player_hp: Math.max(0, php),
      enemy_hp: Math.max(0, ehp),
      player_hp_max: phpMax,
      enemy_hp_max: ehpMax,
      banner_zh: `【我方】${pyou}詠出「${pm}」，${enemy.name_zh} 受創 ${dmgE}。`,
    });
    if (php <= 0 || ehp <= 0) {
      break;
    }

    php -= dmgP;
    frames.push({
      player_hp: Math.max(0, php),
      enemy_hp: Math.max(0, ehp),
      player_hp_max: phpMax,
      enemy_hp_max: ehpMax,
      banner_zh: `【敵方】${enemy.name_zh} 以「${em}」還擊，${pyou}受創 ${dmgP}。`,
    });
    if (php <= 0 || ehp <= 0) {
      break;
    }
  }

  if (php > 0 && ehp > 0) {
    frames.push({
      player_hp: php,
      enemy_hp: ehp,
      player_hp_max: phpMax,
      enemy_hp_max: ehpMax,
      banner_zh: "── 鏖戰未絕，魔力與體勢先一步見底——此役判為落敗。 ──",
    });
  }

  let win: boolean;
  if (php <= 0 && ehp <= 0) {
    win = rng.random() < 0.48;
    frames.push({
      player_hp: 0,
      enemy_hp: 0,
      player_hp_max: phpMax,
      enemy_hp_max: ehpMax,
      banner_zh:
        "煙塵散去──" + (win ? `${pyou}仍站著。` : `${pyou}先跪倒；對方亦踉蹌，但戰果歸敵。`),
    });
  } else {
    win = ehp <= 0 && php > 0;
  }

  const treasure = win ? { ...enemy.treasure_deltas } : {};

  return {
    win,
    frames,
    participation_deltas: { ...ENCOUNTER_PARTICIPATION_DELTAS },
    treasure_deltas: treasure,
    player_atk: patk,
    player_def: pdef,
    enemy_atk: eatk,
    enemy_def: edef,
  };
}
