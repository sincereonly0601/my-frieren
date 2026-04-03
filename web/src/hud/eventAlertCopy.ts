/**
 * 全畫面事件前導標題與前導句（與桌面 `main.py` 之 `_EVENT_ALERT_*` 對齊）。
 */

export type EventAlertKind = "major" | "incident" | "encounter" | "whim" | "ending";

const TITLE_ENDING = "角色結局";

/** 結局前導最前層：全畫面事件框附標題（與 `mountEndingPreludeAndPagesHud` 兩頁敘事銜接）。 */
const TEASER_ENDING =
  "十五年培養至此告一段落；聖堂即將對照歷史典範，揭示他最可能的命途，並獻上為這段旅程落幕的畫面。";

const TITLE_MAJOR = "重大事件";
const TITLE_INCIDENT = "突發事件";
const TITLE_ENCOUNTER = "遭遇戰";
const TITLE_WHIM = "奇遇事件";

const TEASER_MAJOR_BY_AGE: Record<number, string> = {
  8: "石室深處的符文將映入眼底——邊境、禁書與無名術式，即將在妳面前展開第一頁。",
  13: "口試廳燈火穩定，紀錄員的筆卻不停——俘虜的一句話，即將逼出妳對公義的界定。",
  17: "告示板前雨絲與紅字交錯——北境、徵召與餘生，即將等妳簽下無法假裝沒看見的選擇。",
};

const TEASER_INCIDENT =
  "平穩的日子裡即將泛起漣漪：一則旅途中的插曲，正等妳讀完、選完、承擔後果。";

const TEASER_FALLBACK =
  "關鍵抉擇即將展開——Enter 後細讀內文，為這段養成寫下新的一筆。";

const TEASER_ENCOUNTER_BY_AGE: Record<number, string> = {
  6: "小路轉角傳來非人的氣息——這一戰無法迴避，咒文與意志即將正面受試。",
  11: "名號與危險同幅膨脹：強敵當前，勝負將在電光石火間分曉。",
  16: "壓迫感如暴風眼逼近——頭目級的存在，正把妳逼進不得不拔術式的距離。",
};

const TEASER_WHIM =
  "你在轉角與某段故事對上眼——彷彿下一幕正要開口，等你應聲。";

/**
 * 遭遇戰前導等以「妳」撰寫之句，男性主角改為「你」（與 `encounter_protagonist_pronoun_adjust_zh` 一致）。
 *
 * @param text - 原文
 * @param gender - 主角性別
 */
export function adjustProtagonistPronounZh(
  text: string,
  gender: "male" | "female",
): string {
  if (gender !== "male") {
    return text;
  }
  return text.replace(/妳/g, "你");
}

/**
 * @param kind - 事件類型
 * @param ageYear - 重大 8／13／17；遭遇 6／11／16；其餘可省略
 * @param gender - 用於遭遇戰／重大／突發前導之人稱
 */
export function getEventAlertCopy(
  kind: EventAlertKind,
  ageYear: number | undefined,
  gender: "male" | "female",
): { title: string; teaser: string } {
  if (kind === "ending") {
    return {
      title: TITLE_ENDING,
      teaser: adjustProtagonistPronounZh(TEASER_ENDING, gender),
    };
  }
  if (kind === "whim") {
    return { title: TITLE_WHIM, teaser: TEASER_WHIM };
  }
  if (kind === "encounter") {
    const a = ageYear ?? 6;
    const teaser = adjustProtagonistPronounZh(
      TEASER_ENCOUNTER_BY_AGE[a] ?? TEASER_FALLBACK,
      gender,
    );
    return { title: TITLE_ENCOUNTER, teaser };
  }
  if (kind === "incident") {
    return {
      title: TITLE_INCIDENT,
      teaser: adjustProtagonistPronounZh(TEASER_INCIDENT, gender),
    };
  }
  const a = ageYear ?? 8;
  const teaser = adjustProtagonistPronounZh(
    TEASER_MAJOR_BY_AGE[a] ?? TEASER_FALLBACK,
    gender,
  );
  return { title: TITLE_MAJOR, teaser };
}
