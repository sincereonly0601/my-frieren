/**
 * 聖堂領養者問卷：題組與結算邏輯（對照桌面 `adopter_questionnaire.py`）。
 */

import type { GameStateStored } from "../save/idbSave";

/** 問卷題數 */
export const ADOPTER_QUESTIONNAIRE_COUNT = 5;

export type AdopterDeltaKey =
  | "int_stat"
  | "str_stat"
  | "fth_stat"
  | "pragmatic"
  | "social";

export type AdopterOption = {
  labelZh: string;
  deltas: Partial<Record<AdopterDeltaKey, number>>;
};

export type AdopterQuestion = {
  promptZh: string;
  options: [AdopterOption, AdopterOption, AdopterOption];
};

/** 與桌面 `ADOPTER_QUESTIONNAIRE` 一致 */
export const ADOPTER_QUESTIONNAIRE: readonly AdopterQuestion[] = [
  {
    promptZh:
      "首先，請問您家中能否負擔孩子往後的修行與行旅開支；聖堂需估算補助與魔法學舍的預備金，" +
      "以免誤將無力遠行的孩子送往北境試煉。",
    options: [
      {
        labelZh: "家計偏緊，先保證三餐與藥費，修行資材採最基礎配置。",
        deltas: { pragmatic: 2, str_stat: 1 },
      },
      {
        labelZh: "日常穩定，可按季添購教材與訓練用品，逐步拉高學習密度。",
        deltas: { pragmatic: 1, int_stat: 1, social: 1 },
      },
      {
        labelZh: "資源充足，願先投資高階咒式、遠行見習與跨區導師指導。",
        deltas: { int_stat: 2, fth_stat: 1 },
      },
    ],
  },
  {
    promptZh:
      "魔王死後已過多年，邊境仍傳聞魔族與盜匪；教會不問您效忠何方，" +
      "只問這樣的世道是否常令您徹夜難眠？",
    options: [
      {
        labelZh: "風險意識高，家中有固定演練與守夜制度，先求不被突襲。",
        deltas: { str_stat: 2, pragmatic: 1 },
      },
      {
        labelZh: "以情報判讀為主，追蹤告示與路線消息，避免做出錯誤判斷。",
        deltas: { int_stat: 2, social: 1 },
      },
      {
        labelZh: "相信社群互助，與鄰里與商隊維持聯絡，透過合作分攤風險。",
        deltas: { social: 2, fth_stat: 1 },
      },
    ],
  },
  {
    promptZh:
      "以人類短暫的數十年為尺，您最盼望這片大陸變成什麼模樣？" +
      "（聖堂將此與史書上勇者一行之世相互對照。）",
    options: [
      {
        labelZh: "盼社會先恢復彼此扶持，讓普通人能平安過日子。",
        deltas: { social: 2, fth_stat: 1 },
      },
      {
        labelZh: "盼戰禍教訓制度化，靠知識與紀錄減少重複犯錯。",
        deltas: { int_stat: 3 },
      },
      {
        labelZh: "盼秩序穩定與規範落地，孩子能在可預期環境中成長。",
        deltas: { pragmatic: 2, str_stat: 1 },
      },
    ],
  },
  {
    promptZh:
      "對這名即將託付予您的孩子，您最深的期望是什麼？" +
      "（此條列為密件，僅供啟蒙導師參考。）",
    options: [
      {
        labelZh: "第一目標是平安與自保，先把身體與求生能力打底。",
        deltas: { str_stat: 2, pragmatic: 1 },
      },
      {
        labelZh: "希望孩子具備判讀與思辨力，不被話術與情緒牽著走。",
        deltas: { int_stat: 2, social: 1 },
      },
      {
        labelZh: "希望保有同理與信念，在困局中仍能照顧自己與他人。",
        deltas: { fth_stat: 1, social: 2 },
      },
    ],
  },
  {
    promptZh:
      "最後一題：您如何看待「未來」？不是占星或預言，" +
      "而是今夜就寢前，您對明日仍願意相信的那一句話。",
    options: [
      {
        labelZh: "未來靠日復一日的紀律累積，不靠運氣或偶然。",
        deltas: { pragmatic: 2, str_stat: 1 },
      },
      {
        labelZh: "未來靠持續學習與驗證，能修正錯誤就不怕走慢。",
        deltas: { int_stat: 2, pragmatic: 1 },
      },
      {
        labelZh: "未來靠彼此扶持與信念，願意一起承擔才走得長遠。",
        deltas: { social: 2, fth_stat: 1 },
      },
    ],
  },
] as const;

/**
 * 問卷判讀子句：由桌面 `ADOPTER_OPTION_CLAUSES_ZH` 語意保留、**字量約減半**（網頁版）。
 */
const ADOPTER_OPTION_CLAUSES_ZH_WEB: readonly (readonly string[])[] = [
  [
    "家計保守，先穩定基本生活與基礎訓練",
    "家計穩定，按季投入教材與訓練用品",
    "資源充足，優先投資高階學習與見習",
  ],
  [
    "偏重防衛紀律，先建立守備與應變",
    "偏重情報判讀，以資訊降低決策風險",
    "偏重合作互助，以連結分攤不確定性",
  ],
  [
    "願日常安穩，社群仍保有互助溫度",
    "願經驗可傳承，靠知識避免重蹈覆轍",
    "願規範可依循，讓成長環境更可預期",
  ],
  [
    "優先平安自保，先鞏固體能與生存基礎",
    "優先思辨判讀，強化理性與獨立判斷",
    "優先同理信念，重視關係與內在韌性",
  ],
  [
    "相信紀律累積，按步推進走向明日",
    "相信學習驗證，修正中持續前進",
    "相信同行信念，以互助承擔未來",
  ],
];

const STAT_PRIORITY: readonly string[] = [
  "int_stat",
  "str_stat",
  "fth_stat",
  "pragmatic",
  "social",
];

const STAT_LABEL_ADOPTER_ZH: Readonly<Record<string, string>> = {
  int_stat: "智力",
  str_stat: "力量",
  fth_stat: "信仰",
  pragmatic: "務實",
  social: "社交",
  truth_seek: "真理探求",
};

/** 題幹顯示：去空白與換行，斷行交給 CSS */
export function flattenAdopterPromptZh(text: string): string {
  return text.split(/\s+/).join("");
}

/**
 * 依每題選項索引（0～2）累加各欄位增量。
 *
 * @param choiceIndices - 長度須為 {@link ADOPTER_QUESTIONNAIRE_COUNT}
 */
export function mergeAdopterQuestionnaire(
  choiceIndices: readonly number[],
): Record<string, number> {
  if (choiceIndices.length !== ADOPTER_QUESTIONNAIRE_COUNT) {
    throw new Error(
      `expected ${ADOPTER_QUESTIONNAIRE_COUNT} choices, got ${choiceIndices.length}`,
    );
  }
  const acc: Record<string, number> = {};
  for (let qi = 0; qi < choiceIndices.length; qi++) {
    const ci = choiceIndices[qi]!;
    const opts = ADOPTER_QUESTIONNAIRE[qi]!.options;
    if (ci < 0 || ci >= opts.length) {
      throw new Error(`invalid option index ${ci} for question ${qi}`);
    }
    const opt = opts[ci]!;
    for (const [k, v] of Object.entries(opt.deltas)) {
      if (typeof v !== "number") {
        continue;
      }
      acc[k] = (acc[k] ?? 0) + v;
    }
  }
  return Object.fromEntries(Object.entries(acc).filter(([, v]) => v !== 0));
}

/**
 * 依選項索引取判讀子句（{@link ADOPTER_OPTION_CLAUSES_ZH_WEB}）。
 */
function adopterClausesForJudgmentWeb(
  choiceIndices: readonly number[],
): readonly [string, string, string, string, string] {
  if (choiceIndices.length !== ADOPTER_QUESTIONNAIRE_COUNT) {
    throw new Error(
      `expected ${ADOPTER_QUESTIONNAIRE_COUNT} choices, got ${choiceIndices.length}`,
    );
  }
  const out: string[] = [];
  for (let qi = 0; qi < choiceIndices.length; qi++) {
    const ci = choiceIndices[qi]!;
    const row = ADOPTER_OPTION_CLAUSES_ZH_WEB[qi]!;
    if (ci < 0 || ci >= row.length) {
      throw new Error(`invalid option index ${ci} for question ${qi}`);
    }
    out.push(row[ci]!);
  }
  return out as unknown as [string, string, string, string, string];
}

/**
 * 判讀內文：承桌面 `questionnaire_judgment_zh` 結構，**總字量約減半**；不含標題（標題由 HUD）。
 * 網頁版濃縮為單段連寫，長度以約五行視覺寬度為目標。
 */
export function questionnaireJudgmentZh(
  choiceIndices: readonly number[],
  merged: Record<string, number>,
): string {
  const [c0, c1, c2, c3, c4] = adopterClausesForJudgmentWeb(choiceIndices);
  const lead =
    "聖堂已完成五問對照：" +
    `家計「${c0}」、` +
    `風險「${c1}」、` +
    `願景「${c2}」、` +
    `教養「${c3}」、` +
    `未來「${c4}」。`;
  if (Object.keys(merged).length === 0) {
    return `${lead}整體取向均衡，首季先以通用課綱啟蒙，並依互動再微調培養重點。`;
  }
  const ranked = Object.entries(merged).sort((a, b) => {
    const dv = b[1] - a[1];
    if (dv !== 0) {
      return dv;
    }
    const ia = STAT_PRIORITY.indexOf(a[0]!);
    const ib = STAT_PRIORITY.indexOf(b[0]!);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
  const topKey = ranked[0]![0]!;
  const closingHalf: Record<string, string> = {
    int_stat: "綜觀歸求知辨識——理性留可核對之路。",
    str_stat: "綜觀讀堅韌護衛——體魄與平安在前。",
    fth_stat: "綜觀讀守望信靠——動盪裡信高於算計。",
    pragmatic: "綜觀讀務實界線——重執行與現實站穩。",
    social: "綜觀讀牽絆同行——重溫度、不必獨擔。",
    truth_seek: "綜觀讀求真執著——近事實、遠修辭。",
  };
  const closingLine =
    closingHalf[topKey] ?? "綜觀筆調複合；啟蒙對照卷末子句。";
  return (
    `${lead}` +
    `${closingLine}` +
    "本結果已登錄為首季建議，導師將據此調整課業、試煉與陪伴節奏。"
  );
}

/**
 * 「智力+2  力量+1」式單行（兩半形空格分隔）。
 */
export function formatAdopterMergedDeltasZh(merged: Record<string, number>): string {
  if (Object.keys(merged).length === 0) {
    return "（無數值變化）";
  }
  const bits = Object.entries(merged)
    .filter(([, v]) => v !== 0)
    .sort((a, b) => {
      const ia = STAT_PRIORITY.indexOf(a[0]!);
      const ib = STAT_PRIORITY.indexOf(b[0]!);
      const sa = ia === -1 ? 99 : ia;
      const sb = ib === -1 ? 99 : ib;
      if (sa !== sb) {
        return sa - sb;
      }
      return a[0]!.localeCompare(b[0]!);
    })
    .map(([k, v]) => {
      const label = STAT_LABEL_ADOPTER_ZH[k] ?? k;
      return `${label}${v > 0 ? "+" : ""}${v}`;
    });
  return bits.length ? bits.join("  ") : "（無數值變化）";
}

const ADOPTER_DELTA_KEYS: readonly AdopterDeltaKey[] = [
  "int_stat",
  "str_stat",
  "fth_stat",
  "pragmatic",
  "social",
];

/**
 * 將問卷合併增量套用至狀態（不低於 0，對照桌面 `apply_deltas`／`_CLAMP_INT_FIELDS`）。
 *
 * @param game - 可變狀態（與桌面 `GameState` 鍵名一致）
 * @param merged - {@link mergeAdopterQuestionnaire} 結果
 */
export function applyAdopterDeltasToGameState(
  game: GameStateStored,
  merged: Record<string, number>,
): void {
  for (const k of ADOPTER_DELTA_KEYS) {
    const delta = merged[k];
    if (typeof delta !== "number") {
      continue;
    }
    game[k] = Math.max(0, game[k] + delta);
  }
}

/** @deprecated 請改用 {@link applyAdopterDeltasToGameState} */
export const applyAdopterDeltasToWebMiniState = applyAdopterDeltasToGameState;
