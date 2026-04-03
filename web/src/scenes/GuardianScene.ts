import Phaser from "phaser";

import { mountPlaceholderHudError } from "../hud/domHud";
import {
  GUARDIAN_HEROINE_NAME_MAX_LEN,
  mountGuardianHud,
} from "../hud/onboardingHud";
import {
  loadGameSave,
  syncPhaseFromTimeLeft,
  writeGameSave,
} from "../save/idbSave";

/**
 * 監護人說明、性別、取名（對應桌面 `Screen.GUARDIAN_INTRO`）。
 */
export class GuardianScene extends Phaser.Scene {
  private _gender: "male" | "female" | null = null;
  /** 切換性別重繪時保留尚未寫入存檔的輸入內容 */
  private _nameDraft = "";

  public constructor() {
    super({ key: "Guardian" });
  }

  /** @inheritdoc */
  public create(): void {
    void this.boot();
  }

  /**
   * 載入存檔並繪製；若已完成前置或已有姓名則轉場。
   */
  private async boot(): Promise<void> {
    try {
      const save = await loadGameSave();
      if (save == null) {
        this.scene.start("Menu");
        return;
      }
      if (save.game.onboarding_complete) {
        this.scene.start("Placeholder", {
          resetVisits: false,
          resetGame: false,
          countVisit: false,
        });
        return;
      }
      if (!save.game.intro_done) {
        this.scene.start("Intro", { resetProgress: false });
        return;
      }
      if (save.game.heroine_name.trim() !== "") {
        this.scene.start("OnboardingQuiz");
        return;
      }
      this._gender = null;
      this._nameDraft = save.game.heroine_name.slice(
        0,
        GUARDIAN_HEROINE_NAME_MAX_LEN,
      );
      await this.remount();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 依 `this._gender`／`this._nameDraft` 繪製表單。
   */
  private async remount(): Promise<void> {
    mountGuardianHud({
      gender: this._gender,
      nameDraft: this._nameDraft,
      onGenderChange: (g) => {
        this._gender = g;
      },
      onConfirmAll: () => {
        void this.persistGuardian();
      },
    });
  }

  /**
   * 寫入性別、姓名與 `guardianIntroDone`，進入聖堂問卷。
   */
  private async persistGuardian(): Promise<void> {
    try {
      const prev = await loadGameSave();
      if (prev == null) {
        return;
      }
      const input = document.getElementById(
        "guardian-name-input",
      ) as HTMLInputElement | null;
      const raw = input?.value?.trim() ?? "";
      if (!raw) {
        return;
      }
      if (this._gender === null) {
        return;
      }
      const name = raw.slice(0, GUARDIAN_HEROINE_NAME_MAX_LEN);
      const game = {
        ...prev.game,
        heroine_name: name,
        guardian_intro_done: true,
        protagonist_gender: this._gender,
      };
      syncPhaseFromTimeLeft(game);
      await writeGameSave({
        ...prev,
        game,
        lastSavedAt: new Date().toISOString(),
      });
      this.scene.start("OnboardingQuiz");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }
}
