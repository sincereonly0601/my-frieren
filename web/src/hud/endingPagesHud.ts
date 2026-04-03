/**
 * 結局多頁瀏覽：敘事頁 0…n-1，接一頁全幅 CG（對齊桌面 `_ending_cg_page_index`／`draw_ending_cg_screen`）。
 */

import { syncWebBgmEnding, syncWebBgmOpening } from "../audio/webBgm";
import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import { cgUrlCandidatesFromProjectPath } from "../sim/encounterAssetUrls";
import type { EndingJson } from "../sim/types";
import { escapeHtml } from "./domHud";

const PH_HIDE = "hud-gallery__ph--hide";

export type EndingPagesMode = "play" | "gallery";

/**
 * 掛載結局翻頁：可鍵盤左右／Enter（僅在 CG 頁確認結束）；回傳中止函式（不觸發 onComplete）。
 *
 * @param host - 內容寫入此節點（通關時為 `#hud`；畫廊時為覆蓋層內之面板）
 * @param ending - 結局資料
 * @param mode - 通關或畫廊（版型皆同畫廊；敘事末頁亦為「下一頁」、CG 末頁「返回畫廊」）
 * @param onComplete - CG 頁按「結束」或 Enter 時呼叫
 * @returns 中止（例如畫廊關閉鈕），不呼叫 onComplete
 */
export function mountEndingPagesFlow(
  host: HTMLElement,
  ending: EndingJson,
  mode: EndingPagesMode,
  onComplete: () => void,
): () => void {
  if (mode === "gallery") {
    syncWebBgmOpening();
  } else {
    syncWebBgmEnding();
  }
  let page = 0;
  const cgIdx = ending.narrative_pages.length;
  const isGallery = mode === "gallery";
  const doneLabel = isGallery ? "返回畫廊" : "結束";
  /** 單行標題：人名 · 副標題（畫廊通關結局與桌面敘事抬頭對齊） */
  const headingOneLine = `${escapeHtml(ending.name)} · ${escapeHtml(ending.title)}`;

  let disposed = false;

  const teardown = (): void => {
    if (disposed) {
      return;
    }
    disposed = true;
    document.removeEventListener("keydown", onKeyDown);
  };

  const finish = (): void => {
    if (disposed) {
      return;
    }
    teardown();
    onComplete();
  };

  const onKeyDown = (ev: KeyboardEvent): void => {
    if (disposed) {
      return;
    }
    if (ev.key === "ArrowLeft") {
      ev.preventDefault();
      page = Math.max(0, page - 1);
      render();
      return;
    }
    if (ev.key === "ArrowRight") {
      ev.preventDefault();
      page = Math.min(cgIdx, page + 1);
      render();
      return;
    }
    if (ev.key === "Enter") {
      if (page === cgIdx) {
        ev.preventDefault();
        finish();
      }
    }
    if (isGallery && ev.key === "Escape") {
      ev.preventDefault();
      finish();
    }
  };

  /** 通關與畫廊共用「通關結局」版型（對齊圖片畫廊敘事／CG 版面）。 */
  const galleryRootClass = " hud-ending-pages--gallery";
  const navRowClass =
    "hud-actions hud-actions--event hud-ending-pages__row hud-ending-pages__row--gallery-corners";
  const prevBtnClass =
    "hud-btn hud-btn--secondary hud-gallery-paged__corner-btn hud-ending-pages__nav-btn";
  const fwdBtnClass = "hud-btn hud-gallery-paged__corner-btn hud-ending-pages__nav-btn";

  const render = (): void => {
    if (disposed) {
      return;
    }
    if (page < cgIdx) {
      const text = ending.narrative_pages[page] ?? "";
      const isLastNarrative = page === cgIdx - 1;
      const nextLabel = isGallery ? "下一頁" : isLastNarrative ? "進入 CG" : "下一頁";
      const titleBlock = `<div class="hud-ending-pages__sticky-head"><p class="hud-line hud-title hud-event-body-title hud-ending-pages__title-line">${headingOneLine}</p></div>`;
      host.innerHTML = `
        <div class="hud-ending-pages hud-ending-pages--narrative hud-event-body hud-event-body--spaced${galleryRootClass}">
          <div class="hud-event-body__inner hud-stack hud-stack--wide">
            ${titleBlock}
            <p class="hud-line hud-sub hud-sub--wrap hud-event-body-text">${escapeHtml(text)}</p>
            <div class="${navRowClass}">
              <button type="button" class="${prevBtnClass}" data-act="prev"${page <= 0 ? " disabled" : ""}>上一頁</button>
              <button type="button" class="${fwdBtnClass}" data-act="next">${escapeHtml(nextLabel)}</button>
            </div>
          </div>
        </div>
      `;
      host.querySelector('[data-act="prev"]')?.addEventListener("click", () => {
        if (page > 0) {
          page -= 1;
          render();
        }
      });
      host.querySelector('[data-act="next"]')?.addEventListener("click", () => {
        page += 1;
        render();
      });
    } else {
      const urls = cgUrlCandidatesFromProjectPath(ending.cg_path);
      const galleryCgOverlayNav = `<div class="hud-ending-cg__overlay-bottom" aria-label="CG 導覽">
            <button type="button" class="hud-btn hud-btn--secondary hud-ending-cg__overlay-pill" data-act="prev"${
              cgIdx <= 0 ? " disabled" : ""
            }>上一頁</button>
            <button type="button" class="hud-btn hud-btn--secondary hud-ending-cg__overlay-pill" data-act="done">${escapeHtml(
              doneLabel,
            )}</button>
          </div>`;
      const cgFrameCls = "hud-ending-cg__frame hud-ending-cg__frame--gallery-overlay-nav";
      const quoteCls =
        "hud-line hud-sub hud-sub--wrap hud-ending-quote hud-ending-cg__quote hud-ending-cg__quote--gallery";
      host.innerHTML = `
        <div class="hud-ending-pages hud-ending-pages--cg${galleryRootClass}">
          <div class="${cgFrameCls}">
            <img class="hud-ending-cg__img" alt="" decoding="async" />
            <div class="hud-gallery__ph hud-ending-cg__ph">無法載入 CG</div>
            ${galleryCgOverlayNav}
          </div>
          <div class="hud-ending-cg__bar hud-ending-cg__bar--gallery">
            <p class="${quoteCls}"><span class="hud-ending-cg__quote-attribution">${escapeHtml(ending.name)}：</span>「${escapeHtml(ending.quote)}」</p>
          </div>
        </div>
      `;
      const img = host.querySelector<HTMLImageElement>(".hud-ending-cg__img");
      const ph = host.querySelector<HTMLElement>(".hud-ending-cg__ph");
      if (img && urls.length > 0) {
        wireImageFallbackChain(img, urls, ph, PH_HIDE);
      } else if (ph) {
        ph.textContent = "無 CG 路徑";
      }
      host.querySelector('[data-act="prev"]')?.addEventListener("click", () => {
        if (cgIdx > 0) {
          page = cgIdx - 1;
          render();
        }
      });
      host.querySelector('[data-act="done"]')?.addEventListener("click", () => {
        finish();
      });
    }
  };

  document.addEventListener("keydown", onKeyDown);
  render();

  return (): void => {
    teardown();
  };
}
