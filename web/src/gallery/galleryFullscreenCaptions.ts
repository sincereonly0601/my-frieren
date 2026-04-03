/**
 * 夥伴／強敵／獎勵畫廊大圖底欄文案（對齊桌面 `draw_companion_cg_fullscreen`／`draw_encounter_cg_fullscreen`／`reward_gallery_footer_source_zh` 所用資料源）。
 */

import type { EncounterEnemyJson, WhimEncounterJson } from "../sim/types";
import rewardCaptionsByRel from "../sim/data/gallery_reward_captions.json";

/** 與桌面 `_normalize_footer_blob_continuous_zh` 相同：`"".join(s.split())` 併成單段連續 */
export function normalizeFooterBlobContinuousZh(text: string): string {
  const s = (text ?? "").trim();
  if (!s) {
    return s;
  }
  return s.split(/\s+/).join("");
}

/** 與桌面 `_encounter_gallery_intro_default_zh` 相同 */
const ENCOUNTER_GALLERY_INTRO_DEFAULT_ZH =
  "遭遇戰圖為遊戲內設計，外觀未必與劇中一一對應；" +
  "魔物擅用地形與視線，魔法使靠距離與詠唱節奏，先讀環境與威脅層次再談反擊，別在迷霧裡先慌了腳步。";

/** 與桌面 `reward_gallery_scene_fallback_zh` 相同（token 未用於文案） */
const REWARD_SCENE_FALLBACK_ZH =
  "多條結局線交會後解鎖的紀念構圖，燈火與咒文微光依場景再演繹；不同人生的殘響疊進同一畫框，像把長旅剪成一格靜照。" +
  "畫框裡不必交代來龍去脈，只要仍記得當初為何出發；邊緣光暈顫著，像把回憶調到剛好能看清。";

const REWARD_CAPTIONS = rewardCaptionsByRel as Record<string, string>;

/**
 * 同行的夥伴全螢幕底欄敘述（對齊桌面 `_companion_gallery_desc_short`）。
 *
 * @param meta - 奇遇資料
 */
export function companionGalleryDescShort(meta: WhimEncounterJson): string {
  const authored = normalizeFooterBlobContinuousZh(meta.gallery_footer_zh ?? "");
  if (authored) {
    return authored;
  }
  const head = `${meta.location_zh}——${meta.epithet}。`;
  for (const para of [meta.preamble_para1, meta.preamble_para2]) {
    const raw = normalizeFooterBlobContinuousZh(para ?? "");
    if (!raw) {
      continue;
    }
    for (const seg of raw.split("。")) {
      const t = seg.trim();
      if (t) {
        return head + t + "。";
      }
    }
  }
  return head;
}

/**
 * 強敵畫廊全螢幕底欄（對齊桌面 `_encounter_gallery_footer_blob`）。
 *
 * @param enemy - 敵方定義
 */
export function encounterGalleryFooterBlob(enemy: EncounterEnemyJson): string {
  const raw = normalizeFooterBlobContinuousZh(enemy.gallery_intro_zh ?? "");
  return raw || ENCOUNTER_GALLERY_INTRO_DEFAULT_ZH;
}

/**
 * 與桌面 `_reward_footer_blob_continuous_zh` 相同
 *
 * @param text - 原始文案
 */
function rewardFooterBlobContinuousZh(text: string): string {
  return normalizeFooterBlobContinuousZh(text);
}

/**
 * 獎勵全螢幕底欄單段敘述（對齊桌面 `reward_gallery_footer_source_zh`）。
 *
 * @param rel - 如 `assets/cg/rewards/denken.jpg`
 * @param rewardNoteZh - 館藏註解；無則查表或泛用文
 * @param token - 規範 token（`+` 分隔）
 */
export function rewardGalleryFooterSourceZh(
  rel: string,
  rewardNoteZh: string | null | undefined,
  _token: string,
): string {
  void _token;
  const relN = rel.replace(/\\/g, "/").trim();
  let raw: string;
  if (rewardNoteZh != null && rewardNoteZh.trim() !== "") {
    raw = rewardNoteZh.trim();
  } else {
    const cap = REWARD_CAPTIONS[relN];
    if (cap != null && cap.trim() !== "") {
      raw = cap.trim();
    } else {
      raw = REWARD_SCENE_FALLBACK_ZH;
    }
  }
  return rewardFooterBlobContinuousZh(raw);
}
