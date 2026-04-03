/**
 * 本機持久化（IndexedDB）。v3 之 `game` 與桌面版 `game_state.GameState.to_json_dict()` 鍵名一致；
 * `adopterQuizAnswers` 僅網頁聖堂問卷用，置於信封層（桌面無此欄）。
 */

const DB_NAME = "frieren-factory-web";
const DB_VERSION = 1;
const STORE = "meta";
/** 舊版單一存檔鍵（遷移後寫入欄位 1 並刪除） */
const SAVE_KEY_LEGACY = "gameSaveV1";
/** 目前使用中的欄位 1～4 */
const KEY_ACTIVE_SLOT = "activeSaveSlot";

/** 與桌面 `save_slots.SLOT_COUNT` 一致 */
export const SAVE_SLOT_COUNT = 4;

/**
 * @param slotIndex - 1～{@link SAVE_SLOT_COUNT}
 */
function saveSlotKey(slotIndex: number): string {
  return `saveSlot_${slotIndex}`;
}

/** 與桌面版一致：60 季、自 3 歲（36 個月）起算 */
export const TOTAL_TRAINING_QUARTERS = 60;
export const START_AGE_MONTHS = 36;

/**
 * 舊版僅計數；讀取時會遷移。
 */
export type GameSaveV1 = {
  schemaVersion: 1;
  placeholderVisits: number;
  lastSavedAt: string;
};

/** 人生階段（桌面 `phase`） */
export type WebMiniPhase = "childhood" | "adolescence" | "young_adult";

/**
 * 與桌面 `GameState` JSON 快照同鍵名（`to_json_dict`／`save.json`）。
 */
export type GameStateStored = {
  time_left: number;
  int_stat: number;
  str_stat: number;
  fth_stat: number;
  pragmatic: number;
  romantic: number;
  solitude: number;
  social: number;
  truth_seek: number;
  corruption: number;
  flags: string[];
  magic_ids: string[];
  phase: WebMiniPhase;
  intro_done: boolean;
  heroine_name: string;
  protagonist_gender: "male" | "female";
  guardian_intro_done: boolean;
  onboarding_complete: boolean;
  saved_at: string;
  incident_years_fired: number[];
  incident_ids_fired: string[];
  major_years_fired: number[];
  encounter_years_fired: number[];
  whim_slots: number[];
  whim_npc_keys: string[];
  whim_question_indices: number[];
  whim_fired: boolean[];
};

/**
 * v2 信封內 `game`（camelCase）；僅用於自舊存檔遷移。
 */
type LegacyV2Game = {
  timeLeft: number;
  heroineName: string;
  protagonistGender: "male" | "female";
  phase: WebMiniPhase;
  introDone: boolean;
  guardianIntroDone: boolean;
  onboardingComplete: boolean;
  intStat: number;
  strStat: number;
  socialStat: number;
  fthStat: number;
  pragmaticStat: number;
  romanticStat: number;
  solitudeStat: number;
  /** v2 曾誤放在 `game` 內 */
  adopterQuizAnswers?: [number, number, number, number, number] | null;
};

/**
 * 目前寫入格式（v3）。
 */
export type GameSaveV3 = {
  schemaVersion: 3;
  placeholderVisits: number;
  lastSavedAt: string;
  game: GameStateStored;
  /** 網頁聖堂問卷五題；桌面 GameState 無此欄 */
  adopterQuizAnswers: [number, number, number, number, number] | null;
};

/** 非持久化工作中進度（停用自動存檔時供場景銜接） */
let volatileWorkingSave: GameSaveV3 | null = null;

/** @deprecated 請改用 {@link GameSaveV3}；保留型別名供外部相容 */
export type GameSaveV2 = GameSaveV3;

/** 與 {@link GameStateStored} 同義（舊名） */
export type WebMiniState = GameStateStored;

/**
 * 新局 `game` 預設（對照桌面 `GameState` dataclass 預設）。
 */
export function defaultGameStateStored(): GameStateStored {
  return {
    time_left: TOTAL_TRAINING_QUARTERS,
    int_stat: 0,
    str_stat: 0,
    fth_stat: 0,
    pragmatic: 0,
    romantic: 0,
    solitude: 0,
    social: 0,
    truth_seek: 0,
    corruption: 0,
    flags: [],
    magic_ids: [],
    phase: "childhood",
    intro_done: false,
    heroine_name: "",
    protagonist_gender: "male",
    guardian_intro_done: false,
    onboarding_complete: false,
    saved_at: "",
    incident_years_fired: [],
    incident_ids_fired: [],
    major_years_fired: [],
    encounter_years_fired: [],
    whim_slots: [],
    whim_npc_keys: [],
    whim_question_indices: [],
    whim_fired: [],
  };
}

/** @deprecated 請改用 {@link defaultGameStateStored} */
export function defaultWebMiniState(): GameStateStored {
  return defaultGameStateStored();
}

/**
 * 空存檔信封（新遊戲／重置進度）。
 */
export function emptyGameSaveV3(): GameSaveV3 {
  return {
    schemaVersion: 3,
    placeholderVisits: 0,
    lastSavedAt: new Date().toISOString(),
    game: defaultGameStateStored(),
    adopterQuizAnswers: null,
  };
}

/**
 * 與桌面 `_make_cheat_bootstrap_state` 對齊：屬性偏高；但不直接跳過開場流程。
 */
export function makeCheatBootstrapGameSaveV3(): GameSaveV3 {
  const base = emptyGameSaveV3();
  const g = { ...base.game };
  g.int_stat = 55;
  g.str_stat = 55;
  g.fth_stat = 55;
  g.pragmatic = 55;
  g.romantic = 0;
  g.solitude = 0;
  g.social = 55;
  g.truth_seek = 12;
  g.corruption = 0;
  g.saved_at = new Date().toISOString();
  // `intro_done` / `guardian_intro_done` / `onboarding_complete` 保持預設值，
  // 讓玩家仍可正常通過前言流程；屬性加成則從本輪開始即生效。
  return {
    ...base,
    game: g,
    lastSavedAt: new Date().toISOString(),
  };
}

/**
 * 依剩餘季數推算目前年齡（月數），與桌面版每季 3 個月、自 3 歲（36 月）起算一致。
 *
 * @param timeLeft - 剩餘季數 0～60
 */
export function ageMonthsFromTimeLeft(timeLeft: number): number {
  const tl = Math.max(0, Math.min(TOTAL_TRAINING_QUARTERS, timeLeft));
  const spent = TOTAL_TRAINING_QUARTERS - tl;
  return START_AGE_MONTHS + spent * 3;
}

/**
 * 依剩餘季數推算人生階段（與桌面版 `refresh_life_phase` 規則一致）。
 *
 * @param timeLeft - 剩餘季數 0～60
 */
export function phaseFromTimeLeft(timeLeft: number): WebMiniPhase {
  const ageMonths = ageMonthsFromTimeLeft(timeLeft);
  const ay = Math.floor(ageMonths / 12);
  if (ay < 8) {
    return "childhood";
  }
  if (ay < 13) {
    return "adolescence";
  }
  return "young_adult";
}

/**
 * 寫入前將 `game.phase` 與 `time_left` 對齊。
 *
 * @param game - 可變狀態
 */
export function syncPhaseFromTimeLeft(game: GameStateStored): void {
  game.phase = phaseFromTimeLeft(game.time_left);
}

function parseStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((x): x is string => typeof x === "string");
}

function parseNumberArray(raw: unknown): number[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((x): x is number => typeof x === "number" && Number.isFinite(x));
}

function parseBoolArray(raw: unknown): boolean[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((x): x is boolean => typeof x === "boolean");
}

/**
 * 由任意物件補齊為完整 {@link GameStateStored}（相容桌面 `from_json_dict` 寬鬆度）。
 *
 * @param o - 原始 `game` 物件
 */
export function normalizeGameStateStored(o: unknown): GameStateStored | null {
  if (!o || typeof o !== "object") {
    return null;
  }
  const g = o as Record<string, unknown>;
  const z = defaultGameStateStored();

  const time_left =
    typeof g.time_left === "number" ? g.time_left : typeof g.timeLeft === "number" ? g.timeLeft : null;
  if (time_left === null) {
    return null;
  }

  const heroine_name =
    typeof g.heroine_name === "string"
      ? g.heroine_name
      : typeof g.heroineName === "string"
        ? g.heroineName
        : null;
  if (heroine_name === null) {
    return null;
  }

  let protagonist_gender: "male" | "female" = "male";
  const pg = g.protagonist_gender ?? g.protagonistGender;
  if (pg === "female" || pg === "male") {
    protagonist_gender = pg;
  }

  let phase: WebMiniPhase = z.phase;
  const ph = g.phase;
  if (ph === "childhood" || ph === "adolescence" || ph === "young_adult") {
    phase = ph;
  }

  const legacyNoIntro =
    !Object.prototype.hasOwnProperty.call(g, "intro_done") &&
    !Object.prototype.hasOwnProperty.call(g, "introDone");
  const intro_done =
    typeof g.intro_done === "boolean"
      ? g.intro_done
      : typeof g.introDone === "boolean"
        ? g.introDone
        : legacyNoIntro
          ? true
          : false;

  const legacyNoGuardian =
    !Object.prototype.hasOwnProperty.call(g, "guardian_intro_done") &&
    !Object.prototype.hasOwnProperty.call(g, "guardianIntroDone");
  const onboarding_complete =
    typeof g.onboarding_complete === "boolean"
      ? g.onboarding_complete
      : typeof g.onboardingComplete === "boolean"
        ? g.onboardingComplete
        : false;
  const guardian_intro_done =
    typeof g.guardian_intro_done === "boolean"
      ? g.guardian_intro_done
      : typeof g.guardianIntroDone === "boolean"
        ? g.guardianIntroDone
        : legacyNoGuardian
          ? heroine_name.trim() !== "" || onboarding_complete === true
          : false;

  const int_stat = typeof g.int_stat === "number" ? g.int_stat : typeof g.intStat === "number" ? g.intStat : z.int_stat;
  const str_stat = typeof g.str_stat === "number" ? g.str_stat : typeof g.strStat === "number" ? g.strStat : z.str_stat;
  const fth_stat = typeof g.fth_stat === "number" ? g.fth_stat : typeof g.fthStat === "number" ? g.fthStat : z.fth_stat;
  const social =
    typeof g.social === "number"
      ? g.social
      : typeof g.socialStat === "number"
        ? g.socialStat
        : z.social;
  const pragmatic =
    typeof g.pragmatic === "number"
      ? g.pragmatic
      : typeof g.pragmaticStat === "number"
        ? g.pragmaticStat
        : z.pragmatic;
  const romantic =
    typeof g.romantic === "number"
      ? g.romantic
      : typeof g.romanticStat === "number"
        ? g.romanticStat
        : z.romantic;
  const solitude =
    typeof g.solitude === "number"
      ? g.solitude
      : typeof g.solitudeStat === "number"
        ? g.solitudeStat
        : z.solitude;
  const truth_seek = typeof g.truth_seek === "number" ? g.truth_seek : z.truth_seek;
  const corruption = typeof g.corruption === "number" ? g.corruption : z.corruption;

  const flagsRaw = g.flags;
  const flags = Array.isArray(flagsRaw)
    ? [...new Set(parseStringArray(flagsRaw))].sort()
    : [];

  return {
    time_left,
    int_stat,
    str_stat,
    fth_stat,
    pragmatic,
    romantic,
    solitude,
    social,
    truth_seek,
    corruption,
    flags,
    magic_ids: parseStringArray(g.magic_ids),
    phase,
    intro_done,
    heroine_name,
    protagonist_gender,
    guardian_intro_done,
    onboarding_complete,
    saved_at: typeof g.saved_at === "string" ? g.saved_at : "",
    incident_years_fired: parseNumberArray(g.incident_years_fired),
    incident_ids_fired: parseStringArray(g.incident_ids_fired),
    major_years_fired: parseNumberArray(g.major_years_fired).map((n) =>
      n === 16 || n === 18 ? 17 : n,
    ),
    encounter_years_fired: parseNumberArray(g.encounter_years_fired),
    whim_slots: parseNumberArray(g.whim_slots),
    whim_npc_keys: parseStringArray(g.whim_npc_keys),
    whim_question_indices: parseNumberArray(g.whim_question_indices),
    whim_fired: parseBoolArray(g.whim_fired),
  };
}

/**
 * @param raw - 存檔內問卷答案
 */
function parseAdopterQuizAnswers(
  raw: unknown,
): [number, number, number, number, number] | null {
  if (!Array.isArray(raw) || raw.length !== 5) {
    return null;
  }
  const out: number[] = [];
  for (const x of raw) {
    if (typeof x !== "number" || !Number.isInteger(x) || x < 0 || x > 2) {
      return null;
    }
    out.push(x);
  }
  return out as [number, number, number, number, number];
}

function parseLegacyV2GameStrict(o: unknown): LegacyV2Game | null {
  if (!o || typeof o !== "object") {
    return null;
  }
  const g = o as Record<string, unknown>;
  if (
    typeof g.timeLeft !== "number" ||
    typeof g.heroineName !== "string" ||
    (g.protagonistGender !== "male" && g.protagonistGender !== "female") ||
    (g.phase !== "childhood" && g.phase !== "adolescence" && g.phase !== "young_adult") ||
    typeof g.onboardingComplete !== "boolean" ||
    typeof g.intStat !== "number" ||
    typeof g.strStat !== "number" ||
    typeof g.fthStat !== "number"
  ) {
    return null;
  }
  const z = defaultGameStateStored();
  const legacyNoIntroKey = !Object.prototype.hasOwnProperty.call(g, "introDone");
  const introDone =
    typeof g.introDone === "boolean" ? g.introDone : legacyNoIntroKey ? true : false;
  const legacyNoGuardianKey = !Object.prototype.hasOwnProperty.call(g, "guardianIntroDone");
  const guardianIntroDone =
    typeof g.guardianIntroDone === "boolean"
      ? g.guardianIntroDone
      : legacyNoGuardianKey
        ? g.heroineName.trim() !== "" || g.onboardingComplete === true
        : false;
  return {
    timeLeft: g.timeLeft,
    heroineName: g.heroineName,
    protagonistGender: g.protagonistGender,
    phase: g.phase,
    introDone,
    guardianIntroDone,
    onboardingComplete: g.onboardingComplete,
    intStat: g.intStat,
    strStat: g.strStat,
    fthStat: g.fthStat,
    socialStat: typeof g.socialStat === "number" ? g.socialStat : z.social,
    pragmaticStat: typeof g.pragmaticStat === "number" ? g.pragmaticStat : z.pragmatic,
    romanticStat: typeof g.romanticStat === "number" ? g.romanticStat : z.romantic,
    solitudeStat: typeof g.solitudeStat === "number" ? g.solitudeStat : z.solitude,
    adopterQuizAnswers: parseAdopterQuizAnswers(g.adopterQuizAnswers) ?? undefined,
  };
}

function legacyV2GameToStored(legacy: LegacyV2Game): GameStateStored {
  const g = legacy;
  return {
    ...defaultGameStateStored(),
    time_left: g.timeLeft,
    heroine_name: g.heroineName,
    protagonist_gender: g.protagonistGender,
    phase: g.phase,
    intro_done: g.introDone,
    guardian_intro_done: g.guardianIntroDone,
    onboarding_complete: g.onboardingComplete,
    int_stat: g.intStat,
    str_stat: g.strStat,
    fth_stat: g.fthStat,
    social: g.socialStat,
    pragmatic: g.pragmaticStat,
    romantic: g.romanticStat,
    solitude: g.solitudeStat,
  };
}

function migrateV2EnvelopeToV3(v2: {
  schemaVersion: 2;
  placeholderVisits: number;
  lastSavedAt: string;
  game: LegacyV2Game;
}): GameSaveV3 {
  const quizFromGame =
    v2.game.adopterQuizAnswers !== undefined
      ? v2.game.adopterQuizAnswers
      : null;
  return {
    schemaVersion: 3,
    placeholderVisits: v2.placeholderVisits,
    lastSavedAt: v2.lastSavedAt,
    adopterQuizAnswers: quizFromGame,
    game: legacyV2GameToStored(v2.game),
  };
}

/**
 * v1 僅計數 → v2 形狀再轉 v3。
 */
function migrateV1ToV3(v1: GameSaveV1): GameSaveV3 {
  const v2Game = defaultGameStateStored();
  /** 轉成 legacy 形狀再統一走 legacyV2GameToStored 會多餘；直接 v3 */
  return {
    schemaVersion: 3,
    placeholderVisits: v1.placeholderVisits,
    lastSavedAt: v1.lastSavedAt,
    adopterQuizAnswers: null,
    game: v2Game,
  };
}

function normalizeRawSave(raw: unknown): GameSaveV3 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const ver = o.schemaVersion;

  if (ver === 3) {
    const visits = o.placeholderVisits;
    const at = o.lastSavedAt;
    const gameRaw = o.game;
    const parsed = normalizeGameStateStored(gameRaw);
    if (typeof visits !== "number" || typeof at !== "string" || parsed == null) {
      return null;
    }
    const quiz =
      parseAdopterQuizAnswers(o.adopterQuizAnswers) ??
      (gameRaw && typeof gameRaw === "object" && "adopterQuizAnswers" in (gameRaw as object)
        ? parseAdopterQuizAnswers(
            (gameRaw as Record<string, unknown>).adopterQuizAnswers,
          )
        : null);
    return {
      schemaVersion: 3,
      placeholderVisits: visits,
      lastSavedAt: at,
      game: parsed,
      adopterQuizAnswers: quiz,
    };
  }

  if (ver === 2) {
    const visits = o.placeholderVisits;
    const at = o.lastSavedAt;
    const game = o.game;
    const parsed = parseLegacyV2GameStrict(game);
    if (typeof visits !== "number" || typeof at !== "string" || parsed == null) {
      return null;
    }
    return migrateV2EnvelopeToV3({
      schemaVersion: 2,
      placeholderVisits: visits,
      lastSavedAt: at,
      game: parsed,
    });
  }

  if (ver === 1) {
    const visits = o.placeholderVisits;
    const at = o.lastSavedAt;
    if (typeof visits !== "number" || typeof at !== "string") {
      return null;
    }
    return migrateV1ToV3({
      schemaVersion: 1,
      placeholderVisits: visits,
      lastSavedAt: at,
    });
  }

  return null;
}

let migrationPromise: Promise<void> | null = null;

/**
 * 將舊鍵 `gameSaveV1` 併入欄位 1（僅當欄位 1 尚無資料時），並刪除舊鍵。
 *
 * @param db - 已開啟之 DB
 */
async function migrateLegacySaveIntoSlots(db: IDBDatabase): Promise<void> {
  const legacyRaw: unknown = await idbGet(db, SAVE_KEY_LEGACY);
  if (legacyRaw == null) {
    return;
  }
  const normalized = normalizeRawSave(legacyRaw);
  if (normalized == null) {
    return;
  }
  const slot1Raw: unknown = await idbGet(db, saveSlotKey(1));
  if (slot1Raw == null) {
    await idbPut(db, saveSlotKey(1), normalized);
  }
  /** 欄位 1 已有資料時仍以欄位為準；舊鍵僅遷移一次後移除 */
  await idbDelete(db, SAVE_KEY_LEGACY);
}

/**
 * 確保已完成單槽→五槽遷移（全程序共用單次 Promise）。
 */
function ensureSlotsMigrated(): Promise<void> {
  if (migrationPromise == null) {
    migrationPromise = (async () => {
      const db = await openDb();
      try {
        await migrateLegacySaveIntoSlots(db);
      } finally {
        db.close();
      }
    })().catch((e) => {
      migrationPromise = null;
      throw e;
    });
  }
  return migrationPromise;
}

/**
 * @param db - 已開啟之 DB
 * @param key - object store 鍵
 */
function idbGet(db: IDBDatabase, key: string): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    tx.onerror = (): void => {
      reject(tx.error ?? new Error("idb get tx"));
    };
    const req = tx.objectStore(STORE).get(key);
    req.onerror = (): void => {
      reject(req.error ?? new Error("idb get"));
    };
    req.onsuccess = (): void => {
      resolve(req.result);
    };
  });
}

/**
 * @param db - 已開啟之 DB
 * @param key - 鍵
 * @param value - 值
 */
function idbPut(db: IDBDatabase, key: string, value: unknown): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = (): void => {
      resolve();
    };
    tx.onerror = (): void => {
      reject(tx.error ?? new Error("idb put tx"));
    };
    tx.objectStore(STORE).put(value, key);
  });
}

/**
 * @param db - 已開啟之 DB
 * @param key - 鍵
 */
function idbDelete(db: IDBDatabase, key: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = (): void => {
      resolve();
    };
    tx.onerror = (): void => {
      reject(tx.error ?? new Error("idb delete tx"));
    };
    tx.objectStore(STORE).delete(key);
  });
}

/**
 * 由剩餘季數推算存檔摘要用年紀字串（對齊桌面 `save_slots._age_phrase_from_time_left`）。
 *
 * @param timeLeft - 剩餘季數
 */
export function agePhraseFromTimeLeftZh(timeLeft: number): string {
  const tl = Math.max(0, Math.min(TOTAL_TRAINING_QUARTERS, Math.floor(timeLeft)));
  const am = START_AGE_MONTHS + (TOTAL_TRAINING_QUARTERS - tl) * 3;
  return `${Math.floor(am / 12)} 歲 ${am % 12} 個月`;
}

/**
 * ISO 時間轉本地顯示（對齊桌面 `save_slots._format_saved_at_local`）。
 *
 * @param isoStr - `lastSavedAt` 或 `game.saved_at`
 */
export function formatSavedAtLocalZh(isoStr: string): string {
  const s = (isoStr ?? "").trim();
  if (!s) {
    return "（尚無記錄時間）";
  }
  try {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) {
      return s;
    }
    const pad = (n: number): string => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return s;
  }
}

/**
 * 單欄存檔列表列用摘要。
 */
export type SaveSlotSummary = {
  /** 1～4 */
  slotIndex: number;
  /** 無存檔或可視為全新空欄 */
  empty: boolean;
  heroineName: string;
  genderZh: string;
  agePhrase: string;
  savedAtLocal: string;
};

/**
 * 是否為「空欄」（新局尚未推進，供新遊戲挑欄位用）。
 *
 * @param save - 存檔
 */
export function isVacantSaveSlot(save: GameSaveV3): boolean {
  const g = save.game;
  const statSum =
    g.int_stat +
    g.str_stat +
    g.social +
    g.fth_stat +
    g.pragmatic +
    g.romantic +
    g.solitude;
  return (
    save.placeholderVisits === 0 &&
    !g.intro_done &&
    !g.onboarding_complete &&
    g.heroine_name.trim() === "" &&
    g.time_left === TOTAL_TRAINING_QUARTERS &&
    statSum === 0
  );
}

/**
 * 主選單／讀檔選單意義下是否可視為已有遊戲進度（與舊單槽邏輯一致）。
 *
 * @param save - 存檔
 */
export function saveHasMenuContinueProgress(save: GameSaveV3): boolean {
  if (save.placeholderVisits > 0) {
    return true;
  }
  const g = save.game;
  if (!g.intro_done || !g.onboarding_complete) {
    return true;
  }
  return (
    g.time_left < TOTAL_TRAINING_QUARTERS ||
    g.heroine_name.trim() !== "" ||
    g.int_stat +
      g.str_stat +
      g.social +
      g.fth_stat +
      g.pragmatic +
      g.romantic +
      g.solitude >
      0 ||
    g.onboarding_complete
  );
}

/**
 * 讀取指定欄位存檔（不變更使用中欄位）。
 *
 * @param slotIndex - 1～{@link SAVE_SLOT_COUNT}
 */
export async function loadGameSaveFromSlot(slotIndex: number): Promise<GameSaveV3 | null> {
  if (slotIndex < 1 || slotIndex > SAVE_SLOT_COUNT) {
    return null;
  }
  await ensureSlotsMigrated();
  const db = await openDb();
  try {
    const raw: unknown = await idbGet(db, saveSlotKey(slotIndex));
    return normalizeRawSave(raw);
  } finally {
    db.close();
  }
}

/**
 * 寫入指定欄位（通常請改用 {@link writeGameSave} 寫入目前使用中欄位）。
 *
 * @param slotIndex - 1～{@link SAVE_SLOT_COUNT}
 * @param data - 存檔
 */
export async function writeGameSaveToSlot(slotIndex: number, data: GameSaveV3): Promise<void> {
  if (slotIndex < 1 || slotIndex > SAVE_SLOT_COUNT) {
    throw new Error(`slotIndex 須為 1～${SAVE_SLOT_COUNT}`);
  }
  await ensureSlotsMigrated();
  const db = await openDb();
  try {
    await idbPut(db, saveSlotKey(slotIndex), data);
  } finally {
    db.close();
  }
}

/**
 * @returns 目前使用中欄位 1～4（預設 1）
 */
export async function getActiveSaveSlot(): Promise<number> {
  await ensureSlotsMigrated();
  const db = await openDb();
  try {
    const raw: unknown = await idbGet(db, KEY_ACTIVE_SLOT);
    const n = typeof raw === "number" ? raw : Number(raw);
    if (Number.isInteger(n) && n >= 1 && n <= SAVE_SLOT_COUNT) {
      return n;
    }
    return 1;
  } finally {
    db.close();
  }
}

/**
 * 設定接下來 {@link loadGameSave}／{@link writeGameSave} 所使用之欄位。
 *
 * @param slotIndex - 1～{@link SAVE_SLOT_COUNT}
 */
export async function setActiveSaveSlot(slotIndex: number): Promise<void> {
  if (slotIndex < 1 || slotIndex > SAVE_SLOT_COUNT) {
    throw new Error(`slotIndex 須為 1～${SAVE_SLOT_COUNT}`);
  }
  await ensureSlotsMigrated();
  const db = await openDb();
  try {
    await idbPut(db, KEY_ACTIVE_SLOT, slotIndex);
    volatileWorkingSave = null;
  } finally {
    db.close();
  }
}

/**
 * 有進度之欄位中，依 `lastSavedAt` 取最近一筆。
 *
 * @returns 欄位與存檔；無則 null
 */
export async function getLatestResumableSlot(): Promise<{
  slot: number;
  save: GameSaveV3;
} | null> {
  await ensureSlotsMigrated();
  let best: { t: number; slot: number; save: GameSaveV3 } | null = null;
  for (let i = 1; i <= SAVE_SLOT_COUNT; i += 1) {
    const s = await loadGameSaveFromSlot(i);
    if (s == null || !saveHasMenuContinueProgress(s)) {
      continue;
    }
    const t = Date.parse(s.lastSavedAt) || 0;
    if (best == null || t > best.t) {
      best = { t, slot: i, save: s };
    }
  }
  return best == null ? null : { slot: best.slot, save: best.save };
}

/**
 * 新遊戲時優先使用第一個空欄；若皆滿則回傳 1（將由開場重置覆寫）。
 */
export async function pickSlotForNewGameStart(): Promise<number> {
  await ensureSlotsMigrated();
  for (let i = 1; i <= SAVE_SLOT_COUNT; i += 1) {
    const s = await loadGameSaveFromSlot(i);
    if (s == null || isVacantSaveSlot(s)) {
      return i;
    }
  }
  return 1;
}

/**
 * 四欄摘要（供「讀取進度」選單）。
 */
export async function listSaveSlotSummaries(): Promise<SaveSlotSummary[]> {
  await ensureSlotsMigrated();
  const out: SaveSlotSummary[] = [];
  for (let i = 1; i <= SAVE_SLOT_COUNT; i += 1) {
    const s = await loadGameSaveFromSlot(i);
    if (s == null || isVacantSaveSlot(s)) {
      out.push({
        slotIndex: i,
        empty: true,
        heroineName: "",
        genderZh: "",
        agePhrase: "",
        savedAtLocal: "",
      });
      continue;
    }
    const g = s.game;
    const genderZh = g.protagonist_gender === "female" ? "女" : "男";
    const name = g.heroine_name.trim() || "孩子";
    out.push({
      slotIndex: i,
      empty: false,
      heroineName: name,
      genderZh,
      agePhrase: agePhraseFromTimeLeftZh(g.time_left),
      savedAtLocal: formatSavedAtLocalZh(s.lastSavedAt || g.saved_at),
    });
  }
  return out;
}

function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") {
    return Promise.reject(new Error("此瀏覽器不支援 IndexedDB"));
  }
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = (): void => {
      reject(req.error ?? new Error("IndexedDB open failed"));
    };
    req.onsuccess = (): void => {
      resolve(req.result);
    };
    req.onupgradeneeded = (): void => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
  });
}

/**
 * 讀取目前進度：優先回傳記憶體工作進度；若無再讀取目前使用中欄位。
 */
export async function loadGameSave(): Promise<GameSaveV3 | null> {
  if (volatileWorkingSave != null) {
    return volatileWorkingSave;
  }
  await ensureSlotsMigrated();
  const slot = await getActiveSaveSlot();
  return loadGameSaveFromSlot(slot);
}

/**
 * 更新工作進度（僅記憶體，不寫入 IndexedDB）。
 *
 * @param data - 完整存檔
 */
export async function writeGameSave(data: GameSaveV3): Promise<void> {
  volatileWorkingSave = data;
}

/**
 * 刪除欄位 1～4 與舊版單槽鍵，並將使用中欄位重設為 1。
 */
export async function deleteAllSaveSlots(): Promise<void> {
  await ensureSlotsMigrated();
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.oncomplete = (): void => {
        resolve();
      };
      tx.onerror = (): void => {
        reject(tx.error ?? new Error("deleteAllSaveSlots tx"));
      };
      const os = tx.objectStore(STORE);
      for (let i = 1; i <= SAVE_SLOT_COUNT; i += 1) {
        os.delete(saveSlotKey(i));
      }
      os.delete(SAVE_KEY_LEGACY);
      os.put(1, KEY_ACTIVE_SLOT);
    });
    volatileWorkingSave = null;
  } finally {
    db.close();
  }
}
