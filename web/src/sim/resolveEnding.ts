import type { GameStateStored } from "../save/idbSave";

type SharedEndingTemplateId =
  | "templateA"
  | "templateB"
  | "templateC"
  | "templateD"
  | "templateE"
  | "templateF"
  | "templateG"
  | "templateH"
  | "templateI"
  | "templateJ"
  | "templateK";

/**
 * 依照簡化後之 11 組共用結局規則，回傳共用模板代號（男女共用數值條件）。
 *
 * @param state - 通關狀態
 */
function resolveSharedEndingTemplate(state: GameStateStored): SharedEndingTemplateId {
  // 隱藏／極端路線優先。
  if (
    state.int_stat >= 70 &&
    state.pragmatic >= state.social + 20 &&
    state.int_stat >= state.str_stat + 6 &&
    state.int_stat >= state.fth_stat + 6
  ) {
    // D：極端理性學者線（賽莉耶／鄧肯）
    return "templateD";
  }

  if (
    state.fth_stat >= 68 &&
    state.fth_stat >= state.int_stat + 10 &&
    state.fth_stat >= state.str_stat + 6 &&
    state.pragmatic >= state.social
  ) {
    // B：高信仰＋高務實虔誠線（弗蘭梅／克拉福特）
    return "templateB";
  }

  if (
    state.social < 24 &&
    state.pragmatic < 24 &&
    state.str_stat >= state.int_stat + 10 &&
    state.str_stat >= 60
  ) {
    // E：冷血／危險向戰士（尤蓓爾／葛納烏）
    return "templateE";
  }

  if (
    state.social < 20 &&
    state.pragmatic < 22 &&
    state.str_stat >= 78 &&
    state.str_stat >= state.int_stat + 14
  ) {
    // K：極限勇者線（艾莉／南方勇者）
    return "templateK";
  }

  // 其餘依主戰鬥屬性與社交／務實／信仰分流。
  const dominantScores: [SharedEndingTemplateId, number][] = [
    ["templateA", state.int_stat],
    ["templateC", state.str_stat],
    ["templateI", state.fth_stat],
  ];
  dominantScores.sort((a, b) => b[1] - a[1]);
  const topStatId = dominantScores[0]?.[0] ?? "templateA";

  if (topStatId === "templateA") {
    // 智力主軸分流：核心主角型（A）、守護者型（C 映射用）、務實考官型（F）。
    if (
      state.int_stat >= 60 &&
      state.int_stat >= state.str_stat + 5 &&
      state.int_stat >= state.fth_stat &&
      state.pragmatic >= state.social &&
      state.fth_stat >= state.str_stat
    ) {
      // A：智力主角線（芙莉蓮／欣梅爾）
      return "templateA";
    }

    if (
      state.pragmatic >= state.social + 10 &&
      state.str_stat >= 60 &&
      state.str_stat >= state.fth_stat &&
      state.str_stat >= state.int_stat
    ) {
      // F：務實前衛／考官（冉則／艾冉）
      return "templateF";
    }

    // 其餘智力主軸，走較溫柔守護線（費倫／修塔爾克）。
    return "templateC";
  }

  if (topStatId === "templateC") {
    // 力量主軸分流：守護型戰士（C）、軍事拘束型（G）、和事佬／跑圖型（H）。
    if (
      state.str_stat >= 60 &&
      state.str_stat >= state.int_stat &&
      state.str_stat >= state.fth_stat &&
      state.social >= state.pragmatic &&
      state.fth_stat >= 40
    ) {
      // C：溫柔守護型前衛（費倫／修塔爾克）
      return "templateC";
    }

    if (
      state.str_stat >= 60 &&
      state.str_stat > state.int_stat &&
      state.str_stat >= state.fth_stat &&
      state.pragmatic >= state.social + 5 &&
      state.fth_stat <= state.int_stat
    ) {
      // G：拘束／捕獲專家（梅特黛／威亞貝爾）
      return "templateG";
    }

    // 其他力量主軸則走跑圖／和事佬線（拉歐芬／贊恩）。
    return "templateH";
  }

  // 信仰主軸分流：溫暖僧侶（I）、冷靜邊界（J）。
  if (
    state.fth_stat >= 60 &&
    state.fth_stat > state.int_stat &&
    state.fth_stat >= state.str_stat &&
    state.pragmatic >= state.social &&
    state.social >= state.int_stat - 5
  ) {
    // I：溫暖照顧型僧侶（康涅／海塔）
    return "templateI";
  }

  // 其餘信仰主軸 → 冷靜邊界線（拉比涅／蘭特）。
  return "templateJ";
}

function mapTemplateToEndingKey(
  templateId: SharedEndingTemplateId,
  gender: "male" | "female",
): string {
  switch (templateId) {
    case "templateA":
      return gender === "male" ? "himmel" : "frieren";
    case "templateB":
      return gender === "male" ? "kraft" : "flamme";
    case "templateC":
      return gender === "male" ? "stark" : "fern";
    case "templateD":
      return gender === "male" ? "denken" : "serie";
    case "templateE":
      return gender === "male" ? "genau" : "ubel";
    case "templateF":
      return gender === "male" ? "eisen" : "sense";
    case "templateG":
      return gender === "male" ? "wirbel" : "methode";
    case "templateH":
      return gender === "male" ? "sein" : "laufen";
    case "templateI":
      return gender === "male" ? "heiter" : "kanne";
    case "templateJ":
      return gender === "male" ? "land" : "lavine";
    case "templateK":
      return gender === "male" ? "hero_south" : "ehre";
    default:
      return gender === "male" ? "himmel" : "frieren";
  }
}

/**
 * 網頁版結局鍵判定：依共用 11 組模板與主角性別回傳結局資料鍵（`endings.json` 之 `key`）。
 * 不再與桌面 `endings.py` 完全同步，桌機版邏輯維持原樣。
 *
 * @param state - 通關狀態
 */
export function resolveEndingKey(state: GameStateStored): string {
  const gender: "male" | "female" =
    state.protagonist_gender === "male" ? "male" : "female";
  const template = resolveSharedEndingTemplate(state);
  return mapTemplateToEndingKey(template, gender);
}
