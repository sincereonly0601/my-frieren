/**
 * 培養回饋插圖 URL 候選（對齊 `training_feedback_fx.py` 之 manifest 與檔名前綴慣例）。
 * 圖檔請置於 `public/assets/training_fx/`（開發時為 `web/public/assets/training_fx/`）。
 */

/** 與桌面 `_ACTION_FRAME_PREFIX` 一致 */
const ACTION_FRAME_PREFIX: Record<number, string> = {
  1: "read",
  2: "train",
  3: "pray",
  4: "chat",
  5: "work",
  6: "copy",
  7: "visit",
  8: "solo",
};

const MALE_ACTION_PREFIX: Record<number, string> = {
  2: "train_male",
  3: "pray_male",
  4: "chat_male",
  5: "work_male",
  6: "copy_male",
  7: "visit_male",
  8: "solo_male",
};

const FEMALE_ACTION_PREFIX: Record<number, string> = {
  2: "train_female",
  3: "pray_female",
  4: "chat_female",
  5: "work_female",
  6: "copy_female",
  7: "visit_female",
  8: "solo_female",
};

const FX_EXTS: readonly string[] = [".png", ".webp", ".jpg", ".jpeg"];

let manifestPromise: Promise<Record<string, string[]> | null> | null = null;

/**
 * @returns Vite `BASE_URL`（結尾必為 `/`）
 */
function baseUrl(): string {
  const b = import.meta.env.BASE_URL ?? "/";
  return b.endsWith("/") ? b : `${b}/`;
}

/**
 * @param rel - 相對於網站根之路徑，勿以 `/` 開頭
 */
function assetUrl(rel: string): string {
  const r = rel.replace(/^\/+/, "");
  return `${baseUrl()}${r}`;
}

/**
 * 併入某前綴之慣例檔名候選（`{p}.ext`、`{p}_01.ext`）。
 *
 * @param prefix - 檔名前綴
 * @param bucket - 去重用
 */
function pushPrefixUrls(prefix: string, bucket: string[]): void {
  for (const ext of FX_EXTS) {
    for (const stem of [`${prefix}${ext}`, `${prefix}_01${ext}`, `${prefix}_1${ext}`]) {
      const u = assetUrl(`assets/training_fx/${stem}`);
      if (!bucket.includes(u)) {
        bucket.push(u);
      }
    }
  }
}

/**
 * 依性別與鍵取得前綴試探順序（對齊 `_paths_for_action`）。
 *
 * @param actionKey - 1～8
 * @param gender - 主角性別
 */
function orderedPrefixesForAction(
  actionKey: number,
  gender: "male" | "female",
): string[] {
  const out: string[] = [];
  if (actionKey === 1) {
    if (gender === "male") {
      out.push("read_male", "read");
    } else {
      out.push("read_female", "read");
    }
    return out;
  }
  if (gender === "male") {
    const p = MALE_ACTION_PREFIX[actionKey];
    if (p) {
      out.push(p);
    }
  } else {
    const p = FEMALE_ACTION_PREFIX[actionKey];
    if (p) {
      out.push(p);
    }
  }
  const neutral = ACTION_FRAME_PREFIX[actionKey];
  if (neutral) {
    out.push(neutral);
  }
  return out;
}

/**
 * 讀取並快取 `assets/training_fx/manifest.json`（失敗則為 null）。
 */
async function loadManifestOnce(): Promise<Record<string, string[]> | null> {
  if (manifestPromise == null) {
    manifestPromise = (async () => {
      try {
        const r = await fetch(assetUrl("assets/training_fx/manifest.json"), {
          cache: "no-store",
        });
        if (!r.ok) {
          return null;
        }
        const raw: unknown = await r.json();
        if (!raw || typeof raw !== "object") {
          return null;
        }
        const o = raw as Record<string, unknown>;
        const out: Record<string, string[]> = {};
        for (const [k, v] of Object.entries(o)) {
          if (typeof k !== "string") {
            continue;
          }
          if (typeof v === "string" && v.trim() !== "") {
            out[k] = [v.trim()];
          } else if (Array.isArray(v)) {
            const names = v.filter((x): x is string => typeof x === "string" && x.trim() !== "");
            if (names.length > 0) {
              out[k] = names.map((s) => s.trim());
            }
          }
        }
        return out;
      } catch {
        return null;
      }
    })();
  }
  return manifestPromise;
}

/**
 * 自 manifest 鍵取得 URL 列表（檔名相對 `training_fx/`）。
 *
 * @param manifest - manifest 物件
 * @param actionKey - 1～8
 * @param gender - 性別
 */
function urlsFromManifest(
  manifest: Record<string, string[]> | null,
  actionKey: number,
  gender: "male" | "female",
): string[] {
  if (manifest == null) {
    return [];
  }
  const keys =
    gender === "male"
      ? [`${actionKey}_male`, String(actionKey)]
      : [`${actionKey}_female`, String(actionKey)];
  const out: string[] = [];
  for (const key of keys) {
    const list = manifest[key];
    if (!list) {
      continue;
    }
    for (const fn of list) {
      const f = fn.replace(/^\/+/, "");
      const u = assetUrl(`assets/training_fx/${f}`);
      if (!out.includes(u)) {
        out.push(u);
      }
    }
  }
  return out;
}

/**
 * 產生插圖載入遞補 URL 清單（manifest 優先，其餘依檔名慣例）。
 *
 * @param actionKey - 培養 1～8
 * @param gender - 主角性別
 */
export async function buildTrainingFeedbackImageUrlCandidates(
  actionKey: number,
  gender: "male" | "female",
): Promise<string[]> {
  const manifest = await loadManifestOnce();
  const fromM = urlsFromManifest(manifest, actionKey, gender);
  const rest: string[] = [];
  for (const p of orderedPrefixesForAction(actionKey, gender)) {
    pushPrefixUrls(p, rest);
  }
  const merged = [...fromM];
  for (const u of rest) {
    if (!merged.includes(u)) {
      merged.push(u);
    }
  }
  return merged;
}
