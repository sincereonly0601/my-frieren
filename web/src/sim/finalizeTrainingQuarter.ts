/**
 * 培養一季結算：滿歲事件優先序、奇遇、結局（與桌面 `_finalize_pending_training_quarter` 一致）。
 */

import {
  ageMonthsFromTimeLeft,
  syncPhaseFromTimeLeft,
  type GameStateStored,
} from "../save/idbSave";
import { TRAINING_ACTION_BY_KEY, applyTrainingDeltas } from "../game/trainingActions";
import { applyGameDeltas, addGameFlags } from "./applyGameDeltas";
import { simulateEncounter, type BattleOutcome } from "./encounterSim";
import type { EncounterEnemyJson, IncidentEventJson } from "./types";
import { ALL_INCIDENTS, ENCOUNTERS, MAJOR_BY_AGE } from "./gameData";
import type { SimRng } from "./rng";
import { whimActiveIndexForCompletedQuarters } from "./whimSchedule";
import { resolveEndingKey } from "./resolveEnding";

/** 滿歲突發事件觸發年齡（不含 6／11／16 遭遇戰與 8／13／18 重大） */
const INCIDENT_TRIGGER_YEARS = new Set([4, 5, 7, 9, 10, 12, 14, 15, 17]);

/**
 * @param game - 狀態快照
 */
export function cloneGameState(game: GameStateStored): GameStateStored {
  return {
    ...game,
    flags: [...game.flags],
    magic_ids: [...game.magic_ids],
    incident_years_fired: [...game.incident_years_fired],
    incident_ids_fired: [...game.incident_ids_fired],
    major_years_fired: [...game.major_years_fired],
    encounter_years_fired: [...game.encounter_years_fired],
    whim_slots: [...game.whim_slots],
    whim_npc_keys: [...game.whim_npc_keys],
    whim_question_indices: [...game.whim_question_indices],
    whim_fired: [...game.whim_fired],
  };
}

function incidentTierForAgeYear(ageYears: number): number | null {
  if ([4, 5, 6, 7].includes(ageYears)) {
    return 1;
  }
  if ([9, 10, 11, 12].includes(ageYears)) {
    return 2;
  }
  if ([14, 15, 16, 17].includes(ageYears)) {
    return 3;
  }
  return null;
}

/**
 * 自符合年齡層池隨機一則突發（可排除已發生 id）。
 *
 * @param ageYears - 本次滿足之滿歲
 * @param rng - 亂數源
 * @param excludeIds - 已觸發過的事件 id
 */
export function pickRandomIncident(
  ageYears: number,
  rng: SimRng,
  excludeIds: ReadonlySet<string>,
): IncidentEventJson | null {
  const tier = incidentTierForAgeYear(ageYears);
  if (tier == null) {
    return null;
  }
  let pool = ALL_INCIDENTS.filter((e) => e.tier === tier);
  if (excludeIds.size > 0) {
    pool = pool.filter((e) => !excludeIds.has(e.id));
  }
  if (pool.length === 0) {
    return null;
  }
  return rng.choice(pool);
}

export type QuarterInterrupt =
  | { kind: "major"; ageYear: number }
  | {
      kind: "encounter";
      ageYear: number;
      enemy: EncounterEnemyJson;
      outcome: BattleOutcome;
    }
  | { kind: "incident"; ageYear: number; incident: IncidentEventJson }
  | { kind: "whim"; slotIndex: number }
  | { kind: "ending"; endingKey: string };

/**
 * 僅套用本季培養五維增量（不扣季；與桌面顯示回饋期行為一致）。
 *
 * @param game - 可變狀態
 * @param trainingKeyNum - 1～8
 */
export function applyQuarterTrainingDeltasOnly(
  game: GameStateStored,
  trainingKeyNum: number,
): void {
  const action = TRAINING_ACTION_BY_KEY[trainingKeyNum];
  if (action != null) {
    applyTrainingDeltas(game, action.deltas);
  }
}

/**
 * 扣一季、同步階段後，決定第一個要攔截的事件（重大／遭遇／突發／奇遇／結局）。
 *
 * @param game - 可變狀態
 * @param preYears - 扣季前之滿歲年數（`ageMonthsFromTimeLeft` 於扣季前換算）
 * @param rng - 亂數源
 */
export function spendQuarterAndResolveFirstInterrupt(
  game: GameStateStored,
  preYears: number,
  rng: SimRng,
): QuarterInterrupt | null {
  game.time_left -= 1;
  syncPhaseFromTimeLeft(game);
  const postYears = Math.floor(ageMonthsFromTimeLeft(game.time_left) / 12);

  let interrupt: QuarterInterrupt | null = null;

  if (postYears > preYears) {
    const post = postYears;
    if ([8, 13, 18].includes(post) && !game.major_years_fired.includes(post)) {
      if (MAJOR_BY_AGE.has(post)) {
        interrupt = { kind: "major", ageYear: post };
      }
    } else if ([6, 11, 16].includes(post) && !game.encounter_years_fired.includes(post)) {
      const pool =
        post === 6
          ? ENCOUNTERS.monsters
          : post === 11
            ? ENCOUNTERS.elites
            : ENCOUNTERS.bosses;
      const enemy = rng.choice(pool);
      const outcome = simulateEncounter(enemy, game, rng);
      interrupt = { kind: "encounter", ageYear: post, enemy, outcome };
    } else if (
      INCIDENT_TRIGGER_YEARS.has(post) &&
      !game.incident_years_fired.includes(post)
    ) {
      const exclude = new Set(game.incident_ids_fired);
      const inc = pickRandomIncident(post, rng, exclude);
      if (inc != null) {
        interrupt = { kind: "incident", ageYear: post, incident: inc };
      }
    }
  }

  if (interrupt == null) {
    const whimI = whimActiveIndexForCompletedQuarters(game);
    if (whimI != null) {
      interrupt = { kind: "whim", slotIndex: whimI };
    }
  }

  if (interrupt == null && game.time_left <= 0) {
    interrupt = { kind: "ending", endingKey: resolveEndingKey(game) };
  }

  return interrupt;
}

/**
 * 執行：培養數值、扣一季、同步階段，並決定接下來要攔截的單一事件（若有）。
 * 網頁版一般改為先 {@link applyQuarterTrainingDeltasOnly} 再顯示回饋，關閉後
 * {@link spendQuarterAndResolveFirstInterrupt}；本函式保留供測試或一鍵結算。
 *
 * @param game - 可變狀態（已為副本）
 * @param trainingKeyNum - 1～8
 * @param rng - 亂數源
 * @returns 若有事件則非 null
 */
export function resolveQuarterInterrupt(
  game: GameStateStored,
  trainingKeyNum: number,
  rng: SimRng,
): QuarterInterrupt | null {
  const preYears = Math.floor(ageMonthsFromTimeLeft(game.time_left) / 12);
  applyQuarterTrainingDeltasOnly(game, trainingKeyNum);
  return spendQuarterAndResolveFirstInterrupt(game, preYears, rng);
}

/**
 * 事件結束後：僅檢查奇遇或結局（不再扣季）。
 *
 * @param game - 可變狀態
 * @param rng - 亂數源（保留參數與桌面擴充一致）
 */
export function scanIdleFollowUp(
  game: GameStateStored,
  _rng: SimRng,
): QuarterInterrupt | null {
  void _rng;
  const whimI = whimActiveIndexForCompletedQuarters(game);
  if (whimI != null) {
    return { kind: "whim", slotIndex: whimI };
  }
  if (game.time_left <= 0) {
    return { kind: "ending", endingKey: resolveEndingKey(game) };
  }
  return null;
}

/**
 * 套用重大事件選項（五維、隱藏值、旗標、已觸發年齡）。
 *
 * @param game - 可變狀態
 * @param ageYear - 滿歲
 * @param optionIndex - 0～2
 */
export function applyMajorOption(
  game: GameStateStored,
  ageYear: number,
  optionIndex: number,
): void {
  const me = MAJOR_BY_AGE.get(ageYear);
  if (me == null || optionIndex < 0 || optionIndex > 2) {
    return;
  }
  const opt = me.options[optionIndex];
  if (opt == null) {
    return;
  }
  applyGameDeltas(game, opt.deltas);
  applyGameDeltas(game, opt.extra_deltas);
  addGameFlags(game, opt.flags_add);
  if (game.protagonist_gender === "male") {
    addGameFlags(game, opt.flags_add_if_male);
  }
  if (!game.major_years_fired.includes(ageYear)) {
    game.major_years_fired.push(ageYear);
  }
}

/**
 * 套用遭遇戰結算獎勵與參戰五維。
 *
 * @param game - 可變狀態
 * @param ageYear - 滿歲
 * @param outcome - 模擬結果
 */
export function applyEncounterOutcome(
  game: GameStateStored,
  ageYear: number,
  outcome: BattleOutcome,
): void {
  if (!game.encounter_years_fired.includes(ageYear)) {
    game.encounter_years_fired.push(ageYear);
  }
  applyGameDeltas(game, outcome.participation_deltas);
  if (outcome.win) {
    applyGameDeltas(game, outcome.treasure_deltas);
  }
}

/**
 * 套用突發事件選項。
 *
 * @param game - 可變狀態
 * @param ageYear - 滿歲
 * @param incident - 事件
 * @param optionIndex - 0～2
 */
export function applyIncidentOption(
  game: GameStateStored,
  ageYear: number,
  incident: IncidentEventJson,
  optionIndex: number,
): void {
  const opt = incident.options[optionIndex];
  if (opt == null) {
    return;
  }
  applyGameDeltas(game, opt.deltas);
  if (!game.incident_ids_fired.includes(incident.id)) {
    game.incident_ids_fired.push(incident.id);
  }
  if (!game.incident_years_fired.includes(ageYear)) {
    game.incident_years_fired.push(ageYear);
  }
}

/**
 * 套用奇遇測驗結果。
 *
 * @param game - 可變狀態
 * @param slotIndex - 排程索引
 * @param deltas - 正解或錯解之五維增量
 */
export function applyWhimOutcome(
  game: GameStateStored,
  slotIndex: number,
  deltas: Record<string, number>,
): void {
  applyGameDeltas(game, deltas);
  if (slotIndex >= 0 && slotIndex < game.whim_fired.length) {
    const next = [...game.whim_fired];
    next[slotIndex] = true;
    game.whim_fired = next;
  }
}
