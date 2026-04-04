import type { GameStateStored } from "../save/idbSave";

/** 賽莉耶／南方勇者隱藏線：重大事件寫入之旗標鍵（全劇僅此一組結局旗標）。 */
const SERIE_MILESTONE_FLAGS: readonly string[] = [
  "series_milestone_1",
  "series_milestone_2",
  "series_milestone_3",
];

/**
 * 是否已集齊指定旗標（隱藏結局用）。
 *
 * @param state - 通關狀態
 * @param keys - 須全部存在的旗標鍵
 */
function hasAllMilestoneFlags(
  state: GameStateStored,
  keys: readonly string[],
): boolean {
  const flags = new Set(state.flags ?? []);
  return keys.every((k) => flags.has(k));
}

/**
 * @param n - 五維整數
 * @returns 是否落在 100～199（含）
 */
function inRange100To199(n: number): boolean {
  return n >= 100 && n <= 199;
}

/**
 * 女角賽莉耶／男角南方勇者隱藏：須集齊三段重大事件旗標（見設定頁各歲須選之選項），且智力、力量、信仰皆≥100。
 *
 * @param s - 通關狀態
 */
function matchesSouthSerieHidden(s: GameStateStored): boolean {
  return (
    hasAllMilestoneFlags(s, SERIE_MILESTONE_FLAGS) &&
    s.int_stat >= 100 &&
    s.str_stat >= 100 &&
    s.fth_stat >= 100
  );
}

/**
 * 網頁版結局鍵判定（與設定頁「第 2～11 條」對齊）：
 * 隱藏（男南方勇者／女賽莉耶：三段旗標＋智力/力量/信仰≥100）、單維 ≥200 鏈、第 6～10 條、第 11 條預設（贊恩／康涅）。
 * 第 9 條內：男角同底層數值下，務實≤社交→葛納烏、務實＞社交→威亞貝爾；威亞貝爾進線之正向門檻見設定頁。女角務實＞社交→梅特黛，否則→尤蓓爾。
 * 第 10 條：男鄧肯、女艾莉。
 *
 * @param state - 通關狀態
 * @returns `endings.json` 之結局 `key`
 */
export function resolveEndingKey(state: GameStateStored): string {
  const male = state.protagonist_gender === "male";

  if (matchesSouthSerieHidden(state)) {
    return male ? "hero_south" : "serie";
  }

  if (state.str_stat >= 200) {
    return male ? "stark" : "fern";
  }
  if (state.int_stat >= 200 && state.str_stat < 200) {
    return male ? "himmel" : "frieren";
  }
  if (
    state.fth_stat >= 200 &&
    state.str_stat < 200 &&
    state.int_stat < 200 &&
    state.social < 200
  ) {
    return male ? "kraft" : "flamme";
  }
  if (
    state.social >= 200 &&
    state.str_stat < 200 &&
    state.int_stat < 200 &&
    state.fth_stat < 200
  ) {
    return male ? "sein" : "laufen";
  }

  if (
    inRange100To199(state.str_stat) &&
    inRange100To199(state.int_stat) &&
    state.fth_stat < 200 &&
    state.social < 200
  ) {
    return male ? "eisen" : "sense";
  }
  if (
    inRange100To199(state.int_stat) &&
    inRange100To199(state.fth_stat) &&
    state.str_stat < 100 &&
    state.social < 200
  ) {
    return male ? "heiter" : "kanne";
  }
  if (
    inRange100To199(state.social) &&
    inRange100To199(state.fth_stat) &&
    state.str_stat < 200 &&
    state.int_stat < 100
  ) {
    return male ? "land" : "lavine";
  }
  if (
    inRange100To199(state.str_stat) &&
    inRange100To199(state.pragmatic) &&
    state.fth_stat < 200 &&
    state.social < 200 &&
    state.int_stat < 100
  ) {
    if (!male) {
      return state.pragmatic > state.social ? "methode" : "ubel";
    }
    if (state.pragmatic <= state.social) {
      return "genau";
    }
    return "wirbel";
  }
  if (
    inRange100To199(state.fth_stat) &&
    inRange100To199(state.pragmatic) &&
    state.str_stat < 100 &&
    state.int_stat < 100 &&
    state.social < 100
  ) {
    return male ? "denken" : "ehre";
  }

  return male ? "sein" : "kanne";
}
