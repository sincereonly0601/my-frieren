import { installWebBgmGestureUnlock } from "./audio/webBgm";
import { createGame } from "./game/createGame";
import { installGameStageSizeVars } from "./game/installGameStageSizeVars";
import { installLandscapeGate } from "./orientation/landscapeGate";

/**
 * 全舞台背景圖：`public/ui/bg.png`。以 `document.baseURI` 組絕對 URL 寫入 CSS 變數，
 * 供 `.game-stage__fit` 使用；避免 `var(--*)` 內相對 `url` 依 bundled `assets/*.css` 錯解而 404。
 */
function installGameStageBackgroundImageVar(): void {
  try {
    const href = new URL("ui/bg.png", document.baseURI).href;
    document.documentElement.style.setProperty("--game-stage-fit-bg-image", `url("${href}")`);
  } catch {
    /* 離線或極端環境：略過，仍顯示 CSS 內建漸層底 */
  }
}

installGameStageBackgroundImageVar();

/**
 * 開發模式：在 `<html>` 標記類別，讓 CSS 將 `#app` 固定為視窗內最大 13∶6（與遊戲舞台比例一致）。
 * 正式建置不套用，維持 `#app` 全螢幕。
 */
if (import.meta.env.DEV) {
  document.documentElement.classList.add("dev-fixed-aspect-view");
}

const parent = document.querySelector("#game");
if (!(parent instanceof HTMLElement)) {
  throw new Error("找不到 #game 容器（須為 div，Phaser 會自行建立 canvas）");
}

installLandscapeGate();
installGameStageSizeVars();
installWebBgmGestureUnlock();
createGame();
