/**
 * 遊戲設定：選項與雙欄版面對齊桌面 `CHEAT_MENU_ITEMS`（網頁版作弊項直接顯示，無密碼）。
 */

import {
  cheatDisableAllEndingCgs,
  cheatUnlockAllEndingCgs,
  cheatUnlockAllWhimsAndEnemies,
  clearCheatEndingKeysSnapshot,
  resetGalleryUnlockDocToEmpty,
} from "../save/galleryUnlock";
import { deleteAllSaveSlots } from "../save/idbSave";
import { applyWebBgmMutePreference, syncWebBgmOpening } from "../audio/webBgm";
import {
  isBgmMutedPreferred,
  isCheatBootstrapPreferred,
  isCheatGalleryAllEndingsActive,
  setBgmMutedPreferred,
  setCheatBootstrapPreferred,
  setCheatGalleryAllEndingsActive,
} from "../save/webPrefs";
import { escapeHtml, showHudMessageToast } from "./hudToast";

const HUD_ID = "hud";
const CHEAT_REVEAL_TAP_TARGET = 10;

/** 是否已解鎖顯示「作弊專區」按鈕（僅本次遊戲啟動期間有效）。 */
let isCheatEntryVisible = false;

/** 對齊 `main.py` 之 `CHEAT_MENU_ITEMS` */
const CHEAT_MENU_ITEMS_ZH: readonly string[] = [
  "芙莉蓮測驗",
  "各人物結局解鎖條件",
  "背景音樂",
  "清空畫廊已解鎖CG圖",
  "清空所有存檔",
  "作弊開局：開局高屬性養成",
  "解鎖畫廊全部結局CG圖",
  "解鎖畫廊全部夥伴與敵人CG圖",
] as const;

const MSG_CONFIRM_GALLERY_ON =
  "確定要開啟「解鎖畫廊全部結局CG圖」作弊功能？\n\n按「確定」繼續，「取消」則返回。";
const MSG_CONFIRM_BOOTSTRAP =
  "確定要開啟「作弊開局：開局高屬性養成」？\n\n開啟後不會跳過前言；通過前言後仍將獲得等同作弊狀態之屬性加成。\n\n按「確定」繼續，「取消」則返回。";
const MSG_CONFIRM_BOOTSTRAP_OFF =
  "確定要關閉「作弊開局：開局高屬性養成」？\n\n按「確定」繼續，「取消」則返回。";
const MSG_CONFIRM_GALLERY_OFF =
  "確定要關閉「解鎖畫廊全部結局CG圖」作弊？\n\n按「確定」繼續，「取消」則返回。";
/** 對齊 `main.py` 之 `_CHEAT_MODAL_CONFIRM_CLEAR_GALLERY`（網頁版不含鍵盤提示） */
const MSG_CONFIRM_CLEAR_GALLERY =
  "確定要清空「圖片畫廊」內所有已解鎖的 CG 紀錄？\n\n按「確定」繼續，「取消」則返回。";
/** 對齊 `main.py` 之 `_CHEAT_MODAL_CONFIRM_CLEAR_SAVES`（網頁版不含鍵盤提示） */
const MSG_CONFIRM_CLEAR_SAVES =
  "確定要刪除所有存檔？\n\n按「確定」繼續，「取消」則返回。";
const MSG_CONFIRM_UNLOCK_WE =
  "確定要解鎖「同行的夥伴(奇遇)」與「遭遇的強敵(遭遇戰)」畫廊內全部 CG？\n\n按「確定」繼續，「取消」則返回。";

type RowPrefs = {
  /** 背景音樂「開」＝非靜音 */
  bgmOn: boolean;
  bootstrapOn: boolean;
  galleryAllOn: boolean;
};

type EndingRuleGender = "male" | "female";

type EndingRuleDef = {
  readonly key: string;
  readonly nameZh: string;
  readonly titleZh: string;
  readonly lines: readonly string[];
};

const MALE_ENDING_RULES: readonly EndingRuleDef[] = [
  {
    key: "himmel",
    nameZh: "欣梅爾",
    titleZh: "勇者之名與笑容",
    lines: [
      "智力≥60，且智力比力量至少高 5，智力≥信仰。",
      "務實≥社交。",
      "信仰≥力量。",
    ],
  },
  {
    key: "kraft",
    nameZh: "克拉福特",
    titleZh: "特殊：無名的虔誠",
    lines: [
      "信仰≥68。",
      "信仰比智力至少高 10，且信仰比力量至少高 6。",
      "務實≥社交。",
    ],
  },
  {
    key: "stark",
    nameZh: "修塔爾克",
    titleZh: "戰士之脊",
    lines: [
      "力量≥60，且力量≥智力與信仰。",
      "社交≥務實。",
      "信仰≥40。",
    ],
  },
  {
    key: "denken",
    nameZh: "鄧肯",
    titleZh: "大魔法使的黃昏",
    lines: [
      "智力≥70。",
      "務實比社交至少高 20。",
      "智力比力量至少高 6，且智力比信仰至少高 6。",
    ],
  },
  {
    key: "genau",
    nameZh: "葛納烏",
    titleZh: "一級魔法使",
    lines: [
      "社交＜24，且務實＜24。",
      "力量比智力至少高 10。",
      "力量≥60。",
    ],
  },
  {
    key: "eisen",
    nameZh: "艾冉",
    titleZh: "矮人戰士",
    lines: [
      "力量≥60。",
      "力量≥信仰與智力。",
      "務實比社交至少高 10。",
    ],
  },
  {
    key: "wirbel",
    nameZh: "威亞貝爾",
    titleZh: "一級魔法使：捕獲與索敵",
    lines: [
      "力量≥60，且力量＞智力，力量≥信仰。",
      "務實比社交至少高 5。",
      "信仰≤智力。",
    ],
  },
  {
    key: "sein",
    nameZh: "贊恩",
    titleZh: "贖罪與再出發",
    lines: [
      "力量≥50。",
      "社交≥務實。",
      "信仰≥智力。",
    ],
  },
  {
    key: "heiter",
    nameZh: "海塔",
    titleZh: "僧侶與酒與祈禱",
    lines: [
      "信仰≥60。",
      "信仰＞智力，且信仰≥力量。",
      "務實≥社交。",
      "社交≥智力−5。",
    ],
  },
  {
    key: "land",
    nameZh: "蘭特",
    titleZh: "孤僻的一級魔法使",
    lines: [
      "信仰≥55。",
      "信仰＞智力，且信仰＞力量。",
      "社交≤務實+5。",
    ],
  },
  {
    key: "hero_south",
    nameZh: "南方勇者",
    titleZh: "隱藏：人類最強的開路者",
    lines: [
      "社交＜20，且務實＜22。",
      "力量≥78。",
      "力量比智力至少高 14。",
    ],
  },
] as const;

const FEMALE_ENDING_RULES: readonly EndingRuleDef[] = [
  {
    key: "frieren",
    nameZh: "芙莉蓮",
    titleZh: "長壽精靈魔法使",
    lines: [
      "智力≥60，且智力比力量至少高 5，智力≥信仰。",
      "務實≥社交。",
      "信仰≥力量。",
    ],
  },
  {
    key: "flamme",
    nameZh: "弗蘭梅",
    titleZh: "大魔法使：人類的魔法與心憶",
    lines: [
      "信仰≥68。",
      "信仰比智力至少高 10，且信仰比力量至少高 6。",
      "務實≥社交。",
    ],
  },
  {
    key: "fern",
    nameZh: "費倫",
    titleZh: "芙莉蓮的弟子，人類少女",
    lines: [
      "力量≥60，且力量≥智力與信仰。",
      "社交≥務實。",
      "信仰≥40。",
    ],
  },
  {
    key: "serie",
    nameZh: "賽莉耶",
    titleZh: "隱藏：最初的大魔法使",
    lines: [
      "智力≥70。",
      "務實比社交至少高 20。",
      "智力比力量至少高 6，且智力比信仰至少高 6。",
    ],
  },
  {
    key: "ubel",
    nameZh: "尤蓓爾",
    titleZh: "危險向：殺戮魔法的一級魔法使",
    lines: [
      "社交＜24，且務實＜24。",
      "力量比智力至少高 10。",
      "力量≥60。",
    ],
  },
  {
    key: "sense",
    nameZh: "冉則",
    titleZh: "一級魔法使，魔法使考試考官",
    lines: [
      "力量≥60。",
      "力量≥信仰與智力。",
      "務實比社交至少高 10。",
    ],
  },
  {
    key: "methode",
    nameZh: "梅特黛",
    titleZh: "擁抱魔法使：追蹤與拘束",
    lines: [
      "力量≥60，且力量＞智力，力量≥信仰。",
      "務實比社交至少高 5。",
      "信仰≤智力。",
    ],
  },
  {
    key: "laufen",
    nameZh: "拉歐芬",
    titleZh: "防禦與高速移動的魔法使",
    lines: [
      "力量≥50。",
      "社交≥務實。",
      "信仰≥智力。",
    ],
  },
  {
    key: "kanne",
    nameZh: "康涅",
    titleZh: "操控水的魔法使",
    lines: [
      "信仰≥60。",
      "信仰＞智力，且信仰≥力量。",
      "務實≥社交。",
      "社交≥智力−5。",
    ],
  },
  {
    key: "lavine",
    nameZh: "拉比涅",
    titleZh: "操控冰的魔法使",
    lines: [
      "信仰≥55。",
      "信仰＞智力，且信仰＞力量。",
      "社交≤務實+5。",
    ],
  },
  {
    key: "ehre",
    nameZh: "艾莉",
    titleZh: "年輕的貴族魔法使",
    lines: [
      "社交＜20，且務實＜22。",
      "力量≥78。",
      "力量比智力至少高 14。",
    ],
  },
] as const;

function getEndingRuleList(gender: EndingRuleGender): readonly EndingRuleDef[] {
  return gender === "male" ? MALE_ENDING_RULES : FEMALE_ENDING_RULES;
}

/**
 * 遊戲設定內「各人物結局解鎖條件」完整頁（非覆蓋子視窗）。
 *
 * @param onBackSettings - 返回遊戲設定主頁
 * @param onStartFrierenQuiz - 從設定啟動芙莉蓮測驗
 * @param view - 目前檢視狀態
 */
function mountEndingRulesSettingsHud(
  onBackSettings: () => void,
  onStartFrierenQuiz: () => void,
  view?:
    | { view: "gender" }
    | { view: "list"; gender: EndingRuleGender }
    | { view: "detail"; gender: EndingRuleGender; key: string },
): void {
  const el = hudEl();
  if (!el) {
    return;
  }

  const state =
    view ??
    ({
      view: "gender",
    } as const);

  if (state.view === "gender") {
    el.innerHTML = `
      <div class="hud-settings-root hud-settings-root--rules-select hud-stack hud-stack--narrow hud-gallery hud-gallery--hub">
        <div class="hud-page-head">
          <p class="hud-line hud-title">各人物結局解鎖條件</p>
        </div>
        <div class="hud-settings-rules-root">
          <div class="hud-settings-rules-gender-list" role="navigation" aria-label="結局路線">
            <button type="button" class="hud-btn hud-btn--secondary hud-settings-row hud-settings-row--full" data-rules-gender="male">男性主角路線</button>
            <button type="button" class="hud-btn hud-btn--secondary hud-settings-row hud-settings-row--full" data-rules-gender="female">女性主角路線</button>
          </div>
        </div>
        <footer class="hud-gallery-hub__footer">
          <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="rules-back-root">上一頁</button>
        </footer>
      </div>
    `;
    el.hidden = false;
    const root = el.querySelector<HTMLElement>(".hud-settings-root");
    if (!root) {
      return;
    }
    root
      .querySelectorAll<HTMLButtonElement>("[data-rules-gender]")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          const g = btn.dataset.rulesGender === "female" ? "female" : "male";
          mountEndingRulesSettingsHud(onBackSettings, onStartFrierenQuiz, {
            view: "list",
            gender: g,
          });
        });
      });
    root
      .querySelector<HTMLButtonElement>('[data-act="rules-back-root"]')
      ?.addEventListener("click", () => {
        mountGameSettingsHud(onBackSettings, onStartFrierenQuiz);
      });
    return;
  }

  if (state.view === "list") {
    const { gender } = state;
    const rules = getEndingRuleList(gender);
    const genderLabel = gender === "male" ? "男性主角路線" : "女性主角路線";
    const itemsHtml = rules
      .map(
        (r) =>
          `<button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-rules-key="${escapeHtml(
            r.key,
          )}">${escapeHtml(r.nameZh)}</button>`,
      )
      .join("");
    el.innerHTML = `
      <div class="hud-settings-root hud-stack hud-stack--narrow hud-gallery hud-gallery--hub">
        <div class="hud-page-head">
          <p class="hud-line hud-title">各人物結局解鎖條件</p>
        </div>
        <div class="hud-settings-rules-root">
          <div class="hud-gallery-hub__list hud-gallery-hub__list--grid hud-settings-rules-list-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr));" role="navigation" aria-label="${escapeHtml(
            genderLabel,
          )}人物列表">
            ${itemsHtml}
          </div>
        </div>
        <footer class="hud-gallery-hub__footer">
          <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="rules-back-gender">上一頁</button>
        </footer>
      </div>
    `;
    el.hidden = false;
    const root = el.querySelector<HTMLElement>(".hud-settings-root");
    if (!root) {
      return;
    }
    root.querySelectorAll<HTMLButtonElement>("[data-rules-key]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.rulesKey ?? "";
        mountEndingRulesSettingsHud(onBackSettings, onStartFrierenQuiz, {
          view: "detail",
          gender,
          key,
        });
      });
    });
    root
      .querySelector<HTMLButtonElement>('[data-act="rules-back-gender"]')
      ?.addEventListener("click", () => {
        mountEndingRulesSettingsHud(onBackSettings, onStartFrierenQuiz, {
          view: "gender",
        });
      });
    return;
  }

  const { gender, key } = state;
  const rules = getEndingRuleList(gender);
  const def = rules.find((r) => r.key === key) ?? rules[0];
  const lines = def.lines;
  el.innerHTML = `
    <div class="hud-settings-root hud-settings-root--rules hud-stack hud-stack--narrow hud-gallery hud-gallery--hub">
      <div class="hud-page-head">
        <p class="hud-line hud-title">${escapeHtml(`${def.nameZh} 結局解鎖條件`)}</p>
      </div>
      <div class="hud-settings-rules-root">
        <ul class="hud-settings-rules-list">
          ${lines
            .map(
              (ln) => {
                const cleaned = ln.replace(/。/g, "").trim();
                return `<li class="hud-line hud-sub hud-sub--wrap hud-settings-rules-line">${escapeHtml(
                  cleaned,
                )}</li>`;
              },
            )
            .join("")}
        </ul>
      </div>
      <footer class="hud-gallery-hub__footer">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="rules-back-list">上一頁</button>
      </footer>
    </div>
  `;
  el.hidden = false;
  const root = el.querySelector<HTMLElement>(".hud-settings-root");
  if (!root) {
    return;
  }
  root
    .querySelector<HTMLButtonElement>('[data-act="rules-back-list"]')
    ?.addEventListener("click", () => {
      mountEndingRulesSettingsHud(onBackSettings, onStartFrierenQuiz, {
        view: "list",
        gender,
      });
    });
}

/**
 * 對齊桌面 `_cheat_menu_row_label`：部分列附（開）／（關）。
 *
 * @param itemI - `CHEAT_MENU_ITEMS` 索引 0～7
 * @param st - 目前偏好狀態
 */
function cheatMenuRowLabelZh(itemI: number, st: RowPrefs): string {
  const base = CHEAT_MENU_ITEMS_ZH[itemI] ?? "";
  if (itemI === 2) {
    return `${base}（${st.bgmOn ? "開" : "關"}）`;
  }
  if (itemI === 5) {
    return `${base}（${st.bootstrapOn ? "開" : "關"}）`;
  }
  return base;
}

/**
 * @returns 目前列標籤用偏好（同步讀 localStorage）
 */
function readRowPrefs(): RowPrefs {
  return {
    bgmOn: !isBgmMutedPreferred(),
    bootstrapOn: isCheatBootstrapPreferred(),
    galleryAllOn: isCheatGalleryAllEndingsActive(),
  };
}

/**
 * @returns HUD 根節點
 */
function hudEl(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

/**
 * 依偏好重繪各列按鈕文字。
 *
 * @param root - `.hud-settings-root`
 */
function refreshSettingRowLabels(root: HTMLElement): void {
  const st = readRowPrefs();
  root.querySelectorAll<HTMLButtonElement>("[data-setting-idx]").forEach((btn) => {
    const i = Number(btn.dataset.settingIdx);
    if (!Number.isInteger(i) || i < 0 || i > 7) {
      return;
    }
    btn.textContent = cheatMenuRowLabelZh(i, st);
  });
}

/**
 * 全視窗確認對話（Enter 確定、Esc 取消；並提供「確定／取消」按鈕）。
 *
 * @param root - 後備掛載點（僅在找不到 `#hud` 時使用）
 * @param messageZh - 純文字，可用 `\n` 換行
 * @param onConfirm - 使用者確認後執行（可為 async）
 */
function openSettingsConfirmModal(
  root: HTMLElement,
  messageZh: string,
  onConfirm: () => void | Promise<void>,
): void {
  const host = hudEl() ?? root;
  host.querySelector(".hud-settings-confirm")?.remove();
  const wrap = document.createElement("div");
  wrap.className = "hud-settings-confirm";
  wrap.innerHTML = `
    <div
      class="hud-settings-subpanel__card hud-settings-confirm__card"
      role="alertdialog"
      aria-modal="true"
      aria-describedby="hud-settings-confirm-msg"
    >
      <div id="hud-settings-confirm-msg" class="hud-settings-confirm__message hud-line">${escapeHtml(messageZh)}</div>
      <div class="hud-settings-confirm__actions">
        <button type="button" class="hud-btn hud-settings-confirm__btn hud-settings-confirm__btn--ok" data-act="confirm-ok">確定</button>
        <button type="button" class="hud-btn hud-btn--secondary hud-settings-confirm__btn" data-act="confirm-cancel">取消</button>
      </div>
    </div>
  `;

  let settled = false;
  const close = (): void => {
    window.removeEventListener("keydown", onKeyDown);
    wrap.remove();
  };
  const cancel = (): void => {
    if (settled) {
      return;
    }
    settled = true;
    close();
  };
  const confirm = (): void => {
    if (settled) {
      return;
    }
    settled = true;
    close();
    void Promise.resolve(onConfirm());
  };

  const onKeyDown = (ev: KeyboardEvent): void => {
    if (ev.key === "Escape") {
      ev.preventDefault();
      cancel();
    } else if (ev.key === "Enter") {
      ev.preventDefault();
      confirm();
    }
  };

  window.addEventListener("keydown", onKeyDown);
  wrap.addEventListener("click", (ev) => {
    if (ev.target === wrap) {
      cancel();
    }
  });
  wrap.querySelector(".hud-settings-confirm__card")?.addEventListener("click", (ev) => {
    ev.stopPropagation();
  });
  wrap.querySelector('[data-act="confirm-cancel"]')?.addEventListener("click", cancel);
  wrap.querySelector('[data-act="confirm-ok"]')?.addEventListener("click", confirm);

  host.appendChild(wrap);
  wrap.querySelector<HTMLButtonElement>('[data-act="confirm-ok"]')?.focus();
}

/**
 * 顯示全螢幕子層（測驗占位等）。
 *
 * @param root - 設定根節點
 * @param title - 標題
 * @param bodyHtml - 已跳脫之內文 HTML
 */
function openSubPanel(root: HTMLElement, title: string, bodyHtml: string): void {
  root.querySelector(".hud-settings-subpanel")?.remove();
  const wrap = document.createElement("div");
  wrap.className = "hud-settings-subpanel";
  wrap.innerHTML = `
    <div class="hud-settings-subpanel__card" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
      <p class="hud-line hud-title hud-settings-subpanel__title">${escapeHtml(title)}</p>
      <div class="hud-settings-subpanel__body">${bodyHtml}</div>
      <button type="button" class="hud-btn hud-settings-subpanel__close">關閉</button>
    </div>
  `;
  root.appendChild(wrap);
  wrap.querySelector(".hud-settings-subpanel__close")?.addEventListener("click", () => {
    wrap.remove();
  });
}

/**
 * 顯示「作弊專區」子面板，內含三個作弊相關選項。
 *
 * @param root - 設定根節點
 */
function openCheatPanel(root: HTMLElement): void {
  root.querySelector(".hud-settings-subpanel")?.remove();
  const wrap = document.createElement("div");
  wrap.className = "hud-settings-subpanel hud-settings-subpanel--cheat";
  wrap.innerHTML = `
    <div
      class="hud-settings-subpanel__card hud-settings-root hud-stack hud-gallery hud-gallery--hub"
      role="dialog"
      aria-modal="true"
      aria-label="作弊專區"
    >
      <div class="hud-page-head">
        <p class="hud-line hud-title">作弊專區</p>
      </div>
      <div
        class="hud-gallery-hub__list hud-settings-cheat-list"
        role="navigation"
        aria-label="作弊專區選項"
      >
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-setting-idx="5"></button>
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-setting-idx="6"></button>
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-setting-idx="7"></button>
      </div>
      <footer class="hud-gallery-hub__footer">
        <button
          type="button"
          class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back hud-settings-cheat-back"
          data-act="cheat-back"
        >
          上一頁
        </button>
      </footer>
    </div>
  `;
  root.appendChild(wrap);
  refreshSettingRowLabels(root);
  wrap.querySelector<HTMLButtonElement>('[data-act="cheat-back"]')?.addEventListener("click", () => {
    wrap.remove();
  });
  wrap.querySelectorAll<HTMLButtonElement>("[data-setting-idx]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.dataset.settingIdx);
      if (!Number.isInteger(i) || i < 5 || i > 7) {
        return;
      }
      // 作弊專區不會啟動芙莉蓮測驗，故此處傳入 no-op。
      void handleSettingRowClick(
        i,
        root,
        () => {
          refreshSettingRowLabels(root);
        },
        () => {},
        () => {},
      );
    });
  });
}

/**
 * 繪製遊戲設定畫面並綁定與桌面對齊之八項行為。
 *
 * @param onBack - 返回主選單
 * @param onStartFrierenQuiz - 從設定啟動芙莉蓮測驗
 */
export function mountGameSettingsHud(
  onBack: () => void,
  onStartFrierenQuiz: () => void,
): void {
  const el = hudEl();
  if (!el) {
    return;
  }
  syncWebBgmOpening();
  const rowsHtml = [
    [0, 3],
    [1, 4],
    [2, "cheat"],
  ]
    .map((pair) => {
      const [left, right] = pair;
      const leftBtn = `<button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-setting-idx="${left}"></button>`;
      if (right === "cheat") {
        const cheatBtn = `<button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-act="settings-cheat"${isCheatEntryVisible ? "" : ' hidden aria-hidden="true"'}>作弊專區</button>`;
        return `${leftBtn}${cheatBtn}`;
      }
      const rightIdx = right as number;
      return `${leftBtn}
          <button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item hud-settings-row" data-setting-idx="${rightIdx}"></button>`;
    })
    .join("");

  el.innerHTML = `
    <div class="hud-settings-root hud-stack hud-stack--narrow hud-gallery hud-gallery--hub">
      <div class="hud-page-head">
        <p class="hud-line hud-title" data-act="settings-title">遊戲設定</p>
      </div>
      <div class="hud-gallery-hub__list hud-gallery-hub__list--grid" role="navigation" aria-label="遊戲設定選項">
        ${rowsHtml}
      </div>
      <footer class="hud-gallery-hub__footer">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="settings-back">回主畫面</button>
      </footer>
    </div>
  `;
  el.hidden = false;

  const root = el.querySelector<HTMLElement>(".hud-settings-root");
  if (!root) {
    return;
  }
  refreshSettingRowLabels(root);

  root.querySelector('[data-act="settings-back"]')?.addEventListener("click", () => {
    onBack();
  });

  root.querySelector('[data-act="settings-cheat"]')?.addEventListener("click", () => {
    openCheatPanel(root);
  });

  const titleEl = root.querySelector<HTMLElement>('[data-act="settings-title"]');
  const cheatBtnEl = root.querySelector<HTMLButtonElement>('[data-act="settings-cheat"]');
  let titleTapCount = 0;
  titleEl?.addEventListener("click", () => {
    if (isCheatEntryVisible) {
      return;
    }
    titleTapCount += 1;
    if (titleTapCount < CHEAT_REVEAL_TAP_TARGET) {
      return;
    }
    isCheatEntryVisible = true;
    if (cheatBtnEl) {
      cheatBtnEl.hidden = false;
      cheatBtnEl.removeAttribute("aria-hidden");
    }
    showHudMessageToast("已解鎖：作弊專區", 1600);
  });

  root.querySelectorAll<HTMLButtonElement>("[data-setting-idx]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.dataset.settingIdx);
      if (!Number.isInteger(i) || i < 0 || i > 7) {
        return;
      }
      void handleSettingRowClick(
        i,
        root,
        () => {
          refreshSettingRowLabels(root);
        },
        () => {
          mountGameSettingsHud(onBack, onStartFrierenQuiz);
        },
        onStartFrierenQuiz,
      );
    });
  });
}

/**
 * 單列點擊：對齊桌面 Enter 行為（非同步寫入 IndexedDB／localStorage）。
 *
 * @param itemI - 0～7
 * @param root - 設定根節點（子面板用）
 * @param onStateChange - 成功變更偏好後重繪列標
 * @param onStartFrierenQuiz - 從設定啟動芙莉蓮測驗
 */
async function handleSettingRowClick(
  itemI: number,
  root: HTMLElement,
  onStateChange: () => void,
  onBackSettings: () => void,
  onStartFrierenQuiz: () => void,
): Promise<void> {
  if (itemI === 0) {
    onStartFrierenQuiz();
    return;
  }
  if (itemI === 1) {
    mountEndingRulesSettingsHud(onBackSettings, onStartFrierenQuiz);
    return;
  }
  if (itemI === 2) {
    const next = !isBgmMutedPreferred();
    setBgmMutedPreferred(next);
    applyWebBgmMutePreference();
    showHudMessageToast(next ? "背景音樂：關" : "背景音樂：開", 1600);
    onStateChange();
    return;
  }
  if (itemI === 3) {
    openSettingsConfirmModal(root, MSG_CONFIRM_CLEAR_GALLERY, async () => {
      try {
        await resetGalleryUnlockDocToEmpty();
        setCheatGalleryAllEndingsActive(false);
        clearCheatEndingKeysSnapshot();
        showHudMessageToast("已清空畫廊解鎖紀錄", 2200);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        showHudMessageToast(`清空失敗：${msg}`, 3200);
      }
      onStateChange();
    });
    return;
  }
  if (itemI === 4) {
    openSettingsConfirmModal(root, MSG_CONFIRM_CLEAR_SAVES, async () => {
      try {
        await deleteAllSaveSlots();
        showHudMessageToast("已刪除所有存檔", 2200);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        showHudMessageToast(`刪除失敗：${msg}`, 3200);
      }
    });
    return;
  }
  if (itemI === 5) {
    if (isCheatBootstrapPreferred()) {
      openSettingsConfirmModal(root, MSG_CONFIRM_BOOTSTRAP_OFF, async () => {
        setCheatBootstrapPreferred(false);
        showHudMessageToast("已關閉：作弊開局：開局高屬性養成", 2200);
        onStateChange();
      });
      return;
    }
    openSettingsConfirmModal(root, MSG_CONFIRM_BOOTSTRAP, async () => {
      setCheatBootstrapPreferred(true);
      showHudMessageToast(
        "已開啟：作弊開局：開局高屬性養成（請從標題選「新遊戲」）",
        2600,
      );
      onStateChange();
    });
    return;
  }
  if (itemI === 6) {
    if (isCheatGalleryAllEndingsActive()) {
      openSettingsConfirmModal(root, MSG_CONFIRM_GALLERY_OFF, async () => {
        try {
          await cheatDisableAllEndingCgs();
          setCheatGalleryAllEndingsActive(false);
          showHudMessageToast(
            "已關閉：畫廊全解鎖作弊（保留實際破關解鎖）",
            2200,
          );
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          showHudMessageToast(`操作失敗：${msg}`, 3200);
        }
        onStateChange();
      });
      return;
    }
    openSettingsConfirmModal(root, MSG_CONFIRM_GALLERY_ON, async () => {
      try {
        await cheatUnlockAllEndingCgs();
        setCheatGalleryAllEndingsActive(true);
        showHudMessageToast("已開啟：畫廊全部結局 CG 解鎖", 2200);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        showHudMessageToast(`操作失敗：${msg}`, 3200);
      }
      onStateChange();
    });
    return;
  }
  if (itemI === 7) {
    openSettingsConfirmModal(root, MSG_CONFIRM_UNLOCK_WE, async () => {
      try {
        await cheatUnlockAllWhimsAndEnemies();
        showHudMessageToast(
          "已解鎖：同行的夥伴(奇遇)、遭遇的強敵(遭遇戰)（全部 CG）",
          2400,
        );
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        showHudMessageToast(`操作失敗：${msg}`, 3200);
      }
      onStateChange();
    });
    return;
  }
}
