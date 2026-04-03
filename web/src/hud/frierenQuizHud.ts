import { escapeHtml } from "./domHud";

const HUD_ID = "hud";

function hudEl(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

export type FrierenQuizIntroHudHandlers = {
  /** 按下「開始測驗」 */
  onStart: () => void;
  /** 按下「返回遊戲設定」 */
  onBack: () => void;
};

/**
 * 芙莉蓮測驗導覽／說明頁。
 */
export function mountFrierenQuizIntroHud(
  h: FrierenQuizIntroHudHandlers,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  const body =
    "將從題庫隨機抽出 10 題，每題 10 分，滿分 100 分。作答後會顯示正解與詳解，隨時可選擇中途離開，下次再從新的組合重新挑戰。";
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz">
      <div class="hud-page-head hud-page-head--frieren-quiz">
        <p class="hud-line hud-title hud-title--proto">芙莉蓮測驗</p>
      </div>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt">${escapeHtml(
        body,
      )}</p>
      <div class="hud-actions hud-actions--single hud-actions--adopter-result">
        <button type="button" class="hud-btn hud-btn--proto hud-btn--adopter-continue" data-act="start">開始測驗</button>
      </div>
      <footer class="hud-gallery-hub__footer">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="back-settings">上一頁</button>
      </footer>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>('[data-act="start"]')?.addEventListener(
    "click",
    () => {
      h.onStart();
    },
  );
  el
    .querySelector<HTMLButtonElement>('[data-act="back-settings"]')
    ?.addEventListener("click", () => {
      h.onBack();
    });
}

export type FrierenQuizQuestionHudHandlers = {
  /** 第幾題（0 起算） */
  questionIndex: number;
  /** 題目總數 */
  questionCount: number;
  /** 題幹文字（已整理空白） */
  promptPlain: string;
  /** 選項全文 */
  optionLabels: readonly string[];
  /** 點選選項即記錄答案並前進 */
  onPickOption: (optionIndex: number) => void;
};

/**
 * 顯示芙莉蓮測驗單題。
 *
 * @param h - 題目與選項及回呼
 */
export function mountFrierenQuizQuestionHud(
  h: FrierenQuizQuestionHudHandlers,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  const n = h.questionIndex + 1;
  const total = h.questionCount;
  const promptHtml = `${escapeHtml(h.promptPlain)}<span class="hud-adopter-quiz-inline-progress" aria-label="第 ${n} 題，共 ${total} 題">（${n}/${total}）</span>`;
  const buttons = h.optionLabels
    .map((label, idx) => {
      const t = escapeHtml(label);
      return `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-oi="${idx}">${t}</button>`;
    })
    .join("");
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz">
      <div class="hud-page-head hud-page-head--frieren-quiz">
        <p class="hud-line hud-title hud-title--proto">芙莉蓮測驗</p>
      </div>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt">${promptHtml}</p>
      <div class="hud-adopter-quiz-options" role="group" aria-label="選項">
        ${buttons}
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelectorAll<HTMLButtonElement>("[data-oi]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = parseInt(btn.dataset.oi ?? "0", 10);
      if (Number.isNaN(i)) {
        return;
      }
      if (i < 0 || i >= h.optionLabels.length) {
        return;
      }
      h.onPickOption(i);
    });
  });
}

export type FrierenQuizFeedbackHudHandlers = {
  /** 第幾題（0 起算） */
  questionIndex: number;
  /** 題目總數 */
  questionCount: number;
  /** 題幹文字（已整理空白） */
  promptPlain: string;
  /** 三個選項全文（顯示順序與作答當下相同） */
  optionLabels: readonly string[];
  /** 正確選項所在槽位 0～2 */
  correctSlot: number;
  /** 玩家實際選擇的槽位 0～2 */
  chosenSlot: number;
  /** 詳解主句（「正確答案為「…」。」） */
  explanationHead: string;
  /** 詳解其餘補充文字，可為空 */
  explanationTail: string;
  /** 是否為本輪最後一題 */
  isLastQuestion: boolean;
  /** 按下「下一題／查看成績」 */
  onNext: () => void;
  /** 按下「離開測驗」 */
  onExit: () => void;
};

/**
 * 顯示芙莉蓮測驗單題作答後之詳解頁。
 *
 * @param h - 題目、選項與詳解內容
 */
export function mountFrierenQuizFeedbackHud(
  h: FrierenQuizFeedbackHudHandlers,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  const n = h.questionIndex + 1;
  const total = h.questionCount;
  const promptHtml = `${escapeHtml(h.promptPlain)}<span class="hud-adopter-quiz-inline-progress" aria-label="第 ${n} 題，共 ${total} 題">（${n}/${total}）</span>`;
  const verdict = h.chosenSlot === h.correctSlot ? "正確！" : "錯誤。";
  const verdictCls =
    h.chosenSlot === h.correctSlot
      ? "hud-frieren-quiz-verdict--ok"
      : "hud-frieren-quiz-verdict--bad";
  const headEsc = escapeHtml(h.explanationHead);
  const tailEsc = escapeHtml(h.explanationTail);
  const nextLabel = h.isLastQuestion ? "查看成績" : "下一題";
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz">
      <div class="hud-page-head hud-page-head--frieren-quiz hud-page-head--frieren-quiz-feedback">
        <p class="hud-line hud-title hud-title--proto">芙莉蓮測驗</p>
        <button type="button" class="hud-btn hud-gallery-paged__corner-btn hud-frieren-quiz-exit" data-act="exit">離開測驗</button>
      </div>
      <div class="hud-frieren-quiz-feedback">
        <p class="hud-line hud-sub hud-sub--proto hud-frieren-quiz-verdict ${verdictCls}">${verdict}</p>
        <p class="hud-line hud-sub hud-sub--proto hud-frieren-quiz-expl-head">${headEsc}</p>
        ${
          tailEsc
            ? `<p class="hud-line hud-sub hud-sub--proto hud-frieren-quiz-expl-tail">${tailEsc}</p>`
            : ""
        }
      </div>
      <footer class="hud-frieren-quiz-feedback__footer">
        <button type="button" class="hud-btn hud-gallery-paged__corner-btn hud-frieren-quiz-next" data-act="next">${nextLabel}</button>
      </footer>
    </div>
  `;
  el.hidden = false;
  el.scrollTop = 0;
  el.querySelector<HTMLButtonElement>('[data-act="next"]')?.addEventListener(
    "click",
    () => {
      h.onNext();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="exit"]')?.addEventListener(
    "click",
    () => {
      h.onExit();
    },
  );
}

export type FrierenQuizResultHudHandlers = {
  /** 結果主標題（例：芙莉蓮測驗　結算） */
  titleZh: string;
  /** 總分行（例：總分：80／100） */
  scoreLineZh: string;
  /** 評級名稱行（例：評級：良好表現） */
  tierLineZh: string;
  /** 評語正文單段文字（自動換行） */
  bodyZh: string;
  /** 返回遊戲設定 */
  onBackToSettings: () => void;
};

/**
 * 顯示芙莉蓮測驗結果頁。
 *
 * @param h - 結果標題與內文
 */
export function mountFrierenQuizResultHud(
  h: FrierenQuizResultHudHandlers,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  const bodyEsc = escapeHtml(h.bodyZh.trim());
  const titleEsc = escapeHtml(h.titleZh);
  const scoreEsc = escapeHtml(h.scoreLineZh);
  const tierEsc = escapeHtml(h.tierLineZh);
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result">
      <div class="hud-page-head hud-page-head--frieren-quiz">
        <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">${titleEsc}</p>
      </div>
      <div class="hud-adopter-result-body hud-adopter-result-body--frieren">
        <p class="hud-line hud-sub hud-sub--proto hud-frieren-quiz-result-line hud-frieren-quiz-result-line--score">${scoreEsc}</p>
        <p class="hud-line hud-sub hud-sub--proto hud-frieren-quiz-result-line hud-frieren-quiz-result-line--tier">${tierEsc}</p>
        <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para">${bodyEsc}</p>
      </div>
      <footer class="hud-gallery-hub__footer hud-gallery-hub__footer--frieren">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="back-settings">結束測驗</button>
      </footer>
    </div>
  `;
  el.hidden = false;
  el
    .querySelector<HTMLButtonElement>('[data-act="back-settings"]')
    ?.addEventListener(
    "click",
    () => {
        h.onBackToSettings();
      },
    );
}

