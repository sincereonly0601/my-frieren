import Phaser from "phaser";

import { GuardianScene } from "../scenes/GuardianScene";
import { IntroScene } from "../scenes/IntroScene";
import { MenuScene } from "../scenes/MenuScene";
import { FrierenQuizScene } from "../scenes/FrierenQuizScene";
import { OnboardingContractScene } from "../scenes/OnboardingContractScene";
import { OnboardingQuizScene } from "../scenes/OnboardingQuizScene";
import { PlaceholderScene } from "../scenes/PlaceholderScene";
import { TitleScene } from "../scenes/TitleScene";
import { TrainingPreambleScene } from "../scenes/TrainingPreambleScene";

/** 與 CSS `.game-stage__fit`（`aspect-ratio: 13/6`）一致之 Phaser 內部設計寬度。 */
export const GAME_DESIGN_WIDTH = 1300;
/** 與 {@link GAME_DESIGN_WIDTH} 成對之設計高度（13∶6）。 */
export const GAME_DESIGN_HEIGHT = 600;

/**
 * 取裝置像素比上限，避免 3x 以上機種 Canvas 過大。
 *
 * @returns 建議給 Phaser `resolution` 的倍率（1～2.5）
 */
function devicePixelRatioCap(): number {
  return Math.min(window.devicePixelRatio || 1, 2.5);
}

/**
 * 建立 Phaser 實例：`#game` 置於固定 13∶6 舞台（見 `index.html`、`.game-stage__fit`）；
 * 使用 `Scale.FIT` 與固定 {@link GAME_DESIGN_WIDTH}×{@link GAME_DESIGN_HEIGHT} 設計座標，由舞台尺寸驅動縮放。
 * 產品預設為手機橫向（見 `installLandscapeGate`、PWA `manifest`）；直向窄螢幕會顯示橫置提示。
 * 使用 `resolution` 對齊裝置像素比，避免高 DPI 螢幕上文字與線條模糊。
 *
 * @returns 已啟動之 `Phaser.Game`（首場景為 {@link TitleScene}）
 */
export function createGame(): Phaser.Game {
  const dpr = devicePixelRatioCap();
  /** 執行期支援 `resolution`；型別檔略舊時以斷言通過檢查 */
  const config = {
    type: Phaser.AUTO,
    parent: "game",
    /** 透明以透出 `.game-stage__fit` 之共用背景圖（見 `installGameStageBackgroundImageVar`） */
    transparent: true,
    scale: {
      mode: Phaser.Scale.FIT,
      autoCenter: Phaser.Scale.CENTER_BOTH,
      width: GAME_DESIGN_WIDTH,
      height: GAME_DESIGN_HEIGHT,
    },
    resolution: dpr,
    scene: [
      TitleScene,
      MenuScene,
      IntroScene,
      GuardianScene,
      OnboardingQuizScene,
      OnboardingContractScene,
      TrainingPreambleScene,
      FrierenQuizScene,
      PlaceholderScene,
    ],
    input: {
      activePointers: 3,
    },
    render: {
      antialias: true,
      pixelArt: false,
      roundPixels: false,
    },
  } as Phaser.Types.Core.GameConfig;
  return new Phaser.Game(config);
}
