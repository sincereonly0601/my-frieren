/**
 * 將 `.game-stage__fit`（13∶6 內接矩形）的實際像素寬高同步到 `document.documentElement` 的 CSS 變數，
 * 供掛在 `body` 的 `fixed` 層以 `var(--game-stage-fit-wpx)` 等對齊遊戲舞台（`cqw` 無祖先容器時）。
 *
 * - `--game-stage-fit-wpx`／`--game-stage-fit-hpx`：數值＋`px`；量測失敗時後援為 `100vw`／`100dvh`。
 */

const FIT_SELECTOR = ".game-stage__fit";

/**
 * 綁定 `ResizeObserver` 與 `resize`，在下一幀讀取邊界框，避免與版面尚未穩定競態。
 */
export function installGameStageSizeVars(): void {
  const root = document.documentElement;

  /**
   * @param w - 寬度後援字串
   * @param h - 高度後援字串
   */
  const setFallback = (w: string, h: string): void => {
    root.style.setProperty("--game-stage-fit-wpx", w);
    root.style.setProperty("--game-stage-fit-hpx", h);
  };

  const fit = document.querySelector(FIT_SELECTOR);
  if (!(fit instanceof HTMLElement)) {
    setFallback("100vw", "100dvh");
    return;
  }

  const apply = (): void => {
    requestAnimationFrame(() => {
      const r = fit.getBoundingClientRect();
      const w = Math.round(r.width * 1000) / 1000;
      const h = Math.round(r.height * 1000) / 1000;
      if (w > 0 && h > 0) {
        root.style.setProperty("--game-stage-fit-wpx", `${w}px`);
        root.style.setProperty("--game-stage-fit-hpx", `${h}px`);
      } else {
        setFallback("100vw", "100dvh");
      }
    });
  };

  apply();

  if (typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => {
      apply();
    });
    ro.observe(fit);
  }

  window.addEventListener("resize", apply);
}
