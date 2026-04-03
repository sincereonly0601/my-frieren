/**
 * 網頁版循環 BGM：對齊 `main.py` 之 `_bgm_track_for_screen`／`sync_bgm`。
 * 靜音偏好見 {@link isBgmMutedPreferred}；首次播放可能需使用者觸控後才成功（瀏覽器自動播放策略）。
 */

import type { WebMiniPhase } from "../save/idbSave";
import { isBgmMutedPreferred } from "../save/webPrefs";
import {
  BGM_FILE_ADOLESCENCE,
  BGM_FILE_CHILDHOOD,
  BGM_FILE_MAJOR,
  BGM_FILE_OPENING,
  BGM_FILE_PROLOGUE,
  bgmAssetUrl,
} from "./bgmPaths";

/** 與 `main.py` 之 `Screen` 對應之簡化模式（網頁流程用） */
export type WebBgmMode =
  | { kind: "opening" }
  | { kind: "prologue" }
  | { kind: "play"; phase: WebMiniPhase }
  | { kind: "major" }
  | { kind: "ending" };

let lastMode: WebBgmMode | null = null;
let audioEl: HTMLAudioElement | null = null;
let loadedUrl = "";

/** 是否已掛過 `error` 除錯（避免重複註冊） */
let errorLogAttached = false;

/**
 * @returns 共用之 `<audio>`（循環、預載）
 */
function getAudio(): HTMLAudioElement {
  if (audioEl == null) {
    audioEl = new Audio();
    audioEl.loop = true;
    audioEl.preload = "auto";
    audioEl.volume = 1;
    if (import.meta.env.DEV && !errorLogAttached) {
      errorLogAttached = true;
      audioEl.addEventListener("error", () => {
        const err = audioEl?.error;
        const code = err?.code;
        const msg = err?.message ?? "";
        // eslint-disable-next-line no-console -- 開發時協助排查 404／格式不支援
        console.warn(
          "[BGM] 音檔載入或播放失敗（請確認 public/assets/bgm 檔名與程式一致、路徑 404、或瀏覽器是否支援 OGG）",
          { src: audioEl?.currentSrc || audioEl?.src, code, msg },
        );
      });
    }
  }
  return audioEl;
}

/**
 * @param mode - 當前畫面語意
 * @returns 應播放之 OGG 檔名
 */
function fileForMode(mode: WebBgmMode): string {
  switch (mode.kind) {
    case "opening":
    case "ending":
      return BGM_FILE_OPENING;
    case "prologue":
      return BGM_FILE_PROLOGUE;
    case "major":
      return BGM_FILE_MAJOR;
    case "play": {
      const ph = mode.phase;
      if (ph === "childhood") {
        return BGM_FILE_CHILDHOOD;
      }
      if (ph === "adolescence") {
        return BGM_FILE_ADOLESCENCE;
      }
      return BGM_FILE_PROLOGUE;
    }
    default:
      return BGM_FILE_OPENING;
  }
}

/**
 * @param url - 絕對音檔 URL
 */
function applyLoadedTrack(url: string): void {
  const a = getAudio();
  if (loadedUrl !== url) {
    loadedUrl = url;
    a.src = url;
    a.load();
  }
}

/**
 * 依畫面切換 BGM：與正在播放檔不同則換源並循環；已靜音則僅換源並 pause。
 *
 * @param mode - 對齊桌機之曲別
 */
export function syncWebBgm(mode: WebBgmMode): void {
  lastMode = mode;
  const url = bgmAssetUrl(fileForMode(mode));
  applyLoadedTrack(url);
  if (isBgmMutedPreferred()) {
    getAudio().pause();
    return;
  }
  void getAudio()
    .play()
    .catch(() => {
      /* 多數為自動播放限制；後續每次使用者觸控會再試 {@link resumeWebBgmAfterUserGesture} */
    });
}

/** 標題／主選單／讀檔／畫廊／設定／芙莉蓮測驗等 */
export function syncWebBgmOpening(): void {
  syncWebBgm({ kind: "opening" });
}

/** 開場、監護人、問卷、契約 */
export function syncWebBgmPrologue(): void {
  syncWebBgm({ kind: "prologue" });
}

/**
 * @param phase - 存檔 `game.phase`
 */
export function syncWebBgmPlayPhase(phase: WebMiniPhase): void {
  syncWebBgm({ kind: "play", phase });
}

/** 重大事件、遭遇戰（含前導） */
export function syncWebBgmMajor(): void {
  syncWebBgm({ kind: "major" });
}

/** 結局流程（與開場同一檔） */
export function syncWebBgmEnding(): void {
  syncWebBgm({ kind: "ending" });
}

/**
 * 事件前導：配樂與 Enter／點擊後即將進入之畫面相同（對齊桌面 `EVENT_ALERT`）。
 *
 * @param next - 即將進入之事件類型
 * @param lifePhase - 培養階段（突發／奇遇前導用）
 */
export function syncWebBgmEventAlert(
  next: "major" | "incident" | "encounter" | "whim" | "ending",
  lifePhase: WebMiniPhase,
): void {
  if (next === "major" || next === "encounter") {
    syncWebBgmMajor();
    return;
  }
  if (next === "ending") {
    syncWebBgmEnding();
    return;
  }
  syncWebBgmPlayPhase(lifePhase);
}

/**
 * 設定裡切換「背景音樂」開關後呼叫：不換曲，僅 pause／resume。
 */
export function applyWebBgmMutePreference(): void {
  if (lastMode == null) {
    return;
  }
  const a = getAudio();
  if (isBgmMutedPreferred()) {
    a.pause();
    return;
  }
  if (loadedUrl === "") {
    syncWebBgm(lastMode);
    return;
  }
  void a.play().catch(() => {});
}

/**
 * 使用者首次觸控後再嘗試播放（繞過自動播放限制）。
 */
export function resumeWebBgmAfterUserGesture(): void {
  if (isBgmMutedPreferred() || lastMode == null) {
    return;
  }
  if (loadedUrl === "") {
    syncWebBgm(lastMode);
    return;
  }
  void getAudio().play().catch(() => {});
}

/**
 * 註冊持續之使用者互動監聽（capture）：每次觸控／按鍵皆嘗試 `play()`。
 * 僅用 `once` 時，若首次事件發生在 `syncWebBgm` 之前或未被攔到，會導致整局無聲。
 */
export function installWebBgmGestureUnlock(): void {
  const bump = (): void => {
    resumeWebBgmAfterUserGesture();
  };
  document.addEventListener("pointerdown", bump, { capture: true, passive: true });
  document.addEventListener("touchstart", bump, { capture: true, passive: true });
  document.addEventListener("keydown", bump, { capture: true });
}
