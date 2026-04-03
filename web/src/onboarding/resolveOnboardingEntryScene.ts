import type { GameSaveV3 } from "../save/idbSave";

/**
 * 讀檔後應進入的場景鍵（與桌面版 `goto_after_load` 順序對齊的子集）。
 *
 * @param save - 已解析之存檔（v3）
 */
export function resolveOnboardingEntryScene(save: GameSaveV3): string {
  const g = save.game;
  if (!g.intro_done) {
    return "Intro";
  }
  if (g.onboarding_complete) {
    return "Placeholder";
  }
  if (g.heroine_name.trim() !== "") {
    return "OnboardingQuiz";
  }
  return "Guardian";
}
