import Phaser from "phaser";

import { mountPlaceholderHudError } from "../hud/domHud";
import { mountIntroHud } from "../hud/onboardingHud";
import { PROLOGUE_SECTIONS } from "../story/onboardingCopy";
import {
  emptyGameSaveV3,
  loadGameSave,
  makeCheatBootstrapGameSaveV3,
  syncPhaseFromTimeLeft,
  writeGameSave,
} from "../save/idbSave";
import { isCheatBootstrapPreferred } from "../save/webPrefs";

/**
 * 開場前提三頁（對應桌面 `Screen.INTRO`）。
 */
export class IntroScene extends Phaser.Scene {
  private _resetProgress = false;
  private _page = 0;

  public constructor() {
    super({ key: "Intro" });
  }

  /** @inheritdoc */
  public init(data: object): void {
    const d = data as { resetProgress?: boolean };
    this._resetProgress = d?.resetProgress === true;
  }

  /** @inheritdoc */
  public create(): void {
    void this.boot();
  }

  /**
   * 可選整表重置後載入；已讀過開場則跳監護人。
   */
  private async boot(): Promise<void> {
    try {
      if (this._resetProgress) {
        const base = isCheatBootstrapPreferred()
          ? makeCheatBootstrapGameSaveV3()
          : emptyGameSaveV3();
        await writeGameSave({
          ...base,
          lastSavedAt: new Date().toISOString(),
        });
      }
      const save = await loadGameSave();
      if (save == null) {
        this.scene.start("Menu");
        return;
      }
      if (save.game.intro_done) {
        this.scene.start("Guardian");
        return;
      }
      this._page = 0;
      this.mountIntro();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 依 `this._page` 繪製開場 HUD。
   */
  private mountIntro(): void {
    mountIntroHud({
      pageIndex: this._page,
      onPrev: () => {
        if (this._page > 0) {
          this._page -= 1;
          this.mountIntro();
        }
      },
      onNext: () => {
        const max = PROLOGUE_SECTIONS.length - 1;
        if (this._page < max) {
          this._page += 1;
          this.mountIntro();
        }
      },
      onFinishIntro: () => {
        void this.finishIntro();
      },
    });
  }

  /**
   * 標記 `introDone` 並進入監護人畫面。
   */
  private async finishIntro(): Promise<void> {
    try {
      const prev = await loadGameSave();
      if (prev == null) {
        return;
      }
      const game = { ...prev.game, intro_done: true };
      syncPhaseFromTimeLeft(game);
      await writeGameSave({
        ...prev,
        game,
        lastSavedAt: new Date().toISOString(),
      });
      this.scene.start("Guardian");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }
}
