/**
 * 培養回饋右欄：無點陣圖時以 Canvas 繪製動效（對齊桌面 `training_feedback_fx._paint_feedback_box_surface` 向量分支）。
 */

/**
 * 以路徑繪製圓角矩形（填色／描邊前呼叫）。
 *
 * @param ctx - 2D 情境
 * @param x - 左上 x
 * @param y - 左上 y
 * @param w - 寬
 * @param h - 高
 * @param r - 圓角半徑
 */
function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawBook(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const cy = lh / 2;
  const pageW = lw / 3;
  const l = { x: cx - pageW - 4, y: cy - 12, w: pageW, h: 24 };
  const rr = { x: cx + 4, y: cy - 12, w: pageW, h: 24 };
  ctx.fillStyle = "rgb(230, 228, 215)";
  roundRectPath(ctx, l.x, l.y, l.w, l.h, 4);
  ctx.fill();
  roundRectPath(ctx, rr.x, rr.y, rr.w, rr.h, 4);
  ctx.fill();
  ctx.strokeStyle = "rgb(160, 140, 120)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, l.y);
  ctx.lineTo(cx, l.y + l.h);
  ctx.stroke();
  const y = cy - 8 + Math.sin(t * 7) * 6;
  ctx.fillStyle = "rgb(80, 60, 45)";
  ctx.beginPath();
  ctx.arc(cx + 18, y, 3, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawDumbbell(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const cy = lh / 2 + Math.sin(t * 9) * 6;
  ctx.strokeStyle = "rgb(185, 195, 210)";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(cx - 20, cy);
  ctx.lineTo(cx + 20, cy);
  ctx.stroke();
  ctx.fillStyle = "rgb(120, 130, 150)";
  roundRectPath(ctx, cx - 30, cy - 10, 8, 20, 2);
  ctx.fill();
  roundRectPath(ctx, cx - 22, cy - 8, 6, 16, 2);
  ctx.fill();
  roundRectPath(ctx, cx + 16, cy - 8, 6, 16, 2);
  ctx.fill();
  roundRectPath(ctx, cx + 22, cy - 10, 8, 20, 2);
  ctx.fill();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawPrayer(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const cy = lh / 2;
  const glow = 130 + 40 * (0.5 + 0.5 * Math.sin(t * 5.5));
  const c = `rgb(${Math.floor(glow)}, ${Math.floor(glow)}, 120)`;
  ctx.strokeStyle = c;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(cx, cy - 16);
  ctx.lineTo(cx, cy + 16);
  ctx.moveTo(cx - 10, cy);
  ctx.lineTo(cx + 10, cy);
  ctx.stroke();
  ctx.strokeStyle = "rgba(220, 210, 150, 0.35)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, 18, 0, Math.PI * 2);
  ctx.stroke();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawChat(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const cy = lh / 2;
  const dx = Math.sin(t * 6) * 4;
  const ax = cx - 28 + dx;
  const ay = cy - 14;
  const bx = cx + 4 - dx;
  const by = cy - 2;
  ctx.fillStyle = "rgb(170, 210, 255)";
  roundRectPath(ctx, ax, ay, 24, 16, 5);
  ctx.fill();
  ctx.fillStyle = "rgb(210, 175, 255)";
  roundRectPath(ctx, bx, by, 24, 16, 5);
  ctx.fill();
  ctx.fillStyle = "rgb(170, 210, 255)";
  ctx.beginPath();
  ctx.moveTo(ax + 6, ay + 16);
  ctx.lineTo(ax + 10, ay + 16);
  ctx.lineTo(ax + 8, ay + 20);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgb(210, 175, 255)";
  ctx.beginPath();
  ctx.moveTo(bx + 14, by + 16);
  ctx.lineTo(bx + 18, by + 16);
  ctx.lineTo(bx + 16, by + 20);
  ctx.closePath();
  ctx.fill();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawWork(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const cy = lh / 2;
  const ang = t * 4;
  ctx.strokeStyle = "rgb(220, 190, 140)";
  ctx.lineWidth = 3;
  for (let i = 0; i < 4; i += 1) {
    const a = ang + i * (Math.PI / 2);
    const x = cx + Math.cos(a) * 14;
    const y = cy + Math.sin(a) * 14;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  ctx.fillStyle = "rgb(130, 100, 70)";
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * @param ctx - 2D 情境
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param t - 秒
 */
function drawVisit(ctx: CanvasRenderingContext2D, lw: number, lh: number, t: number): void {
  const cx = lw / 2;
  const base = lh / 2 + 10;
  for (let i = 0; i < 4; i += 1) {
    const x = cx - 22 + i * 14;
    const lit = (Math.floor(t * 8) + i) % 4 === 0;
    ctx.fillStyle = lit ? "rgb(230, 220, 165)" : "rgb(120, 130, 145)";
    ctx.beginPath();
    ctx.arc(x, base - (i % 2) * 6, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

/**
 * 繪製單幀向量內容（含外框底，對齊桌面深色盒）。
 *
 * @param ctx - 2D 情境（已套用 DPR scale）
 * @param lw - 邏輯寬
 * @param lh - 邏輯高
 * @param actionKey - 1～8
 * @param t - 秒
 */
function paintVectorFrame(
  ctx: CanvasRenderingContext2D,
  lw: number,
  lh: number,
  actionKey: number,
  t: number,
): void {
  ctx.clearRect(0, 0, lw, lh);
  ctx.fillStyle = "rgba(32, 38, 50, 0.82)";
  roundRectPath(ctx, 0, 0, lw, lh, 8);
  ctx.fill();
  ctx.strokeStyle = "rgb(110, 124, 155)";
  ctx.lineWidth = 2;
  roundRectPath(ctx, 0, 0, lw, lh, 8);
  ctx.stroke();
  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  roundRectPath(ctx, 8, 8, lw - 16, lh - 16, 6);
  ctx.stroke();

  if (actionKey === 1 || actionKey === 6) {
    drawBook(ctx, lw, lh, t);
  } else if (actionKey === 2 || actionKey === 8) {
    drawDumbbell(ctx, lw, lh, t);
  } else if (actionKey === 3) {
    drawPrayer(ctx, lw, lh, t);
  } else if (actionKey === 4) {
    drawChat(ctx, lw, lh, t);
  } else if (actionKey === 5) {
    drawWork(ctx, lw, lh, t);
  } else if (actionKey === 7) {
    drawVisit(ctx, lw, lh, t);
  }
}

/**
 * 啟動培養回饋向量動畫；圖片載入成功時應呼叫回傳之停止函式。
 *
 * @param canvas - 已置於 `.hud-training-feedback-fx` 內之 canvas
 * @param actionKey - 培養 1～8
 * @returns 取消 `requestAnimationFrame` 並隱藏邏輯由呼叫端配合 class 處理
 */
export function startTrainingFeedbackVectorAnimation(
  canvas: HTMLCanvasElement,
  actionKey: number,
): () => void {
  let raf = 0;

  const tick = (ts: number): void => {
    raf = window.requestAnimationFrame(tick);
    const rect = canvas.getBoundingClientRect();
    const lw = Math.max(8, rect.width);
    const lh = Math.max(8, rect.height);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const pw = Math.floor(lw * dpr);
    const ph = Math.floor(lh * dpr);
    if (canvas.width !== pw || canvas.height !== ph) {
      canvas.width = pw;
      canvas.height = ph;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const t = ts / 1000;
    const key = actionKey >= 1 && actionKey <= 8 ? actionKey : 1;
    paintVectorFrame(ctx, lw, lh, key, t);
  };

  raf = window.requestAnimationFrame(tick);

  return (): void => {
    window.cancelAnimationFrame(raf);
  };
}
