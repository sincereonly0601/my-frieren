/**
 * 圖片依 URL 清單遞補載入；全敗時可選保留占位顯示。
 */

/**
 * {@link wireImageFallbackChain} 之可選回呼：點陣圖成功或全數失敗時各觸發一次。
 */
export type WireImageFallbackCallbacks = {
  /** 任一 URL 載入為有效點陣圖時呼叫一次 */
  onRasterSuccess?: () => void;
  /**
   * 所有 URL 皆失敗（或 `urls` 為空）時呼叫一次；若提供此回呼，將**不**自動還原文字占位，
   * 由呼叫端決定後續 UI（例如改顯示 Canvas 向量回退）。
   */
  onRasterExhausted?: () => void;
};

/**
 * 依序嘗試 URL；成功則隱藏占位，全敗則保留或還原占位。
 *
 * @param img - 目標 img
 * @param urls - 完整 URL 列表
 * @param ph - 占位節點（可 null）
 * @param hideClass - 載入成功時加在占位上
 * @param callbacks - 可選；提供 `onRasterExhausted` 時，全敗不會自動 `showPh`
 */
export function wireImageFallbackChain(
  img: HTMLImageElement,
  urls: readonly string[],
  ph: HTMLElement | null,
  hideClass: string,
  callbacks?: WireImageFallbackCallbacks,
): void {
  const hidePh = (): void => {
    if (ph) {
      ph.classList.add(hideClass);
    }
  };
  const showPh = (): void => {
    if (ph) {
      ph.classList.remove(hideClass);
    }
  };
  let i = 0;
  let successNotified = false;
  img.style.display = "";
  const notifySuccess = (): void => {
    if (successNotified) {
      return;
    }
    successNotified = true;
    callbacks?.onRasterSuccess?.();
  };
  const next = (): void => {
    if (i >= urls.length) {
      img.removeAttribute("src");
      img.style.display = "none";
      if (callbacks?.onRasterExhausted) {
        callbacks.onRasterExhausted();
      } else {
        showPh();
      }
      return;
    }
    const u = urls[i]!;
    i += 1;
    img.onerror = () => {
      next();
    };
    img.onload = () => {
      if (img.naturalWidth > 0) {
        hidePh();
        notifySuccess();
      }
    };
    img.src = u;
    if (img.complete && img.naturalWidth > 0) {
      hidePh();
      notifySuccess();
    }
  };
  img.decoding = "async";
  next();
}
