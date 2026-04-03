import Phaser from "phaser";

import {
  ADOPTER_QUESTIONNAIRE,
  ADOPTER_QUESTIONNAIRE_COUNT,
  applyAdopterDeltasToGameState,
  flattenAdopterPromptZh,
  formatAdopterMergedDeltasZh,
  mergeAdopterQuestionnaire,
  questionnaireJudgmentZh,
} from "../game/adopterQuestionnaire";
import { mountPlaceholderHudError } from "../hud/domHud";
import {
  mountAdopterQuizIntroHud,
  mountAdopterQuizQuestionHud,
  mountAdopterQuizResultHud,
} from "../hud/onboardingHud";
import {
  loadGameSave,
  syncPhaseFromTimeLeft,
  writeGameSave,
} from "../save/idbSave";

/**
 * 聖堂問卷五題＋判讀（對照桌面 `Screen.ADOPTER_QUESTIONNAIRE`）。
 */
export class OnboardingQuizScene extends Phaser.Scene {
  /** 尚未寫入存檔之本輪作答緩衝 */
  private _answers: number[] = [0, 0, 0, 0, 0];

  private _qIndex = 0;

  public constructor() {
    super({ key: "OnboardingQuiz" });
  }

  /** @inheritdoc */
  public create(): void {
    this.setAdopterQuizBackground(true);
    void this.boot();
  }

  /**
   * 載入存檔；若已有五題答案則僅顯示判讀（不重複套用增量）。
   */
  private async boot(): Promise<void> {
    try {
      const save = await loadGameSave();
      if (save == null) {
        this.setAdopterQuizBackground(false);
        this.scene.start("Menu");
        return;
      }
      if (save.game.heroine_name.trim() === "") {
        this.setAdopterQuizBackground(false);
        this.scene.start("Guardian");
        return;
      }
      if (save.game.onboarding_complete) {
        this.setAdopterQuizBackground(false);
        this.scene.start("Placeholder", {
          resetVisits: false,
          resetGame: false,
          countVisit: false,
        });
        return;
      }
      const done = save.adopterQuizAnswers;
      if (done !== null) {
        this.showResultFromSave(done);
        return;
      }
      this._qIndex = 0;
      this._answers = [0, 0, 0, 0, 0];
      mountAdopterQuizIntroHud(() => {
        this.mountQuestion();
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 繪製當前題（第 {@link OnboardingQuizScene._qIndex} 題）。
   */
  private mountQuestion(): void {
    const q = ADOPTER_QUESTIONNAIRE[this._qIndex];
    if (!q) {
      return;
    }
    const labels = q.options.map((o) => o.labelZh) as [string, string, string];
    mountAdopterQuizQuestionHud({
      questionIndex: this._qIndex,
      promptPlain: flattenAdopterPromptZh(q.promptZh),
      optionLabels: labels,
      onPickOption: (optionIndex) => {
        void this.onAnswer(optionIndex);
      },
    });
  }

  /**
   * 記錄選項；最末題後合併增量、寫檔並顯示判讀。
   *
   * @param optionIndex - 0～2
   */
  private async onAnswer(optionIndex: number): Promise<void> {
    try {
      this._answers[this._qIndex] = optionIndex;
      if (this._qIndex < ADOPTER_QUESTIONNAIRE_COUNT - 1) {
        this._qIndex += 1;
        this.mountQuestion();
        return;
      }
      const tuple = this._answers as [number, number, number, number, number];
      const merged = mergeAdopterQuestionnaire(tuple);
      const judgmentZh = questionnaireJudgmentZh(tuple, merged);
      const prev = await loadGameSave();
      if (prev == null) {
        return;
      }
      const game = { ...prev.game };
      applyAdopterDeltasToGameState(game, merged);
      syncPhaseFromTimeLeft(game);
      await writeGameSave({
        ...prev,
        game,
        adopterQuizAnswers: tuple,
        lastSavedAt: new Date().toISOString(),
      });
      this.mountResultHud(judgmentZh, merged);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      mountPlaceholderHudError(msg);
    }
  }

  /**
   * 由存檔答案顯示判讀（不重複加數值）。
   *
   * @param answers - 已儲存之五題索引
   */
  private showResultFromSave(
    answers: [number, number, number, number, number],
  ): void {
    const merged = mergeAdopterQuestionnaire(answers);
    const judgmentZh = questionnaireJudgmentZh(answers, merged);
    this.mountResultHud(judgmentZh, merged);
  }

  /**
   * @param merged - 供底部「數值變化」列顯示
   */
  private mountResultHud(
    judgmentZh: string,
    merged: Record<string, number>,
  ): void {
    const body = formatAdopterMergedDeltasZh(merged);
    const statLineZh =
      body === "（無數值變化）" ? body : `數值變化：${body}`;
    mountAdopterQuizResultHud({
      judgmentZh,
      statLineZh,
      onContinue: () => {
        this.setAdopterQuizBackground(false);
        this.scene.start("OnboardingContract");
      },
    });
  }

  /**
   * 切換聖堂監護人問卷場景專用背景圖（`bg2`）與預設全遊戲背景（`bg`）。
   *
   * @param useAltBackground - 為 `true` 時套用 `bg2`，否則還原為 `bg`
   */
  private setAdopterQuizBackground(useAltBackground: boolean): void {
    try {
      const docEl = document.documentElement;
      const file = useAltBackground ? "ui/bg2.png" : "ui/bg.png";
      const href = new URL(file, document.baseURI).href;
      docEl.style.setProperty("--game-stage-fit-bg-image", `url("${href}")`);
    } catch {
      // 環境若不支援 DOM 或 URL，略過背景切換
    }
  }
}
