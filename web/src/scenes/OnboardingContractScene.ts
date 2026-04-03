import Phaser from "phaser";

import { mountPlaceholderHudError } from "../hud/domHud";
import { mountOnboardingContractHud } from "../hud/onboardingHud";
import {
  loadGameSave,
  syncPhaseFromTimeLeft,
  writeGameSave,
} from "../save/idbSave";

/**
 * 監護契約占位（對應桌面 `Screen.CONTRACT_SEAL`）。
 */
export class OnboardingContractScene extends Phaser.Scene {
  public constructor() {
    super({ key: "OnboardingContract" });
  }

  /** @inheritdoc */
  public create(): void {
    void this.boot();
  }

  /**
   * 顯示簽署按鈕；確認後 `onboardingComplete` 並進 hub。
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
      if (save.game.heroine_name.trim() === "") {
        this.scene.start("Guardian");
        return;
      }
      await mountOnboardingContractHud(save.game.heroine_name, () => {
        void this.sealAndGoHub();
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 寫入 `onboardingComplete` 並進入養成 hub。
   */
  private async sealAndGoHub(): Promise<void> {
    try {
      const prev = await loadGameSave();
      if (prev == null) {
        return;
      }
      const game = { ...prev.game, onboarding_complete: true };
      syncPhaseFromTimeLeft(game);
      await writeGameSave({
        ...prev,
        game,
        lastSavedAt: new Date().toISOString(),
      });
      this.scene.start("TrainingPreamble");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }
}
