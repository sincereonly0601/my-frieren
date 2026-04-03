import Phaser from "phaser";

import { syncWebBgmPlayPhase, syncWebBgmPrologue } from "../audio/webBgm";
import { mountTrainingPreambleHud } from "../hud/onboardingHud";
import { loadGameSave } from "../save/idbSave";

/**
 * 契約結束後、首次進入培養前之全畫面前導（文案見 {@link mountTrainingPreambleHud}）。
 */
export class TrainingPreambleScene extends Phaser.Scene {
  public constructor() {
    super({ key: "TrainingPreamble" });
  }

  /** @inheritdoc */
  public create(): void {
    void (async () => {
      try {
        const save = await loadGameSave();
        if (save != null) {
          syncWebBgmPlayPhase(save.game.phase);
        } else {
          syncWebBgmPrologue();
        }
      } catch {
        syncWebBgmPrologue();
      }
      mountTrainingPreambleHud(() => {
        this.scene.start("Placeholder", {
          resetVisits: false,
          resetGame: false,
          countVisit: true,
        });
      });
    })();
  }
}
