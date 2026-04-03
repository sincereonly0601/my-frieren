/**
 * HUD 根節點上的短提示（與存檔成功 toast 相同樣式）。
 */

const HUD_ID = "hud";
const DEFAULT_TOAST_MS = 2000;

/**
 * 供 `innerHTML` 顯示用文字跳脫。
 *
 * @param s - 任意顯示字串
 */
export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * 顯示約 {@link durationMs} 後自動消失之訊息；可點擊提前關閉。
 *
 * @param messageZh - 已為純文字（會經 {@link escapeHtml}）
 * @param durationMs - 停留毫秒
 */
export function showHudMessageToast(messageZh: string, durationMs = DEFAULT_TOAST_MS): void {
  const el = document.getElementById(HUD_ID);
  if (!el) {
    return;
  }
  el.querySelectorAll(".hud-app-toast").forEach((n) => {
    n.remove();
  });
  const t = document.createElement("div");
  t.className = "hud-app-toast";
  t.setAttribute("role", "status");
  t.setAttribute("aria-live", "polite");
  t.innerHTML = `<p class="hud-app-toast__text">${escapeHtml(messageZh)}</p>`;
  el.appendChild(t);
  requestAnimationFrame(() => {
    t.classList.add("hud-app-toast--visible");
  });
  const dismiss = (): void => {
    t.classList.remove("hud-app-toast--visible");
    window.setTimeout(() => {
      t.remove();
    }, 200);
  };
  const tid = window.setTimeout(dismiss, durationMs);
  t.addEventListener(
    "click",
    () => {
      window.clearTimeout(tid);
      dismiss();
    },
    { once: true },
  );
}
