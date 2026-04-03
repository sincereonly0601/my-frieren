import Phaser from "phaser";

import { syncWebBgmOpening } from "../audio/webBgm";
import {
  computeFrierenQuizScore,
  frierenQuizResultTier,
  type FrierenQuizAnswer,
  type WhimQuestionLike,
} from "../game/frierenQuizData";
import {
  mountFrierenQuizFeedbackHud,
  mountFrierenQuizIntroHud,
  mountFrierenQuizQuestionHud,
  mountFrierenQuizResultHud,
} from "../hud/frierenQuizHud";

import questionsJson from "../../../whim_questions.json";

type FrierenQuizPhase = "intro" | "question" | "feedback" | "results";

const MAX_QUESTIONS_PER_RUN = 10;

/**
 * 芙莉蓮測驗（Web 版）：沿用桌機版 110 題題庫與評級邏輯。
 * 流程：導覽頁 → （題目頁 → 解答頁）×10 → 評價頁。
 */
export class FrierenQuizScene extends Phaser.Scene {
  private _phase: FrierenQuizPhase = "intro";
  private _questions: WhimQuestionLike[] = [];
  private _perm: [number, number, number][] = [];
  private _answers: FrierenQuizAnswer[] = [];
  private _qIndex = 0;

  public constructor() {
    super({ key: "FrierenQuiz" });
  }

  /** @inheritdoc */
  public create(): void {
    syncWebBgmOpening();
    this.setFrierenBackground(true);
    this._phase = "intro";
    this._qIndex = 0;
    this._answers = [];
    this._questions = this.pickRandomQuestions();
    this._perm = this._questions.map(() => this.randomPermutation());
    this.mountIntro();
  }

  private mountIntro(): void {
    mountFrierenQuizIntroHud({
      onStart: () => {
        this._phase = "question";
        this._qIndex = 0;
        this._answers = [];
        this.mountQuestion();
      },
      onBack: () => {
        this.setFrierenBackground(false);
        this.scene.start("Menu");
      },
    });
  }

  private mountQuestion(): void {
    const q = this._questions[this._qIndex];
    if (!q) {
      this.showResults();
      return;
    }
    const perm = this._perm[this._qIndex];
    const labels = perm.map((i) => q.options[i]);
    mountFrierenQuizQuestionHud({
      questionIndex: this._qIndex,
      questionCount: this._questions.length,
      promptPlain: q.stem,
      optionLabels: labels,
      onPickOption: (slotIndex) => {
        this.handleAnswer(slotIndex);
      },
    });
  }

  private handleAnswer(slotIndex: number): void {
    const q = this._questions[this._qIndex];
    const perm = this._perm[this._qIndex];
    if (!q || !perm) {
      return;
    }
    const chosenSlot = Math.max(0, Math.min(2, slotIndex));
    const correctSlot = perm.indexOf(q.correct_index);
    const correct = chosenSlot === correctSlot;
    const record: FrierenQuizAnswer = {
      question: q,
      perm,
      chosenSlot,
      correct,
    };
    this._answers = [...this._answers, record];
    this._phase = "feedback";
    this.mountFeedback(record);
  }

  private mountFeedback(ans: FrierenQuizAnswer): void {
    const q = ans.question;
    const perm = ans.perm;
    const labels = perm.map((i) => q.options[i]);
    const rawExpl =
      (q.explanation_zh ?? "").trim().length > 0
        ? (q.explanation_zh ?? "").trim()
        : this.defaultExplanationZh(q);
    const [head, tail] = this.splitExplanationHeadTail(q, rawExpl);
    mountFrierenQuizFeedbackHud({
      questionIndex: this._qIndex,
      questionCount: this._questions.length,
      promptPlain: q.stem,
      optionLabels: labels,
      correctSlot: perm.indexOf(q.correct_index),
      chosenSlot: ans.chosenSlot,
      explanationHead: head,
      explanationTail: tail,
      isLastQuestion: this._qIndex >= this._questions.length - 1,
      onNext: () => {
        if (this._qIndex < this._questions.length - 1) {
          this._qIndex += 1;
          this._phase = "question";
          this.mountQuestion();
        } else {
          this._phase = "results";
          this.showResults();
        }
      },
      onExit: () => {
        this.scene.start("Menu");
      },
    });
  }

  private showResults(): void {
    const score = computeFrierenQuizScore(this._answers);
    const [tierName, tierBody] = frierenQuizResultTier(score);
    const total = this._questions.length * 10;
    const titleZh = "芙莉蓮測驗　結算";
    const scoreLineZh = `總分：${score}／${total}`;
    const tierLineZh = `評級：${tierName}`;
    const bodyZh = score < total ? this.appendRetryHint(tierBody) : tierBody;
    mountFrierenQuizResultHud({
      titleZh,
      scoreLineZh,
      tierLineZh,
      bodyZh,
      onBackToSettings: () => {
        this.setFrierenBackground(false);
        this.scene.start("Menu");
      },
    });
  }

  private pickRandomQuestions(): WhimQuestionLike[] {
    const raw = questionsJson as unknown as Array<{
      stem: string;
      options: [string, string, string];
      correct_index: number;
      explanation_zh?: string;
    }>;
    const all: WhimQuestionLike[] = raw.map((q, i) => ({
      qid: `q${i + 1}`.padStart(3, "0"),
      stem: q.stem,
      options: q.options,
      correct_index: q.correct_index,
      explanation_zh: q.explanation_zh ?? "",
    }));
    const pool = [...all];
    const picked: WhimQuestionLike[] = [];
    const target = Math.min(MAX_QUESTIONS_PER_RUN, pool.length);
    for (let i = 0; i < target; i += 1) {
      const j = Math.floor(Math.random() * pool.length);
      const [item] = pool.splice(j, 1);
      if (!item) {
        break;
      }
      picked.push(item);
    }
    return picked;
  }

  private randomPermutation(): [number, number, number] {
    const arr: number[] = [0, 1, 2];
    for (let i = arr.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return [arr[0], arr[1], arr[2]];
  }

  private defaultExplanationZh(q: WhimQuestionLike): string {
    const ok = q.options[q.correct_index];
    const wrong = [0, 1, 2].filter((i) => i !== q.correct_index);
    const w0 = q.options[wrong[0]];
    const w1 = q.options[wrong[1]];
    return `正確答案為「${ok}」。與「${w0}」「${w1}」相比，正確項在人物、地點、魔法規則、物品或時間軸上的定位不同；釐清選項之間的因果與名詞對應，比記憶單一畫面更能鞏固設定知識。`;
  }

  private splitExplanationHeadTail(
    question: WhimQuestionLike,
    explSource: string,
  ): [string, string] {
    const ok = question.options[question.correct_index];
    const prefix = `正確答案為「${ok}」。`;
    let t = explSource.trim();
    if (t.startsWith("詳解：") || t.startsWith("詳解:")) {
      t = t.replace(/^詳解[:：]\s*/, "");
    }
    if (t.startsWith(prefix)) {
      return [prefix, t.slice(prefix.length).trim()];
    }
    return [prefix, t];
  }

  private appendRetryHint(body: string): string {
    const trimmed = body.trim();
    if (!trimmed) {
      return "可於遊戲設定再次挑戰。";
    }
    if (trimmed.endsWith("。")) {
      return `${trimmed.slice(0, -1)}，可於遊戲設定再次挑戰。`;
    }
    return `${trimmed}，可於遊戲設定再次挑戰。`;
  }

  private tierSealPhrase(score: number): string {
    const perQuestion = 10;
    const maxQuestions = 10;
    const total = perQuestion * maxQuestions;
    const s = Math.max(0, Math.min(total, score));
    const idx = Math.min(10, Math.floor(s / 10));
    const phrases: string[] = [
      "亟待加強",
      "萌芽初學",
      "摸索累積",
      "漸有起色",
      "根基尚可",
      "表現平穩",
      "已達門檻",
      "表現良好",
      "相當優秀",
      "僅差一線",
      "認證合格",
    ];
    return phrases[idx] ?? "認證合格";
  }

  /**
   * 切換芙莉蓮測驗專用背景圖（`bg2`）與預設全遊戲背景（`bg`）。
   *
   * @param useAltBackground - 為 `true` 時套用 `bg2`，否則還原為 `bg`
   */
  private setFrierenBackground(useAltBackground: boolean): void {
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

