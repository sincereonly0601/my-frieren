/**
 * 遭遇戰：自動播映交鋒記錄、雙血條、左右 CG 與面板數值；結束後進入餘韻（敘事＋數值）。
 */

import { syncWebBgmMajor } from "../audio/webBgm";
import type { GameStateStored } from "../save/idbSave";
import type { BattleOutcome } from "../sim/encounterSim";
import type { EncounterEnemyJson } from "../sim/types";
import {
  encounterBattleImageUrlCandidates,
  encounterBattleModeTitleZh,
  heroinePortraitUrlCandidates,
} from "../sim/encounterAssetUrls";
import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import { adjustProtagonistPronounZh } from "./eventAlertCopy";
import { escapeHtml } from "./domHud";
import { formatMergedDeltasLineZh } from "./formatEventDeltas";

/** 與桌面 `ENCOUNTER_BATTLE_TICKS_PER_STEP`＋約 60fps 相近之影格間隔 */
const MS_PER_BATTLE_FRAME = 530;

/**
 * 遭遇戰餘韻內文（打贏）：單段連續文字，於現有版型下約四行；有起承轉合，不以刪節號結尾。
 * 使用「妳」；男性主角時由 {@link adjustProtagonistPronounZh} 轉為「你」。
 */
const ENCOUNTER_AFTERMATH_MERGED_BODY_WIN_ZH =
  "妳收束氣息，把傷勢與得失一併收進心底。這一勝來得並不輕鬆，卻讓界線更清楚。戰場上的聲響退去，妳仍記得交手時的力度與節奏。妳重新站穩腳步，明白這只是途中一站，往後每一步仍要審慎以對，不敢鬆懈。";

/**
 * 遭遇戰餘韻內文（打輸）：單段、約四行、有頭有尾，不以刪節號結尾。
 * 使用「妳」；男性主角時由 {@link adjustProtagonistPronounZh} 轉為「你」。
 */
const ENCOUNTER_AFTERMATH_MERGED_BODY_LOSE_ZH =
  "妳承認這一仗沒能討好，身體的回饋比語言更直白。敗北未將妳擊垮，反而讓該守的界線浮現。妳撐住腳步調整呼吸，把狼狽與不甘仔細收好。心裡重新對準方向，妳知道下一步仍要從穩住自己開始，慢慢找回節奏。";

/** 遭遇戰占位隱藏 class（傳入 {@link wireImageFallbackChain}） */
const ENCOUNTER_CG_PH_HIDE = "hud-encounter-battle__cgph--hide";

/**
 * 交鋒記錄顯示用：移除句尾全形句號（資料內可保留，畫面上不顯示）。
 *
 * @param line - 單列台詞
 * @returns 供 escape 前套用之字串
 */
function encounterLogLineForDisplay(line: string): string {
  let t = line.trimEnd();
  while (t.endsWith("。")) {
    t = t.slice(0, -1);
  }
  return t;
}

export type EncounterBattleContext = {
  game: GameStateStored;
  enemy: EncounterEnemyJson;
  outcome: BattleOutcome;
};

/**
 * 繪製遭遇戰播映與餘韻；結束時呼叫 `onDone`（由外層套用存檔與鏈式事件）。
 *
 * @param el - `#hud`
 * @param ctx - 狀態與模擬結果
 * @param onDone - 餘韻「返回培養」後
 */
export function mountEncounterBattleFlow(
  el: HTMLElement,
  ctx: EncounterBattleContext,
  onDone: () => void,
): void {
  syncWebBgmMajor();
  const { game, enemy, outcome } = ctx;
  const frames = outcome.frames;
  const heroName = (game.heroine_name ?? "").trim() || "……";
  const phase = game.phase;
  const gender = game.protagonist_gender;
  const modeTitle = encounterBattleModeTitleZh(enemy.tier);

  let frameIdx = 0;
  let timer: ReturnType<typeof setInterval> | null = null;
  let onLastFrame = false;

  const clearTimer = (): void => {
    if (timer != null) {
      clearInterval(timer);
      timer = null;
    }
  };

  const renderFrame = (): void => {
    const fi = Math.max(0, Math.min(frameIdx, frames.length - 1));
    const fr = frames[fi]!;
    /**
     * 開戰第一影格；側欄「生命」僅顯示初始數值（單一數字），與頂條即時血量分開。
     */
    const frInitial = frames[0] ?? fr;
    const pPct =
      fr.player_hp_max <= 0 ? 0 : Math.max(0, Math.min(100, (100 * fr.player_hp) / fr.player_hp_max));
    const ePct =
      fr.enemy_hp_max <= 0 ? 0 : Math.max(0, Math.min(100, (100 * fr.enemy_hp) / fr.enemy_hp_max));

    const diaryLines = frames.slice(0, fi + 1).map((f) => f.banner_zh);
    const diaryHtml = diaryLines
      .map(
        (line) =>
          `<p class="hud-encounter-log__line">${escapeHtml(encounterLogLineForDisplay(line))}</p>`,
      )
      .join("");

    const atEnd = fi >= frames.length - 1;
    const hint = atEnd ? "點擊畫面進入餘韻" : "交鋒自動播映中…";

    el.innerHTML = `
      <div class="hud-encounter-battle" role="dialog" aria-modal="true">
        <header class="hud-encounter-battle__head">
          <p class="hud-encounter-battle__mode">${escapeHtml(modeTitle)}　${escapeHtml(enemy.name_zh)}</p>
        </header>
        <div class="hud-encounter-battle__bars">
          <div class="hud-encounter-hp hud-encounter-hp--player">
            <div class="hud-encounter-hp__label">${escapeHtml(heroName)}　${fr.player_hp}/${fr.player_hp_max}</div>
            <div class="hud-encounter-hp__track" role="progressbar" aria-valuemin="0" aria-valuemax="${fr.player_hp_max}" aria-valuenow="${fr.player_hp}">
              <div class="hud-encounter-hp__fill hud-encounter-hp__fill--player" style="width:${pPct}%"></div>
            </div>
          </div>
          <div class="hud-encounter-hp hud-encounter-hp--enemy">
            <div class="hud-encounter-hp__label">${fr.enemy_hp}/${fr.enemy_hp_max}　${escapeHtml(enemy.name_zh)}</div>
            <div class="hud-encounter-hp__track" role="progressbar" aria-valuemin="0" aria-valuemax="${fr.enemy_hp_max}" aria-valuenow="${fr.enemy_hp}">
              <div class="hud-encounter-hp__fill hud-encounter-hp__fill--enemy" style="width:${ePct}%"></div>
            </div>
          </div>
        </div>
        <div class="hud-encounter-battle__main">
          <aside class="hud-encounter-battle__side hud-encounter-battle__side--left">
            <div class="hud-encounter-battle__cgframe">
              <img class="hud-encounter-battle__cgimg" data-role="hero-cg" alt="" />
              <div class="hud-encounter-battle__cgph" data-role="hero-ph">主角立繪</div>
            </div>
            <ul class="hud-encounter-battle__stats">
              <li>生命　${frInitial.player_hp}</li>
              <li>戰鬥　${outcome.player_atk}</li>
              <li>防禦　${outcome.player_def}</li>
            </ul>
          </aside>
          <section class="hud-encounter-battle__log" aria-label="交鋒記錄">
            <p class="hud-encounter-log__title">交鋒記錄</p>
            <div class="hud-encounter-log__scroll">${diaryHtml}</div>
          </section>
          <aside class="hud-encounter-battle__side hud-encounter-battle__side--right">
            <div class="hud-encounter-battle__cgframe">
              <img class="hud-encounter-battle__cgimg" data-role="enemy-cg" alt="" />
              <div class="hud-encounter-battle__cgph" data-role="enemy-ph">${escapeHtml(enemy.name_zh)}</div>
            </div>
            <ul class="hud-encounter-battle__stats">
              <li>${frInitial.enemy_hp}　生命</li>
              <li>${outcome.enemy_atk}　戰鬥</li>
              <li>${outcome.enemy_def}　防禦</li>
            </ul>
          </aside>
        </div>
        <footer class="hud-encounter-battle__footer">
          <p class="hud-encounter-battle__hint">${escapeHtml(hint)}</p>
        </footer>
      </div>
    `;

    const heroImg = el.querySelector<HTMLImageElement>('[data-role="hero-cg"]');
    const enemyImg = el.querySelector<HTMLImageElement>('[data-role="enemy-cg"]');
    const heroPh = el.querySelector<HTMLElement>("[data-role='hero-ph']");
    const enemyPh = el.querySelector<HTMLElement>("[data-role='enemy-ph']");
    if (heroImg) {
      wireImageFallbackChain(
        heroImg,
        heroinePortraitUrlCandidates(phase, gender),
        heroPh,
        ENCOUNTER_CG_PH_HIDE,
      );
    }
    if (enemyImg) {
      wireImageFallbackChain(
        enemyImg,
        encounterBattleImageUrlCandidates(enemy.id),
        enemyPh,
        ENCOUNTER_CG_PH_HIDE,
      );
    }

    const logScroll = el.querySelector(".hud-encounter-log__scroll");
    if (logScroll) {
      logScroll.scrollTop = logScroll.scrollHeight;
    }

    const battleRoot = el.querySelector(".hud-encounter-battle");
    if (atEnd && onLastFrame) {
      battleRoot?.classList.add("hud-encounter-battle--await-tap");
      battleRoot?.addEventListener(
        "click",
        () => {
          clearTimer();
          showAftermath();
        },
        { once: true },
      );
    }
  };

  const showAftermath = (): void => {
    clearTimer();
    const win = outcome.win;
    const mergedLoreRaw = win ? ENCOUNTER_AFTERMATH_MERGED_BODY_WIN_ZH : ENCOUNTER_AFTERMATH_MERGED_BODY_LOSE_ZH;
    const mergedLore = adjustProtagonistPronounZh(mergedLoreRaw, gender);

    const hasTreasure = win && Object.keys(outcome.treasure_deltas).length > 0;
    const tn = (enemy.treasure_name_zh ?? "").trim();
    let headFirst: string;
    if (win) {
      headFirst = tn
        ? `戰勝對象：${enemy.name_zh}　　　　　獲得寶物：${tn}`
        : `戰勝對象：${enemy.name_zh}${hasTreasure ? "　獲得寶物" : ""}`;
    } else {
      headFirst = `敗北：${enemy.name_zh}`;
    }

    const statLineCore =
      win && hasTreasure
        ? formatMergedDeltasLineZh(outcome.participation_deltas, outcome.treasure_deltas)
        : formatMergedDeltasLineZh(outcome.participation_deltas);
    const statPrefix = win && hasTreasure ? "本段數值+寶物加成：" : "本段數值：";
    const dockDelta = escapeHtml(statPrefix + statLineCore);

    const aftermathTitle = "遭遇戰　餘韻判讀";
    const headWinLose = win ? "hud-encounter-aftermath__head--win" : "hud-encounter-aftermath__head--lose";
    const bodyHtml = [
      `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para hud-encounter-aftermath__head ${headWinLose}">${escapeHtml(headFirst)}</p>`,
      `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para">${escapeHtml(mergedLore)}</p>`,
    ].join("");

    el.innerHTML = `
      <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result hud-stack--incident-aftermath-result hud-stack--encounter-aftermath">
        <div class="hud-page-head">
          <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">${escapeHtml(aftermathTitle)}</p>
        </div>
        <div class="hud-adopter-result-body">
          ${bodyHtml}
        </div>
        <div class="hud-adopter-result-footer">
          <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-stat" aria-label="數值變化">${dockDelta}</p>
          <div class="hud-actions hud-actions--adopter-result">
            <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn hud-btn--adopter-continue" data-act="done">返回培養</button>
          </div>
        </div>
      </div>
    `;
    el.querySelector('[data-act="done"]')?.addEventListener("click", () => {
      onDone();
    });
  };

  el.hidden = false;

  if (frames.length <= 1) {
    frameIdx = 0;
    onLastFrame = true;
    renderFrame();
  } else {
    renderFrame();
    timer = setInterval(() => {
      if (frameIdx < frames.length - 1) {
        frameIdx += 1;
        renderFrame();
      } else {
        onLastFrame = true;
        clearTimer();
        renderFrame();
      }
    }, MS_PER_BATTLE_FRAME);
  }
}
