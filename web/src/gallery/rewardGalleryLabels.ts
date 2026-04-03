/**
 * 獎勵畫廊格標題中文（對齊 `gallery_rewards.reward_token_label_zh` 與檔名 key 解析）。
 */

import {
  GALLERY_FEMALE_ENDING_KEYS,
  GALLERY_MALE_ENDING_KEYS,
} from "./galleryConstants";
import { ENDINGS_BY_KEY } from "../sim/gameData";

/** 與桌面 `gallery_rewards._INTERNAL_TOKEN_SEP` 一致 */
const INTERNAL_TOKEN_SEP = "+";

/** 合法結局 slug（對齊桌面 `GALLERY_ENDING_KEYS` 集合） */
const GALLERY_ENDING_KEY_SET: ReadonlySet<string> = new Set([
  ...GALLERY_MALE_ENDING_KEYS,
  ...GALLERY_FEMALE_ENDING_KEYS,
]);

/** 與桌面 `_REWARD_NARR_NAME_ORDER` 一致（敘事慣用順序；其餘 key 預設 200） */
const REWARD_NARR_NAME_ORDER: Record<string, number> = {
  himmel: 10,
  frieren: 20,
  eisen: 30,
  heiter: 40,
  stark: 50,
  fern: 60,
  flamme: 70,
  serie: 80,
  ubel: 90,
  sense: 100,
  laufen: 110,
  kanne: 120,
  lavine: 130,
  ehre: 140,
  methode: 150,
  sein: 160,
  denken: 170,
  land: 180,
  genau: 190,
  wirbel: 200,
  kraft: 210,
  hero_south: 220,
};

/**
 * 主檔名尾端 `_` + 純數字之變體序號（對齊 `_REWARD_FILENAME_TRAILING_VARIANT_RE`）。
 *
 * @param stem - 不含副檔名之主檔名
 */
function rewardStemWithoutTrailingVariantIndex(stem: string): string {
  const cf = stem.toLowerCase();
  const m = /^(.+)_(\d+)$/.exec(cf);
  if (m == null) {
    return stem;
  }
  const suffix = `_${m[2]}`;
  if (!cf.endsWith(suffix)) {
    return stem;
  }
  return stem.slice(0, -suffix.length);
}

/**
 * 將主檔名解析為 1～4 個合法結局 key（深度優先、長 key 優先）；失敗則 null。
 *
 * @param stem - 不含副檔名
 */
function segmentFilenameStemToKeys(stem: string): string[] | null {
  const s = stem.toLowerCase();
  const n = s.length;
  let found: string[] | null = null;

  /**
   * @param i - 目前字元索引
   * @param acc - 已解析之 key 列（檔名由左而右順序）
   */
  function dfs(i: number, acc: string[]): void {
    if (found !== null) {
      return;
    }
    if (i === n) {
      if (acc.length >= 1 && acc.length <= 4 && new Set(acc).size === acc.length) {
        found = [...acc];
      }
      return;
    }
    if (s[i] === "_") {
      return;
    }
    const candidates = [...GALLERY_ENDING_KEY_SET].filter((k) => s.startsWith(k, i));
    candidates.sort((a, b) => b.length - a.length);
    for (const k of candidates) {
      const j = i + k.length;
      if (j === n) {
        dfs(j, [...acc, k]);
      } else if (j < n && s[j] === "_") {
        dfs(j + 1, [...acc, k]);
      }
      if (found !== null) {
        return;
      }
    }
  }

  dfs(0, []);
  return found;
}

/**
 * 解析獎勵圖主檔名（對齊 `_segment_reward_filename_stem`）。
 *
 * @param stem - 不含副檔名
 */
export function segmentRewardFilenameStem(stem: string): string[] | null {
  const direct = segmentFilenameStemToKeys(stem);
  if (direct != null) {
    return direct;
  }
  const base = rewardStemWithoutTrailingVariantIndex(stem);
  if (base === stem) {
    return null;
  }
  return segmentFilenameStemToKeys(base);
}

/**
 * 規範 token（排序後以 `+` 連接）。
 *
 * @param keys - slug 列表
 */
function canonicalTokenFromKeys(keys: readonly string[]): string {
  return [...keys].sort().join(INTERNAL_TOKEN_SEP);
}

/**
 * @param parts - token 拆出之 slug
 */
function rewardKeysSortedNarr(parts: string[]): string[] {
  return [...parts].sort(
    (a, b) =>
      (REWARD_NARR_NAME_ORDER[a] ?? 200) - (REWARD_NARR_NAME_ORDER[b] ?? 200) ||
      a.localeCompare(b),
  );
}

/**
 * 顯示用 key 順序：優先檔名由左而右，否則敘事慣用排序（對齊 `_key_order_for_display`）。
 *
 * @param parts - token 拆出之 slug（非空）
 * @param filenameKeyOrder - 檔名解析順序；須與 parts 集合完全一致
 */
function keyOrderForDisplay(
  parts: string[],
  filenameKeyOrder: readonly string[] | null,
): string[] {
  const partsSet = new Set(parts);
  if (
    filenameKeyOrder != null &&
    filenameKeyOrder.length === partsSet.size &&
    new Set(filenameKeyOrder).size === partsSet.size &&
    filenameKeyOrder.every((k) => partsSet.has(k))
  ) {
    return [...filenameKeyOrder];
  }
  return rewardKeysSortedNarr(parts);
}

/**
 * 獎勵 token → 畫廊格內中文稱呼（全形間隔號連接，對齊 `reward_token_label_zh`）。
 *
 * @param token - 規範 token（`+` 分隔）
 * @param filenameKeyOrder - 檔名由左而右之 key 序；無則依敘事排序
 */
export function rewardTokenLabelZh(
  token: string,
  filenameKeyOrder: readonly string[] | null,
): string {
  const parts = token.split(INTERNAL_TOKEN_SEP).filter((p) => p !== "");
  if (parts.length === 0) {
    return token;
  }
  const orderKeys = keyOrderForDisplay(parts, filenameKeyOrder);
  return orderKeys.map((p) => ENDINGS_BY_KEY.get(p)?.name ?? p).join("・");
}

/**
 * 由 `assets/cg/rewards/…` 相對路徑產生格內標題與全螢幕底欄標題用中文（與桌面格內標題一致）。
 *
 * @param rel - 如 `assets/cg/rewards/denken.jpg`
 * @param manifestToken - 來自 `gallery_reward_entries` 之規範 token；檔名無法解析時用於轉中文
 */
/**
 * 由獎勵圖相對路徑解析檔名由左而右之結局 key 序（對齊桌面 `filename_key_order`）。
 *
 * @param rel - 如 `assets/cg/rewards/frieren_himmel.jpg`
 */
export function rewardFilenameKeyOrderFromRel(rel: string): readonly string[] | null {
  const norm = rel.replace(/\\/g, "/");
  const filePart = norm.replace(/^.*\//, "");
  const stem = filePart.replace(/\.[^.]+$/i, "");
  return segmentRewardFilenameStem(stem);
}

export function rewardDisplayNamesForRel(
  rel: string,
  manifestToken?: string,
): { label: string; caption: string } {
  const norm = rel.replace(/\\/g, "/");
  const filePart = norm.replace(/^.*\//, "");
  const stem = filePart.replace(/\.[^.]+$/i, "");
  const keys = segmentRewardFilenameStem(stem);
  if (keys != null) {
    const canon = canonicalTokenFromKeys(keys);
    const zh = rewardTokenLabelZh(canon, keys);
    return { label: zh, caption: zh };
  }
  if (manifestToken != null && manifestToken.trim() !== "") {
    const zh = rewardTokenLabelZh(manifestToken.trim(), null);
    return { label: zh, caption: zh };
  }
  return { label: stem, caption: stem };
}
