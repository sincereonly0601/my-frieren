/**
 * 網頁版僅存於 localStorage 之偏好（BGM、作弊開局開關、畫廊全結局作弊旗標）。
 * BGM 預設為開啟；開／關皆寫入 {@link LS_BGM_ENABLED}，關閉分頁或重載後仍沿用。
 */

/** `"1"`＝背景音樂開；`"0"`＝關。無此鍵時視為開（預設）。 */
const LS_BGM_ENABLED = "ff-web-bgm-enabled";
/** 舊版僅在關閉時寫入之鍵；讀取時遷移至 {@link LS_BGM_ENABLED} */
const LS_BGM_MUTED_LEGACY = "ff-web-bgm-muted";
const LS_CHEAT_BOOTSTRAP = "ff-web-cheat-bootstrap";
const LS_CHEAT_GALLERY_ALL = "ff-cheat-gallery-all-active";

/**
 * @param s - 原始字串
 */
function readFlag(key: string): boolean {
  if (typeof localStorage === "undefined") {
    return false;
  }
  return localStorage.getItem(key) === "1";
}

/**
 * @param key - localStorage 鍵
 * @param on - 是否寫入為啟用
 */
function writeFlag(key: string, on: boolean): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  if (on) {
    localStorage.setItem(key, "1");
  } else {
    localStorage.removeItem(key);
  }
}

/**
 * 背景音樂是否靜音（預設否＝音樂開；偏好存於 localStorage 可跨重啟）。
 *
 * @returns 若使用者關閉 BGM 則為 true
 */
export function isBgmMutedPreferred(): boolean {
  if (typeof localStorage === "undefined") {
    return false;
  }
  const v = localStorage.getItem(LS_BGM_ENABLED);
  if (v === "0") {
    return true;
  }
  if (v === "1") {
    return false;
  }
  if (localStorage.getItem(LS_BGM_MUTED_LEGACY) === "1") {
    try {
      localStorage.setItem(LS_BGM_ENABLED, "0");
      localStorage.removeItem(LS_BGM_MUTED_LEGACY);
    } catch {
      /* 略過（如無痕拒寫） */
    }
    return true;
  }
  return false;
}

/**
 * 寫入 BGM 開關，供下次進入遊戲還原。
 *
 * @param muted - true ＝關閉音樂；false ＝開啟音樂
 */
export function setBgmMutedPreferred(muted: boolean): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  try {
    localStorage.setItem(LS_BGM_ENABLED, muted ? "0" : "1");
    localStorage.removeItem(LS_BGM_MUTED_LEGACY);
  } catch {
    /* 私密模式等：略過寫入 */
  }
}

/**
 * @returns 是否啟用「作弊開局」（新遊戲重置寫入高屬性狀態，對齊桌面）
 */
export function isCheatBootstrapPreferred(): boolean {
  return readFlag(LS_CHEAT_BOOTSTRAP);
}

/**
 * @param on - 是否啟用作弊開局
 */
export function setCheatBootstrapPreferred(on: boolean): void {
  writeFlag(LS_CHEAT_BOOTSTRAP, on);
}

/**
 * @returns 「解鎖畫廊全部結局 CG」作弊是否視為開啟（用於設定列（開）／（關））
 */
export function isCheatGalleryAllEndingsActive(): boolean {
  return readFlag(LS_CHEAT_GALLERY_ALL);
}

/**
 * @param on - 是否標記為開啟（關閉時應一併還原 ending_keys 快照）
 */
export function setCheatGalleryAllEndingsActive(on: boolean): void {
  writeFlag(LS_CHEAT_GALLERY_ALL, on);
}
