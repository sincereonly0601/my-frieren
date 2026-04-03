/**
 * 圖片畫廊（DOM）：對齊桌面主選單「圖片畫廊」五類；CG 路徑與桌面 `assets/cg/` 相同，置於 `web/public/assets/`。
 */

import {
  cgUrlCandidatesFromProjectPath,
  encounterGalleryImageUrlCandidates,
  resolveEncounterIdForAssets,
  whimCompanionCgUrlCandidates,
} from "../sim/encounterAssetUrls";
import {
  loadGalleryUnlockSets,
  rewardTokenForRelPath,
  type GalleryUnlockSets,
} from "../save/galleryUnlock";
import {
  ENDINGS_BY_KEY,
  ENCOUNTERS,
  WHIM_BY_KEY,
  WHIM_ENCOUNTER_KEYS_ORDER,
} from "../sim/gameData";
import type { EncounterEnemyJson, EndingJson } from "../sim/types";
import galleryRewardRelPaths from "../sim/data/gallery_rewards.json";
import {
  GALLERY_FEMALE_ENDING_KEYS,
  GALLERY_HUB_ITEMS_ZH,
  GALLERY_MALE_ENDING_KEYS,
} from "../gallery/galleryConstants";
import {
  companionGalleryDescShort,
  encounterGalleryFooterBlob,
  rewardGalleryFooterSourceZh,
} from "../gallery/galleryFullscreenCaptions";
import { trimGalleryCaptionForOneLine, trimGalleryCaptionForTwoLines } from "../gallery/galleryLightboxCaption";
import { rewardDisplayNamesForRel } from "../gallery/rewardGalleryLabels";
import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import { syncWebBgmOpening } from "../audio/webBgm";
import { loadGameSave } from "../save/idbSave";
import { escapeHtml } from "./domHud";
import { mountEndingPagesFlow } from "./endingPagesHud";

const HUD_ID = "hud";
const PH_HIDE = "hud-gallery__ph--hide";

/** 畫廊列表每頁張數（對齊桌面單頁格數概念，改為橫向四格） */
const GALLERY_ITEMS_PER_PAGE = 4;

/** 未解鎖提示顯示時間（對齊桌面 `toast_until = now_ms + 2200`） */
const GALLERY_LOCKED_TOAST_MS = 2200;

/** 通關結局圖（男女）— 對齊桌面 Enter 未解鎖 */
const GALLERY_LOCKED_TOAST_ENDING_ZH = "尚未解鎖此通關 CG";

/** 遭遇強敵圖 — 對齊桌面 */
const GALLERY_LOCKED_TOAST_ENCOUNTER_ZH = "戰勝該敵後解鎖此 CG";

/** 同行夥伴（奇遇）— 對齊桌面 */
const GALLERY_LOCKED_TOAST_COMPANION_ZH = "尚未解鎖此夥伴 CG";

/** 獎勵組合圖 — 對齊桌面 */
const GALLERY_LOCKED_TOAST_REWARD_ZH =
  "尚未達成此格所列全部角色結局，解鎖後即可欣賞 CG";

/**
 * 顯示畫廊「尚未解鎖」提示（可點擊提前關閉）。
 *
 * @param hudEl - `#hud` 根節點
 * @param messageZh - 與桌面相同之說明句
 */
function showGalleryLockedToast(hudEl: HTMLElement, messageZh: string): void {
  hudEl.querySelectorAll(".hud-gallery-toast").forEach((n) => {
    n.remove();
  });
  const t = document.createElement("div");
  t.className = "hud-gallery-toast";
  t.setAttribute("role", "status");
  t.setAttribute("aria-live", "polite");
  t.innerHTML = `<p class="hud-gallery-toast__text">${escapeHtml(messageZh)}</p>`;
  hudEl.appendChild(t);
  requestAnimationFrame(() => {
    t.classList.add("hud-gallery-toast--visible");
  });
  const dismiss = (): void => {
    t.classList.remove("hud-gallery-toast--visible");
    window.setTimeout(() => {
      t.remove();
    }, 200);
  };
  const tid = window.setTimeout(dismiss, GALLERY_LOCKED_TOAST_MS);
  t.addEventListener(
    "click",
    () => {
      window.clearTimeout(tid);
      dismiss();
    },
    { once: true },
  );
}

/**
 * @returns HUD 根節點
 */
function hudRoot(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

type GalleryCellSpec = {
  /** 縮圖下標題 */
  label: string;
  /** 大圖／縮圖共用 URL 候選 */
  urls: readonly string[];
  /** 預覽底欄說明 */
  caption: string;
  /** 是否已解鎖（未解鎖顯示與桌面相同之叉叉格） */
  unlocked: boolean;
  /**
   * 通關結局格：有值時點擊走桌面同款「兩頁敘事＋一頁 CG」（見 `draw_gallery_ending_pages`）。
   */
  endingFull?: EndingJson;
};

/**
 * 展開畫廊 UI；返回主選單時呼叫 `onBackToMenu`。
 *
 * @param onBackToMenu - 關閉畫廊並還原主選單
 */
export function mountGalleryFlow(onBackToMenu: () => void): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  syncWebBgmOpening();
  renderHub(el, onBackToMenu);
  el.hidden = false;
}

/**
 * @param enemies - 遭遇戰敵方列表
 */
function allEncounterEnemiesSorted(enemies: EncounterEnemyJson[]): EncounterEnemyJson[] {
  const tierRank: Record<string, number> = { monster: 0, elite: 1, boss: 2 };
  return [...enemies].sort((a, b) => {
    const d = tierRank[a.tier]! - tierRank[b.tier]!;
    if (d !== 0) {
      return d;
    }
    return a.id.localeCompare(b.id);
  });
}

/**
 * 畫廊主選：五類以 2×3 網格排列（上列男女結局、中列夥伴／強敵、下列左獎勵、右留白）＋底欄「回主選單」。
 *
 * @param el - HUD 根
 * @param onBackToMenu - 回標題選單層級
 */
function renderHub(el: HTMLElement, onBackToMenu: () => void): void {
  const items = GALLERY_HUB_ITEMS_ZH.map(
    (label, i) => `
    <button type="button" class="hud-btn hud-btn--secondary hud-gallery-hub__item" data-hub="${i}">
      ${escapeHtml(label)}
    </button>`,
  ).join("");
  /** 右下空格，與 `data-hub` 0～4 之列順序對齊（橫屏手機較省垂直空間） */
  const gridSpacer = `<div class="hud-gallery-hub__grid-spacer" aria-hidden="true"></div>`;
  el.innerHTML = `
    <div class="hud-stack hud-stack--narrow hud-gallery hud-gallery--hub">
      <div class="hud-page-head">
        <p class="hud-line hud-title">圖片畫廊</p>
      </div>
      <div class="hud-gallery-hub__list hud-gallery-hub__list--grid" role="navigation" aria-label="畫廊分類">
        ${items}${gridSpacer}
      </div>
      <footer class="hud-gallery-hub__footer">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-hub__back" data-act="gallery-back-menu">回主選單</button>
      </footer>
    </div>
  `;
  el.querySelector('[data-act="gallery-back-menu"]')?.addEventListener("click", () => {
    onBackToMenu();
  });
  el.querySelectorAll<HTMLButtonElement>("[data-hub]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.hub);
      openHubSection(el, idx, onBackToMenu);
    });
  });
}

/**
 * @param el - HUD 根
 * @param hubIndex - 0～4 對齊桌面畫廊主選
 * @param onBackToMenu - 完全離開畫廊
 */
function openHubSection(el: HTMLElement, hubIndex: number, onBackToMenu: () => void): void {
  if (hubIndex === 0) {
    renderEndingSection(el, GALLERY_MALE_ENDING_KEYS, GALLERY_HUB_ITEMS_ZH[0]!, onBackToMenu);
    return;
  }
  if (hubIndex === 1) {
    renderEndingSection(el, GALLERY_FEMALE_ENDING_KEYS, GALLERY_HUB_ITEMS_ZH[1]!, onBackToMenu);
    return;
  }
  if (hubIndex === 2) {
    renderCompanionSection(el, onBackToMenu);
    return;
  }
  if (hubIndex === 3) {
    renderEncounterSection(el, onBackToMenu);
    return;
  }
  renderRewardSection(el, onBackToMenu);
}

/**
 * 結局 CG 網格（依桌面格位順序）。
 *
 * @param keys - 結局 slug 列表
 * @param title - 區塊標題
 * @param onBackToMenu - 離開畫廊
 */
function renderEndingSection(
  el: HTMLElement,
  keys: readonly string[],
  title: string,
  onBackToMenu: () => void,
): void {
  void loadGalleryUnlockSets().then((sets: GalleryUnlockSets) => {
    const specs: GalleryCellSpec[] = keys.map((key) => {
      const e: EndingJson | undefined = ENDINGS_BY_KEY.get(key);
      const name = e?.name ?? "？？？？";
      const cgPath = e?.cg_path ?? "";
      const urls = cgPath ? cgUrlCandidatesFromProjectPath(cgPath) : [];
      const cap = e ? `${e.name} — ${e.title}` : name;
      return {
        label: name,
        urls,
        caption: cap,
        unlocked: sets.endings.has(key),
        endingFull: e,
      };
    });
    mountGridShell(el, title, specs, () => renderHub(el, onBackToMenu), GALLERY_LOCKED_TOAST_ENDING_ZH);
  });
}

/**
 * 奇遇夥伴 CG。
 *
 * @param el - HUD 根
 * @param onBackToMenu - 離開畫廊
 */
function renderCompanionSection(el: HTMLElement, onBackToMenu: () => void): void {
  void loadGalleryUnlockSets().then((sets: GalleryUnlockSets) => {
    const specs: GalleryCellSpec[] = WHIM_ENCOUNTER_KEYS_ORDER.map((key) => {
      const w = WHIM_BY_KEY.get(key);
      const name = w?.display_name ?? key;
      const basename = w?.cg_basename ?? key;
      const urls = whimCompanionCgUrlCandidates(basename);
      const cap = w ? companionGalleryDescShort(w) : "奇遇場景；畫面依該格鍵再演繹，氛圍與旅路、魔法基調一致。";
      return { label: name, urls, caption: cap, unlocked: sets.whims.has(basename) };
    });
    mountGridShell(
      el,
      GALLERY_HUB_ITEMS_ZH[2]!,
      specs,
      () => renderHub(el, onBackToMenu),
      GALLERY_LOCKED_TOAST_COMPANION_ZH,
    );
  });
}

/**
 * 遭遇戰畫廊圖。
 *
 * @param el - HUD 根
 * @param onBackToMenu - 離開畫廊
 */
function renderEncounterSection(el: HTMLElement, onBackToMenu: () => void): void {
  void loadGalleryUnlockSets().then((sets: GalleryUnlockSets) => {
    const flat = allEncounterEnemiesSorted([
      ...ENCOUNTERS.monsters,
      ...ENCOUNTERS.elites,
      ...ENCOUNTERS.bosses,
    ]);
    const specs: GalleryCellSpec[] = flat.map((enemy) => {
      const canon = resolveEncounterIdForAssets(enemy.id);
      return {
        label: enemy.name_zh,
        urls: encounterGalleryImageUrlCandidates(enemy.id),
        caption: encounterGalleryFooterBlob(enemy),
        unlocked: sets.enemies.has(canon),
      };
    });
    mountGridShell(
      el,
      GALLERY_HUB_ITEMS_ZH[3]!,
      specs,
      () => renderHub(el, onBackToMenu),
      GALLERY_LOCKED_TOAST_ENCOUNTER_ZH,
    );
  });
}

/**
 * 獎勵組合 CG（路徑由 `gallery_rewards.reward_cg_tables` 掃描匯出）。
 *
 * @param el - HUD 根
 * @param onBackToMenu - 離開畫廊
 */
function renderRewardSection(el: HTMLElement, onBackToMenu: () => void): void {
  void loadGalleryUnlockSets().then((sets: GalleryUnlockSets) => {
    const paths = galleryRewardRelPaths as string[];
    const specs: GalleryCellSpec[] = paths.map((rel) => {
      const token = rewardTokenForRelPath(rel);
      const { label } = rewardDisplayNamesForRel(rel, token);
      const cap = rewardGalleryFooterSourceZh(rel, undefined, token ?? "");
      return {
        label,
        urls: cgUrlCandidatesFromProjectPath(rel),
        caption: cap,
        unlocked: token != null && sets.rewards.has(token),
      };
    });
    mountGridShell(
      el,
      GALLERY_HUB_ITEMS_ZH[4]!,
      specs,
      () => renderHub(el, onBackToMenu),
      GALLERY_LOCKED_TOAST_REWARD_ZH,
      true,
    );
  });
}

/**
 * 分頁網格：每頁四張橫圖、左上上一頁／右上下一頁、右下返回畫廊主選。
 *
 * @param el - HUD 根
 * @param title - 當前分類標題
 * @param specs - 格子資料
 * @param onBackHub - 回五類選單（「返回畫廊」）
 * @param lockedToastZh - 未解鎖格點擊時提示（與桌面 `toast_message` 一致）
 * @param lightboxRewardFraming - 為 True 時大圖略上移構圖（僅獎勵畫廊），使圖下方少被右下鈕遮擋
 */
function mountGridShell(
  el: HTMLElement,
  title: string,
  specs: readonly GalleryCellSpec[],
  onBackHub: () => void,
  lockedToastZh: string,
  lightboxRewardFraming = false,
): void {
  /** 本分類內所有已解鎖、可走大圖 lightbox 之格（跨網格頁連續上一張／下一張） */
  const navigableAll = specs.filter((s) => s.unlocked && !s.endingFull);
  const totalPages = Math.max(1, Math.ceil(specs.length / GALLERY_ITEMS_PER_PAGE));
  let pageIndex = 0;

  const renderPage = (): void => {
    const start = pageIndex * GALLERY_ITEMS_PER_PAGE;
    const slice = specs.slice(start, start + GALLERY_ITEMS_PER_PAGE);
    const cellsHtml = slice
      .map((s) => {
        const locked = !s.unlocked;
        const lockLayer = locked
          ? '<div class="hud-gallery-locked-cross" aria-hidden="true"></div>'
          : "";
        const capCls = locked ? " hud-gallery-caption--locked" : "";
        const cellCls = locked ? " hud-gallery-cell--locked" : "";
        const ariaDis = locked ? ' aria-disabled="true"' : "";
        return `
      <button type="button" class="hud-gallery-cell${cellCls}"${ariaDis}>
        <div class="hud-gallery-frame hud-gallery-frame--landscape">
          ${lockLayer}
          <img class="hud-gallery-thumb" alt="" decoding="async" />
          <div class="hud-gallery__ph">${escapeHtml(s.label)}</div>
        </div>
        <span class="hud-gallery-caption${capCls}">${escapeHtml(s.label)}</span>
      </button>`;
      })
      .join("");
    const pageInline =
      totalPages > 1
        ? `<span class="hud-gallery-paged__hint-inline" aria-hidden="true">　${pageIndex + 1} / ${totalPages}</span>`
        : "";
    el.innerHTML = `
    <div class="hud-gallery hud-gallery--grid hud-gallery--paged">
      <header class="hud-gallery-paged__bar" aria-label="畫廊導覽">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn" data-act="gallery-prev"${
          pageIndex <= 0 ? " disabled" : ""
        }>上一頁</button>
        <div class="hud-gallery-paged__title-wrap">
          <p class="hud-line hud-title hud-gallery-paged__title">${escapeHtml(title)}${pageInline}</p>
        </div>
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn" data-act="gallery-next"${
          pageIndex >= totalPages - 1 ? " disabled" : ""
        }>下一頁</button>
      </header>
      <div class="hud-gallery-grid hud-gallery-grid--paged-landscape" role="list">${cellsHtml}</div>
      <footer class="hud-gallery-paged__footer">
        <button type="button" class="hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-gallery-paged__back" data-act="gallery-back-hub">返回畫廊</button>
      </footer>
    </div>
  `;
    el.querySelector('[data-act="gallery-back-hub"]')?.addEventListener("click", onBackHub);
    el.querySelector('[data-act="gallery-prev"]')?.addEventListener("click", () => {
      if (pageIndex > 0) {
        pageIndex -= 1;
        renderPage();
      }
    });
    el.querySelector('[data-act="gallery-next"]')?.addEventListener("click", () => {
      if (pageIndex < totalPages - 1) {
        pageIndex += 1;
        renderPage();
      }
    });
    const buttons = el.querySelectorAll<HTMLButtonElement>(".hud-gallery-cell");
    buttons.forEach((btn, i) => {
      const spec = slice[i];
      if (!spec) {
        return;
      }
      if (!spec.unlocked) {
        btn.addEventListener("click", () => {
          showGalleryLockedToast(el, lockedToastZh);
        });
        return;
      }
      const img = btn.querySelector<HTMLImageElement>(".hud-gallery-thumb");
      const ph = btn.querySelector<HTMLElement>(".hud-gallery__ph");
      if (img && spec.urls.length > 0) {
        wireImageFallbackChain(img, spec.urls, ph, PH_HIDE);
      }
      btn.addEventListener("click", () => {
        if (spec.endingFull) {
          openEndingGalleryOverlay(el, spec.endingFull);
        } else {
          const pos = navigableAll.indexOf(spec);
          openLightbox(el, navigableAll, pos >= 0 ? pos : 0, lightboxRewardFraming);
        }
      });
    });
  };

  renderPage();
}

/**
 * 通關結局格：敘事頁＋CG 頁（對齊桌面 `draw_gallery_ending_pages`），覆蓋於縮圖網格之上。
 *
 * @param el - `#hud`
 * @param ending - 結局資料
 */
function openEndingGalleryOverlay(el: HTMLElement, ending: EndingJson): void {
  const overlay = document.createElement("div");
  overlay.className = "hud-gallery-ending-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.innerHTML = `<div class="hud-gallery-ending-overlay__panel"></div>`;
  const panel = overlay.querySelector<HTMLElement>(".hud-gallery-ending-overlay__panel");
  if (!panel) {
    return;
  }
  el.appendChild(overlay);
  mountEndingPagesFlow(panel, ending, "gallery", () => {
    overlay.remove();
  });
}

/**
 * 大圖預覽：圖頂「上一頁／下一頁」、圖區右下「關閉」（同 nav-pill 樣式）；底欄說明經量測收在約定行數內（夥伴／強敵兩行、獎勵一行；超過才截，並去掉尾端弱句讀）。
 *
 * @param el - HUD 根
 * @param navigable - 本分類內可走 lightbox 之已解鎖格（不含結局全螢幕格）
 * @param startIndex - 起始索引
 * @param rewardFraming - 獎勵大圖：略上移構圖，使圖下方多露出一截、少被右下「關閉」遮擋
 */
function openLightbox(
  el: HTMLElement,
  navigable: readonly GalleryCellSpec[],
  startIndex: number,
  rewardFraming = false,
): void {
  if (navigable.length === 0) {
    return;
  }
  let idx = Math.max(0, Math.min(startIndex, navigable.length - 1));

  const closeLb = (): void => {
    el.querySelector(".hud-gallery-lightbox")?.remove();
    document.removeEventListener("keydown", onKey);
  };

  const onKey = (ev: KeyboardEvent): void => {
    if (ev.key === "Escape") {
      closeLb();
      return;
    }
    if (ev.key === "ArrowLeft" && idx > 0) {
      ev.preventDefault();
      idx -= 1;
      paint();
      return;
    }
    if (ev.key === "ArrowRight" && idx < navigable.length - 1) {
      ev.preventDefault();
      idx += 1;
      paint();
    }
  };

  const wrap = document.createElement("div");
  wrap.className = rewardFraming ? "hud-gallery-lightbox hud-gallery-lightbox--reward" : "hud-gallery-lightbox";
  wrap.setAttribute("role", "dialog");
  wrap.setAttribute("aria-modal", "true");
  const navHidden = navigable.length <= 1 ? " hud-gallery-lightbox__overlay-top--hidden" : "";
  wrap.innerHTML = `
    <div class="hud-gallery-lightbox__backdrop" data-close="1"></div>
    <div class="hud-gallery-lightbox__panel">
      <div class="hud-gallery-lightbox__frame">
        <img class="hud-gallery-lightbox__img" alt="" decoding="async" />
        <div class="hud-gallery__ph hud-gallery-lightbox__ph">無圖或載入失敗</div>
        <div class="hud-gallery-lightbox__overlay-top${navHidden}" aria-label="大圖換張">
          <button type="button" class="hud-gallery-lightbox__nav-pill" data-act="lb-prev">上一頁</button>
          <button type="button" class="hud-gallery-lightbox__nav-pill" data-act="lb-next">下一頁</button>
        </div>
        <button type="button" class="hud-gallery-lightbox__nav-pill hud-gallery-lightbox__nav-pill--br" data-close="1">關閉</button>
      </div>
      <div class="hud-gallery-lightbox__footer">
        <p class="hud-gallery-lightbox__cap"></p>
      </div>
    </div>
  `;
  el.appendChild(wrap);

  const img = wrap.querySelector<HTMLImageElement>(".hud-gallery-lightbox__img");
  const ph = wrap.querySelector<HTMLElement>(".hud-gallery-lightbox__ph");
  const cap = wrap.querySelector<HTMLElement>(".hud-gallery-lightbox__cap");
  const btnPrev = wrap.querySelector<HTMLButtonElement>('[data-act="lb-prev"]');
  const btnNext = wrap.querySelector<HTMLButtonElement>('[data-act="lb-next"]');

  const paint = (): void => {
    const spec = navigable[idx]!;
    if (cap) {
      const fullCap = spec.caption;
      cap.textContent = fullCap;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (!wrap.isConnected || !cap.isConnected) {
            return;
          }
          if (cap.clientWidth <= 0) {
            cap.textContent = fullCap;
            return;
          }
          cap.textContent = rewardFraming
            ? trimGalleryCaptionForOneLine(cap, fullCap)
            : trimGalleryCaptionForTwoLines(cap, fullCap);
        });
      });
    }
    if (img && ph) {
      if (spec.urls.length > 0) {
        img.style.display = "";
        ph.classList.remove(PH_HIDE);
        ph.textContent = "無圖或載入失敗";
        wireImageFallbackChain(img, spec.urls, ph, PH_HIDE);
      } else {
        img.removeAttribute("src");
        img.style.display = "none";
        ph.classList.remove(PH_HIDE);
        ph.textContent = "無圖或載入失敗";
      }
    }
    if (btnPrev) {
      btnPrev.disabled = idx <= 0;
    }
    if (btnNext) {
      btnNext.disabled = idx >= navigable.length - 1;
    }
  };

  btnPrev?.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (idx > 0) {
      idx -= 1;
      paint();
    }
  });
  btnNext?.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (idx < navigable.length - 1) {
      idx += 1;
      paint();
    }
  });

  wrap.querySelectorAll("[data-close]").forEach((n) => {
    n.addEventListener("click", () => {
      closeLb();
    });
  });
  document.addEventListener("keydown", onKey);
  paint();
}
