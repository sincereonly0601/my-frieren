/**
 * 培養途中攔截事件：重大／突發／遭遇／奇遇／結局（DOM 疊加於 Phaser 上）。
 */

import { syncWebBgmEventAlert } from "../audio/webBgm";
import type { GameStateStored, WebMiniPhase } from "../save/idbSave";
import type { BattleOutcome } from "../sim/encounterSim";
import type { EncounterEnemyJson, EndingJson, IncidentEventJson, WhimEncounterJson } from "../sim/types";
import type { WhimQuestionJson } from "../sim/types";
import { escapeHtml } from "./domHud";
import { mountEndingPagesFlow } from "./endingPagesHud";
import { mountEncounterBattleFlow } from "./encounterBattleSequence";
import { adjustProtagonistPronounZh, getEventAlertCopy, type EventAlertKind } from "./eventAlertCopy";
import { formatMergedDeltasLineZh } from "./formatEventDeltas";
import { finalizeNarrativeZhParagraph } from "./zhParagraphClamp";
import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import { INCIDENT_AFTERMATH_BY_ID, MAJOR_BY_AGE } from "../sim/gameData";
import { whimCompanionCgUrlCandidates } from "../sim/encounterAssetUrls";

const HUD_ID = "hud";
const INCIDENT_AFTERMATH_MIN_CHARS_PER_PARA = 44;
/** 突發事件選擇頁題幹：約兩行；與 `hud-incident-quiz-prompt--twoline`（高度裁切、不用 line-clamp 省略號）併用。 */
const INCIDENT_BODY_PROMPT_MIN_CHARS = 36;
const INCIDENT_BODY_PROMPT_MAX_CHARS = 44;
/** 奇遇第一頁右欄本文：約 5 行；與資料 `preamble_para1` 濃縮字量對齊（不足略補、過長截斷不加「…」）。 */
const WHIM_INTRO1_BODY_MIN_CHARS = 100;
const WHIM_INTRO1_BODY_MAX_CHARS = 100;
/** 奇遇第二頁：第一段約 3 行、第二段（對話）約 2 行；與資料濃縮字量對齊（min=max，截斷不加「…」）。 */
const WHIM_INTRO2_FIRST_MIN_CHARS = 90;
const WHIM_INTRO2_FIRST_MAX_CHARS = 90;
const WHIM_INTRO2_SECOND_MIN_CHARS = 56;
const WHIM_INTRO2_SECOND_MAX_CHARS = 56;
/** 奇遇餘韻（第四頁）：兩段各約 2 行；與資料濃縮字量對齊（min=max，截斷不加「…」）。 */
const WHIM_AFTERMATH_PARA_MIN_CHARS = 56;
const WHIM_AFTERMATH_PARA_MAX_CHARS = 56;

/**
 * 重大事件前言單頁：正文五行。奇遇第一頁右欄較窄故用 100 字；重大前言為全寬 `40em`，約每行 36 字，需約 180 字才滿五行。
 */
const MAJOR_PREAMBLE_MERGED_MIN_CHARS = 180;
const MAJOR_PREAMBLE_MERGED_MAX_CHARS = 180;
/** 重大事件選擇題幹：兩行視覺列（與 `hud-whim-clamp--2`、資料 `choice_prompt_zh` 字量對齊）。 */
const MAJOR_CHOICE_PROMPT_MIN_CHARS = 56;
const MAJOR_CHOICE_PROMPT_MAX_CHARS = 56;
/** 重大事件餘韻合併段：在問卷判讀寬欄（約 `580px`）下約四行；字量高於舊版以避免寬螢幕只折成三行。 */
const MAJOR_AFTERMATH_MERGED_MIN_CHARS = 144;
const MAJOR_AFTERMATH_MERGED_MAX_CHARS = 144;

/** 重大事件前言合併段補句（資料不足 {@link MAJOR_PREAMBLE_MERGED_MIN_CHARS} 時依序接上）。 */
const MAJOR_MERGED_PAD: readonly string[] = [
  "你把腳步放慢，讓敘事在心裡落位。",
  "你知道這一刻會跟著選擇走很久。",
  "遠處的聲音變小，眼前的路卻更清楚。",
  "你讓呼吸穩下來，預備承擔下一步。",
];

/** 重大事件餘韻合併段補句。 */
const MAJOR_AFTERMATH_PAD: readonly string[] = [
  "你把這一步的重量收好，預備回到日常裡慢慢消化。",
  "回頭看時，這條路仍會在你心裡發聲。",
  "你知道成長常從這種餘味開始，慢慢變成下一步的把握。",
  "遠方的風向與近處的腳步一齊改寫，你仍試著把句子說完整。",
  "回到培養節奏後，這件事仍會在安靜時回來敲門。",
  "你把當時的心跳與遲疑一併收進記憶裡，預備走下一步。",
];

/** 突發事件題幹補句（短句，避免補滿後超出兩行可視高度）。 */
const INCIDENT_BODY_PROMPT_PAD: readonly string[] = [
  "妳得選一條能承擔的路。",
  "妳把局面看清楚再表態。",
  "沒有人替妳代答。",
  "這一步會跟著妳走一段。",
  "妳不打算敷衍帶過。",
];

/** 補字句用盡後仍不足時輪替接上，確保所有奇遇都達標。 */
const WHIM_GENERIC_PAD_SENTENCES: readonly string[] = [
  "你仍把這一刻收進眼底。",
  "故事還在繼續，只是腳步更清楚了。",
  "你讓呼吸慢下來，把思緒整理成接下來能走的路。",
  "遠處的聲音變小，眼前的選擇卻更清楚。",
  "你知道這不是結尾，而是下一個起點的門檻。",
];

/**
 * 將段落補到至少 `minChars`（連續文字，不插入硬換行）。
 *
 * @param text - 原始段落
 * @param minChars - 目標最小字數
 * @param fallback - 空字串時替換句
 * @param additions - 依序接上的補句
 * @returns 補齊後段落
 */
function padZhParagraphToMinLength(
  text: string,
  minChars: number,
  fallback: string,
  additions: readonly string[],
): string {
  const trimmed = text.trim();
  if (trimmed.length >= minChars) {
    return trimmed;
  }
  let out = trimmed.length > 0 ? trimmed : fallback;
  for (const add of additions) {
    if (out.length >= minChars) {
      break;
    }
    const needsPunct = !/[。！？]$/.test(out);
    out += `${needsPunct ? "。" : ""}${add}`;
  }
  let gi = 0;
  while (out.length < minChars && gi < 48) {
    const add = WHIM_GENERIC_PAD_SENTENCES[gi % WHIM_GENERIC_PAD_SENTENCES.length]!;
    const needsPunct = !/[。！？]$/.test(out);
    out += `${needsPunct ? "。" : ""}${add}`;
    gi++;
  }
  return out;
}

/**
 * 奇遇測驗題幹：移除全形「【」「】」與外層括號，供第三頁顯示。
 *
 * @param stem - 題目原文
 * @returns 顯示用文字
 */
function whimQuizStemDisplayZh(stem: string): string {
  return stem
    .trim()
    .replace(/^[【\s]+/, "")
    .replace(/[】\s]+$/, "")
    .replace(/[【】]/g, "")
    .trim();
}

/**
 * 突發事件選擇頁題幹：補足／截斷至約兩行（連續文字、截斷不加刪節號）。
 *
 * @param raw - `incident.body`
 * @returns 供顯示用之題幹
 */
function padIncidentBodyPromptZh(raw: string): string {
  const fallback = "局面逼妳表態，無人代答；妳看清細節再選能承擔的路。";
  const padded = padZhParagraphToMinLength(
    raw.trim(),
    INCIDENT_BODY_PROMPT_MIN_CHARS,
    fallback,
    INCIDENT_BODY_PROMPT_PAD,
  );
  return finalizeNarrativeZhParagraph(padded, INCIDENT_BODY_PROMPT_MAX_CHARS);
}

/**
 * 將突發事件餘韻段落補到約兩行字量（連續文字，不插入硬換行）。
 *
 * @param text - 原始段落
 * @param paraIndex - 段落序（0: 第一段；1: 第二段）
 * @returns 補字後段落
 */
function padIncidentAftermathParagraphZh(text: string, paraIndex: 0 | 1): string {
  const trimmed = text.trim();
  if (trimmed.length >= INCIDENT_AFTERMATH_MIN_CHARS_PER_PARA) {
    return trimmed;
  }
  const fallback = paraIndex === 0 ? "你把這一刻牢牢記住。" : "這次抉擇也成了往後行路的刻痕。";
  const additions =
    paraIndex === 0
      ? [
          "那一瞬間你知道，眼前的取捨不會只停在當下。",
          "你把當時的心跳與遲疑一起收進記憶裡。",
          "回頭看時，這一步仍有重量。",
        ]
      : [
          "回到日常後，這件事仍在心裡慢慢發酵。",
          "它提醒你，往後每一步都要更清楚地選擇。",
          "你明白成長常從這種不舒服的餘味開始。",
        ];
  let out = trimmed.length > 0 ? trimmed : fallback;
  for (const add of additions) {
    if (out.length >= INCIDENT_AFTERMATH_MIN_CHARS_PER_PARA) {
      break;
    }
    const needsPunct = !/[。！？]$/.test(out);
    out += `${needsPunct ? "。" : ""}${add}`;
  }
  return out;
}

/**
 * 奇遇第一頁右欄：正文約 5 行（不足補句、過長截斷不加「…」；與 CSS `line-clamp: 5` 併用）。
 *
 * @param raw - `preamble_para1`
 */
function padWhimIntroFirstBody(raw: string): string {
  const padded = padZhParagraphToMinLength(raw, WHIM_INTRO1_BODY_MIN_CHARS, "風裡帶著遠方與偶然，你站穩腳步，把這一刻收進眼底。", [
    "遠處人聲與腳步交錯，像故事翻頁時紙邊的細響。",
    "你提醒自己別急著下結論，先把氣息調勻，再讓思緒跟上。",
    "這條路上沒有標準答案，只有此刻你願意承擔的選擇。",
    "你把目光放遠一點，看見路邊細節也在替這段旅途作證。",
    "心裡像有一盞小燈被風吹得搖，卻沒有熄。",
    "你忽然更清楚自己為何站在這裡，而不是別處。",
  ]);
  return finalizeNarrativeZhParagraph(padded, WHIM_INTRO1_BODY_MAX_CHARS);
}

/**
 * 奇遇第二頁：第一段約 3 行；第二段（對話）約 2 行以內。
 *
 * @param raw - `preamble_para2` 或 `chat`
 * @param paraIndex - 0：第二段前言；1：對話段
 */
function padWhimIntroSecondPageParagraph(raw: string, paraIndex: 0 | 1): string {
  const fallback =
    paraIndex === 0
      ? "話題像河水分岔，你沿著較清的一邊聽下去。"
      : "對方抬眼看你，像在等你把下一句說得更誠實。";
  const additions =
    paraIndex === 0
      ? [
          "你試著把情緒與事實分開，先聽見字裡行間真正的擔憂。",
          "空氣裡有猶豫，也有期待；你知道回應要慢一點才站得住。",
          "你把句子在心裡先排過一次，再讓它慢慢出口。",
          "遠處鐘聲像提醒：此刻的每一句話都會留下痕跡。",
        ]
      : [
          "你選擇先把立場放軟，把問題說清楚。",
          "對方聽見你聲音裡的誠實。",
          "有些理解要晚一點才會抵達。",
        ];
  const minC = paraIndex === 0 ? WHIM_INTRO2_FIRST_MIN_CHARS : WHIM_INTRO2_SECOND_MIN_CHARS;
  const maxC = paraIndex === 0 ? WHIM_INTRO2_FIRST_MAX_CHARS : WHIM_INTRO2_SECOND_MAX_CHARS;
  const padded = padZhParagraphToMinLength(raw, minC, fallback, additions);
  return finalizeNarrativeZhParagraph(padded, maxC);
}

/**
 * 奇遇餘韻：每段約 2 行以內（不超過）（答對／答錯皆同規則）。
 *
 * @param text - 原始段落
 * @param paraIndex - 第一段或第二段
 */
function padWhimAftermathParagraph(text: string, paraIndex: 0 | 1): string {
  const fallback = paraIndex === 0 ? "餘音在胸口繞了一下。" : "你把它寫進往後走路的節奏裡。";
  const additions =
    paraIndex === 0
      ? [
          "那一瞬間的情緒與事實交疊，你仍試著把句子說完整。",
          "你記得自己當時的呼吸，也記得沒有退路的那種清亮。",
          "你沒有急著把感受命名，先讓它在胸口停一會兒。",
        ]
      : [
          "回到日常後，這件事仍會在安靜時回來敲門。",
          "你知道成長常從這種不完美的餘味開始，慢慢變成力量。",
          "往後遇到類似的岔路，你會多一點把握，也少一點慌。",
        ];
  const padded = padZhParagraphToMinLength(text, WHIM_AFTERMATH_PARA_MIN_CHARS, fallback, additions);
  return finalizeNarrativeZhParagraph(padded, WHIM_AFTERMATH_PARA_MAX_CHARS);
}

/**
 * 重大事件前言合併段：補足／截斷至五行字量（連續文字、不插硬換行、截斷不加刪節號）。
 *
 * @param raw - `preamble_merged_zh`（或回退為兩段前言合併）
 * @returns 供顯示用之段落
 */
function padMajorPreambleMergedZh(raw: string): string {
  const fallback =
    "眼前這一幕與後果相連，你知道下一步要為選擇負責，並把細節記清楚，預備在培養裡寫下新的一筆。";
  const padded = padZhParagraphToMinLength(
    raw.trim(),
    MAJOR_PREAMBLE_MERGED_MIN_CHARS,
    fallback,
    MAJOR_MERGED_PAD,
  );
  return finalizeNarrativeZhParagraph(padded, MAJOR_PREAMBLE_MERGED_MAX_CHARS);
}

/**
 * 重大事件選擇題幹：補足／截斷至兩行字量（連續文字、截斷不加刪節號）。
 *
 * @param raw - `choice_prompt_zh`
 * @returns 供顯示用之題幹
 */
function padMajorChoicePromptZh(raw: string): string {
  const fallback = "妳須擇一條路並承擔，沒有旁觀的餘地，章程與名聲都跟著這一句走。";
  const additions: readonly string[] = [
    "此刻寫下的方向會跟著妳很久。",
    "邊境與公會都會記得妳怎麼選。",
    "你知道這一步會改寫往後的地圖。",
  ];
  const padded = padZhParagraphToMinLength(
    raw.trim(),
    MAJOR_CHOICE_PROMPT_MIN_CHARS,
    fallback,
    additions,
  );
  return finalizeNarrativeZhParagraph(padded, MAJOR_CHOICE_PROMPT_MAX_CHARS);
}

/**
 * 合併重大事件餘韻兩段為單一連續敘述（句間依需要補句讀）。
 *
 * @param a - 餘韻第一段
 * @param b - 餘韻第二段
 * @returns 合併後字串
 */
function mergeMajorResolutionBodiesZh(a: string, b: string): string {
  const t1 = a.trim();
  const t2 = b.trim();
  if (!t1) {
    return t2;
  }
  if (!t2) {
    return t1;
  }
  const bridge = /[。！？]$/.test(t1) ? "" : "。";
  return `${t1}${bridge}${t2}`;
}

/**
 * 重大事件餘韻合併段：補足／截斷至約四行寬欄折行（連續文字、截斷不加刪節號）。
 *
 * @param merged - 已合併之全文
 * @returns 供顯示用之段落
 */
function padMajorAftermathMergedZh(merged: string): string {
  const fallback =
    "妳把這一刻收進心底，預備回到培養裡繼續前進；餘音仍在胸口繞，你知道選擇已寫下，往後每一步都要更審慎以對。";
  const padded = padZhParagraphToMinLength(
    merged.trim(),
    MAJOR_AFTERMATH_MERGED_MIN_CHARS,
    fallback,
    MAJOR_AFTERMATH_PAD,
  );
  return finalizeNarrativeZhParagraph(padded, MAJOR_AFTERMATH_MERGED_MAX_CHARS);
}

function hudRoot(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

/**
 * 全畫面事件前導（點擊後進入本傳）。
 *
 * @param el - HUD 根節點
 * @param kind - 事件類型（決定框色與文案）
 * @param ageYear - 重大／遭遇滿歲；其餘可省略
 * @param gender - 前導句人稱
 * @param playPhase - 培養階段（突發／奇遇前導之 BGM 與進入後相同；重大／遭遇略過）
 * @param onContinue - 進入下一階
 */
function mountEventAlertHud(
  el: HTMLElement,
  kind: EventAlertKind,
  ageYear: number | undefined,
  gender: "male" | "female",
  playPhase: WebMiniPhase,
  onContinue: () => void,
): void {
  syncWebBgmEventAlert(kind, playPhase);
  const { title, teaser } = getEventAlertCopy(kind, ageYear, gender);
  el.innerHTML = `
    <div class="hud-event-alert-root hud-event-alert-root--${kind}" role="dialog" aria-modal="true">
      <button type="button" class="hud-event-alert-hitbox" aria-label="繼續進入事件">
        <span class="hud-event-alert-frame hud-event-alert-frame--${kind}">
          <span class="hud-event-alert-title">${escapeHtml(title)}</span>
          <span class="hud-event-alert-teaser">${escapeHtml(teaser)}</span>
          <span class="hud-event-alert-hint">點擊畫面繼續</span>
        </span>
      </button>
    </div>
  `;
  el.hidden = false;
  el.querySelector(".hud-event-alert-hitbox")?.addEventListener("click", () => {
    onContinue();
  });
}

/**
 * 重大事件：全畫面前導 → 前言 → 三選一 → 餘韻（底部數值＋返回）。
 *
 * @param game - 目前狀態（性別、稱謂）
 * @param ageYear - 滿歲
 * @param onComplete - 選項索引 0～2
 */
export function mountMajorEventHud(
  game: GameStateStored,
  ageYear: number,
  onComplete: (optionIndex: number) => void,
): void {
  const me = MAJOR_BY_AGE.get(ageYear);
  const el = hudRoot();
  if (!el || !me) {
    return;
  }

  const gender = game.protagonist_gender;
  let step: "alert" | "pre" | "pick" | "done" = "alert";
  let chosen = 0;

  const render = (): void => {
    if (step === "alert") {
      mountEventAlertHud(el, "major", ageYear, gender, game.phase, () => {
        step = "pre";
        render();
      });
      return;
    }

    if (step === "pre") {
      const mergedSrc =
        (me.preamble_merged_zh ?? "").trim() ||
        mergeMajorResolutionBodiesZh(me.preamble_body[0] ?? "", me.preamble_body[1] ?? "");
      const bodyZh = adjustProtagonistPronounZh(padMajorPreambleMergedZh(mergedSrc), gender);
      el.innerHTML = `
        <div class="hud-event-body hud-event-body--spaced hud-event-body--whim-intro">
          <div class="hud-event-body__inner hud-stack hud-stack--wide hud-event-body__inner--whim-intro">
            <p class="hud-line hud-title hud-event-body-title">重大事件　${escapeHtml(me.title)}</p>
            <p class="hud-line hud-sub hud-sub--wrap hud-event-body-text hud-whim-clamp hud-major-preamble-para">${escapeHtml(bodyZh)}</p>
            <div class="hud-whim-nav-footer">
              <button type="button" class="hud-btn hud-gallery-paged__corner-btn" data-act="next">選擇立場</button>
            </div>
          </div>
        </div>
      `;
      el.querySelector('[data-act="next"]')?.addEventListener("click", () => {
        step = "pick";
        render();
      });
    } else if (step === "pick") {
      const promptRaw = (me.choice_prompt_zh ?? "").trim() || me.preamble_title;
      const promptZh = adjustProtagonistPronounZh(padMajorChoicePromptZh(promptRaw), gender);
      const opts = me.options
        .map(
          (o, i) =>
            `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-opt="${i}">${escapeHtml(o.label)}</button>`,
        )
        .join("");
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz hud-stack--major-event-quiz">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto">
              重大事件　${escapeHtml(me.title)}<span class="hud-whim-intro1__loc">（${escapeHtml(me.preamble_title)}）</span>
            </p>
          </div>
          <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt hud-whim-clamp hud-major-choice-prompt">${escapeHtml(promptZh)}</p>
          <div class="hud-adopter-quiz-options" role="group" aria-label="重大事件選項">
            ${opts}
          </div>
        </div>
      `;
      el.querySelectorAll("[data-opt]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const i = Number((btn as HTMLElement).dataset.opt);
          chosen = i;
          step = "done";
          render();
        });
      });
    } else {
      const rb = me.resolution_bodies[chosen] ?? ["", ""];
      const mergedRaw = mergeMajorResolutionBodiesZh(rb[0] ?? "", rb[1] ?? "");
      const mergedZh = adjustProtagonistPronounZh(padMajorAftermathMergedZh(mergedRaw), gender);
      const opt = me.options[chosen];
      const deltaLine = opt
        ? formatMergedDeltasLineZh(opt.deltas, opt.extra_deltas)
        : formatMergedDeltasLineZh({});
      const aftermathTitle = "重大事件　餘韻判讀";
      const bodyHtml = `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para hud-whim-clamp hud-major-aftermath-para">${escapeHtml(mergedZh)}</p>`;
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result hud-stack--incident-aftermath-result hud-stack--encounter-aftermath">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">${escapeHtml(aftermathTitle)}</p>
          </div>
          <div class="hud-adopter-result-body">
            ${bodyHtml}
          </div>
          <div class="hud-adopter-result-footer">
            <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-stat" aria-label="數值變化">本段數值：${escapeHtml(deltaLine)}</p>
            <div class="hud-actions hud-actions--adopter-result">
              <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn hud-btn--adopter-continue" data-act="done">返回培養</button>
            </div>
          </div>
        </div>
      `;
      el.querySelector('[data-act="done"]')?.addEventListener("click", () => {
        onComplete(chosen);
      });
    }
  };

  el.hidden = false;
  render();
}

/**
 * 突發事件：全畫面前導 → 本文與選項 → 餘韻（底部數值＋返回）。
 *
 * @param incident - 事件資料
 * @param gender - 前導句人稱
 * @param playPhase - 存檔階段（與培養／突發本傳同一套 BGM）
 * @param onComplete - 選項索引
 */
export function mountIncidentHud(
  incident: IncidentEventJson,
  gender: "male" | "female",
  playPhase: WebMiniPhase,
  onComplete: (optionIndex: number) => void,
): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  let step: "alert" | "body" | "after" = "alert";
  let chosen = 0;

  const aftermathFor = (opt: number): string[] => {
    const triple = INCIDENT_AFTERMATH_BY_ID[incident.id];
    if (!triple || !triple[opt]) {
      return ["選擇已記錄。", ""];
    }
    const paras = triple[opt];
    return [paras[0] ?? "", paras[1] ?? ""];
  };

  const render = (): void => {
    if (step === "alert") {
      mountEventAlertHud(el, "incident", undefined, gender, playPhase, () => {
        step = "body";
        render();
      });
      return;
    }

    if (step === "body") {
      const opts = incident.options
        .map(
          (o, i) =>
            `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-opt="${i}">${escapeHtml(o.label)}</button>`,
        )
        .join("");
      const bodyPromptZh = adjustProtagonistPronounZh(padIncidentBodyPromptZh(incident.body), gender);
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz hud-stack--incident-body-quiz">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto">突發事件 · ${escapeHtml(incident.title)}</p>
          </div>
          <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt hud-incident-quiz-prompt hud-incident-quiz-prompt--twoline">${escapeHtml(bodyPromptZh)}</p>
          <div class="hud-adopter-quiz-options" role="group" aria-label="突發事件選項">
            ${opts}
          </div>
        </div>
      `;
      el.querySelectorAll("[data-opt]").forEach((btn) => {
        btn.addEventListener("click", () => {
          chosen = Number((btn as HTMLElement).dataset.opt);
          step = "after";
          render();
        });
      });
    } else {
      const [rawA, rawB] = aftermathFor(chosen);
      const a = padIncidentAftermathParagraphZh(rawA, 0);
      const b = padIncidentAftermathParagraphZh(rawB, 1);
      const deltas = incident.options[chosen]?.deltas ?? {};
      const deltaLine = formatMergedDeltasLineZh(deltas);
      const bodyHtml = [a, b]
        .map((p) => escapeHtml(p.trim()))
        .filter((p) => p.length > 0)
        .map((p) => `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para">${p}</p>`)
        .join("");
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result hud-stack--incident-aftermath-result">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">突發事件　餘韻判讀</p>
          </div>
          <div class="hud-adopter-result-body">
            ${bodyHtml}
          </div>
          <div class="hud-adopter-result-footer">
            <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-stat" aria-label="數值變化">本段數值：${escapeHtml(deltaLine)}</p>
            <div class="hud-actions hud-actions--adopter-result">
              <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn hud-btn--adopter-continue" data-act="done">返回培養</button>
            </div>
          </div>
        </div>
      `;
      el.querySelector('[data-act="done"]')?.addEventListener("click", () => {
        onComplete(chosen);
      });
    }
  };

  el.hidden = false;
  render();
}

/**
 * 遭遇戰：全畫面前導 → 對戰播映（雙血條、左右 CG、交鋒記錄）→ 餘韻敘事與數值。
 *
 * @param game - 存檔狀態（姓名、階段、性別、立繪路徑）
 * @param enemy - 敵方資料（CG、餘韻文、寶物名）
 * @param outcome - 模擬結果（影格、面板攻防）
 * @param encounterAge - 滿歲 6／11／16（前導句）
 * @param onDismiss - 餘韻結束後套用獎勵
 */
export function mountEncounterHud(
  game: GameStateStored,
  enemy: EncounterEnemyJson,
  outcome: BattleOutcome,
  encounterAge: number,
  onDismiss: () => void,
): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  el.hidden = false;
  mountEventAlertHud(el, "encounter", encounterAge, game.protagonist_gender, game.phase, () => {
    mountEncounterBattleFlow(el, { game, enemy, outcome }, onDismiss);
  });
}

/**
 * 奇遇：全畫面前導 → 導引 → 測驗 → 餘韻（底部數值＋返回）。
 * 第一頁導引：標題（角色名＋括號地點）、左 CG／右欄本文約五行＋同欄右下「下一頁」（避免左欄撐高把按鈕推遠）。
 *
 * @param enc - NPC 資料
 * @param q - 題目
 * @param optionPerm - 畫面上三格對應之原始選項索引
 * @param correctSlot - 正解槽位 0～2
 * @param gender - 前導與答題回饋人稱
 * @param playPhase - 存檔階段
 * @param onComplete - 是否答對
 */
export function mountWhimEventHud(
  enc: WhimEncounterJson,
  q: WhimQuestionJson,
  optionPerm: readonly [number, number, number],
  correctSlot: number,
  gender: "male" | "female",
  playPhase: WebMiniPhase,
  onComplete: (correct: boolean) => void,
): void {
  const el = hudRoot();
  if (!el) {
    return;
  }

  let whimStep: "alert" | "intro1" | "intro2" | "quiz" | "after" = "alert";
  let chosenSlot = 0;
  let wasCorrect = false;

  const labels = optionPerm.map((pi, slot) => q.options[pi] ?? "") as [string, string, string];

  const render = (): void => {
    if (whimStep === "alert") {
      mountEventAlertHud(el, "whim", undefined, gender, playPhase, () => {
        whimStep = "intro1";
        render();
      });
      return;
    }

    if (whimStep === "intro1") {
      el.innerHTML = `
        <div class="hud-event-body hud-event-body--spaced hud-event-body--whim-intro">
          <div class="hud-event-body__inner hud-stack hud-stack--wide hud-event-body__inner--whim-intro">
            <p class="hud-line hud-title hud-event-body-title">
              ${escapeHtml(enc.display_name)}<span class="hud-whim-intro1__loc">（${escapeHtml(enc.location_zh)}）</span>
            </p>
            <div class="hud-whim-intro1__row">
              <div class="hud-whim-intro1__cg-wrap">
                <div class="hud-whim-intro1__frame">
                  <img class="hud-whim-intro1__img" alt="" decoding="async" />
                  <div class="hud-whim-intro1__ph" aria-hidden="true"></div>
                </div>
              </div>
              <div class="hud-whim-intro1__right">
                <div class="hud-whim-intro1__body">
                  <p class="hud-line hud-sub hud-sub--wrap hud-event-body-text hud-whim-clamp hud-whim-clamp--5">${escapeHtml(padWhimIntroFirstBody(enc.preamble_para1))}</p>
                </div>
                <div class="hud-whim-nav-footer hud-whim-nav-footer--intro1">
                  <button type="button" class="hud-btn hud-gallery-paged__corner-btn" data-act="next">下一頁</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
      const img = el.querySelector<HTMLImageElement>(".hud-whim-intro1__img");
      const ph = el.querySelector<HTMLElement>(".hud-whim-intro1__ph");
      if (img) {
        img.alt = enc.display_name;
        const urls = whimCompanionCgUrlCandidates(enc.cg_basename);
        wireImageFallbackChain(img, urls, ph, "hud-whim-intro1__ph--hide");
      }
      el.querySelector('[data-act="next"]')?.addEventListener("click", () => {
        whimStep = "intro2";
        render();
      });
    } else if (whimStep === "intro2") {
      el.innerHTML = `
        <div class="hud-event-body hud-event-body--spaced hud-event-body--whim-intro">
          <div class="hud-event-body__inner hud-stack hud-stack--wide hud-event-body__inner--whim-intro">
            <p class="hud-line hud-title hud-event-body-title">
              ${escapeHtml(enc.display_name)}<span class="hud-whim-intro1__loc">（${escapeHtml(enc.location_zh)}）</span>
            </p>
            <p class="hud-line hud-sub hud-sub--wrap hud-event-body-text hud-whim-clamp hud-whim-clamp--3">${escapeHtml(
              padWhimIntroSecondPageParagraph(enc.preamble_para2, 0),
            )}</p>
            <p class="hud-line hud-sub hud-sub--wrap hud-event-body-text hud-whim-clamp hud-whim-clamp--2">${escapeHtml(
              padWhimIntroSecondPageParagraph(enc.chat, 1),
            )}</p>
            <div class="hud-whim-nav-footer">
              <button type="button" class="hud-btn hud-gallery-paged__corner-btn" data-act="next">下一頁</button>
            </div>
          </div>
        </div>
      `;
      el.querySelector('[data-act="next"]')?.addEventListener("click", () => {
        whimStep = "quiz";
        render();
      });
    } else if (whimStep === "quiz") {
      const stemDisplay = whimQuizStemDisplayZh(q.stem);
      const btns = labels
        .map(
          (text, slot) =>
            `<button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-adopter-quiz-opt" data-slot="${slot}">${escapeHtml(text)}</button>`,
        )
        .join("");
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-quiz hud-stack--whim-quiz">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto">奇遇測驗</p>
          </div>
          <p class="hud-line hud-sub hud-sub--proto hud-onboarding-body hud-adopter-quiz-prompt hud-whim-quiz__stem">${escapeHtml(stemDisplay)}</p>
          <div class="hud-adopter-quiz-options" role="group" aria-label="奇遇測驗選項">
            ${btns}
          </div>
        </div>
      `;
      el.querySelectorAll("[data-slot]").forEach((btn) => {
        btn.addEventListener("click", () => {
          chosenSlot = Number((btn as HTMLElement).dataset.slot);
          wasCorrect = chosenSlot === correctSlot;
          whimStep = "after";
          render();
        });
      });
    } else {
      const p1Raw = wasCorrect ? enc.aftermath_correct_para1 : enc.aftermath_wrong_para1;
      const p2Raw = wasCorrect ? enc.aftermath_correct_para2 : enc.aftermath_wrong_para2;
      const p1 = padWhimAftermathParagraph(p1Raw, 0);
      const p2 = padWhimAftermathParagraph(p2Raw, 1);
      const pronoun = gender === "male" ? "你" : "妳";
      const head = wasCorrect ? `${pronoun}答對了。` : `${pronoun}答錯了。`;
      const deltas = wasCorrect ? enc.deltas_correct : enc.deltas_wrong;
      const deltaLine = formatMergedDeltasLineZh(deltas);
      const bodyHtml = [p1, p2]
        .map((p) => escapeHtml(p.trim()))
        .filter((p) => p.length > 0)
        .map((p) => `<p class="hud-line hud-sub hud-sub--proto hud-adopter-result-para hud-whim-clamp hud-whim-clamp--2">${p}</p>`)
        .join("");
      el.innerHTML = `
        <div class="hud-stack hud-stack--wide hud-stack--onboarding hud-stack--adopter-result hud-stack--incident-aftermath-result hud-stack--whim-aftermath">
          <div class="hud-page-head">
            <p class="hud-line hud-title hud-title--proto hud-adopter-result-title">${escapeHtml(head)}</p>
          </div>
          <div class="hud-adopter-result-body">
            ${bodyHtml}
          </div>
          <div class="hud-adopter-result-footer">
            <p class="hud-line hud-sub hud-sub--proto hud-adopter-result-stat" aria-label="數值變化">本段數值：${escapeHtml(deltaLine)}</p>
            <div class="hud-actions hud-actions--adopter-result">
              <button type="button" class="hud-btn hud-btn--secondary hud-btn--proto hud-gallery-paged__corner-btn hud-gallery-hub__back hud-intro-nav__btn hud-btn--adopter-continue" data-act="done">返回培養</button>
            </div>
          </div>
        </div>
      `;
      el.querySelector('[data-act="done"]')?.addEventListener("click", () => {
        onComplete(wasCorrect);
      });
    }
  };

  el.hidden = false;
  render();
}

/**
 * 結局：若干敘事頁後接一頁全幅 CG（對齊桌面版結局翻頁）。
 *
 * @param ending - 結局資料
 * @param onExit - 返回標題或選單
 */
export function mountEndingHud(ending: EndingJson, onExit: () => void): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  el.hidden = false;
  mountEndingPagesFlow(el, ending, "play", onExit);
}
