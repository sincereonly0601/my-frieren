import Phaser from "phaser";

import { resolveOnboardingEntryScene } from "../onboarding/resolveOnboardingEntryScene";
import { mountGalleryFlow } from "../hud/galleryDomHud";
import {
  mountMenuHud,
  mountMenuHudError,
  mountSaveSlotSelectHud,
  mountSettingsHud,
} from "../hud/domHud";
import { showHudMessageToast } from "../hud/hudToast";
import {
  getLatestResumableSlot,
  isVacantSaveSlot,
  listSaveSlotSummaries,
  loadGameSaveFromSlot,
  pickSlotForNewGameStart,
  setActiveSaveSlot,
} from "../save/idbSave";

/**
 * 主選單：選項對齊桌面；存檔為四欄（IndexedDB）。
 */
export class MenuScene extends Phaser.Scene {
  public constructor() {
    super({ key: "Menu" });
  }

  /** @inheritdoc */
  public create(): void {
    void this.mountMenuFromSave();
  }

  /**
   * 載入存檔後繪製主選單。
   */
  private async mountMenuFromSave(): Promise<void> {
    try {
      mountMenuHud({
        onNewGame: () => {
          void this.startNewGame();
        },
        onLoadLatest: () => {
          void this.loadLatestProgress();
        },
        onOpenSlotLoad: () => {
          void this.openSaveSlotPicker();
        },
        onGallery: () => {
          mountGalleryFlow(() => {
            void this.mountMenuFromSave();
          });
        },
        onSettings: () => {
          mountSettingsHud(
            () => {
              void this.mountMenuFromSave();
            },
            () => {
              this.scene.start("FrierenQuiz");
            },
          );
        },
        onQuit: () => {
          window.close();
          window.setTimeout(() => {
            alert("瀏覽器可能阻擋關閉視窗；請手動關閉本分頁。");
          }, 200);
        },
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountMenuHudError(msg);
    }
  }

  /**
   * 新遊戲：優先空欄，設為使用中欄位後開場重置。
   */
  private async startNewGame(): Promise<void> {
    const slot = await pickSlotForNewGameStart();
    await setActiveSaveSlot(slot);
    this.scene.start("Intro", { resetProgress: true });
  }

  /**
   * 讀取最近儲存時間之可續關欄位；無則提示。
   */
  private async loadLatestProgress(): Promise<void> {
    const latest = await getLatestResumableSlot();
    if (latest == null) {
      showHudMessageToast("尚無可接關的存檔", 2600);
      return;
    }
    await this.loadFromSlot(latest.slot);
  }

  /**
   * 讀取進度：四欄選單。
   */
  private async openSaveSlotPicker(): Promise<void> {
    const summaries = await listSaveSlotSummaries();
    mountSaveSlotSelectHud(
      summaries,
      (slotIndex) => {
        void this.loadFromSlot(slotIndex);
      },
      "load",
      () => {
        void this.mountMenuFromSave();
      },
    );
  }

  /**
   * @param slotIndex - 1～4
   */
  private async loadFromSlot(slotIndex: number): Promise<void> {
    const save = await loadGameSaveFromSlot(slotIndex);
    if (save == null || isVacantSaveSlot(save)) {
      return;
    }
    await setActiveSaveSlot(slotIndex);
    this.scene.start(resolveOnboardingEntryScene(save));
  }
}
