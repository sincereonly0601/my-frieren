import Phaser from "phaser";

import whimQuestions from "../data/whim_questions.json";
import { TRAINING_ACTION_BY_KEY } from "../game/trainingActions";
import { formatTrainingFeedbackModalMessage } from "../game/trainingFeedbackCopy";
import { buildTrainingFeedbackImageUrlCandidates } from "../game/trainingFxUrls";
import {
  mountPlayHud,
  mountPlaceholderHudError,
  mountSaveSlotSelectHud,
  showSaveToSlotToast,
} from "../hud/domHud";
import { mountTrainingFeedbackHud } from "../hud/trainingFeedbackHud";
import { syncWebBgmPlayPhase } from "../audio/webBgm";
import {
  mountEncounterHud,
  mountEndingPreludeAndPagesHud,
  mountIncidentHud,
  mountMajorEventHud,
  mountWhimEventHud,
} from "../hud/quarterEventHud";
import { resolveOnboardingEntryScene } from "../onboarding/resolveOnboardingEntryScene";
import {
  ageMonthsFromTimeLeft,
  defaultGameStateStored,
  emptyGameSaveV3,
  listSaveSlotSummaries,
  loadGameSave,
  setActiveSaveSlot,
  syncPhaseFromTimeLeft,
  TOTAL_TRAINING_QUARTERS,
  writeGameSaveToSlot,
  type GameSaveV3,
  type GameStateStored,
} from "../save/idbSave";
import {
  addGalleryEndingUnlock,
  addGalleryEnemyUnlock,
  addGalleryWhimUnlock,
} from "../save/galleryUnlock";
import { ENDINGS_BY_KEY, ENDINGS_LIST, WHIM_BY_KEY } from "../sim/gameData";
import {
  applyEncounterOutcome,
  applyIncidentOption,
  applyMajorOption,
  applyQuarterTrainingDeltasOnly,
  applyWhimOutcome,
  cloneGameState,
  scanIdleFollowUp,
  spendQuarterAndResolveFirstInterrupt,
  type QuarterInterrupt,
} from "../sim/finalizeTrainingQuarter";
import { SimRng } from "../sim/rng";
import { seedWhimScheduleForNewPlaythrough } from "../sim/whimSchedule";
import type { WhimQuestionJson } from "../sim/types";

/**
 * 培養主畫面：八種指令與桌面版相同之每季結算（重大／遭遇／突發／奇遇／結局）。
 */
export class PlaceholderScene extends Phaser.Scene {
  private readonly _rng = new SimRng();
  private _resetVisits = false;
  private _resetGame = false;
  /** 為 false 時進場不累加 `placeholderVisits` */
  private _countVisit = true;
  /**
   * 本場景內養成進度（僅在玩家於「儲存」選單點選欄位時寫入 IndexedDB；不自動存檔）。
   */
  private _workingSave: GameSaveV3 | null = null;

  public constructor() {
    super({ key: "Placeholder" });
  }

  /** @inheritdoc */
  public init(data: object): void {
    const d = data as
      | {
          resetVisits?: boolean;
          resetGame?: boolean;
          countVisit?: boolean;
        }
      | undefined;
    this._resetVisits = d?.resetVisits === true;
    this._resetGame = d?.resetGame === true;
    this._countVisit = d?.countVisit !== false;
  }

  /** @inheritdoc */
  public create(): void {
    // 培養主畫面與其事件改回使用預設 BG 背景
    this.setTrainingBackground(false);
    void this.persistVisitAndMountHud();
  }

  /**
   * 深拷貝 `game` 欄位供可變更陣列（與桌面進入養成時奇遇排程一致）。
   *
   * @param g - 來源狀態
   */
  private cloneStoredGame(g: GameStateStored): GameStateStored {
    return cloneGameState(g);
  }

  /**
   * 進場累加 visit、套用重置、奇遇排程，再繪製培養 HUD。
   */
  private async persistVisitAndMountHud(): Promise<void> {
    try {
      let prev = await loadGameSave();
      if (prev == null) {
        prev = emptyGameSaveV3();
      }
      if (!prev.game.onboarding_complete) {
        this.setTrainingBackground(false);
        this.scene.start(resolveOnboardingEntryScene(prev));
        return;
      }
      let game: GameStateStored = this._resetGame
        ? defaultGameStateStored()
        : this.cloneStoredGame(prev.game);
      let adopterQuizAnswers = prev.adopterQuizAnswers;
      if (this._resetGame) {
        adopterQuizAnswers = null;
      }
      syncPhaseFromTimeLeft(game);
      if (game.time_left === TOTAL_TRAINING_QUARTERS && game.whim_slots.length === 0) {
        seedWhimScheduleForNewPlaythrough(game, this._rng);
      }
      let visits = prev.placeholderVisits;
      if (this._resetVisits) {
        visits = 0;
      }
      const next: GameSaveV3 = {
        schemaVersion: 3,
        placeholderVisits: visits + (this._countVisit ? 1 : 0),
        lastSavedAt: new Date().toISOString(),
        adopterQuizAnswers,
        game,
      };
      this._workingSave = next;
      this.wirePlayHud(next);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 切換培養主畫面／季結算事件（奇遇／重大事件／遭遇戰／突發事件／結局）背景圖。
   *
   * @param useAltBackground - 為 `true` 時套用 `bg2`，否則還原為 `bg`
   */
  private setTrainingBackground(useAltBackground: boolean): void {
    try {
      const docEl = document.documentElement;
      const file = useAltBackground ? "ui/bg2.png" : "ui/bg.png";
      const href = new URL(file, document.baseURI).href;
      docEl.style.setProperty("--game-stage-fit-bg-image", `url("${href}")`);
    } catch {
      // 環境若不支援 DOM 或 URL，略過背景切換
    }
  }

  /**
   * 掛上培養介面與事件。
   *
   * @param save - 目前記憶體中的存檔快照（未必已寫回 IndexedDB）
   */
  private wirePlayHud(save: GameSaveV3): void {
    mountPlayHud(save, {
      onMenu: () => {
        this.scene.start("Menu");
      },
      onSaveGame: () => {
        void this.openSaveSlotPickerForSave();
      },
      onPickTraining: (keyNum) => {
        void this.applyTrainingAndRemount(keyNum);
      },
    });
  }

  /**
   * 培養中「儲存」：四欄選單（對齊桌面 `draw_save_slot_screen`／`save_to_slot`）。
   */
  private async openSaveSlotPickerForSave(): Promise<void> {
    try {
      const prev = this._workingSave;
      if (prev == null) {
        return;
      }
      const summaries = await listSaveSlotSummaries();
      mountSaveSlotSelectHud(
        summaries,
        (slotIndex) => {
          void this.saveToChosenSlot(slotIndex);
        },
        "save",
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 寫入指定欄並設為使用中欄位（與桌面 `current_save_slot` 一致）。
   *
   * @param slotIndex - 1～4
   */
  private async saveToChosenSlot(slotIndex: number): Promise<void> {
    try {
      const prev = this._workingSave;
      if (prev == null) {
        return;
      }
      const next: GameSaveV3 = {
        ...prev,
        lastSavedAt: new Date().toISOString(),
      };
      await writeGameSaveToSlot(slotIndex, next);
      await setActiveSaveSlot(slotIndex);
      this._workingSave = next;
      this.wirePlayHud(next);
      showSaveToSlotToast(slotIndex);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 執行一季培養（與桌面結算順序一致）並處理攔截事件鏈。
   *
   * @param keyNum - 1～8
   */
  private async applyTrainingAndRemount(keyNum: number): Promise<void> {
    const action = TRAINING_ACTION_BY_KEY[keyNum];
    if (action == null) {
      return;
    }
    try {
      const prev = this._workingSave;
      if (prev == null || prev.game.time_left <= 0) {
        return;
      }
      const game = this.cloneStoredGame(prev.game);
      const preYears = Math.floor(ageMonthsFromTimeLeft(game.time_left) / 12);
      applyQuarterTrainingDeltasOnly(game, keyNum);
      const pendingSave: GameSaveV3 = { ...prev, game };
      const gender = game.protagonist_gender === "male" ? "male" : "female";
      const messageZh = formatTrainingFeedbackModalMessage(action, gender);
      const imageUrlCandidates = await buildTrainingFeedbackImageUrlCandidates(
        keyNum,
        gender,
      );
      syncWebBgmPlayPhase(pendingSave.game.phase);
      mountTrainingFeedbackHud({
        messageZh,
        imageUrlCandidates,
        actionKey: keyNum,
        onDismiss: () => {
          void this.finalizeTrainingQuarterAfterFeedback(pendingSave, preYears);
        },
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 培養回饋關閉（點畫面或 Enter／Esc）後：扣一季並更新記憶體存檔，再進入事件鏈（不寫 IndexedDB，與桌面自動存檔差異：僅手動儲存欄位時寫入）。
   *
   * @param pendingSave - 已含本季五維增量、尚未扣季之存檔
   * @param preYears - 執行培養前之滿歲
   */
  private async finalizeTrainingQuarterAfterFeedback(
    pendingSave: GameSaveV3,
    preYears: number,
  ): Promise<void> {
    try {
      const interrupt = spendQuarterAndResolveFirstInterrupt(
        pendingSave.game,
        preYears,
        this._rng,
      );
      const next: GameSaveV3 = {
        ...pendingSave,
        lastSavedAt: new Date().toISOString(),
      };
      this._workingSave = next;
      this.presentInterruptChain(next, interrupt);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 依序顯示重大／遭遇／突發／奇遇／結局，並在每一步後檢查後續奇遇或結局。
   *
   * @param save - 目前存檔（`game` 將被就地修改）
   * @param interrupt - 當步要顯示者；null 則回培養 HUD
   */
  private presentInterruptChain(save: GameSaveV3, interrupt: QuarterInterrupt | null): void {
    if (interrupt == null) {
      // 回到培養主畫面時，背景改回預設 BG
      this.setTrainingBackground(false);
      this.wirePlayHud(save);
      return;
    }

    const persistAndContinue = async (fol: QuarterInterrupt | null): Promise<void> => {
      const next: GameSaveV3 = {
        ...save,
        lastSavedAt: new Date().toISOString(),
      };
      this._workingSave = next;
      this.presentInterruptChain(next, fol);
    };

    const g = save.game;

    switch (interrupt.kind) {
      case "major":
        // 培養中被重大事件打斷：改用 BG2 背景
        this.setTrainingBackground(true);
        mountMajorEventHud(g, interrupt.ageYear, (opt) => {
          void (async () => {
            applyMajorOption(g, interrupt.ageYear, opt);
            const fol = scanIdleFollowUp(g, this._rng);
            await persistAndContinue(fol);
          })();
        });
        break;

      case "encounter":
        // 遭遇戰事件：使用 BG2 背景
        this.setTrainingBackground(true);
        mountEncounterHud(g, interrupt.enemy, interrupt.outcome, interrupt.ageYear, () => {
          void (async () => {
            if (interrupt.outcome.win) {
              await addGalleryEnemyUnlock(interrupt.enemy.id);
            }
            applyEncounterOutcome(g, interrupt.ageYear, interrupt.outcome);
            const fol = scanIdleFollowUp(g, this._rng);
            await persistAndContinue(fol);
          })();
        });
        break;

      case "incident":
        // 突發事件：使用 BG2 背景
        this.setTrainingBackground(true);
        mountIncidentHud(interrupt.incident, g.protagonist_gender, g.phase, (opt) => {
          void (async () => {
            applyIncidentOption(g, interrupt.ageYear, interrupt.incident, opt);
            const fol = scanIdleFollowUp(g, this._rng);
            await persistAndContinue(fol);
          })();
        });
        break;

      case "whim": {
        const slot = interrupt.slotIndex;
        const qi = g.whim_question_indices[slot] ?? 0;
        const rawQ = whimQuestions[qi % whimQuestions.length] as WhimQuestionJson;
        const q: WhimQuestionJson = {
          stem: rawQ.stem,
          options: rawQ.options as [string, string, string],
          correct_index: rawQ.correct_index,
        };
        const nk = g.whim_npc_keys[slot] ?? "";
        const enc = WHIM_BY_KEY.get(nk);
        if (enc == null) {
          void (async () => {
            const fol = scanIdleFollowUp(g, this._rng);
            await persistAndContinue(fol);
          })();
          return;
        }
        const permList = [0, 1, 2];
        this._rng.shuffle(permList);
        const optionPerm = permList as [number, number, number];
        const correctSlot = optionPerm.indexOf(q.correct_index);
        // 奇遇事件：使用 BG2 背景
        this.setTrainingBackground(true);
        mountWhimEventHud(enc, q, optionPerm, correctSlot, g.protagonist_gender, g.phase, (ok) => {
          void (async () => {
            if (ok) {
              await addGalleryWhimUnlock(enc.cg_basename);
            }
            const deltas = ok ? enc.deltas_correct : enc.deltas_wrong;
            applyWhimOutcome(g, slot, deltas);
            const fol = scanIdleFollowUp(g, this._rng);
            await persistAndContinue(fol);
          })();
        });
        break;
      }

      case "ending": {
        const ending =
          ENDINGS_BY_KEY.get(interrupt.endingKey) ?? ENDINGS_LIST[0]!;
        // 結局事件：使用 BG2 背景
        this.setTrainingBackground(true);
        mountEndingPreludeAndPagesHud(g, ending, () => {
          void (async () => {
            await addGalleryEndingUnlock(ending.key);
            this.setTrainingBackground(false);
            this.scene.start("Title");
          })();
        });
        break;
      }

      default:
        this.wirePlayHud(save);
    }
  }
}
