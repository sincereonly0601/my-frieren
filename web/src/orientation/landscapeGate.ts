/**
 * 偵測是否為「應提示橫置」的直向視窗：寬度上限避免僅因瀏覽器視窗拉成直長就擋桌面。
 *
 * @returns 若為直向且視窗寬度不超過上限則為 true
 */
function isPortraitNarrowViewport(): boolean {
  return (
    window.matchMedia("(orientation: portrait)").matches &&
    window.matchMedia("(max-width: 1024px)").matches
  );
}

/**
 * 依目前視窗更新橫屏提示層顯示；可見時擋住底下 Canvas／HUD，避免直向誤觸。
 *
 * @param gate - 全螢幕提示根節點
 */
function syncLandscapeGate(gate: HTMLElement): void {
  const show = isPortraitNarrowViewport();
  gate.hidden = !show;
  gate.setAttribute("aria-hidden", show ? "false" : "true");
}

/**
 * 掛載「請橫向遊玩」閘道：監聽 `resize`／`orientationchange` 與 `orientation` media query。
 * 網頁無法保證強制旋轉；此為預設體驗與 PWA `manifest` 的 `orientation` 搭配使用。
 *
 * @returns 解除監聽函式（測試或 HMR 用）
 */
export function installLandscapeGate(): () => void {
  const gate = document.querySelector("#landscape-gate");
  if (!(gate instanceof HTMLElement)) {
    return () => {};
  }

  const mq = window.matchMedia("(orientation: portrait)");
  const onChange = () => {
    syncLandscapeGate(gate);
  };

  syncLandscapeGate(gate);
  window.addEventListener("resize", onChange);
  window.addEventListener("orientationchange", onChange);
  mq.addEventListener("change", onChange);

  return () => {
    window.removeEventListener("resize", onChange);
    window.removeEventListener("orientationchange", onChange);
    mq.removeEventListener("change", onChange);
  };
}
