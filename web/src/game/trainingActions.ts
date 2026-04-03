import type { GameStateStored } from "../save/idbSave";

/**
 * 單季培養對五維的增減（對照 `training_actions.py` 之 `TrainingAction.deltas` 鍵名）。
 */
export type TrainingDeltas = Partial<
  Pick<GameStateStored, "int_stat" | "str_stat" | "social" | "fth_stat" | "pragmatic">
>;

/**
 * 單一季節指令（鍵 1～8 與桌面版數字鍵對齊）。
 */
export type TrainingAction = {
  keyNum: number;
  title: string;
  deltas: TrainingDeltas;
};

const STAT_LABEL_ZH: Record<keyof TrainingDeltas, string> = {
  int_stat: "智力",
  str_stat: "力量",
  social: "社交",
  fth_stat: "信仰",
  pragmatic: "務實",
};

const STAT_KEYS: (keyof TrainingDeltas)[] = [
  "int_stat",
  "str_stat",
  "social",
  "fth_stat",
  "pragmatic",
];

/**
 * 八種培養（資料與桌面版 `TRAINING_ACTIONS` 一致）。
 */
export const TRAINING_ACTIONS: readonly TrainingAction[] = [
  { keyNum: 1, title: "深度閱讀", deltas: { int_stat: 3 } },
  { keyNum: 2, title: "體能訓練", deltas: { str_stat: 3 } },
  { keyNum: 3, title: "聖堂祈禱", deltas: { fth_stat: 3 } },
  { keyNum: 4, title: "同儕相聚", deltas: { social: 3 } },
  { keyNum: 5, title: "幫忙營生", deltas: { pragmatic: 2, social: -1, fth_stat: 2 } },
  { keyNum: 6, title: "靜心抄寫", deltas: { int_stat: 2, fth_stat: 2, str_stat: -1 } },
  { keyNum: 7, title: "義工走訪", deltas: { social: 2, fth_stat: 2, pragmatic: -1 } },
  {
    keyNum: 8,
    title: "獨處鍛鍊",
    deltas: { str_stat: 2, pragmatic: 2, social: -1 },
  },
] as const;

/**
 * 依數字鍵查指令。
 */
export const TRAINING_ACTION_BY_KEY: Record<number, TrainingAction | undefined> =
  TRAINING_ACTIONS.reduce(
    (acc, a) => {
      acc[a.keyNum] = a;
      return acc;
    },
    {} as Record<number, TrainingAction | undefined>,
  );

/**
 * 五維變化一行說明（以兩半形空格分隔，如「智力+3  力量-1」，利於窄鈕內顯示）。
 *
 * @param action - 培養指令
 */
export function formatActionStatEffectsLine(action: TrainingAction): string {
  const parts: string[] = [];
  for (const k of STAT_KEYS) {
    const v = action.deltas[k];
    if (typeof v !== "number" || v === 0) {
      continue;
    }
    const label = STAT_LABEL_ZH[k];
    parts.push(`${label}${v > 0 ? "+" : ""}${v}`);
  }
  return parts.join("  ");
}

/**
 * 將 `deltas` 累加到狀態；各維不低於 0（同桌面版 `_CLAMP_INT_FIELDS` 行為）。
 *
 * @param game - 可變迷你狀態
 * @param deltas - 本季增減
 */
export function applyTrainingDeltas(
  game: GameStateStored,
  deltas: TrainingDeltas,
): void {
  for (const k of STAT_KEYS) {
    const v = deltas[k];
    if (typeof v !== "number") {
      continue;
    }
    game[k] = Math.max(0, game[k] + v);
  }
}
