/**
 * 以 DOM 疊在 Phaser Canvas 上顯示 UI 文案，沿用瀏覽器原生文字渲染（中文較不易糊）。
 * `pointer-events: none` 讓觸控／點擊仍由底下 Phaser 接收（按鈕區除外）。
 */

import {
  formatActionStatEffectsLine,
  TRAINING_ACTIONS,
  type TrainingAction,
} from "../game/trainingActions";
import { TITLE_MENU_ITEMS_ZH } from "../gallery/galleryConstants";
import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import { syncWebBgmOpening, syncWebBgmPlayPhase } from "../audio/webBgm";
import {
  ageMonthsFromTimeLeft,
  type GameSaveV3,
  SAVE_SLOT_COUNT,
  type SaveSlotSummary,
} from "../save/idbSave";
import { heroinePortraitUrlCandidates } from "../sim/encounterAssetUrls";
import { showHudMessageToast } from "./hudToast";

const HUD_ID = "hud";

/** 首屏右下角製作署名（靜態文案） */
const TITLE_SPLASH_CREDIT_ZH = "本遊戲由薯製作";

/** 立繪占位：載入成功時隱藏 */
const PLAY_PORTRAIT_PH_HIDE = "hud-play-portrait__ph--hide";

/**
 * 人生階段鍵（對齊桌面 `play_portrait._STAGE_IMAGE_CANDIDATES`：幼年／少年／青年）。
 *
 * @param phase - `game.phase`
 */
function portraitPhaseKey(
  phase: string,
): "childhood" | "adolescence" | "young_adult" {
  if (phase === "adolescence" || phase === "young_adult") {
    return phase;
  }
  return "childhood";
}

/**
 * @returns HUD 根節點；不存在則為 null
 */
function hudRoot(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

/**
 * 切換全螢幕：若未全螢幕則嘗試進入，全螢幕中則退出。
 *
 * @returns 是否已發出切換請求（若瀏覽器不支援則為 false）
 */
function toggleFullscreen(): boolean {
  const doc = document as Document & {
    webkitFullscreenElement?: Element | null;
    webkitExitFullscreen?: () => Promise<void>;
    mozFullScreenElement?: Element | null;
    mozCancelFullScreen?: () => Promise<void>;
    msFullscreenElement?: Element | null;
    msExitFullscreen?: () => Promise<void>;
  };
  const root = document.documentElement as HTMLElement & {
    webkitRequestFullscreen?: () => Promise<void>;
    mozRequestFullScreen?: () => Promise<void>;
    msRequestFullscreen?: () => Promise<void>;
  };

  const fullscreenElement =
    doc.fullscreenElement ??
    doc.webkitFullscreenElement ??
    doc.mozFullScreenElement ??
    doc.msFullscreenElement ??
    null;

  if (fullscreenElement == null) {
    const request =
      root.requestFullscreen ??
      root.webkitRequestFullscreen ??
      root.mozRequestFullScreen ??
      root.msRequestFullscreen;
    if (!request) {
      return false;
    }
    void request.call(root);
    return true;
  }

  const exit =
    doc.exitFullscreen ??
    doc.webkitExitFullscreen ??
    doc.mozCancelFullScreen ??
    doc.msExitFullscreen;
  if (!exit) {
    return false;
  }
  void exit.call(doc);
  return true;
}

/**
 * 供 `innerHTML` 顯示用文字跳脫。
 *
 * @param s - 使用者輸入或存檔字串
 */
export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * 供 HTML 屬性值跳脫。
 *
 * @param s - 輸入框初值
 */
export function escapeAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function phaseLabelZh(phase: string): string {
  if (phase === "childhood") {
    return "幼年";
  }
  if (phase === "adolescence") {
    return "少年";
  }
  return "青年";
}

/**
 * @param gender - 存檔之性別
 * @returns 顯示用「男／女」
 */
function genderLabelZh(gender: "male" | "female"): string {
  return gender === "female" ? "女" : "男";
}

/**
 * 與桌面版相同：由 `timeLeft` 換算總月數後拆成「幾歲幾月」。
 *
 * @param timeLeft - 剩餘培養季數
 */
function formatAgeYearMonthZh(timeLeft: number): string {
  const totalMonths = ageMonthsFromTimeLeft(timeLeft);
  const y = Math.floor(totalMonths / 12);
  const m = totalMonths % 12;
  return `${y}歲${m}月`;
}

/**
 * 清空 HUD 內容並隱藏。
 */
export function clearHud(): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  el.innerHTML = "";
  el.hidden = true;
}

/**
 * 顯示首屏文案（標題／點擊繼續）。
 * 版面見 `.hud-stack--title-splash`：視窗正中、主標黃色放大。
 */
export function mountTitleHud(): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  syncWebBgmOpening();
  el.innerHTML = `
    <div class="hud-stack hud-stack--title-splash">
      <p class="hud-line hud-title hud-title--splash">葬送的魔法使夢工廠</p>
      <p class="hud-line hud-tap hud-tap--title-splash">點擊畫面繼續</p>
      <p class="hud-line hud-title-splash-credit">${escapeHtml(TITLE_SPLASH_CREDIT_ZH)}</p>
      <button
        type="button"
        class="hud-btn hud-btn--secondary hud-btn--fullscreen"
        data-act="fullscreen"
      >
        全螢幕切換
      </button>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>('[data-act="fullscreen"]')?.addEventListener(
    "click",
    () => {
      toggleFullscreen();
    },
  );
}

export type MainMenuHudHandlers = {
  onNewGame: () => void;
  /** 依 `lastSavedAt` 接最近一筆可續關存檔 */
  onLoadLatest: () => void;
  /** 開啟四欄「讀取進度」選單 */
  onOpenSlotLoad: () => void;
  onGallery: () => void;
  onSettings: () => void;
  onQuit: () => void;
};

/**
 * 顯示標題主選單與綁定按鈕。
 *
 * @param handlers - 各選項回呼
 */
export function mountMenuHud(handlers: MainMenuHudHandlers): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  syncWebBgmOpening();
  const [t0, t1, t2, t3, t4, t5] = TITLE_MENU_ITEMS_ZH;
  el.innerHTML = `
    <div class="hud-stack hud-stack--narrow menu-hud menu-hud--title">
      <div class="hud-page-head">
        <p class="hud-line hud-title hud-title--menu">葬送的魔法使夢工廠</p>
        <p class="hud-line hud-sub hud-sub--menu-tagline">養成 × 奇幻 × 告別</p>
        <button
          type="button"
          class="hud-btn hud-btn--secondary hud-btn--fullscreen"
          data-act="fullscreen"
        >
          全螢幕切換
        </button>
      </div>
      <div class="hud-actions hud-actions--title-menu hud-actions--title-menu-cols">
        <div class="hud-actions__col hud-actions__col--menu">
          <button type="button" class="hud-btn hud-btn--menu-row" data-act="new-game">${escapeHtml(t0)}</button>
          <button type="button" class="hud-btn hud-btn--menu-row" data-act="load-latest">${escapeHtml(t1)}</button>
          <button type="button" class="hud-btn hud-btn--menu-row" data-act="load-slot">${escapeHtml(t2)}</button>
        </div>
        <div class="hud-actions__col hud-actions__col--menu">
          <button type="button" class="hud-btn hud-btn--secondary hud-btn--menu-row" data-act="gallery">${escapeHtml(t3)}</button>
          <button type="button" class="hud-btn hud-btn--secondary hud-btn--menu-row" data-act="settings">${escapeHtml(t4)}</button>
          <button type="button" class="hud-btn hud-btn--secondary hud-btn--menu-row" data-act="quit">${escapeHtml(t5)}</button>
        </div>
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelector<HTMLButtonElement>('[data-act="fullscreen"]')?.addEventListener(
    "click",
    () => {
      toggleFullscreen();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="new-game"]')?.addEventListener(
    "click",
    () => {
      handlers.onNewGame();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="load-latest"]')?.addEventListener("click", () => {
    handlers.onLoadLatest();
  });
  el.querySelector<HTMLButtonElement>('[data-act="load-slot"]')?.addEventListener("click", () => {
    handlers.onOpenSlotLoad();
  });
  el.querySelector<HTMLButtonElement>('[data-act="gallery"]')?.addEventListener(
    "click",
    () => {
      handlers.onGallery();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="settings"]')?.addEventListener(
    "click",
    () => {
      handlers.onSettings();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="quit"]')?.addEventListener("click", () => {
    handlers.onQuit();
  });
}

/**
 * 四欄選單用途：讀檔時空欄不可選；培養中儲存時四格皆可選（對齊桌面 `Screen.SAVE_SLOT`）。
 */
export type SaveSlotPickerMode = "load" | "save";

/**
 * 讀取進度／選擇儲存欄位：四欄（對齊桌面 `SLOT_COUNT`）。
 *
 * @param summaries - 各欄摘要
 * @param onPickSlot - `load`：僅非空欄；`save`：任一格（空欄寫入新存檔）
 * @param mode - 預設 `load`
 * @param onBackToMenu - 讀檔頁右上角「回主選單」
 */
export function mountSaveSlotSelectHud(
  summaries: readonly SaveSlotSummary[],
  onPickSlot: (slotIndex: number) => void,
  mode: SaveSlotPickerMode = "load",
  onBackToMenu?: () => void,
): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  syncWebBgmOpening();
  const isSave = mode === "save";
  const rows = summaries
    .map((s) => {
      const slotTag = `欄位 ${s.slotIndex}`;
      if (s.empty) {
        const line = `${slotTag} （空欄）`;
        const dis = isSave ? "" : " disabled";
        const emptyCls = isSave ? " hud-save-slot-row--save-empty" : "";
        return `
        <button type="button" class="hud-btn hud-btn--secondary hud-save-slot-row${emptyCls}"${dis} data-slot="${s.slotIndex}">
          <span class="hud-save-slot-row__line hud-save-slot-row__line--empty">${escapeHtml(line)}</span>
        </button>`;
      }
      const cells = [
        ["slot", slotTag],
        ["name", s.heroineName],
        ["gender", s.genderZh],
        ["age", s.agePhrase],
        ["time", s.savedAtLocal],
      ]
        .map(
          ([role, t]) =>
            `<span class="hud-save-slot-row__cell hud-save-slot-row__cell--${role}">${escapeHtml(t)}</span>`,
        )
        .join("");
      return `
        <button type="button" class="hud-btn hud-save-slot-row" data-slot="${s.slotIndex}">
          <span class="hud-save-slot-row__line hud-save-slot-row__line--filled">${cells}</span>
        </button>`;
    })
    .join("");
  const title = isSave ? "選擇儲存欄位" : "讀取進度";
  const topRightBtn = !isSave
    ? `<button type="button" class="hud-btn hud-btn--secondary hud-save-slot-screen__home" data-act="slot-home">回主選單</button>`
    : "";
  el.innerHTML = `
    <div class="hud-stack hud-stack--narrow menu-hud hud-save-slot-screen">
      ${topRightBtn}
      <div class="hud-page-head">
        <p class="hud-line hud-title">${escapeHtml(title)}</p>
      </div>
      <div class="hud-actions hud-actions--save-slots" role="list">
        ${rows}
      </div>
    </div>
  `;
  el.hidden = false;
  el.querySelectorAll<HTMLButtonElement>(".hud-save-slot-row:not([disabled])").forEach((btn) => {
    btn.addEventListener("click", () => {
      const n = Number(btn.dataset.slot);
      if (n >= 1 && n <= SAVE_SLOT_COUNT) {
        onPickSlot(n);
      }
    });
  });
  el.querySelector('[data-act="slot-home"]')?.addEventListener("click", () => {
    onBackToMenu?.();
  });
}

/**
 * 與桌面存檔成功 `toast_message` 一致之短提示（約 2s，可點擊提前關閉）。
 *
 * @param slotIndex - 1～4
 */
export function showSaveToSlotToast(slotIndex: number): void {
  if (slotIndex < 1 || slotIndex > SAVE_SLOT_COUNT) {
    return;
  }
  showHudMessageToast(`已儲存至欄位 ${slotIndex}`, 2000);
}

/**
 * 主選單讀檔失敗時顯示。
 *
 * @param message - 錯誤摘要
 */
export function mountMenuHudError(message: string): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  const safe = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  el.innerHTML = `
    <div class="hud-stack hud-stack--narrow">
      <div class="hud-page-head">
        <p class="hud-line hud-title">無法讀取存檔</p>
      </div>
      <p class="hud-line hud-sub hud-sub--wrap">${safe}</p>
    </div>
  `;
  el.hidden = false;
}

/**
 * 培養主畫面（八格指令＋邊角選單／存檔）。
 */
export type PlayHudHandlers = {
  onMenu: () => void;
  onSaveGame: () => void;
  onPickTraining: (keyNum: number) => void;
};

/**
 * 繪製培養畫面：與開場／監護人相同的字級與色調；中央為桌面版八種指令。
 *
 * @param save - 目前存檔
 * @param handlers - 選單、存檔、培養選取
 */
export function mountPlayHud(save: GameSaveV3, handlers: PlayHudHandlers): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  syncWebBgmPlayPhase(save.game.phase);
  const g = save.game;
  const nameDisplay = g.heroine_name.trim()
    ? escapeHtml(g.heroine_name.trim())
    : "未取名";
  const genderZh = genderLabelZh(g.protagonist_gender);
  const ageZh = formatAgeYearMonthZh(g.time_left);
  const noSeason = g.time_left <= 0;
  const btnDis = noSeason ? " disabled" : "";
  const buttons = TRAINING_ACTIONS.map((a: TrainingAction) => {
    const fxLine = formatActionStatEffectsLine(a);
    const fxAttr = escapeAttr(fxLine);
    const fxHtml = escapeHtml(fxLine);
    const t = escapeHtml(a.title);
    return `<button type="button" class="hud-btn hud-btn--secondary hud-btn--training"${btnDis} data-key="${a.keyNum}" title="${fxAttr}"><span class="hud-training-btn__title">${t}</span><span class="hud-training-btn__fx">${fxHtml}</span></button>`;
  }).join("");
  el.innerHTML = `
    <div class="hud-play-root">
      <div class="hud-play-corners">
        <button
          type="button"
          class="hud-play-menu-toggle"
          data-act="play-menu-toggle"
          aria-expanded="false"
          aria-controls="hud-play-menu-panel"
          aria-label="開啟功能選單"
          title="功能選單"
        >
          <span class="hud-play-menu-toggle__line" aria-hidden="true"></span>
          <span class="hud-play-menu-toggle__line" aria-hidden="true"></span>
          <span class="hud-play-menu-toggle__line" aria-hidden="true"></span>
        </button>
        <div id="hud-play-menu-panel" class="hud-play-menu-panel hud-play-menu-panel--hidden">
          <button type="button" class="hud-corner-btn hud-play-menu-panel__btn" data-act="save">
            儲存進度
          </button>
          <button type="button" class="hud-corner-btn hud-play-menu-panel__btn" data-act="menu">
            返回主選單
          </button>
        </div>
      </div>
      <div class="hud-stack hud-stack--wide hud-stack--play">
        <div class="hud-play-main-col">
          <div class="hud-play-stats-row">
            <div class="hud-play-stats-panel">
              <table class="hud-play-stats-table" aria-label="五維">
                <tbody>
                  <tr class="hud-play-stat-row">
                    <th scope="row">智力</th>
                    <td class="hud-play-stats-table__num">${g.int_stat}</td>
                  </tr>
                  <tr class="hud-play-stat-row">
                    <th scope="row">力量</th>
                    <td class="hud-play-stats-table__num">${g.str_stat}</td>
                  </tr>
                  <tr class="hud-play-stat-row">
                    <th scope="row">社交</th>
                    <td class="hud-play-stats-table__num">${g.social}</td>
                  </tr>
                  <tr class="hud-play-stat-row">
                    <th scope="row">信仰</th>
                    <td class="hud-play-stats-table__num">${g.fth_stat}</td>
                  </tr>
                  <tr class="hud-play-stat-row">
                    <th scope="row">務實</th>
                    <td class="hud-play-stats-table__num">${g.pragmatic}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="hud-play-portrait" role="img" aria-label="角色立繪（依性別與人生階段載入）">
              <div class="hud-play-portrait__frame">
                <img class="hud-play-portrait__img" alt="" decoding="async" />
                <div class="hud-play-portrait__ph">無立繪：請將圖檔放於 web/public/assets/portraits/，檔名與桌面 play_portrait 相同。</div>
                <p class="hud-line hud-sub hud-sub--proto hud-play-char-line hud-play-char-line--portrait">
                  <strong>${nameDisplay}</strong>
                  · ${genderZh}
                  · ${ageZh}
                  · ${phaseLabelZh(g.phase)}
                </p>
              </div>
            </div>
          </div>
          <div class="hud-training-grid" role="group" aria-label="培養指令">
            ${buttons}
          </div>
        </div>
      </div>
    </div>
  `;
  el.hidden = false;
  const menuToggle = el.querySelector<HTMLButtonElement>('[data-act="play-menu-toggle"]');
  const menuPanel = el.querySelector<HTMLElement>("#hud-play-menu-panel");
  const playCorners = el.querySelector<HTMLElement>(".hud-play-corners");
  const playRoot = el.querySelector<HTMLElement>(".hud-play-root");
  const statsPanel = el.querySelector<HTMLElement>(".hud-play-stats-panel");
  const trainingGrid = el.querySelector<HTMLElement>(".hud-training-grid");
  /**
   * 以實際版面座標對齊左上功能鍵：
   * - 上緣對齊數值表上緣
   * - 左緣對齊培養按鈕區左緣
   */
  const alignPlayMenuButton = (): void => {
    if (!playCorners || !playRoot || !statsPanel || !trainingGrid) {
      return;
    }
    const rootRect = playRoot.getBoundingClientRect();
    const statsRect = statsPanel.getBoundingClientRect();
    const gridRect = trainingGrid.getBoundingClientRect();
    const topPx = Math.max(0, statsRect.top - rootRect.top);
    const leftPx = Math.max(0, gridRect.left - rootRect.left);
    playCorners.style.top = `${topPx}px`;
    playCorners.style.left = `${leftPx}px`;
  };
  requestAnimationFrame(() => {
    alignPlayMenuButton();
    requestAnimationFrame(() => {
      alignPlayMenuButton();
    });
  });
  /**
   * 切換培養頁左上功能選單顯示狀態。
   *
   * @param open - 是否展開選單
   */
  const setPlayMenuOpen = (open: boolean): void => {
    if (!menuToggle || !menuPanel) {
      return;
    }
    menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    menuPanel.classList.toggle("hud-play-menu-panel--hidden", !open);
  };
  menuToggle?.addEventListener("click", () => {
    const openNow = menuToggle.getAttribute("aria-expanded") === "true";
    setPlayMenuOpen(!openNow);
  });
  el.querySelector<HTMLButtonElement>('[data-act="menu"]')?.addEventListener(
    "click",
    () => {
      setPlayMenuOpen(false);
      handlers.onMenu();
    },
  );
  el.querySelector<HTMLButtonElement>('[data-act="save"]')?.addEventListener(
    "click",
    () => {
      setPlayMenuOpen(false);
      handlers.onSaveGame();
    },
  );
  el.querySelectorAll<HTMLButtonElement>("[data-key]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) {
        return;
      }
      const k = Number(btn.dataset.key);
      if (k >= 1 && k <= 8) {
        handlers.onPickTraining(k);
      }
    });
  });
  const pImg = el.querySelector<HTMLImageElement>(".hud-play-portrait__img");
  const pPh = el.querySelector<HTMLElement>(".hud-play-portrait__ph");
  if (pImg) {
    const gender = g.protagonist_gender === "male" ? "male" : "female";
    const urls = heroinePortraitUrlCandidates(portraitPhaseKey(g.phase), gender);
    wireImageFallbackChain(pImg, urls, pPh, PLAY_PORTRAIT_PH_HIDE);
  }
}

/**
 * 存檔失敗時（無痕封鎖、配額、不支援等）之說明。
 *
 * @param message - 簡短錯誤訊息
 */
export function mountPlaceholderHudError(message: string): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  const safe = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  el.innerHTML = `
    <div class="hud-stack hud-stack--narrow">
      <div class="hud-page-head">
        <p class="hud-line hud-title">存檔無法讀寫</p>
      </div>
      <p class="hud-line hud-sub hud-sub--wrap">
        請確認未停用網站資料，並避免在嚴格無痕模式測試。技術細節：${safe}
      </p>
    </div>
  `;
  el.hidden = false;
}

export { mountGameSettingsHud as mountSettingsHud } from "./settingsHud";
