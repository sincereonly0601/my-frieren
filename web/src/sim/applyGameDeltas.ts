import type { GameStateStored } from "../save/idbSave";

/** 與桌面 `game_state._CLAMP_INT_FIELDS` 一致：加總後不得為負 */
const CLAMP_INT_FIELDS = new Set<string>([
  "int_stat",
  "str_stat",
  "fth_stat",
  "pragmatic",
  "romantic",
  "solitude",
  "social",
  "truth_seek",
  "corruption",
]);

/**
 * 依鍵名累加數值（與桌面 `GameState.apply_deltas` 一致）。
 *
 * @param game - 可變狀態
 * @param deltas - 增量字典
 */
export function applyGameDeltas(
  game: GameStateStored,
  deltas: Readonly<Record<string, number>>,
): void {
  for (const [key, delta] of Object.entries(deltas)) {
    if (!(key in game)) {
      continue;
    }
    const cur = game[key as keyof GameStateStored];
    if (typeof cur !== "number") {
      continue;
    }
    let next = cur + Number(delta);
    if (CLAMP_INT_FIELDS.has(key)) {
      next = Math.max(0, next);
    }
    (game as unknown as Record<string, unknown>)[key] = next;
  }
}

/**
 * 冪等加入劇情旗標。
 *
 * @param game - 可變狀態
 * @param flag - 旗標字串
 */
export function addGameFlag(game: GameStateStored, flag: string): void {
  if (!game.flags.includes(flag)) {
    game.flags.push(flag);
  }
}

/**
 * 批量加入旗標。
 *
 * @param game - 可變狀態
 * @param flags - 旗標集合
 */
export function addGameFlags(game: GameStateStored, flags: Iterable<string>): void {
  for (const f of flags) {
    addGameFlag(game, f);
  }
}
