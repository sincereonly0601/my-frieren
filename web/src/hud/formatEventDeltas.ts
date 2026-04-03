/**
 * 事件餘韻／結算用之五維與隱藏值變化一行（與桌面 `format_incident_deltas_brief` 用語一致）。
 */

const LABEL_ZH: Record<string, string> = {
  int_stat: "智力",
  str_stat: "力量",
  social: "社交",
  fth_stat: "信仰",
  pragmatic: "務實",
  truth_seek: "真理探求",
  corruption: "腐化傾向",
};

/**
 * 合併多組增量後格式化為一行顯示（例：`智力+3　力量-1`）。
 *
 * @param parts - 多份增量表（後者覆蓋同鍵時先合併）
 */
export function formatMergedDeltasLineZh(
  ...parts: ReadonlyArray<Readonly<Record<string, number>>>
): string {
  const acc: Record<string, number> = {};
  for (const p of parts) {
    for (const [k, v] of Object.entries(p)) {
      if (typeof v !== "number" || v === 0) {
        continue;
      }
      acc[k] = (acc[k] ?? 0) + v;
    }
  }
  const entries = Object.entries(acc)
    .filter(([, v]) => v !== 0)
    .sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) {
    return "（本段無數值增減）";
  }
  return entries
    .map(([k, v]) => {
      const label = LABEL_ZH[k] ?? k;
      return `${label}${v > 0 ? "+" : ""}${v}`;
    })
    .join("　");
}
