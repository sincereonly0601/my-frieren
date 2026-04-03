/**
 * 監護契約：網頁用偽古文、洗牌種子（種子演算法對照桌面 `_contract_visual_seed`）。
 *
 * **僅兩段**：每段**一整段連寫**（字串內無 `\n`）；換行僅由瀏覽器依欄寬自動折行。段距見 `.hud-contract-runes-inner` 的 `gap`。段落順序仍以種子洗牌。
 */

/**
 * 網頁契約內文：兩則連寫（各一 `<p>`）。
 */
export const CONTRACT_RUNE_LINES_WEB: readonly string[] = [
  "凡締此紙者，無星之夜勿啟其縫，啟則時序洩於指隙。名先於形，形先於憶；「※」為界、「◇」為扉，血脈三結為環。守秘者曰：所見非字，乃他界餘燼之影。遇「卍」影勿誦其名，名出則契焚；監護自落印，滿十二巡方議解。",
  "空行供真名，一成則餘文皆贅；⋄契主無面，有名者負其重。誦此同默認；隙唯月相與印泥知。墨痕自現乃紙自記，勿拭；蝕夜紙背異文，讀或忘本約。「◇◇」相連謂暫緩非作廢，勿誤作解約據。暫緩之間責仍在有名者；故展卷須擇時，勿於蝕時輕誦。",
];

/** 契紙內標題（桌面 `draw_contract_seal_screen` 標頭列）。 */
export const CONTRACT_PAPER_HEADER_ZH = "古式監護契書";

/** 署名區標籤（桌面 `draw_contract_seal_screen` 與此對齊）。 */
export const CONTRACT_NAME_LABEL_ZH = "受監護者之名：";

/**
 * 朱文式方印四字「監護之印」之 DOM 順序（橫排網格、列優先左→右）：
 * 上列「之、監」、下列「印、護」，對應傳統由右而左、由上而下（右列監→護、左列之→印）。
 */
export const CONTRACT_SEAL_GRID_CHARS_ZH: readonly string[] = [
  "之",
  "監",
  "印",
  "護",
];

/**
 * 與桌面 `_contract_visual_seed` 相同：姓名 UTF-8 經 SHA-256，取前四位元組大端序整數再模 2^31。
 *
 * @param name - 主角姓名（與桌面 `heroine_name.strip() or "."` 一致）
 */
export async function contractVisualSeed(name: string): Promise<number> {
  const raw = (name.trim() || ".").normalize("NFC");
  const enc = new TextEncoder().encode(raw);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  const u8 = new Uint8Array(buf);
  const n =
    ((u8[0]! << 24) | (u8[1]! << 16) | (u8[2]! << 8) | u8[3]!) >>> 0;
  return n % 2 ** 31;
}

/**
 * Mulberry32 PRNG；種子非零時較穩定。
 *
 * @param seed - 非負整數
 * @returns 回傳 [0, 1) 的函式
 */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  if (a === 0) {
    a = 0x6d2b79f5;
  }
  return () => {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 依種子打亂偽古文 **兩段** 之順序（對照桌面版打亂多則之概念；網頁為兩塊連寫長文）。
 *
 * @param seed - `contractVisualSeed` 回傳值
 */
export function shuffleContractRunes(seed: number): string[] {
  const arr = [...CONTRACT_RUNE_LINES_WEB];
  const rnd = mulberry32(seed ^ 0x9e3779b9);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    const t = arr[i]!;
    arr[i] = arr[j]!;
    arr[j] = t;
  }
  return arr;
}

/**
 * 非同步取得本姓名對應之偽古文段落（已洗牌）。
 *
 * @param heroineName - 存檔內姓名
 */
export async function shuffledContractRunesForName(
  heroineName: string,
): Promise<string[]> {
  const seed = await contractVisualSeed(heroineName);
  return shuffleContractRunes(seed);
}
