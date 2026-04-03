/**
 * 培養結算回饋全畫面（對齊桌面 `draw_training_feedback_modal`：左文右圖；點畫面任一處或 Enter／Esc 後才扣季）。
 */

import { wireImageFallbackChain } from "../gallery/wireImageFallback";
import {
  splitTrainingFeedbackActionLead,
  splitTrainingFeedbackStatParen,
} from "../game/trainingFeedbackCopy";
import { escapeHtml } from "./hudToast";
import { startTrainingFeedbackVectorAnimation } from "./trainingFeedbackVectorFx";

const HUD_ID = "hud";
const FX_PH_HIDE = "hud-training-feedback-fx__ph--hide";
const FX_CANVAS_SHOW = "hud-training-feedback-fx__canvas--show";

/**
 * @returns HUD 根節點
 */
function hudRoot(): HTMLElement | null {
  return document.getElementById(HUD_ID);
}

export type MountTrainingFeedbackHudOpts = {
  /** 與 {@link formatTrainingFeedbackModalMessage} 產物相同 */
  messageZh: string;
  /** 右側插圖遞補 URL */
  imageUrlCandidates: readonly string[];
  /** 培養鍵 1～8；點陣圖全失敗時用於向量動效（對齊桌面 `training_feedback_fx`） */
  actionKey: number;
  /** 使用者關閉後（Enter／Esc／點擊畫面任一處） */
  onDismiss: () => void;
};

/**
 * 顯示培養回饋面板；點全畫面或 Enter／Esc 關閉並移除鍵盤監聽。
 *
 * @param opts - 文案、圖片候選、關閉回呼
 */
export function mountTrainingFeedbackHud(opts: MountTrainingFeedbackHudOpts): void {
  const el = hudRoot();
  if (!el) {
    return;
  }
  const { bodyBeforeParen, statLine } = splitTrainingFeedbackStatParen(opts.messageZh);
  const { lead, narrative } = splitTrainingFeedbackActionLead(bodyBeforeParen);
  const statPrefix = "數值變化：";
  const statFull = statLine ? `${statPrefix}${statLine}` : "";

  el.innerHTML = `
    <div class="hud-training-feedback-root" role="presentation">
      <div
        class="hud-training-feedback-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="training-feedback-title"
        aria-describedby="training-feedback-hint"
      >
        <h2 id="training-feedback-title" class="hud-training-feedback-title">本季培養回饋</h2>
        <div class="hud-training-feedback-body">
          <div class="hud-training-feedback-text">
            ${lead ? `<p class="hud-training-feedback-lead">${escapeHtml(lead)}</p>` : ""}
            <p class="hud-training-feedback-narrative">${escapeHtml(narrative)}</p>
            ${
              statFull
                ? `<p class="hud-training-feedback-stat" aria-label="${escapeHtml(statPrefix)}">${escapeHtml(statFull)}</p>`
                : ""
            }
          </div>
          <div class="hud-training-feedback-fx" aria-hidden="true">
            <img class="hud-training-feedback-fx__img" alt="" decoding="async" />
            <canvas class="hud-training-feedback-fx__canvas" aria-hidden="true"></canvas>
          </div>
        </div>
        <p id="training-feedback-hint" class="hud-line hud-training-feedback-hint">點擊畫面繼續</p>
      </div>
    </div>
  `;
  el.hidden = false;

  const img = el.querySelector<HTMLImageElement>(".hud-training-feedback-fx__img");
  const ph = el.querySelector<HTMLElement>(".hud-training-feedback-fx__ph");
  const cvs = el.querySelector<HTMLCanvasElement>(".hud-training-feedback-fx__canvas");
  let stopVector: (() => void) | null = null;

  const hideVectorCanvas = (): void => {
    stopVector?.();
    stopVector = null;
    cvs?.classList.remove(FX_CANVAS_SHOW);
  };

  if (img) {
    wireImageFallbackChain(img, opts.imageUrlCandidates, ph, FX_PH_HIDE, {
      onRasterSuccess: () => {
        hideVectorCanvas();
      },
      onRasterExhausted: () => {
        if (ph) {
          ph.classList.add(FX_PH_HIDE);
        }
        if (cvs) {
          cvs.classList.add(FX_CANVAS_SHOW);
          stopVector = startTrainingFeedbackVectorAnimation(cvs, opts.actionKey);
        }
      },
    });
  }

  let done = false;
  const finish = (): void => {
    if (done) {
      return;
    }
    done = true;
    hideVectorCanvas();
    window.removeEventListener("keydown", onKey);
    opts.onDismiss();
  };

  const onKey = (ev: KeyboardEvent): void => {
    if (ev.key === "Enter" || ev.key === "Escape") {
      ev.preventDefault();
      finish();
    }
  };
  window.addEventListener("keydown", onKey);

  el.querySelector(".hud-training-feedback-root")?.addEventListener("click", () => {
    finish();
  });
}
