/**
 * 培養結算回饋文案（對齊 `training_actions.py`／桌面 `format_training_feedback_modal_message`）。
 */

import {
  formatActionStatEffectsLine,
  type TrainingAction,
} from "./trainingActions";

/** 女性主角敘事（鍵 1～8）；勿含全形「：」以免與標題切分衝突。 */
const TRAINING_FEEDBACK_LINES_FEMALE: Record<number, string> = {
  1: "她抱著厚重的術典蜷在燈下，一頁頁把註解與咒紋對齊，反覆驗證哪一筆轉折才說得通。等到最後一道式子終於串起來，窗紙已泛白；她揉揉眼眶，卻覺得思緒比入夜前更清澈。",
  2: "她在操場邊反覆調整步伐與呼吸，木樁、繩梯與負重輪番磨著肩臂與核心。汗水浸透衣襟時，教頭只點了點頭，她知道自己又撐過了一道門檻，吐息也跟著沉了下來。",
  3: "她跪在微涼的石板地上，讀經的聲音與燭火一樣低而堅定，雜念像被一句句壓進地裡。散席後步出迴廊，風裡帶著潮氣，她忽然覺得胸口鬆了一寸，腳步也輕了些。",
  4: "學姊帶來新茶與城裡的消息，她起初只敢聽，後來也慢慢說起自己的練習與糗事。笑聲落定時，她才發現手心不再那麼汗溼，話匣子竟捨不得闔上，連耳朵都還留著餘溫。",
  5: "作坊裡堆滿待補的布袋與秤錘，她挽起袖口從開市忙到收攤，指尖被麻繩磨得發熱。老闆娘塞給她一碗熱湯麵，說這孩子手快心細；她低頭吹湯，嘴角藏不住得意，也藏不住對人情的踏實感。",
  6: "案上墨香若有若無，她照字帖一筆一畫寫下去，雜念像被行筆壓進紙裡。抄到末行抬頭，窗外鳥鳴忽然清晰，心神竟比開筆前更穩，連指尖的顫意都淡了。",
  7: "她提著藥包與舊衣走巷串戶，替長者磨墨、替孩童講一段故事，也順手記下誰家缺米缺柴。回程的路上簿子記滿名字與囑咐，雖累卻覺得胸口被什麼溫溫地填滿，腳步仍願意多繞一條街。",
  8: "四下無人時，她把平日學到的招式拆開又縫合，一次次修正錯力與換氣的節奏。月昇到中天，影子反倒短了；她收勢吐息，身體記住了今天多撐住的那一瞬，心裡也多了一分安靜的把握。",
};

/** 男性主角敘事（鍵 1～8）。 */
const TRAINING_FEEDBACK_LINES_MALE: Record<number, string> = {
  1: "他抱著厚重的術典蜷在燈下，一頁頁把註解與咒紋對齊，反覆驗證哪一筆轉折才說得通。等到最後一道式子終於串起來，窗紙已泛白；他揉揉眼眶，卻覺得思緒比入夜前更清澈。",
  2: "他在操場邊反覆調整步伐與呼吸，木樁、繩梯與負重輪番磨著肩臂與核心。汗水浸透衣襟時，教頭只點了點頭，他知道自己又撐過了一道門檻，吐息也跟著沉了下來。",
  3: "他跪在微涼的石板地上，讀經的聲音與燭火一樣低而堅定，雜念像被一句句壓進地裡。散席後步出迴廊，風裡帶著潮氣，他忽然覺得胸口鬆了一寸，腳步也輕了些。",
  4: "學長帶來新茶與城裡的消息，他起初只敢聽，後來也慢慢說起自己的練習與糗事。笑聲落定時，他才發現手心不再那麼汗溼，話匣子竟捨不得闔上，連耳朵都還留著餘溫。",
  5: "作坊裡堆滿待補的布袋與秤錘，他挽起袖口從開市忙到收攤，指尖被麻繩磨得發熱。老闆塞給他一碗熱湯麵，說這小子手快心細；他低頭吹湯，嘴角藏不住得意，也藏不住對人情的踏實感。",
  6: "案上墨香若有若無，他照字帖一筆一畫寫下去，雜念像被行筆壓進紙裡。抄到末行抬頭，窗外鳥鳴忽然清晰，心神竟比開筆前更穩，連指尖的顫意都淡了。",
  7: "他提著藥包與舊衣走巷串戶，替長者磨墨、替孩童講一段故事，也順手記下誰家缺米缺柴。回程的路上簿子記滿名字與囑咐，雖累卻覺得胸口被什麼溫溫地填滿，腳步仍願意多繞一條街。",
  8: "四下無人時，他把平日學到的招式拆開又縫合，一次次修正錯力與換氣的節奏。月昇到中天，影子反倒短了；他收勢吐息，身體記住了今天多撐住的那一瞬，心裡也多了一分安靜的把握。",
};

/**
 * 單則培養敘事（依性別與鍵）。
 *
 * @param keyNum - 1～8
 * @param genderKey - 主角性別
 */
export function trainingFeedbackLine(
  keyNum: number,
  genderKey: "male" | "female",
): string {
  const table =
    genderKey === "male" ? TRAINING_FEEDBACK_LINES_MALE : TRAINING_FEEDBACK_LINES_FEMALE;
  const hit = table[keyNum];
  if (hit) {
    return hit;
  }
  return genderKey === "male"
    ? "他把這一季的努力，悄悄落在明天。"
    : "她把這一季的努力，悄悄落在明天。";
}

/**
 * 與桌面 `format_training_feedback_modal_message` 相同之單行（供以最後一組全形括號切統計列）。
 *
 * @param action - 培養指令
 * @param genderKey - 主角性別
 */
export function formatTrainingFeedbackModalMessage(
  action: TrainingAction,
  genderKey: "male" | "female",
): string {
  const narrative = trainingFeedbackLine(action.keyNum, genderKey);
  const stats = formatActionStatEffectsLine(action);
  return `${action.title}：${narrative}　（${stats}）`;
}

/**
 * 以最後一組全形「（…）」拆出數值摘要（對齊桌面 `draw_training_feedback_modal`）。
 *
 * @param message - {@link formatTrainingFeedbackModalMessage} 產物
 */
export function splitTrainingFeedbackStatParen(message: string): {
  bodyBeforeParen: string;
  statLine: string;
} {
  const lpar = message.lastIndexOf("（");
  const rpar = message.lastIndexOf("）");
  if (lpar >= 0 && rpar > lpar) {
    return {
      bodyBeforeParen: message.slice(0, lpar).trim(),
      statLine: message.slice(lpar + 1, rpar).trim(),
    };
  }
  return { bodyBeforeParen: message.trim(), statLine: "" };
}

/**
 * 將括號前內文拆成「行動名：」與敘事（對齊桌面 `_split_training_feedback_body`）。
 *
 * @param body - 全形括號之前的字串
 */
export function splitTrainingFeedbackActionLead(body: string): {
  lead: string;
  narrative: string;
} {
  const idx = body.indexOf("：");
  if (idx <= 0) {
    return { lead: "", narrative: body.trim() };
  }
  const lead = body.slice(0, idx + 1).trim();
  const narrative = body.slice(idx + 1).trim();
  if (!narrative) {
    return { lead: "", narrative: body.trim() };
  }
  return { lead, narrative };
}
