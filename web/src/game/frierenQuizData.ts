/**
 * Web 版芙莉蓮測驗：沿用桌機版題庫 `whim_questions.json` 與計分規則。
 * 本檔僅提供型別與分數分級工具，不再內含題庫內容。
 */

export type WhimQuestionLike = {
  /** 題目編號（例：q01～q110） */
  qid: string;
  /** 題幹（繁中） */
  stem: string;
  /** 三個選項文字（題庫固定順序 A／B／C） */
  options: [string, string, string];
  /** 正解在 `options` 中的索引 0～2 */
  correct_index: number;
  /** 詳解（可為空字串） */
  explanation_zh?: string;
};

export type FrierenQuizAnswer = {
  question: WhimQuestionLike;
  /** 顯示時的選項排列（長度 3，元素為 0～2，對應題庫索引） */
  perm: [number, number, number];
  /** 玩家實際點選的槽位 0～2 */
  chosenSlot: number;
  /** 此題是否作答正確 */
  correct: boolean;
};

/**
 * 依桌機版規則計算單輪測驗總分（每題 10 分，滿分 100）。
 *
 * @param answers - 本輪所有作答結果
 * @returns 總分（0～100）
 */
export function computeFrierenQuizScore(answers: readonly FrierenQuizAnswer[]): number {
  const correctCount = answers.filter((a) => a.correct).length;
  const perQuestion = 10;
  const total = answers.length * perQuestion;
  const raw = correctCount * perQuestion;
  if (!Number.isFinite(raw) || total <= 0) {
    return 0;
  }
  const clamped = Math.max(0, Math.min(total, raw));
  return clamped;
}

/**
 * 桌機版 `frieren_quiz.frieren_quiz_result_tier` 的 Web 版對應：
 * 依總分（0～100，10 分一級）回傳評級名稱與評語正文。
 *
 * @param score - 本輪總分
 * @returns [評級名稱, 評語單段正文]
 */
export function frierenQuizResultTier(score: number): [string, string] {
  const perQuestion = 10;
  const maxQuestions = 10;
  const total = perQuestion * maxQuestions;
  const s = Math.max(0, Math.min(total, score));
  const idx = Math.min(10, Math.floor(s / 10));
  const tiers: Array<[string, string]> = [
    [
      "尚需啟程",
      "此輪尚未得分，不妨從第一題重新作答，把角色、魔法與時間軸對照動畫或漫畫情節。複習像芙莉蓮整理魔導書，重點在看清因果，作品裡的伏筆會慢慢浮現。",
    ],
    [
      "初窺門徑",
      "你已踏出第一步，片段會連成線；多看幾集、對照台詞與小道具，知識會像民間魔法一樣累積。錯題當成下次遇見同一橋段的伏筆，回頭看詳解印象更深。",
    ],
    [
      "摸索前行",
      "對世界觀已有輪廓，補齊人名、地名與魔法規則就更穩；芙莉蓮的旅途也充滿試錯。把錯題對回原作段落，因果對上了，分數自然往上走。",
    ],
    [
      "漸入佳境",
      "基礎概念逐漸清晰，與精靈的時間感一樣需要耐心；角色動機與事件順序多對照幾次，記憶會更牢。別衝速度，把細節放進心裡，分數只是遲早的事。",
    ],
    [
      "基礎尚可",
      "你已掌握不少設定，再對照關鍵情節與因果，模糊處就能補滿；距離高分往往只差幾題精準度。針對錯題看詳解，先想場景再選，下一輪會更穩。",
    ],
    [
      "中規中矩",
      "整體表現均衡，看得出你認真看過故事；錯題多半在細節或易混稱謂，回頭對照一次就能鎖定。放慢讀題、把選項連回台詞，通常能再衝一個級距。",
    ],
    [
      "及格之上",
      "知識結構已站穩，足以在酒館裡聊上一整晚劇情；若要衝高分，把易混魔法名與角色關係做成小抄很有幫助。能複述因果，再練一輪就更接近滿分。",
    ],
    [
      "良好表現",
      "對主線與人物關係已有紮實理解，疏漏多半是看漏或記混稱謂，回頭補一眼就好。保持節奏，下一輪把錯題清零不難，相似選項上多停一秒更保險。",
    ],
    [
      "優秀水準",
      "答題準確度很高，幾乎能與費倫的筆記本並駕齊驅；差距常在冷門典故或一字之差。把錯題連回原作、對照台詞，最後一哩路跨過去就是滿分邊緣。",
    ],
    [
      "近乎完美",
      "僅一題之差的頂尖表現；那一題多半是極細的設定或表述陷阱。複習錯題與相鄰選項差異，作答時多停一秒確認主詞，滿分就在眼前。你已站在門檻上，冷靜比死背更能帶你跨過去。",
    ],
    [
      "滿分認證",
      "你對《葬送的芙莉蓮》世界觀、人物與情節已融會貫通，能把時間軸與角色心境串成敘事。這份知識像與芙莉蓮一行人並肩理解故事溫度，值得延續到每一次重溫。",
    ],
  ];
  return tiers[idx];
}


