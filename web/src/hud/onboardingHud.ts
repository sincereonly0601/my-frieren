/**
 * 開場／監護人／聖堂問卷／監護契約之 DOM HUD。
 * 各頁主標題包在 `.hud-page-head` 內，與 `style.css` 搭配以固定標題列高度與視窗頂緣對齊方式。
 */

import {
  CONTRACT_NAME_LABEL_ZH,
  CONTRACT_PAPER_HEADER_ZH,
  shuffledContractRunesForName,
} from "../story/contractCopy";
import { syncWebBgmPrologue } from "../audio/webBgm";
import {
  GUARDIAN_INTRO_BODY,
  GUARDIAN_SECTION_HEADER,
  PROLOGUE_SECTION_HEADERS,
  PROLOGUE_SECTIONS,
} from "../story/onboardingCopy";
import { escapeAttr, escapeHtml } from "./domHud";

const HUD_ID = "hud";

/** 監護人取名欄與寫入存檔之姓名上限（與桌面 `main.py` 取名緩衝一致） */
export const GUARDIAN_HEROINE_NAME_MAX_LEN = 12;

function hudEl(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

export type IntroHudHandlers = {
  pageIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onFinishIntro: () => void;
};

/**
 * 開場三頁（左右換頁，末頁結束並寫入 `introDone`）。
 * 第一頁不顯示「上一頁」按鈕，僅「下一頁」置中。
 */
export function mountIntroHud(h: IntroHudHandlers): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  const i = h.pageIndex;
  const last = i >= PROLOGUE_SECTIONS.length - 1;
  const first = i <= 0;
  const header = escapeHtml(PROLOGUE_SECTION_HEADERS[i] ?? "");
  const body = escapeHtml(PROLOGUE_SECTIONS[i] ?? "");
  const navClass = first ? "hud-actions hud-intro-nav hud-intro-nav--first" : "hud-actions hud-intro-nav";
  const prevBtn = first
    ? ""
    : `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn" data-act="prev">上一頁</button>`;
  const nextBtnHtml = last
    ? `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn" data-act="finish">進入監護人流程</button>`
    : `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn" data-act="next">下一頁</button>`;
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--intro">
      <div class="hud-page-head">
        <p class="hud-line hud-title hud-title--proto">開場</p>
      </div>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-header">${header}</p>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body">${body}</p>
      <div class="${navClass}">
        ${prevBtn}
        ${nextBtnHtml}
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>('[data-act="prev"]')?.addEventListener(
    "click",
    () => {
      h.onPrev();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="next"]')?.addEventListener(
    "click",
    () => {
      h.onNext();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="finish"]')?.addEventListener(
    "click",
    () => {
      h.onFinishIntro();
    },
  );
}

export type GuardianHudHandlers = {
  gender: "male" | "female" | null;
  nameDraft: string;
  onGenderChange: (g: "male" | "female" | null) => void;
  /** 姓名確認後一次寫入並進入問卷 */
  onConfirmAll: () => void;
};

/**
 * 監護人：同一畫面選性別、取名，按確認後進入問卷。
 */
export function mountGuardianHud(h: GuardianHudHandlers): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  const head = escapeHtml(GUARDIAN_SECTION_HEADER);
  const body = escapeHtml(GUARDIAN_INTRO_BODY);
  const maleSel = h.gender === "male" ? " hud-gender--selected" : "";
  const femaleSel = h.gender === "female" ? " hud-gender--selected" : "";
  const maxLen = GUARDIAN_HEROINE_NAME_MAX_LEN;
  const nameVal = escapeAttr(h.nameDraft.slice(0, maxLen));
  const genderConfirmDisabled = h.gender === null ? " disabled" : "";
  const nameConfirmDisabled = h.nameDraft.trim().length === 0 ? " disabled" : "";
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--guardian">
      <div class="hud-page-head">
        <p class="hud-line hud-title hud-title--proto">${head}</p>
      </div>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body">${body}</p>
      <div class="hud-guardian-combined">
        <div class="hud-guardian-step hud-guardian-step--gender" data-step="gender">
          <div class="hud-gender-row" role="group" aria-label="選擇性別">
            <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto${maleSel}" data-g="male">男</button>
            <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto${femaleSel}" data-g="female">女</button>
          </div>
          <div class="hud-guardian-confirm-wrap">
            <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn${genderConfirmDisabled}" data-act="confirm-gender"${genderConfirmDisabled}>確認性別</button>
          </div>
        </div>
        <div class="hud-guardian-step hud-guardian-step--name" data-step="name" hidden>
          <label class="hud-field hud-field--compact hud-guardian-name-field">
            <span class="hud-field-label">孩子姓名（最多 ${maxLen} 字）</span>
            <input id="guardian-name-input" class="hud-input hud-input--compact" type="text" maxlength="${maxLen}" autocomplete="off" value="${nameVal}" />
          </label>
          <div class="hud-guardian-confirm-wrap">
            <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn${nameConfirmDisabled}" data-act="confirm-name"${nameConfirmDisabled}>確認姓名</button>
          </div>
        </div>
      </div>
    </div>
  `;
  el.hidden = false;
  const genderStep = el.querySelector<HTMLElement>(".hud-guardian-step--gender");
  const nameStep = el.querySelector<HTMLElement>(".hud-guardian-step--name");
  const confirmGenderBtn = el.querySelector<HTMLButtonElement>('[data-act="confirm-gender"]');
  const confirmNameBtn = el.querySelector<HTMLButtonElement>('[data-act="confirm-name"]');
  const nameInput = el.querySelector<HTMLInputElement>("#guardian-name-input");
  const genderButtons = Array.from(
    el.querySelectorAll<HTMLButtonElement>("[data-g]"),
  );
  let selectedGender: "male" | "female" | null = h.gender;

  const syncGenderConfirmEnabled = (): void => {
    if (!confirmGenderBtn) {
      return;
    }
    confirmGenderBtn.disabled = selectedGender === null;
  };
  const syncNameConfirmEnabled = (): void => {
    if (!confirmNameBtn || !nameInput) {
      return;
    }
    confirmNameBtn.disabled = nameInput.value.trim().length === 0;
  };

  genderButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const g = btn.dataset.g === "female" ? "female" : "male";
      selectedGender = g;
      h.onGenderChange(g);
      syncGenderConfirmEnabled();
      genderButtons.forEach((b) => {
        const isSelected = b.dataset.g === g;
        b.classList.toggle("hud-gender--selected", isSelected);
      });
    });
  });

  nameInput?.addEventListener("input", () => {
    syncNameConfirmEnabled();
  });

  el.querySelector<HTMLButtonElement>('[data-act="confirm-gender"]')?.addEventListener(
    "click",
    () => {
      if (selectedGender === null) {
        return;
      }
      if (!genderStep || !nameStep) {
        return;
      }
      genderStep.hidden = true;
      nameStep.hidden = false;
      syncNameConfirmEnabled();
      if (nameInput) {
        nameInput.focus();
      }
    },
  );

  el.querySelector<HTMLButtonElement>('[data-act="confirm-name"]')?.addEventListener(
    "click",
    () => {
      const raw = nameInput?.value?.trim() ?? "";
      if (!raw) {
        return;
      }
      h.onConfirmAll();
    },
  );

  syncGenderConfirmEnabled();
  syncNameConfirmEnabled();
}

export type AdopterQuizQuestionHudHandlers = {
  questionIndex: number;
  /** 題幹（已壓空白，利於自動換行） */
  promptPlain: string;
  /** 三則選項全文 */
  optionLabels: readonly [string, string, string];
  /** 點選選項即記錄答案並進下一題／結算 */
  onPickOption: (optionIndex: number) => void;
};

/**
 * 聖堂監護人問卷導言：顯示進場說明，確認後再進入第一題。
 *
 * @param onStartQuiz - 點擊「開始問卷」後進入題目頁
 */
export function mountAdopterQuizIntroHud(onStartQuiz: () => void): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  el.innerHTML = `
    <div class="hud-event-alert-root hud-event-alert-root--incident" role="dialog" aria-modal="true">
      <button type="button" class="hud-event-alert-hitbox" aria-label="進入監護人問卷">
        <span class="hud-event-alert-frame hud-event-alert-frame--incident hud-event-alert-frame--adopter-quiz-intro">
          <span class="hud-event-alert-title">監護人問卷</span>
          <span class="hud-event-alert-teaser">在領養之前，有些事情我們需要再確認...</span>
          <span class="hud-event-alert-hint">點擊畫面繼續</span>
        </span>
      </button>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>(".hud-event-alert-hitbox")?.addEventListener(
    "click",
    () => {
      onStartQuiz();
    },
  );
}

/**
 * 聖堂問卷單題：四選一，點選即作答（對照桌面方向鍵＋確認）。
 * 題號以「（n/5）」附於題幹結尾，不另占一行以節省垂直空間。
 *
 * @param h - 題號與選項
 */
export function mountAdopterQuizQuestionHud(
  h: AdopterQuizQuestionHudHandlers,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  const n = h.questionIndex + 1;
  const promptHtml = `${escapeHtml(h.promptPlain)}<span class="hud-adopter-quiz-inline-progress" aria-label="第 ${n} 題，共 5 題">（${n}/5）</span>`;
  const opt = (i: number) => escapeHtml(h.optionLabels[i] ?? "");
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz">
      <div class="hud-page-head">
        <p class="hud-line hud-title hud-title--proto">聖堂監護人問卷</p>
      </div>
      <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt">${promptHtml}</p>
      <div class="hud-adopter-quiz-options" role="group" aria-label="選項">
        <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-oi="0">${opt(0)}</button>
        <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-oi="1">${opt(1)}</button>
        <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-oi="2">${opt(2)}</button>
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelectorAll<HTMLButtonElement>("[data-oi]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = parseInt(btn.dataset.oi ?? "0", 10);
      if (i >= 0 && i <= 2) {
        h.onPickOption(i);
      }
    });
  });
}

export type AdopterQuizResultHudHandlers = {
  judgmentZh: string;
  statLineZh: string;
  /** 進入監護契約 */
  onContinue: () => void;
};

/**
 * 問卷判讀與數值摘要；確認後進契約場景。
 * 結構：標題 → 可捲內文（段落）→ 底部 `.hud-adopter-result-footer`（數值列＋繼續）。
 *
 * @param h - 判讀正文與「數值變化」列
 */
export function mountAdopterQuizResultHud(h: AdopterQuizResultHudHandlers): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  const paras = h.judgmentZh.split(/\n\n/).map((p) => escapeHtml(p.trim()));
  const bodyHtml = paras
    .filter((x) => x.length > 0)
    .map((p) => `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para">${p}</p>`)
    .join("");
  const statEsc = escapeHtml(h.statLineZh);
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result">
      <div class="hud-page-head">
        <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">聖堂紀錄　領養者問卷判讀</p>
      </div>
      <div class="hud-adopter-result-body">
        ${bodyHtml}
      </div>
      <div class="hud-adopter-result-footer">
        <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-stat">${statEsc}</p>
        <div class="hud-actions hud-actions--adopter-result">
          <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn hud-btn--adopter-continue" data-act="qnext">繼續</button>
        </div>
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>('[data-act="qnext"]')?.addEventListener(
    "click",
    () => {
      h.onContinue();
    },
  );
}

/**
 * 監護契約：偽古文兩段連寫（無硬斷行，由欄寬自動換行）；依姓名種子打亂段順序。
 * 「確認契約」在署印列內、朱印右側；紙面不響應點擊／鍵盤簽署。
 * 確認後由呼叫端寫入 `onboardingComplete`。
 *
 * @param heroineName - 存檔內姓名（顯示至多 {@link GUARDIAN_HEROINE_NAME_MAX_LEN} 字，與桌面一致）
 * @param onSeal - 簽署並繼續（僅觸發一次）
 */
export async function mountOnboardingContractHud(
  heroineName: string,
  onSeal: () => void,
): Promise<void> {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmPrologue();
  const trimmed = heroineName.trim();
  const nmRaw = trimmed.slice(0, GUARDIAN_HEROINE_NAME_MAX_LEN) || "——";
  const nm = escapeHtml(nmRaw);
  const runes = await shuffledContractRunesForName(heroineName);
  const runeHtml = runes
    .map(
      (line) =>
        `<p class="hud-line hud-contract-rune-line">${escapeHtml(line)}</p>`,
    )
    .join("");
  const nameLblEsc = escapeHtml(CONTRACT_NAME_LABEL_ZH);
  const paperHdrEsc = escapeHtml(CONTRACT_PAPER_HEADER_ZH);
  el.innerHTML = `
    <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--contract">
      <div class="hud-contract-paper" role="region" aria-label="監護契約">
        <p class="hud-line hud-contract-paper-hdr">${paperHdrEsc}</p>
        <div class="hud-contract-runes">
          <div class="hud-contract-runes-inner">${runeHtml}</div>
        </div>
        <div class="hud-contract-sign-row">
          <div class="hud-contract-sign-row-inner">
            <div class="hud-contract-sign-col">
              <p class="hud-line hud-contract-name-line">
                <span class="hud-contract-name-lbl-inline">${nameLblEsc}</span>
                <span class="hud-contract-name-sig-inline">${nm}</span>
              </p>
            </div>
            <div class="hud-contract-action-block">
              <button type="button" class="hud-contract-next-btn" data-act="contract-next">
                確認契約
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
  el.hidden = false;
  const nextBtn = el.querySelector<HTMLButtonElement>(
    '[data-act="contract-next"]',
  );
  if (!nextBtn) {
    return;
  }
  let sealed = false;
  const advance = () => {
    if (sealed) {
      return;
    }
    sealed = true;
    onSeal();
  };
  nextBtn.addEventListener("click", () => {
    advance();
  });
  queueMicrotask(() => {
    nextBtn.focus({ preventScroll: true });
  });
}

/** 契約完成後進入培養前之主標（事件前導樣式） */
const TRAINING_PREAMBLE_TITLE_ZH = "培養未來的希望";

/**
 * 培養機制簡介（單段連寫；勿手動插入換行以符合專案「每段由排版引擎折行」約定）。
 */
const TRAINING_PREAMBLE_BODY_ZH =
  "將以季為單位安排培養，逐步影響孩子的能力走向。過程中可能出現重大抉擇、突發狀況、遭遇戰或奇遇，請依畫面提示完成。";

/**
 * 監護契約確認後、進入培養主畫面前之全畫面前導（比照事件前導，可點整頁繼續）。
 *
 * @param onStart - 點擊畫面後進入 {@link PlaceholderScene}
 */
export function mountTrainingPreambleHud(onStart: () => void): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  el.innerHTML = `
    <div class="hud-event-alert-root hud-event-alert-root--incident" role="dialog" aria-modal="true">
      <button type="button" class="hud-event-alert-hitbox" aria-label="開始培養">
        <span class="hud-event-alert-frame hud-event-alert-frame--incident hud-event-alert-frame--training-preamble">
          <span class="hud-event-alert-title">${escapeHtml(TRAINING_PREAMBLE_TITLE_ZH)}</span>
          <span class="hud-event-alert-teaser">${escapeHtml(TRAINING_PREAMBLE_BODY_ZH)}</span>
          <span class="hud-event-alert-hint">點擊畫面繼續</span>
        </span>
      </button>
    </div>
  `;
  el.hidden = false;
  el.querySelector(".hud-event-alert-hitbox")?.addEventListener("click", () => {
    onStart();
  });
}
