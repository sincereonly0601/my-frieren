/**
 * 與桌面 `main.py` 標題選單、`ending_gallery`／`endings` 畫廊順序對齊之常數。
 */

/** 對齊標題主選單順序（含「讀取最新進度」） */
export const TITLE_MENU_ITEMS_ZH: readonly string[] = [
  "新遊戲",
  "讀取最新進度",
  "讀取進度",
  "圖片畫廊",
  "遊戲設定",
  "結束遊戲",
] as const;

/** 對齊 `_GALLERY_HUB_MENU_ITEMS` */
export const GALLERY_HUB_ITEMS_ZH: readonly string[] = [
  "通關結局(男性)",
  "通關結局(女性)",
  "同行的夥伴(奇遇)",
  "遭遇的強敵(遭遇戰)",
  "獎勵圖片",
] as const;

/** 對齊 `ENDING_CG_UNLOCK_DISPLAY_ORDER` 前 11 鍵（女性路線格位順序） */
export const GALLERY_FEMALE_ENDING_KEYS: readonly string[] = [
  "frieren",
  "flamme",
  "fern",
  "sense",
  "methode",
  "laufen",
  "ehre",
  "lavine",
  "kanne",
  "ubel",
  "serie",
] as const;

/** 對齊 `ENDING_CG_UNLOCK_DISPLAY_ORDER` 後 11 鍵（男性路線格位順序） */
export const GALLERY_MALE_ENDING_KEYS: readonly string[] = [
  "himmel",
  "stark",
  "eisen",
  "heiter",
  "sein",
  "denken",
  "land",
  "genau",
  "wirbel",
  "kraft",
  "hero_south",
] as const;
