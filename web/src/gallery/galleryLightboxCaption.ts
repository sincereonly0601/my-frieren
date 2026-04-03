/**
 * 畫廊大圖底欄：依實際欄寬量測，僅在超過約定行數可見高度時截短。
 * `trimGalleryCaptionForTwoLines`：夥伴／強敵；`trimGalleryCaptionForOneLine`：獎勵大圖。
 * 截短為「行內最大字數」（二分法）；尾端若落在弱句讀（逗號／分號等）則一併去掉。
 * 語意是否完整仍仰賴來源**定稿短文**，勿依賴程式硬切長文。
 */

/** 兩行高度容許略大於 2×行高，避免量測與實際 `<p>` 差半像素就誤判溢出 */
const TWO_LINE_HEIGHT_EXTRA_PX = 12;

/** 單行高度容許略大於 1×行高，避免量測與實際 `<p>` 差半像素就誤判溢出 */
const ONE_LINE_HEIGHT_EXTRA_PX = 12;

/** 不宜作為整段說明結尾之標點（多為並列、轉折未完） */
const WEAK_ZH_TAIL = new Set("，；、：");

/**
 * @param s - 已截短之字串
 * @returns 去掉尾端連續弱句讀後之字串
 */
function trimTrailingWeakZhPunct(s: string): string {
  let i = s.length;
  while (i > 0) {
    const ch = s[i - 1]!;
    if (!WEAK_ZH_TAIL.has(ch)) {
      break;
    }
    i -= 1;
  }
  return s.slice(0, i).trimEnd();
}

/**
 * @param measurer - 已掛上 DOM、寬度與字級與底欄一致之隱藏量測節點
 * @param fullText - 原始說明
 * @param maxScrollHeight - 兩行行高上限（像素）
 * @returns 使 `scrollHeight <= maxScrollHeight` 之最大尾索引（exclusive）
 */
function binarySearchMaxLength(measurer: HTMLElement, fullText: string, maxScrollHeight: number): number {
  let lo = 0;
  let hi = fullText.length;
  let best = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    measurer.textContent = fullText.slice(0, mid);
    if (measurer.scrollHeight <= maxScrollHeight) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return best;
}

/**
 * 僅在全文高度超過兩行時截至兩行內；未超過則原樣返回。
 *
 * @param capEl - 已置入 DOM 之 `.hud-gallery-lightbox__cap`（用於寬度與計算樣式）
 * @param fullText - 桌機版來源全文
 * @returns 不超過兩行可見高度之字串（盡可能多保留，不為「斷在句號」而多刪）
 */
export function trimGalleryCaptionForTwoLines(capEl: HTMLElement, fullText: string): string {
  const t = (fullText ?? "").trim();
  if (!t) {
    return "";
  }
  const w = capEl.clientWidth;
  if (w <= 0) {
    return t;
  }
  const cs = getComputedStyle(capEl);
  const fontSize = parseFloat(cs.fontSize) || 16;
  const lhRaw = cs.lineHeight;
  const lineHeightPx =
    lhRaw === "normal" ? fontSize * 1.5 : parseFloat(lhRaw) || fontSize * 1.5;
  const maxScrollHeight = lineHeightPx * 2 + TWO_LINE_HEIGHT_EXTRA_PX;

  const m = document.createElement("div");
  m.setAttribute("aria-hidden", "true");
  m.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "visibility:hidden",
    "pointer-events:none",
    `width:${w}px`,
    "box-sizing:border-box",
    "display:block",
    "margin:0",
    `padding:${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
    `font-family:${cs.fontFamily}`,
    `font-size:${cs.fontSize}`,
    `font-weight:${cs.fontWeight}`,
    `font-style:${cs.fontStyle}`,
    `letter-spacing:${cs.letterSpacing}`,
    `line-height:${cs.lineHeight}`,
    "white-space:normal",
    "word-break:break-word",
    "overflow-wrap:anywhere",
  ].join(";");
  document.body.appendChild(m);

  m.textContent = t;
  if (m.scrollHeight <= maxScrollHeight) {
    m.remove();
    return t;
  }

  const best = binarySearchMaxLength(m, t, maxScrollHeight);
  const out = trimTrailingWeakZhPunct(t.slice(0, best).trimEnd());
  m.remove();
  return out;
}

/**
 * 僅在全文高度超過一行時截至一行內；未超過則原樣返回（獎勵大圖底欄用）。
 *
 * @param capEl - 已置入 DOM 之 `.hud-gallery-lightbox__cap`（用於寬度與計算樣式）
 * @param fullText - 桌機版來源全文
 * @returns 不超過一行可見高度之字串（盡可能多保留，不為「斷在句號」而多刪）
 */
export function trimGalleryCaptionForOneLine(capEl: HTMLElement, fullText: string): string {
  const t = (fullText ?? "").trim();
  if (!t) {
    return "";
  }
  const w = capEl.clientWidth;
  if (w <= 0) {
    return t;
  }
  const cs = getComputedStyle(capEl);
  const fontSize = parseFloat(cs.fontSize) || 16;
  const lhRaw = cs.lineHeight;
  const lineHeightPx =
    lhRaw === "normal" ? fontSize * 1.5 : parseFloat(lhRaw) || fontSize * 1.5;
  const maxScrollHeight = lineHeightPx * 1 + ONE_LINE_HEIGHT_EXTRA_PX;

  const m = document.createElement("div");
  m.setAttribute("aria-hidden", "true");
  m.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "visibility:hidden",
    "pointer-events:none",
    `width:${w}px`,
    "box-sizing:border-box",
    "display:block",
    "margin:0",
    `padding:${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
    `font-family:${cs.fontFamily}`,
    `font-size:${cs.fontSize}`,
    `font-weight:${cs.fontWeight}`,
    `font-style:${cs.fontStyle}`,
    `letter-spacing:${cs.letterSpacing}`,
    `line-height:${cs.lineHeight}`,
    "white-space:normal",
    "word-break:break-word",
    "overflow-wrap:anywhere",
  ].join(";");
  document.body.appendChild(m);

  m.textContent = t;
  if (m.scrollHeight <= maxScrollHeight) {
    m.remove();
    return t;
  }

  const best = binarySearchMaxLength(m, t, maxScrollHeight);
  const out = trimTrailingWeakZhPunct(t.slice(0, best).trimEnd());
  m.remove();
  return out;
}
