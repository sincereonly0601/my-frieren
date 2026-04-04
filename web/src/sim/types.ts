/**
 * 與 `tools/export_web_sim_data.py` 匯出之 JSON 結構對齊的型別。
 */

export type MajorOptionJson = {
  label: string;
  deltas: Record<string, number>;
  flags_add: string[];
  flags_add_if_male: string[];
  flags_add_if_female: string[];
  extra_deltas: Record<string, number>;
};

export type MajorEventJson = {
  age_year: number;
  title: string;
  preamble_title: string;
  preamble_body: string[];
  /** 網頁版前言單頁正文（全寬欄約 180 字／五行濃縮合併段） */
  preamble_merged_zh: string;
  /** 選擇畫面題幹（連續一段；與突發事件 `body` 同級） */
  choice_prompt_zh: string;
  resolution_bodies: string[][];
  options: MajorOptionJson[];
};

export type IncidentOptionJson = {
  label: string;
  deltas: Record<string, number>;
};

export type IncidentEventJson = {
  id: string;
  tier: number;
  title: string;
  body: string;
  options: IncidentOptionJson[];
};

export type EncounterTierJson = "monster" | "elite" | "boss";

export type EncounterEnemyJson = {
  id: string;
  tier: EncounterTierJson;
  name_zh: string;
  name_en: string;
  difficulty: number;
  base_hp: number;
  base_atk: number;
  base_def: number;
  move_names: string[];
  ultimate_zh: string;
  aftermath_win: string[];
  aftermath_lose: string[];
  treasure_deltas: Record<string, number>;
  treasure_name_zh: string;
  gallery_intro_zh: string;
};

export type EncountersBundleJson = {
  monsters: EncounterEnemyJson[];
  elites: EncounterEnemyJson[];
  bosses: EncounterEnemyJson[];
};

export type EndingJson = {
  key: string;
  name: string;
  title: string;
  narrative_pages: string[];
  quote: string;
  cg_path: string;
};

export type WhimEncounterJson = {
  key: string;
  display_name: string;
  epithet: string;
  location_zh: string;
  preamble_para1: string;
  preamble_para2: string;
  chat: string;
  quiz_opening_zh: string;
  aftermath_correct_para1: string;
  aftermath_correct_para2: string;
  aftermath_wrong_para1: string;
  aftermath_wrong_para2: string;
  deltas_correct: Record<string, number>;
  deltas_wrong: Record<string, number>;
  cg_basename: string;
  gallery_footer_zh: string;
};

export type WhimQuestionJson = {
  stem: string;
  options: [string, string, string];
  correct_index: number;
  qid?: string;
  explanation_zh?: string;
};
