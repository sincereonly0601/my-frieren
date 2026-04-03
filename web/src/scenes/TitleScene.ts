import Phaser from "phaser";

import { mountTitleHud } from "../hud/domHud";

/**
 * 首屏：文案改由 DOM HUD 顯示（較清晰）；點擊仍由 Phaser 全畫布接收。
 */
export class TitleScene extends Phaser.Scene {
  public constructor() {
    super({ key: "Title" });
  }

  /** @inheritdoc */
  public create(): void {
    this.setTitleBackground();
    mountTitleHud();
    this.input.once("pointerdown", () => {
      this.scene.start("Menu");
    });
  }

  /**
   * 首屏：強制還原全舞台預設底圖 `bg.png`（結局等流程可能仍留著 `bg2`）。
   */
  private setTitleBackground(): void {
    try {
      const docEl = document.documentElement;
      const href = new URL("ui/bg.png", document.baseURI).href;
      docEl.style.setProperty("--game-stage-fit-bg-image", `url("${href}")`);
    } catch {
      /* 環境若不支援 DOM 或 URL，略過背景切換 */
    }
  }
}
