/**
 * 與桌機 `main.py` 之 `_BGM_*` 檔名一致（`assets/bgm` 內 OGG）。
 * 請將桌機 `assets/bgm/*.ogg` 複製到 `web/public/assets/bgm/`。
 */

/** 標題／主選單／讀檔／畫廊／設定／結局／存檔選單等 */
export const BGM_FILE_OPENING = "Journey of a Lifetime.ogg";

/** 開場前言／監護人／問卷／契約 */
export const BGM_FILE_PROLOGUE = "Fear Brought Me This Far.ogg";

/** 幼年培養、突發、奇遇（青年階段亦回退至此曲，對齊桌機 `young_adult`→Fear） */
export const BGM_FILE_CHILDHOOD = "Time Flows Ever Onward.ogg";

/** 重大事件、遭遇戰 */
export const BGM_FILE_MAJOR = "Zoltraak.ogg";

/** 少年階段 */
export const BGM_FILE_ADOLESCENCE = "The End of One Journey.ogg";

/**
 * @param fileName - 含空白之檔名（與資料夾內實際檔名一致）
 * @returns 絕對音檔 URL（併入 Vite `base`，子路徑部署時仍正確）
 */
export function bgmAssetUrl(fileName: string): string {
  const enc = encodeURIComponent(fileName);
  let base = import.meta.env.BASE_URL;
  if (base === "" || base === undefined) {
    base = "/";
  }
  if (!base.endsWith("/")) {
    base = `${base}/`;
  }
  const rel = `${base}assets/bgm/${enc}`;
  return new URL(rel, document.baseURI).href;
}
