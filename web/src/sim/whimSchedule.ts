/**
 * 奇遇排程與觸發索引（與桌面 `whim_events.py` 一致）。
 */

import {
  START_AGE_MONTHS,
  TOTAL_TRAINING_QUARTERS,
  type GameStateStored,
} from "../save/idbSave";
import type { SimRng } from "./rng";
import { WHIM_ENCOUNTER_KEYS_ORDER } from "./gameData";
import whimQuestions from "../data/whim_questions.json";

/**
 * @param completed - 本季結算後之「已完成季數」
 */
function phaseKeyForCompleted(completed: number): "childhood" | "adolescence" | "young_adult" {
  const am = START_AGE_MONTHS + 3 * completed;
  const ay = Math.floor(am / 12);
  if (ay < 8) {
    return "childhood";
  }
  if (ay < 13) {
    return "adolescence";
  }
  return "young_adult";
}

/**
 * 可排程之已完成季數：該季結束後月相為 3／6／9 月，且滿歲落在指定人生階段。
 *
 * @param phaseKey - 幼年／少年／青年
 */
export function eligibleCompletedForWhimMonthAndPhase(
  phaseKey: "childhood" | "adolescence" | "young_adult",
): number[] {
  const out: number[] = [];
  for (let c = 1; c <= TOTAL_TRAINING_QUARTERS; c++) {
    const am = START_AGE_MONTHS + 3 * c;
    if (![3, 6, 9].includes(am % 12)) {
      continue;
    }
    if (phaseKeyForCompleted(c) !== phaseKey) {
      continue;
    }
    out.push(c);
  }
  return out;
}

/**
 * 新局寫入奇遇排程（若已有排程則不覆寫）。
 *
 * @param game - 可變狀態
 * @param rng - 亂數源
 */
export function seedWhimScheduleForNewPlaythrough(
  game: GameStateStored,
  rng: SimRng,
): void {
  if (game.whim_slots.length > 0) {
    return;
  }
  const phases: ("childhood" | "adolescence" | "young_adult")[] = [
    "childhood",
    "adolescence",
    "young_adult",
  ];
  const pickedSlots: number[] = [];
  for (const ph of phases) {
    const pool = eligibleCompletedForWhimMonthAndPhase(ph);
    if (pool.length === 0) {
      continue;
    }
    pickedSlots.push(rng.choice(pool));
  }
  pickedSlots.sort((a, b) => a - b);
  if (pickedSlots.length === 0) {
    return;
  }
  const nPick = pickedSlots.length;
  const npcKeys = rng.sample([...WHIM_ENCOUNTER_KEYS_ORDER], nPick);
  const nq = whimQuestions.length;
  const idxPool = Array.from({ length: nq }, (_, i) => i);
  const qIndices = rng.sample(idxPool, nPick);
  game.whim_slots = pickedSlots;
  game.whim_npc_keys = npcKeys;
  game.whim_question_indices = qIndices;
  game.whim_fired = pickedSlots.map(() => false);
}

/**
 * 若目前「剛結算完當季」對應排程索引且尚未結算，回傳該索引。
 *
 * @param game - 狀態（須已扣過該季 `time_left`）
 */
export function whimActiveIndexForCompletedQuarters(
  game: GameStateStored,
): number | null {
  const completed = TOTAL_TRAINING_QUARTERS - game.time_left;
  for (let i = 0; i < game.whim_slots.length; i++) {
    const slot = game.whim_slots[i];
    const fired = i < game.whim_fired.length ? Boolean(game.whim_fired[i]) : false;
    if (slot === completed && !fired) {
      return i;
    }
  }
  return null;
}
