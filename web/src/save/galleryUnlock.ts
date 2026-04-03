/**
 * 圖片畫廊解鎖紀錄（IndexedDB，欄位對齊桌面 `ending_gallery_unlock.json`）。
 */

import {
  GALLERY_FEMALE_ENDING_KEYS,
  GALLERY_MALE_ENDING_KEYS,
} from "../gallery/galleryConstants";
import rewardEntries from "../sim/data/gallery_reward_entries.json";
import { ENCOUNTERS, WHIM_ENCOUNTERS } from "../sim/gameData";
import { resolveEncounterIdForAssets } from "../sim/encounterAssetUrls";

const DB_NAME = "frieren-factory-web";
const DB_VERSION = 1;
const STORE = "meta";
const KEY_DOC = "galleryUnlockDocV1";
/** 開啟「全結局 CG」作弊前之 `ending_keys` 快照（JSON 字串陣列） */
const LS_CHEAT_ENDING_SNAPSHOT = "ff-cheat-ending-keys-snapshot";

/**
 * 與桌面 JSON 各分類欄位一致。
 */
export type GalleryUnlockDoc = {
  ending_keys: string[];
  companion_keys: string[];
  enemy_keys: string[];
  whim_keys: string[];
  reward_keys: string[];
};

type RewardEntryJson = { rel: string; token: string; required_keys: string[] };

const REWARD_ENTRIES = rewardEntries as RewardEntryJson[];

/**
 * @returns 空文件
 */
function emptyGalleryUnlockDoc(): GalleryUnlockDoc {
  return {
    ending_keys: [],
    companion_keys: [],
    enemy_keys: [],
    whim_keys: [],
    reward_keys: [],
  };
}

/**
 * @param raw - 任意 JSON
 */
function normalizeDoc(raw: unknown): GalleryUnlockDoc {
  const z = emptyGalleryUnlockDoc();
  if (!raw || typeof raw !== "object") {
    return z;
  }
  const o = raw as Record<string, unknown>;
  const pick = (k: keyof GalleryUnlockDoc): string[] => {
    const v = o[k];
    if (!Array.isArray(v)) {
      return [];
    }
    return v.filter((x): x is string => typeof x === "string" && x.trim() !== "").map((s) => s.trim());
  };
  return {
    ending_keys: [...new Set(pick("ending_keys"))].sort(),
    companion_keys: [...new Set(pick("companion_keys"))].sort(),
    enemy_keys: [...new Set(pick("enemy_keys"))].sort(),
    whim_keys: [...new Set(pick("whim_keys"))].sort(),
    reward_keys: [...new Set(pick("reward_keys"))].sort(),
  };
}

function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") {
    return Promise.reject(new Error("此瀏覽器不支援 IndexedDB"));
  }
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = (): void => {
      reject(req.error ?? new Error("IndexedDB open failed"));
    };
    req.onsuccess = (): void => {
      resolve(req.result);
    };
    req.onupgradeneeded = (): void => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
  });
}

/**
 * 依目前 `ending_keys` 重算 `reward_keys`（與桌面 `eligible_reward_tokens` 一致之 token 集合）。
 *
 * @param doc - 可變文件
 */
export function recomputeGalleryRewardKeys(doc: GalleryUnlockDoc): void {
  const ek = new Set(doc.ending_keys);
  const tokens = new Set<string>();
  for (const row of REWARD_ENTRIES) {
    if (row.required_keys.every((k) => ek.has(k))) {
      tokens.add(row.token);
    }
  }
  doc.reward_keys = [...tokens].sort();
}

/**
 * 讀取畫廊解鎖文件；無則空。
 */
export async function loadGalleryUnlockDoc(): Promise<GalleryUnlockDoc> {
  const db = await openDb();
  try {
    const raw: unknown = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      tx.onerror = (): void => {
        reject(tx.error ?? new Error("read tx"));
      };
      const r = tx.objectStore(STORE).get(KEY_DOC);
      r.onerror = (): void => {
        reject(r.error ?? new Error("get gallery unlock"));
      };
      r.onsuccess = (): void => {
        resolve(r.result);
      };
    });
    return normalizeDoc(raw);
  } finally {
    db.close();
  }
}

/**
 * @param doc - 完整文件
 */
export async function saveGalleryUnlockDoc(doc: GalleryUnlockDoc): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.oncomplete = (): void => {
        resolve();
      };
      tx.onerror = (): void => {
        reject(tx.error ?? new Error("write tx"));
      };
      tx.objectStore(STORE).put(doc, KEY_DOC);
    });
  } finally {
    db.close();
  }
}

/**
 * 通關結局後登錄（冪等）。
 *
 * @param endingKey - `endings.json` 之 `key`
 */
export async function addGalleryEndingUnlock(endingKey: string): Promise<void> {
  const k = (endingKey ?? "").trim();
  if (!k) {
    return;
  }
  const doc = await loadGalleryUnlockDoc();
  if (!doc.ending_keys.includes(k)) {
    doc.ending_keys.push(k);
    doc.ending_keys.sort();
  }
  recomputeGalleryRewardKeys(doc);
  await saveGalleryUnlockDoc(doc);
}

/**
 * 遭遇戰勝利後登錄敵方 id（冪等；正規化別名）。
 *
 * @param enemyId - `EncounterEnemyJson.id`
 */
export async function addGalleryEnemyUnlock(enemyId: string): Promise<void> {
  const canon = resolveEncounterIdForAssets((enemyId ?? "").trim());
  if (!canon) {
    return;
  }
  const doc = await loadGalleryUnlockDoc();
  if (!doc.enemy_keys.includes(canon)) {
    doc.enemy_keys.push(canon);
    doc.enemy_keys.sort();
  }
  await saveGalleryUnlockDoc(doc);
}

/**
 * 奇遇答對後登錄 CG 主檔名鍵（冪等；與桌面 `register_whim_gallery_unlock` 傳入相同）。
 *
 * @param cgBasename - `WhimEncounterJson.cg_basename`
 */
export async function addGalleryWhimUnlock(cgBasename: string): Promise<void> {
  const k = (cgBasename ?? "").trim();
  if (!k) {
    return;
  }
  const doc = await loadGalleryUnlockDoc();
  if (!doc.whim_keys.includes(k)) {
    doc.whim_keys.push(k);
    doc.whim_keys.sort();
  }
  await saveGalleryUnlockDoc(doc);
}

/**
 * 供畫廊 UI 一次載入之集合視圖。
 */
export type GalleryUnlockSets = {
  endings: ReadonlySet<string>;
  enemies: ReadonlySet<string>;
  whims: ReadonlySet<string>;
  rewards: ReadonlySet<string>;
};

/**
 * @param doc - 解鎖文件
 */
export function galleryUnlockSetsFromDoc(doc: GalleryUnlockDoc): GalleryUnlockSets {
  return {
    endings: new Set(doc.ending_keys),
    enemies: new Set(doc.enemy_keys),
    whims: new Set(doc.whim_keys),
    rewards: new Set(doc.reward_keys),
  };
}

/**
 * 讀取並轉成 Set（供分頁畫廊用）。
 */
export async function loadGalleryUnlockSets(): Promise<GalleryUnlockSets> {
  const doc = await loadGalleryUnlockDoc();
  return galleryUnlockSetsFromDoc(doc);
}

const REL_TO_TOKEN: Map<string, string> = (() => {
  const m = new Map<string, string>();
  for (const row of REWARD_ENTRIES) {
    m.set(row.rel, row.token);
  }
  return m;
})();

/**
 * @param rel - 如 `assets/cg/rewards/foo.jpg`
 */
export function rewardTokenForRelPath(rel: string): string | undefined {
  return REL_TO_TOKEN.get(rel);
}

/**
 * @returns 畫廊通關結局格所用之全部結局鍵（男女路線合併去重）
 */
export function allGalleryEndingKeysSorted(): string[] {
  return [
    ...new Set([...GALLERY_MALE_ENDING_KEYS, ...GALLERY_FEMALE_ENDING_KEYS]),
  ].sort();
}

/**
 * 移除全結局作弊用之快照鍵（清空畫廊或關閉作弊時由 UI 層一併呼叫）。
 */
export function clearCheatEndingKeysSnapshot(): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  localStorage.removeItem(LS_CHEAT_ENDING_SNAPSHOT);
}

/**
 * 將畫廊解鎖文件重設為全空（對齊桌面「清空畫廊已解鎖的 CG 圖」）。
 */
export async function resetGalleryUnlockDocToEmpty(): Promise<void> {
  await saveGalleryUnlockDoc(emptyGalleryUnlockDoc());
}

/**
 * 作弊：解鎖全部通關結局 CG 鍵並重算獎勵 token；先快照目前 `ending_keys`。
 */
export async function cheatUnlockAllEndingCgs(): Promise<void> {
  const doc = await loadGalleryUnlockDoc();
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(LS_CHEAT_ENDING_SNAPSHOT, JSON.stringify(doc.ending_keys));
  }
  doc.ending_keys = allGalleryEndingKeysSorted();
  recomputeGalleryRewardKeys(doc);
  await saveGalleryUnlockDoc(doc);
}

/**
 * 關閉全結局作弊：還原快照中之 `ending_keys`（無快照則清空該欄）。
 */
export async function cheatDisableAllEndingCgs(): Promise<void> {
  let restored: string[] = [];
  if (typeof localStorage !== "undefined") {
    const raw = localStorage.getItem(LS_CHEAT_ENDING_SNAPSHOT);
    localStorage.removeItem(LS_CHEAT_ENDING_SNAPSHOT);
    if (raw) {
      try {
        const p: unknown = JSON.parse(raw);
        if (Array.isArray(p)) {
          restored = p.filter((x): x is string => typeof x === "string" && x.trim() !== "");
        }
      } catch {
        restored = [];
      }
    }
  }
  const doc = await loadGalleryUnlockDoc();
  doc.ending_keys = [...new Set(restored.map((s) => s.trim()))].sort();
  recomputeGalleryRewardKeys(doc);
  await saveGalleryUnlockDoc(doc);
}

/**
 * 作弊：登錄全部奇遇 CG 與全部遭遇戰敵方圖鑑鍵（對齊桌面一鍵解鎖夥伴／強敵畫廊）。
 */
export async function cheatUnlockAllWhimsAndEnemies(): Promise<void> {
  const doc = await loadGalleryUnlockDoc();
  const whims = new Set(doc.whim_keys);
  for (const w of WHIM_ENCOUNTERS) {
    whims.add(w.cg_basename);
  }
  doc.whim_keys = [...whims].sort();
  const enemies = new Set(doc.enemy_keys);
  for (const e of [...ENCOUNTERS.monsters, ...ENCOUNTERS.elites, ...ENCOUNTERS.bosses]) {
    enemies.add(resolveEncounterIdForAssets(e.id));
  }
  doc.enemy_keys = [...enemies].sort();
  await saveGalleryUnlockDoc(doc);
}
