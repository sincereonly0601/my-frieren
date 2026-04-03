/**
 * 中文段落依字數上限截斷（連續文字、不插硬換行），供奇遇／重大／突發餘韻等與 CSS 折行併用。
 */

/**
 * 敘事顯示：移除字串**末尾**連續之刪節號（全形 `…` 或半形／全形句點兩個以上），避免畫面以「…」「...」收束。
 * 不處理對白中段的「……」遲疑語氣（僅剝除尾端）。
 *
 * @param text - 段落
 * @returns 尾端無孤立刪節號之字串
 */
export function stripTrailingNarrativeEllipsisZh(text: string): string {
  let t = text.trimEnd();
  const tail = /(?:…|[.．]{2,})+$/u;
  while (tail.test(t)) {
    t = t.replace(tail, "").trimEnd();
  }
  return t;
}

/**
 * 截斷至不超過 `maxChars`，優先於句末／；／，斷開。專案預設**不**補刪節號；僅在 `appendEllipsis: true` 時於截斷處加「…」。
 *
 * @param text - 段落原文
 * @param maxChars - 最大字數（約對應版面視覺行數目標）
 * @param opts - 是否於截斷處加刪節號（預設 **false**，符合全遊戲敘事不以刪節號結尾之約定）
 * @returns 截斷後字串
 */
export function trimZhParagraphToMaxChars(
  text: string,
  maxChars: number,
  opts?: { appendEllipsis?: boolean },
): string {
  const appendEllipsis = opts?.appendEllipsis === true;
  const t = text.trim();
  if (t.length <= maxChars) {
    return t;
  }
  const cut = t.slice(0, maxChars);

  /**
   * 於 `s` 內找最後一個句末標點（。！？）索引，無則為 -1。
   *
   * @param s - 搜尋範圍
   */
  const lastStrongSentenceEnd = (s: string): number =>
    Math.max(s.lastIndexOf("。"), s.lastIndexOf("！"), s.lastIndexOf("？"));

  /** 先找「仍夠長」的句末，避免舊版在 `maxChars` 處腰斬長句。 */
  const preferMin = Math.max(12, Math.floor(maxChars * 0.42));
  let strong = lastStrongSentenceEnd(cut);
  if (strong >= 0 && strong < preferMin) {
    const earlier = lastStrongSentenceEnd(cut.slice(0, preferMin));
    if (earlier >= 0) {
      strong = earlier;
    }
  }

  if (strong >= 0) {
    let out = t.slice(0, strong + 1).trim();
    if (out.length > maxChars) {
      out = appendEllipsis ? `${out.slice(0, maxChars - 1)}…` : out.slice(0, maxChars).trim();
    } else if (out.length < t.length && !/[。！？…]$/.test(out) && appendEllipsis) {
      out += "…";
    }
    return out;
  }

  const weakIdx = Math.max(cut.lastIndexOf("；"), cut.lastIndexOf("，"));
  const minWeak = Math.max(8, Math.floor(maxChars * 0.35));
  if (weakIdx >= minWeak) {
    let out = t.slice(0, weakIdx + 1).trim();
    if (out.length > maxChars) {
      out = appendEllipsis ? `${out.slice(0, maxChars - 1)}…` : out.slice(0, maxChars).trim();
    } else if (out.length < t.length && !/[。！？…]$/.test(out) && appendEllipsis) {
      out += "…";
    }
    return out;
  }

  let out = t.slice(0, maxChars).trim();
  if (out.length < t.length && !/[。！？…]$/.test(out) && appendEllipsis) {
    out += "…";
  }
  return out;
}

/**
 * 敘事段落：截斷至 `maxChars`（不補刪節號）並移除尾端孤立刪節號，供 HUD 一段正文顯示。
 *
 * @param text - 已補齊或原文
 * @param maxChars - 上限字數
 * @returns 可送交 `escapeHtml` 之字串
 */
export function finalizeNarrativeZhParagraph(text: string, maxChars: number): string {
  return stripTrailingNarrativeEllipsisZh(
    trimZhParagraphToMaxChars(text, maxChars, { appendEllipsis: false }),
  );
}
