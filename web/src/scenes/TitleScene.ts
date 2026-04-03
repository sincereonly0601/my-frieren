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
    mountTitleHud();
    this.input.once("pointerdown", () => {
      this.scene.start("Menu");
    });
  }
}
