/**
 * 遭遇戰／立繪圖檔 URL 候選（對齊 `encounter_cg_battle_try_rel_paths` 與 `play_portrait` 檔名順序）。
 * 圖檔請置於 `web/public/assets/`（與桌面 `assets/` 目錄結構相同）。
 */

import type { EncounterTierJson } from "./types";

function abs(rel: string): string {
  const baseRaw = import.meta.env.BASE_URL;
  const base = baseRaw.endsWith("/") ? baseRaw : `${baseRaw}/`;
  const path = rel.startsWith("/") ? rel.slice(1) : rel;
  return `${base}${path}`;
}

/**
 * 專案內 `assets/...` 相對路徑轉為網頁可載入之絕對 URL（對齊 Vite `public/`）。
 *
 * @param rel - 如 `assets/cg/Foo.jpg`
 */
export function publicAssetUrl(rel: string): string {
  return abs(rel);
}

const _CG_TRY_EXTS = [".jpg", ".jpeg", ".png", ".webp"] as const;

/**
 * 依桌面慣例路徑產生多副檔名候選 URL（同主檔名輪替）。
 *
 * @param projectPath - 如 `assets/cg/Frieren_cg.jpg`
 */
export function cgUrlCandidatesFromProjectPath(projectPath: string): string[] {
  const norm = projectPath.replace(/\\/g, "/").trim();
  const lower = norm.toLowerCase();
  const stem = _CG_TRY_EXTS.some((ext) => lower.endsWith(ext))
    ? norm.replace(/\.[^./\\]+$/i, "")
    : norm;
  const seen = new Set<string>();
  const out: string[] = [];
  for (const ext of _CG_TRY_EXTS) {
    const rel = `${stem}${ext}`;
    if (!seen.has(rel)) {
      seen.add(rel);
      out.push(abs(rel));
    }
  }
  return out;
}

/**
 * 奇遇角色 CG 小圖 URL（與圖片畫廊「夥伴」格、`galleryDomHud.companionCgUrlCandidates` 同路徑）。
 *
 * @param basename - `WhimEncounterJson.cg_basename`
 */
export function whimCompanionCgUrlCandidates(basename: string): string[] {
  const stem = `assets/cg/companions/${basename}`;
  return _CG_TRY_EXTS.map((ext) => abs(`${stem}${ext}`));
}

/** 與 `encounter_defs.LEGACY_ENCOUNTER_ID_ALIASES` 一致 */
const LEGACY_ENCOUNTER_ID_ALIASES: Record<string, string> = {
  lernen: "revolte",
  stille: "red_mirror_dragon",
  escape_golem: "spiegel",
  mimic: "spiegel",
  ubel: "zorida",
  lernen_assassin: "hemon",
};

/**
 * @param enemyId - 敵方 id 或舊別名
 */
export function resolveEncounterIdForAssets(enemyId: string): string {
  return LEGACY_ENCOUNTER_ID_ALIASES[enemyId] ?? enemyId;
}

/**
 * @param enemyId - 敵方 id
 */
export function encounterCgTryIds(enemyId: string): string[] {
  const canonical = resolveEncounterIdForAssets(enemyId);
  if (canonical === "revolte") {
    return ["revolte", "lernen"];
  }
  if (enemyId === "stille") {
    return ["red_mirror_dragon", "stille"];
  }
  if (enemyId === "escape_golem") {
    return ["spiegel", "mimic", "escape_golem"];
  }
  if (enemyId === "mimic") {
    return ["spiegel", "mimic"];
  }
  if (canonical === "zorida") {
    return ["zorida", "ubel"];
  }
  if (canonical === "hemon") {
    return ["hemon", "lernen_assassin"];
  }
  return [canonical];
}

/**
 * 戰鬥 CG 載入順序：每 id 先 `_battle.jpg`／`_battle.png`，再畫廊主圖。
 *
 * @param enemyId - 敵方 id
 */
export function encounterBattleImageUrlCandidates(enemyId: string): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const eid of encounterCgTryIds(enemyId)) {
    for (const rel of [
      `assets/cg/encounters/${eid}_battle.jpg`,
      `assets/cg/encounters/${eid}_battle.png`,
      `assets/cg/encounters/${eid}.jpg`,
      `assets/cg/encounters/${eid}.png`,
    ]) {
      if (!seen.has(rel)) {
        seen.add(rel);
        ordered.push(abs(rel));
      }
    }
  }
  return ordered;
}

/**
 * 畫廊用遭遇戰 CG（不含 `_battle` 專用圖），順序與別名解析同戰鬥版。
 *
 * @param enemyId - 敵方 id
 */
export function encounterGalleryImageUrlCandidates(enemyId: string): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const eid of encounterCgTryIds(enemyId)) {
    for (const ext of [".jpg", ".jpeg", ".png", ".webp"] as const) {
      const rel = `assets/cg/encounters/${eid}${ext}`;
      if (!seen.has(rel)) {
        seen.add(rel);
        ordered.push(abs(rel));
      }
    }
  }
  return ordered;
}

const STAGE_BASE_NAMES: Record<string, [string, string]> = {
  childhood: ["childhood.jpg", "childhood.png"],
  adolescence: ["adolescence.jpg", "adolescence.png"],
  young_adult: ["young_adult.jpg", "young_adult.png"],
};

/**
 * 主角立繪 URL 候選（`assets/portraits/`，與桌面 `play_portrait` 一致）。
 *
 * @param phase - 人生階段
 * @param gender - 主角性別
 */
export function heroinePortraitUrlCandidates(
  phase: "childhood" | "adolescence" | "young_adult",
  gender: "male" | "female",
): string[] {
  const base = STAGE_BASE_NAMES[phase] ?? STAGE_BASE_NAMES.childhood;
  const rels: string[] = [];
  if (gender === "male") {
    for (const name of base) {
      const stem = name.replace(/\.(jpg|png)$/i, "");
      const ext = name.endsWith(".png") ? ".png" : ".jpg";
      rels.push(`assets/portraits/${stem}_male${ext}`);
      rels.push(`assets/portraits/${stem}_m${ext}`);
    }
    for (const name of base) {
      rels.push(`assets/portraits/${name}`);
    }
  } else {
    for (const name of base) {
      const stem = name.replace(/\.(jpg|png)$/i, "");
      const ext = name.endsWith(".png") ? ".png" : ".jpg";
      rels.push(`assets/portraits/${stem}_female${ext}`);
    }
    for (const name of base) {
      rels.push(`assets/portraits/${name}`);
    }
  }
  const seen = new Set<string>();
  const urls: string[] = [];
  for (const r of rels) {
    if (!seen.has(r)) {
      seen.add(r);
      urls.push(abs(r));
    }
  }
  return urls;
}

/**
 * 左上角模式標題（與 `encounter_battle_mode_title_zh` 一致）。
 *
 * @param tier - 魔物／強敵／頭目
 */
export function encounterBattleModeTitleZh(tier: EncounterTierJson): string {
  if (tier === "monster") {
    return "遭遇戰 - 魔物戰";
  }
  if (tier === "elite") {
    return "遭遇戰 - 強敵戰";
  }
  return "遭遇戰 - 頭目戰";
}
