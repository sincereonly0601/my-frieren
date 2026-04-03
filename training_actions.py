"""
培養指令：每季一次，僅影響五維（智力、力量、社交、信仰、務實），每次總合固定 +3。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrainingAction:
    """
    單一季節指令。

    Attributes:
        key_num: 對應數字鍵 1～8。
        title: 短標題。
        deltas: 僅含 int_stat／str_stat／social／fth_stat／pragmatic 的增量。
    """

    key_num: int
    title: str
    deltas: dict[str, int]


TRAINING_ACTIONS: tuple[TrainingAction, ...] = (
    TrainingAction(1, "深度閱讀", {"int_stat": 3}),
    TrainingAction(2, "體能訓練", {"str_stat": 3}),
    TrainingAction(3, "聖堂祈禱", {"fth_stat": 3}),
    TrainingAction(4, "同儕相聚", {"social": 3}),
    TrainingAction(5, "幫忙營生", {"pragmatic": 2, "social": -1, "fth_stat": 2}),
    TrainingAction(6, "靜心抄寫", {"int_stat": 2, "fth_stat": 2, "str_stat": -1}),
    TrainingAction(7, "義工走訪", {"social": 2, "fth_stat": 2, "pragmatic": -1}),
    TrainingAction(8, "獨處鍛鍊", {"str_stat": 2, "pragmatic": 2, "social": -1}),
)

TRAINING_ACTION_BY_KEY: dict[int, TrainingAction] = {a.key_num: a for a in TRAINING_ACTIONS}

STAT_LABEL_ZH: dict[str, str] = {
    "int_stat": "智力",
    "str_stat": "力量",
    "fth_stat": "信仰",
    "pragmatic": "務實",
    "social": "社交",
}


def _delta_bits_zh(action: TrainingAction) -> list[str]:
    """
    將 `deltas` 轉成「智力+3」形式的片段列表（順序同 `action.deltas`）。

    Args:
        action: 培養指令。

    Returns:
        每個維度一個字串片段。
    """
    return [
        f"{STAT_LABEL_ZH.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in action.deltas.items()
    ]


def format_action_stat_effects_line(action: TrainingAction) -> str:
    """
    僅產生五維變化說明（不含標題），供培養格第二行顯示。

    Args:
        action: 培養指令。

    Returns:
        例如「智力+3  力量-1」（兩半形空格分隔）。
    """
    return "  ".join(_delta_bits_zh(action))


def format_action_menu_line(action: TrainingAction, *, show_key: bool = True) -> str:
    """
    產生選單用單行說明（含加減數值）。

    Args:
        action: 培養指令。
        show_key: 是否顯示【1】～【8】前綴（方向鍵選單時可關閉）。

    Returns:
        例如「【1】深度閱讀　智力+3」或「深度閱讀　智力+3」。
    """
    body = f"{action.title}　{'  '.join(_delta_bits_zh(action))}"
    if show_key:
        return f"【{action.key_num}】{body}"
    return body


def format_training_feedback_modal_message(
    action: TrainingAction,
    *,
    gender_key: str = "female",
) -> str:
    """
    產生培養結算彈窗用**完整一行字串**（格式固定，供 ``draw_training_feedback_modal`` 拆分）。

    格式（全形標點，勿改順序，括號內勿再嵌 ``（`` ``）``）::

        ``{動作標題}：{敘事句}　（{五維變化，同 format_action_stat_effects_line}）``

    UI 會以**最後一組**全形括號 ``（…）`` 切出數值摘要；前面敘事可含全形逗號，但不要含 ``（``.

    Args:
        action: 培養指令。
        gender_key: 主角性別（敘事人稱）。

    Returns:
        供顯示用的單一字串。
    """
    narrative = training_feedback_line(action, gender_key=gender_key)
    stats = format_action_stat_effects_line(action)
    return f"{action.title}：{narrative}　（{stats}）"


def training_feedback_line(
    action: TrainingAction,
    *,
    gender_key: str = "female",
) -> str:
    """
    回傳培養確認後的敘事回饋（八個選項各一段，內容較充實），人稱依主角性別。

    Args:
        action: 培養指令。
        gender_key: ``male`` 用「他」敘述，其餘用「她」。

    Returns:
        對應敘事（可數句；勿含全形「：」，以免與標題切分衝突）；若 key 不在預期範圍，退回通用句。
    """
    female: dict[int, str] = {
        1: (
            "她抱著厚重的術典蜷在燈下，一頁頁把註解與咒紋對齊，反覆驗證哪一筆轉折才說得通。"
            "等到最後一道式子終於串起來，窗紙已泛白；她揉揉眼眶，卻覺得思緒比入夜前更清澈。"
        ),
        2: (
            "她在操場邊反覆調整步伐與呼吸，木樁、繩梯與負重輪番磨著肩臂與核心。"
            "汗水浸透衣襟時，教頭只點了點頭，她知道自己又撐過了一道門檻，吐息也跟著沉了下來。"
        ),
        3: (
            "她跪在微涼的石板地上，讀經的聲音與燭火一樣低而堅定，雜念像被一句句壓進地裡。"
            "散席後步出迴廊，風裡帶著潮氣，她忽然覺得胸口鬆了一寸，腳步也輕了些。"
        ),
        4: (
            "學姊帶來新茶與城裡的消息，她起初只敢聽，後來也慢慢說起自己的練習與糗事。"
            "笑聲落定時，她才發現手心不再那麼汗溼，話匣子竟捨不得闔上，連耳朵都還留著餘溫。"
        ),
        5: (
            "作坊裡堆滿待補的布袋與秤錘，她挽起袖口從開市忙到收攤，指尖被麻繩磨得發熱。"
            "老闆娘塞給她一碗熱湯麵，說這孩子手快心細；她低頭吹湯，嘴角藏不住得意，也藏不住對人情的踏實感。"
        ),
        6: (
            "案上墨香若有若無，她照字帖一筆一畫寫下去，雜念像被行筆壓進紙裡。"
            "抄到末行抬頭，窗外鳥鳴忽然清晰，心神竟比開筆前更穩，連指尖的顫意都淡了。"
        ),
        7: (
            "她提著藥包與舊衣走巷串戶，替長者磨墨、替孩童講一段故事，也順手記下誰家缺米缺柴。"
            "回程的路上簿子記滿名字與囑咐，雖累卻覺得胸口被什麼溫溫地填滿，腳步仍願意多繞一條街。"
        ),
        8: (
            "四下無人時，她把平日學到的招式拆開又縫合，一次次修正錯力與換氣的節奏。"
            "月昇到中天，影子反倒短了；她收勢吐息，身體記住了今天多撐住的那一瞬，心裡也多了一分安靜的把握。"
        ),
    }
    male: dict[int, str] = {
        1: (
            "他抱著厚重的術典蜷在燈下，一頁頁把註解與咒紋對齊，反覆驗證哪一筆轉折才說得通。"
            "等到最後一道式子終於串起來，窗紙已泛白；他揉揉眼眶，卻覺得思緒比入夜前更清澈。"
        ),
        2: (
            "他在操場邊反覆調整步伐與呼吸，木樁、繩梯與負重輪番磨著肩臂與核心。"
            "汗水浸透衣襟時，教頭只點了點頭，他知道自己又撐過了一道門檻，吐息也跟著沉了下來。"
        ),
        3: (
            "他跪在微涼的石板地上，讀經的聲音與燭火一樣低而堅定，雜念像被一句句壓進地裡。"
            "散席後步出迴廊，風裡帶著潮氣，他忽然覺得胸口鬆了一寸，腳步也輕了些。"
        ),
        4: (
            "學長帶來新茶與城裡的消息，他起初只敢聽，後來也慢慢說起自己的練習與糗事。"
            "笑聲落定時，他才發現手心不再那麼汗溼，話匣子竟捨不得闔上，連耳朵都還留著餘溫。"
        ),
        5: (
            "作坊裡堆滿待補的布袋與秤錘，他挽起袖口從開市忙到收攤，指尖被麻繩磨得發熱。"
            "老闆塞給他一碗熱湯麵，說這小子手快心細；他低頭吹湯，嘴角藏不住得意，也藏不住對人情的踏實感。"
        ),
        6: (
            "案上墨香若有若無，他照字帖一筆一畫寫下去，雜念像被行筆壓進紙裡。"
            "抄到末行抬頭，窗外鳥鳴忽然清晰，心神竟比開筆前更穩，連指尖的顫意都淡了。"
        ),
        7: (
            "他提著藥包與舊衣走巷串戶，替長者磨墨、替孩童講一段故事，也順手記下誰家缺米缺柴。"
            "回程的路上簿子記滿名字與囑咐，雖累卻覺得胸口被什麼溫溫地填滿，腳步仍願意多繞一條街。"
        ),
        8: (
            "四下無人時，他把平日學到的招式拆開又縫合，一次次修正錯力與換氣的節奏。"
            "月昇到中天，影子反倒短了；他收勢吐息，身體記住了今天多撐住的那一瞬，心裡也多了一分安靜的把握。"
        ),
    }
    lines = male if gender_key == "male" else female
    fallback = (
        "他把這一季的努力，悄悄落在明天。"
        if gender_key == "male"
        else "她把這一季的努力，悄悄落在明天。"
    )
    return lines.get(action.key_num, fallback)
