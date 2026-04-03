"""
遊戲會話狀態：時間資源、屬性、劇情旗標、魔法收集與 JSON 存檔。

時間僅在玩家確認執行「會消耗時間」的行為時扣除；選單／對話停頓時不流逝。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAVE_NAME = "save.json"

# 養成總季數：每季代表過去三個月（3／6／9／12 月排程一次），自 3 歲至滿 18 歲共 60 季。
TOTAL_TRAINING_QUARTERS: int = 60
# 遊戲開始時的年齡（月）：3 歲整。
START_AGE_MONTHS: int = 36

# 套用增減值後，數值欄位下限（避免長期負值導致結局判定異常）。
_CLAMP_INT_FIELDS: frozenset[str] = frozenset(
    {
        "int_stat",
        "str_stat",
        "fth_stat",
        "pragmatic",
        "romantic",
        "solitude",
        "social",
        "truth_seek",
        "corruption",
    }
)


@dataclass
class GameState:
    """
    單次遊玩的核心資料（可序列化為 JSON）。

    Attributes:
        time_left: 尚可安排的培養季數（每執行一次指令扣 1，自 60 至 0）。
        int_stat: 智力傾向累積。
        str_stat: 力量傾向累積。
        fth_stat: 信仰傾向累積。
        pragmatic: 務實傾向。
        romantic: 浪漫傾向。
        solitude: 孤獨傾向。
        social: 社交傾向。
        truth_seek: 真理探求（隱藏累積；重大事件等可增減，不參與結局判定）。
        corruption: 腐化（隱藏累積；重大事件等可增減，不參與結局判定）。
        flags: 劇情與關鍵選項旗標（字串集合）；含重大事件的 ``series_milestone_*``／``ubel_milestone_*``，以及男主角專用 ``hero_south_milestone_*``／``kraft_milestone_*``。
        magic_ids: 已習得魔法編號列表（收集冊）。
        phase: 目前人生階段鍵（childhood／adolescence／young_adult），由年齡自動同步。
        intro_done: 是否已看完開場前提（新遊戲首次為 False）。
        heroine_name: 主角顯示姓名（監護人取名後寫入）。
        protagonist_gender: 主角性別，``female`` 或 ``male``（影響結局池與立繪檔名候選；新遊戲預設 ``male``）。
        guardian_intro_done: 是否已在監護人頁完成性別選擇並確認姓名（寫入 ``heroine_name`` 時設為 True；舊存檔曾表示「已按繼續」者仍可能僅為未取名狀態，讀檔邏輯會分流）。
        onboarding_complete: 是否已完成取名、聖堂問卷與監護契約（可進入正式養成）。
        saved_at: 上次寫入存檔的 ISO 時間字串（存檔時更新）。
        incident_years_fired: 已觸發過突發事件的滿歲年齡（不含 8／13／18 重大事件預留；亦不含 6／11／16 遭遇戰專用歲）。
        incident_ids_fired: 同一次遊玩已發生過的突發事件 id（避免重複抽到同一則）。
        major_years_fired: 已觸發過重大事件的滿歲年齡（8／13／18）。
        encounter_years_fired: 已觸發過遭遇戰的滿歲年齡（6／11／16；取代該歲突發事件）。
    """

    time_left: int = TOTAL_TRAINING_QUARTERS
    int_stat: int = 0
    str_stat: int = 0
    fth_stat: int = 0
    pragmatic: int = 0
    romantic: int = 0
    solitude: int = 0
    social: int = 0
    truth_seek: int = 0
    corruption: int = 0
    flags: set[str] = field(default_factory=set)
    magic_ids: list[str] = field(default_factory=list)
    phase: str = "childhood"
    intro_done: bool = False
    heroine_name: str = ""
    protagonist_gender: str = "male"
    guardian_intro_done: bool = False
    onboarding_complete: bool = False
    saved_at: str = ""
    incident_years_fired: list[int] = field(default_factory=list)
    incident_ids_fired: list[str] = field(default_factory=list)
    major_years_fired: list[int] = field(default_factory=list)
    encounter_years_fired: list[int] = field(default_factory=list)
    # --- 奇遇事件（《葬送的芙莉蓮》向 NPC 偶遇測驗）---
    # whim_slots：本局固定三格——幼年／少年／青年各一，對應「已完成季數」索引（僅 3／6／9 月、不含 0 月之槽）。
    # whim_npc_keys：每次奇遇對應的 NPC key（見 whim_events.py：WhimEncounter.key）。
    # whim_question_indices：每次奇遇對應的題目索引（見 whim_questions.py：WhimQuestion）。
    # whim_fired：每次奇遇是否已結算（用於避免重複觸發）。
    whim_slots: list[int] = field(default_factory=list)
    whim_npc_keys: list[str] = field(default_factory=list)
    whim_question_indices: list[int] = field(default_factory=list)
    whim_fired: list[bool] = field(default_factory=list)

    @property
    def age_months(self) -> int:
        """
        目前年齡（月）：自 3 歲起算，每完成一季培養 +3 個月。

        Returns:
            總月數（例如 36 為剛滿 3 歲、尚未執行任何指令時）。
        """
        spent = TOTAL_TRAINING_QUARTERS - self.time_left
        return START_AGE_MONTHS + spent * 3

    def refresh_life_phase(self) -> None:
        """
        依 `age_months` 更新 `phase`：3～7 歲幼年、8～12 歲少年、13～17 歲青年；滿 18 歲仍維持青年外觀直至結局。
        """
        ay = self.age_months // 12
        if ay < 8:
            self.phase = "childhood"
        elif ay < 13:
            self.phase = "adolescence"
        else:
            self.phase = "young_adult"

    def can_spend(self, cost: int) -> bool:
        """
        判斷是否還能支付指定時間成本。

        Args:
            cost: 欲扣除的時間點數（須為非負整數）。

        Returns:
            若 `time_left >= cost` 則為 True。
        """
        return cost >= 0 and self.time_left >= cost

    def spend_time(self, cost: int) -> bool:
        """
        扣除時間點數（僅在玩家執行活動時呼叫）。

        Args:
            cost: 時間成本。

        Returns:
            成功扣除為 True；時間不足則不變更並回傳 False。
        """
        if not self.can_spend(cost):
            return False
        self.time_left -= cost
        return True

    def apply_deltas(self, deltas: dict[str, int]) -> None:
        """
        依鍵名累加數值（省略的鍵不變）；可見與隱藏數值欄位不低於 0。

        Args:
            deltas: 例如 {"int_stat": 2, "str_stat": -1}。
        """
        for key, delta in deltas.items():
            if not hasattr(self, key):
                continue
            current = getattr(self, key)
            if isinstance(current, int):
                new_val = current + int(delta)
                if key in _CLAMP_INT_FIELDS:
                    new_val = max(0, new_val)
                setattr(self, key, new_val)

    def add_flag(self, flag: str) -> None:
        """
        新增劇情旗標（冪等：重複加入無妨）。

        Args:
            flag: 旗標名稱。
        """
        self.flags.add(flag)

    def learn_magic(self, magic_id: str) -> None:
        """
        記錄已獲得的魔法（不重複）。

        Args:
            magic_id: 魔法唯一編號。
        """
        if magic_id not in self.magic_ids:
            self.magic_ids.append(magic_id)

    def to_json_dict(self) -> dict[str, Any]:
        """
        轉成可 JSON 序列化的純資料結構（set → list）。

        Returns:
            字典形式快照。
        """
        data = asdict(self)
        data["flags"] = sorted(self.flags)
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> GameState:
        """
        由 JSON 載入狀態。

        Args:
            data: `to_json_dict` 產生或相容格式的字典。

        Returns:
            還原後的 `GameState`。
        """
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        flags = set(filtered.pop("flags", data.get("flags", [])))
        magic_ids = list(filtered.pop("magic_ids", data.get("magic_ids", [])))
        if "intro_done" not in filtered:
            filtered["intro_done"] = True
        if "saved_at" not in filtered:
            filtered["saved_at"] = ""
        # 舊存檔：無監護人／取名欄位時視為已完成養成開局。
        legacy = "onboarding_complete" not in data
        if legacy:
            filtered["onboarding_complete"] = True
            filtered["guardian_intro_done"] = True
        if "heroine_name" not in data:
            filtered["heroine_name"] = ""
        if "protagonist_gender" not in data:
            filtered["protagonist_gender"] = "female"
        elif filtered.get("protagonist_gender") not in ("female", "male"):
            filtered["protagonist_gender"] = "male"
        if "incident_years_fired" not in data:
            filtered["incident_years_fired"] = []
        if "incident_ids_fired" not in data:
            filtered["incident_ids_fired"] = []
        if "major_years_fired" not in data:
            filtered["major_years_fired"] = []
        if "encounter_years_fired" not in data:
            filtered["encounter_years_fired"] = []
        if "guardian_intro_done" not in data and not legacy:
            filtered["guardian_intro_done"] = False
        state = cls(**filtered)
        state.flags = flags
        state.magic_ids = magic_ids
        if state.onboarding_complete and not (state.heroine_name or "").strip():
            state.heroine_name = "孩子"
        if state.whim_npc_keys:
            from whim_events import canonical_whim_gallery_key

            state.whim_npc_keys = [
                canonical_whim_gallery_key(k) for k in state.whim_npc_keys
            ]
        state.refresh_life_phase()
        return state

    def save_to_file(self, path: str | Path) -> None:
        """
        寫入 JSON 存檔。

        Args:
            path: 檔案路徑。
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.saved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        path.write_text(json.dumps(self.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: str | Path) -> GameState:
        """
        由 JSON 檔載入。

        Args:
            path: 檔案路徑。

        Returns:
            還原後的 `GameState`。
        """
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_json_dict(raw)


def default_save_path(root: str | Path | None = None) -> Path:
    """
    預設存檔路徑（專案目錄下的 save.json）。

    Args:
        root: 專案根目錄；省略則以本檔所在目錄為準。

    Returns:
        絕對或相對於 root 的 `Path`。
    """
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    return base / DEFAULT_SAVE_NAME
