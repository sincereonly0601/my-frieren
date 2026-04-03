"""
聖堂／教會視角之領養者問卷：取名後五題，彙總為初始五維與隱性傾向增量，並產生判讀敘述。
題材語彙對齊「魔王死後的和平年代、聖堂與魔法、魔族與言語、短暫人生與旅途」之奇幻基調。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

from game_state import GameState

_ORIG_W = 320
_ORIG_H = 180

# 問卷題數（與 ``ADOPTER_QUESTIONNAIRE`` 長度一致）。
ADOPTER_QUESTIONNAIRE_COUNT: Final[int] = 5


@dataclass(frozen=True)
class AdopterOption:
    """
    單一選項：顯示文案與對 ``GameState`` 之增量。

    Attributes:
        label_zh: 選項全文（一句為主）。
        deltas: 僅含允許之整數欄位鍵；值可正可負，會由 ``apply_deltas`` clamp。
    """

    label_zh: str
    deltas: dict[str, int]


@dataclass(frozen=True)
class AdopterQuestion:
    """
    一題問卷：教會向領養者提問與選項。

    Attributes:
        prompt_zh: 題幹（可含換行，繪製時會再換行）。
        options: 固定四選一。
    """

    prompt_zh: str
    options: tuple[AdopterOption, AdopterOption, AdopterOption, AdopterOption]


ADOPTER_QUESTIONNAIRE: Final[tuple[AdopterQuestion, ...]] = (
    AdopterQuestion(
        prompt_zh=(
            "首先，請問您家中能否負擔孩子往後的修行與行旅開支；聖堂需估算補助與魔法學舍的預備金，"
            "以免誤將無力遠行的孩子送往北境試煉。"
        ),
        options=(
            AdopterOption(
                "手頭很緊，但省著用仍能溫飽；願以信仰撐過荒年。",
                {"pragmatic": 2, "fth_stat": 1},
            ),
            AdopterOption(
                "勉強足夠日常，偶能為孩子添一冊咒式抄本或一雙耐走的靴。",
                {"pragmatic": 1, "social": 1, "str_stat": 1},
            ),
            AdopterOption(
                "尚稱寬裕，願為資質預留選擇，不讓孩子因缺紙筆與觸媒而卻步。",
                {"int_stat": 2, "pragmatic": 1},
            ),
            AdopterOption(
                "收成與委託起伏不定，難料明年是否還能留在同一座村；只能珍惜此刻。",
                {"fth_stat": 1, "pragmatic": 1, "social": 1},
            ),
        ),
    ),
    AdopterQuestion(
        prompt_zh=(
            "魔王死後已過多年，邊境仍傳聞魔族與盜匪；教會不問您效忠何方，"
            "只問這樣的世道是否常令您徹夜難眠？"
        ),
        options=(
            AdopterOption(
                "征召與警報時有所聞，夜裡總先檢查門栓與油燈。",
                {"str_stat": 2, "fth_stat": 1},
            ),
            AdopterOption(
                "表面太平，流言卻多；我學會辨讀告示、商隊與僧侶傳來的片語。",
                {"int_stat": 2, "pragmatic": 1},
            ),
            AdopterOption(
                "城鎮與市集仍照常運作，孩子還能在廣場聽見吟遊詩人的段子。",
                {"social": 2, "pragmatic": 1},
            ),
            AdopterOption(
                "人人緘默，只求別被捲入；我寧可獨行、少與外人深談。",
                {"pragmatic": 2, "int_stat": 1},
            ),
        ),
    ),
    AdopterQuestion(
        prompt_zh=(
            "以人類短暫的數十年為尺，您最盼望這片大陸變成什麼模樣？"
            "（聖堂將此與史書上勇者一行之世相互對照。）"
        ),
        options=(
            AdopterOption(
                "願苦難少些，鄰人仍願分一口粥、借一盞燈。",
                {"fth_stat": 2, "social": 2},
            ),
            AdopterOption(
                "願魔族與戰禍的教訓被寫進教本，後人不必再靠血換來醒悟。",
                {"int_stat": 3},
            ),
            AdopterOption(
                "願王國與僧院的秩序長存，孩子至少能預料明日是否有課與檢定。",
                {"pragmatic": 3},
            ),
            AdopterOption(
                "願世上仍留一點不必講理的溫柔與荒唐，像傳說裡那些多餘的繞路。",
                {"social": 2, "fth_stat": 1},
            ),
        ),
    ),
    AdopterQuestion(
        prompt_zh=(
            "對這名即將託付予您的孩子，您最深的期望是什麼？"
            "（此條列為密件，僅供啟蒙導師參考。）"
        ),
        options=(
            AdopterOption(
                "平安長大就好，其餘交給命與季節，像村裡大多數人的一生。",
                {"str_stat": 2, "fth_stat": 1},
            ),
            AdopterOption(
                "願他日能辨識言語中的謊意，讀懂人心與紋章背後的意圖。",
                {"int_stat": 2, "social": 1},
            ),
            AdopterOption(
                "先學會活下來與自保，哪怕顯得冷漠；活著才有資格談理想。",
                {"pragmatic": 2, "str_stat": 1},
            ),
            AdopterOption(
                "願他不必為了迎合眾人而磨平自己，即使那條路註定孤獨。",
                {"int_stat": 1, "pragmatic": 1, "social": 1},
            ),
        ),
    ),
    AdopterQuestion(
        prompt_zh=(
            "最後一題：您如何看待「未來」？不是占星或預言，"
            "而是今夜就寢前，您對明日仍願意相信的那一句話。"
        ),
        options=(
            AdopterOption(
                "我相信長夜終會過去，只要還有人願意在窗邊點燈。",
                {"fth_stat": 2, "social": 1},
            ),
            AdopterOption(
                "我更信腳下的里程與帳本，一步一步驗證，不託付給故事。",
                {"pragmatic": 2, "int_stat": 1},
            ),
            AdopterOption(
                "不敢妄想遠方，只求今晚門外無警鐘、屋內尚有呼吸。",
                {"str_stat": 2, "pragmatic": 1},
            ),
            AdopterOption(
                "願與同伴分擔行囊與咒文失敗的後果，不必獨自走完一生。",
                {"social": 3},
            ),
        ),
    ),
)

# 問卷判讀：每題依選項 0～3 之短子句（與 ``ADOPTER_QUESTIONNAIRE`` 題序、選序一致；宜保持簡短以利分段呈現）。
ADOPTER_OPTION_CLAUSES_ZH: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "您坦言手頭緊，聖堂優先核算補助與學舍預備金",
        "您稱日常尚可、偶能添書與靴，導師會留體能與市集課",
        "您預留資材加深咒式，免資質被紙筆所限",
        "收成去留難料仍願託付，備註遷徙風險與珍惜此刻",
    ),
    (
        "夜裡慣檢門栓油燈，讀作警戒與體魄並重",
        "流言多而慣辨告示片語，讀作智性防禦",
        "城鎮照常、廣場仍有詩聲，社交與務實並重",
        "寧緘默獨行，免強制公開禱告與團體展演",
    ),
    (
        "願苦難少些、鄰人仍肯分粥借燈",
        "願戰禍教訓入教本，首季重史觀與智力",
        "願秩序長存，課表偏檢定與流程",
        "願留一點溫柔與荒唐，敘事保留詩與寓言",
    ),
    (
        "最深期望平安長大，其餘交給命與季節",
        "盼他日辨謊意與紋章後意，加深辯論與文書",
        "先學活下與自保，少觸犧牲英雄主義教材",
        "不必為眾人磨平自己，尊重邊界、少強制合群",
    ),
    (
        "信長夜會過去，窗邊仍有人點燈",
        "信里程與帳本，實作早於寓言",
        "不敢妄想遠方，只求今夜無警鐘",
        "願與同伴分擔行囊與咒敗，共禱與團任務常態化",
    ),
)

_STAT_PRIORITY: Final[tuple[str, ...]] = (
    "int_stat",
    "str_stat",
    "fth_stat",
    "pragmatic",
    "social",
)

# 與 ``main`` 餘韻／培養回饋相同語意與間距（避免自 main 循環 import）。
_ADOPTER_STAT_PREFIX: Final[str] = "數值變化："  # main._TRAINING_FEEDBACK_MODAL_STAT_PREFIX
_ADOPTER_STAT_COLOR: Final[tuple[int, int, int]] = (175, 212, 252)  # main._EVENT_AFTERMATH_STAT_COLOR_ON_DARK
_GAP_BEFORE_HINT_LOGICAL_Y: Final[int] = 6  # main._TRAINING_FEEDBACK_MODAL_GAP_BEFORE_HINT_LOGICAL_Y
_GAP_BEFORE_STAT_LOGICAL_Y: Final[int] = 10  # main._TRAINING_FEEDBACK_MODAL_GAP_BEFORE_STAT_LOGICAL_Y

STAT_LABEL_ADOPTER_ZH: Final[dict[str, str]] = {
    "int_stat": "智力",
    "str_stat": "力量",
    "fth_stat": "信仰",
    "pragmatic": "務實",
    "social": "社交",
    "truth_seek": "真理探求",
}


def merge_adopter_questionnaire(choice_indices: tuple[int, ...]) -> dict[str, int]:
    """
    依每題選項索引（0～3）累加各欄位增量。

    Args:
        choice_indices: 長度須與 ``ADOPTER_QUESTIONNAIRE_COUNT`` 相同。

    Returns:
        合併後之增量字典（僅含出現過且非零之鍵）。
    """
    if len(choice_indices) != ADOPTER_QUESTIONNAIRE_COUNT:
        raise ValueError(
            f"expected {ADOPTER_QUESTIONNAIRE_COUNT} choices, got {len(choice_indices)}"
        )
    acc: dict[str, int] = {}
    for qi, ci in enumerate(choice_indices):
        opts = ADOPTER_QUESTIONNAIRE[qi].options
        if not 0 <= ci < len(opts):
            raise ValueError(f"invalid option index {ci} for question {qi}")
        for k, v in opts[ci].deltas.items():
            acc[k] = acc.get(k, 0) + int(v)
    return {k: v for k, v in acc.items() if v != 0}


def _adopter_clauses_for_choices(choice_indices: tuple[int, ...]) -> tuple[str, str, str, str, str]:
    """
    依五題選項索引取出對應子句（供連貫段落組裝）。

    Args:
        choice_indices: 長度須為 ``ADOPTER_QUESTIONNAIRE_COUNT``。

    Returns:
        五則子句，順序同題號。
    """
    if len(choice_indices) != ADOPTER_QUESTIONNAIRE_COUNT:
        raise ValueError(
            f"expected {ADOPTER_QUESTIONNAIRE_COUNT} choices, got {len(choice_indices)}"
        )
    out: list[str] = []
    for qi, ci in enumerate(choice_indices):
        row = ADOPTER_OPTION_CLAUSES_ZH[qi]
        if not 0 <= ci < len(row):
            raise ValueError(f"invalid option index {ci} for question {qi}")
        out.append(row[ci])
    return (out[0], out[1], out[2], out[3], out[4])


def questionnaire_judgment_zh(
    choice_indices: tuple[int, ...],
    merged: dict[str, int],
) -> str:
    """
    依各題選項與合併增量產生教會口吻判讀（不含底部「數值變化」列；該列由結果頁另繪）。

    全文以 ``\\n\\n`` 分為三段：標題列、前四題敘述、第五題與總覽與結語（段落間距由結果頁另加大）。

    Args:
        choice_indices: 五題各選項索引 0～3。
        merged: ``merge_adopter_questionnaire`` 之結果。

    Returns:
        標題＋兩段正文（共三個 ``\\n\\n`` 區塊）。
    """
    c0, c1, c2, c3, c4 = _adopter_clauses_for_choices(choice_indices)
    header = "聖堂紀錄　領養者問卷判讀"
    mid = (
        "聖堂已閱畢五問，並將諸答與邊境通報、學舍補助條目對照。"
        f"家計與修行行旅所費：{c0}。"
        f"邊境與長夜是否仍令您難眠：{c1}。"
        f"以數十年為尺，對大陸之願景：{c2}。"
        f"對此子最深期望：{c3}。"
    )
    tail_plain = (
        "最後一題問『明日』——今夜就寢前仍願相信的那一句。"
        f"您的回答：{c4}。"
        "綜觀加總略分散或持平，啟蒙先採通用基準，相處中再細辨。"
        "姊妹會已錄入備註，供導師首季調整課程與試煉步調。"
    )
    if not merged:
        return f"{header}\n\n{mid}\n\n{tail_plain}"
    ranked = sorted(
        merged.items(),
        key=lambda kv: (-kv[1], _STAT_PRIORITY.index(kv[0]) if kv[0] in _STAT_PRIORITY else 99),
    )
    top_key = ranked[0][0]
    closing = {
        "int_stat": "綜觀加總歸「求知與辨識」——理性留一條可核對的路。",
        "str_stat": "綜觀加總讀「堅韌與護衛」——體魄與平安擺在前頭。",
        "fth_stat": "綜觀加總讀「守望與信靠」——動盪裡仍信高於算計的秩序。",
        "pragmatic": "綜觀加總讀「務實與界線」——重可執行與在現實站穩。",
        "social": "綜觀加總讀「牽絆與同行」——重溫度與不必獨擔。",
        "truth_seek": "綜觀加總讀「對真相的執著」——近事實、遠修辭。",
    }.get(top_key, "綜觀筆調複合；導師啟蒙期將對照卷末子句。")
    tail_merged = (
        f"最後關於明日：{c4}。"
        f"{closing}"
        "總覽與卷上諸答並讀可見呼應，導師首季將微調課業與試煉比重。"
        "姊妹會已錄入備註。"
    )
    return f"{header}\n\n{mid}\n\n{tail_merged}"


def format_adopter_merged_deltas_zh(merged: dict[str, int]) -> str:
    """
    將合併增量化為「智力+2  力量+1」式單行摘要（兩半形空格分隔）。

    Args:
        merged: 合併增量。

    Returns:
        以兩半形空格連接之字串；空則為「（無數值變化）」。
    """
    if not merged:
        return "（無數值變化）"
    bits = [
        f"{STAT_LABEL_ADOPTER_ZH.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in sorted(merged.items(), key=lambda kv: (_STAT_PRIORITY.index(kv[0]) if kv[0] in _STAT_PRIORITY else 99, kv[0]))
        if v != 0
    ]
    return "  ".join(bits) if bits else "（無數值變化）"


def _logical_y_to_canvas_px(canvas_h: int, logical_y: int) -> int:
    """邏輯垂直座標（以 ``_ORIG_H`` 為基準）換算為實際畫素。"""
    return logical_y * canvas_h // _ORIG_H


def _adopter_result_footer_top_px(
    small_font: pygame.font.Font,
    max_w: int,
    nav_raw: str,
    canvas_h: int,
) -> int:
    """
    問卷判讀頁頁尾操作列頂端 y（算法同 ``main._aftermath_footer_top_for_nav_raw``）。

    Args:
        small_font: 頁尾字型。
        max_w: 換行寬。
        nav_raw: 本頁操作說明全文。
        canvas_h: 畫布高度。

    Returns:
        頁尾第一行文字之 y。
    """
    nav_lines = _wrap_cjk(small_font, nav_raw, max_w)
    lh_s = small_font.get_height()
    nav_gap = 2
    nav_content_h = len(nav_lines) * lh_s + max(0, len(nav_lines) - 1) * nav_gap
    bottom_pad = _logical_y_to_canvas_px(canvas_h, 8)
    return canvas_h - bottom_pad - nav_content_h


def _adopter_stat_block_height_px(
    intro_font: pygame.font.Font,
    max_w: int,
    full_stat_line: str,
) -> int:
    """
    「數值變化」區塊高度（同 ``main._aftermath_stat_lines_height_px``）。

    Args:
        intro_font: 與餘韻正文同級之字型。
        max_w: 換行寬。
        full_stat_line: 含前綴之全文。

    Returns:
        像素高度；空白則 0。
    """
    if not full_stat_line.strip():
        return 0
    lines = _wrap_cjk(intro_font, full_stat_line, max_w)
    fh = intro_font.get_height() + 2
    return len(lines) * fh


def _adopter_narrative_bottom_y_with_bottom_stat(
    small_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    max_w: int,
    stat_full_line: str,
    canvas_h: int,
    nav_raw: str,
) -> int:
    """
    判讀正文最底允許 y（不含），已預留底部數值列與頁尾（同 ``main._aftermath_narrative_bottom_y_page0_with_bottom_stat`` 精神）。

    Args:
        small_font: 頁尾字型。
        intro_font: 正文／數值列字型。
        max_w: 換行寬。
        stat_full_line: 含「數值變化：」前綴之全文。
        canvas_h: 畫布高度。
        nav_raw: 頁尾字串。

    Returns:
        敘事截斷用 y 上界。
    """
    footer_top = _adopter_result_footer_top_px(small_font, max_w, nav_raw, canvas_h)
    if not stat_full_line.strip():
        return footer_top - _logical_y_to_canvas_px(canvas_h, 8)
    gap_stat_above_nav = _logical_y_to_canvas_px(canvas_h, _GAP_BEFORE_HINT_LOGICAL_Y)
    gap_narrative_above_stat = _logical_y_to_canvas_px(canvas_h, _GAP_BEFORE_STAT_LOGICAL_Y)
    sh = _adopter_stat_block_height_px(intro_font, max_w, stat_full_line)
    return footer_top - gap_stat_above_nav - sh - gap_narrative_above_stat


def _adopter_result_stat_full_line(merged_deltas: dict[str, int]) -> str:
    """
    組合結果頁底部統計列（含前綴）；無增量則空字串。

    Args:
        merged_deltas: 合併增量。

    Returns:
        供繪製用之全文。
    """
    if not merged_deltas:
        return ""
    body = format_adopter_merged_deltas_zh(merged_deltas)
    if not body or body == "（無數值變化）":
        return ""
    return _ADOPTER_STAT_PREFIX + body


def finalize_adopter_questionnaire(
    choice_indices: tuple[int, ...],
    state: GameState,
) -> tuple[str, dict[str, int]]:
    """
    套用問卷增量至 ``state``，並回傳判讀全文與已套用增量。

    Args:
        choice_indices: 五題各選項索引 0～3。
        state: 新遊戲狀態（尚未進入養成亦可）。

    Returns:
        ``(判讀敘述, 合併增量)``。
    """
    merged = merge_adopter_questionnaire(choice_indices)
    state.apply_deltas(merged)
    text = questionnaire_judgment_zh(choice_indices, merged)
    return text, merged


def _scale_x(canvas_w: int, x: int) -> int:
    """邏輯 x 由 320 基準換算至實際畫布寬。"""
    return x * canvas_w // _ORIG_W


def _scale_y(canvas_h: int, y: int) -> int:
    """邏輯 y 由 180 基準換算至實際畫布高。"""
    return y * canvas_h // _ORIG_H


def _wrap_cjk(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """依字型寬度將中文／混排文字換行。"""
    if max_width <= 0:
        return [text] if text else [""]
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines if lines else [""]


def _flatten_prompt_zh(text: str) -> str:
    """
    題幹顯示用：合併空白與手動換行，使斷行僅依畫面寬度自動發生（語意連貫）。

    Args:
        text: 題幹原文。

    Returns:
        單行連續字串（不含換行）。
    """
    return "".join(text.split())


def _max_adopter_prompt_wrapped_lines(body_font: pygame.font.Font, max_w: int) -> int:
    """
    五題題幹在相同欄寬下換行後之**最大行數**（供題幹區預留固定高度，使各題選項起點一致）。

    Args:
        body_font: 題幹用字型。
        max_w: 題幹可用寬度（與問卷畫面 ``tw`` 相同）。

    Returns:
        至少為 1。
    """
    m = 1
    for q in ADOPTER_QUESTIONNAIRE:
        flat = _flatten_prompt_zh(q.prompt_zh)
        m = max(m, len(_wrap_cjk(body_font, flat, max_w)))
    return m


def _line_step_for_font(font: pygame.font.Font) -> int:
    """
    單行行距（與 ``main._draw_contract_rune_block`` 契約偽古文區一致：lh + max(4, lh//5)）。

    Args:
        font: 用於量測行高之字型。

    Returns:
        游標下移量（像素）。
    """
    lh = font.get_height()
    return lh + max(4, lh // 5)


def _paragraph_gap_after_block(canvas_h: int) -> int:
    """
    段落與段落之間的額外空白（對齊契約書 ``_draw_contract_rune_block`` 之 fragment 間距）。

    Args:
        canvas_h: 畫布高度（供邏輯座標換算）。

    Returns:
        垂直留白像素。
    """
    return _scale_y(canvas_h, 1) + 6


def _paragraph_gap_adopter_judgment(canvas_h: int) -> int:
    """
    問卷判讀結果頁：段落與段落之間額外留白（大於一般契約／偽古文用間距）。

    Args:
        canvas_h: 畫布高度。

    Returns:
        垂直像素。
    """
    return _scale_y(canvas_h, 5) + 18


def _blit_event_style_choice_cell_questionnaire(
    canvas: pygame.Surface,
    canvas_w: int,
    canvas_h: int,
    mx: int,
    y: int,
    max_w: int,
    font: pygame.font.Font,
    label: str,
    selected: bool,
    *,
    opt_gap_after: int,
) -> int:
    """
    單一選項方框（與 ``main._blit_event_style_choice_cell`` 同色與圓角邏輯一致；垂直採緊湊內距，便於四選一長文案。

    Args:
        canvas: 邏輯畫布。
        canvas_w: 畫布寬。
        canvas_h: 畫布高。
        mx: 選項欄基準左 x。
        y: 方框頂 y。
        max_w: 欄寬（內文可用寬為 ``max_w - 2*pad_x``）。
        font: 選項字。
        label: 已含編號之標籤。
        selected: 是否選中。
        opt_gap_after: 與下一選項之垂直間距。

    Returns:
        下一選項起點 y。
    """
    lh = font.get_height() + 1
    pad_x = _scale_x(canvas_w, 6)
    pad_y = _scale_y(canvas_h, 3)
    inner_tw = max(1, max_w - 2 * pad_x)
    cell_w = max_w + 2 * pad_x
    lines = _wrap_cjk(font, label, inner_tw)
    block_h = len(lines) * lh + 2 * pad_y
    cell = pygame.Rect(mx - pad_x, y, cell_w, block_h)
    fill = (58, 74, 102) if selected else (36, 40, 52)
    border = (140, 165, 205) if selected else (70, 78, 96)
    bw = 2
    rad = max(3, min(cell.h // 8, cell.w // 8))
    pygame.draw.rect(canvas, fill, cell, border_radius=rad)
    pygame.draw.rect(canvas, border, cell, width=bw, border_radius=rad)
    title_col = (248, 250, 255) if selected else (210, 216, 228)
    ty = y + pad_y
    for L in lines:
        canvas.blit(font.render(L, True, title_col), (mx + pad_x, ty))
        ty += lh
    return y + block_h + opt_gap_after


def draw_adopter_questionnaire_screen(
    canvas: pygame.Surface,
    header_font: pygame.font.Font,
    body_font: pygame.font.Font,
    question_index: int,
    choice_index: int,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製領養者問卷單題畫面（四選一）；主文與開場前言等同字級（``header_font``／``body_font`` 通常為同一像素）。

    Args:
        canvas: 邏輯畫布。
        header_font: 頁首標題列。
        body_font: 題幹、選項、頁尾操作提示。
        question_index: 目前題號 0～4。
        choice_index: 游標選項 0～3。
        star_xy: 與標題畫面共用之星點座標。
        tick: 影格（星空閃爍）。
    """
    cw, ch = canvas.get_size()
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(cw, 14)
    tw = cw - 2 * mx
    foot_text = "↑↓ 選擇　Enter 下一題　Esc 上一題"
    foot_lines = _wrap_cjk(body_font, foot_text, tw) or [foot_text]
    foot_h = len(foot_lines) * _line_step_for_font(body_font) + _scale_y(ch, 8)
    y_limit = ch - foot_h
    y = _scale_y(ch, 10)
    hdr_lstep = _line_step_for_font(header_font)
    title_line = (
        "聖堂問卷　領養者諮詢（教會紀錄用）"
        f"　第 {question_index + 1}／{ADOPTER_QUESTIONNAIRE_COUNT} 題"
    )
    for hl in _wrap_cjk(header_font, title_line, tw):
        if y + header_font.get_height() > y_limit:
            break
        canvas.blit(header_font.render(hl, True, (255, 210, 175)), (mx, y))
        y += hdr_lstep
    y += _scale_y(ch, 12)

    q = ADOPTER_QUESTIONNAIRE[question_index]
    prompt_flat = _flatten_prompt_zh(q.prompt_zh)
    body_lstep = _line_step_for_font(body_font)
    prompt_lines = _wrap_cjk(body_font, prompt_flat, tw)
    max_prompt_lines = _max_adopter_prompt_wrapped_lines(body_font, tw)
    drawn_prompt_lines = 0
    for wl in prompt_lines:
        if y + body_font.get_height() > y_limit:
            break
        canvas.blit(body_font.render(wl, True, (218, 222, 236)), (mx, y))
        y += body_lstep
        drawn_prompt_lines += 1
    # 題幹較短之題在下方補垂直留白，使選項區與其他題對齊（題幹未因版面截斷時才補）。
    if drawn_prompt_lines == len(prompt_lines):
        y += max(0, max_prompt_lines - len(prompt_lines)) * body_lstep

    y += _scale_y(ch, 14)

    opt_gap = _scale_y(ch, 2)
    n_opt = len(q.options)
    for oi, opt in enumerate(q.options):
        disp = f"{oi + 1}. {opt.label_zh}"
        lh = body_font.get_height() + 1
        pad_y = _scale_y(ch, 3)
        inner_tw = max(1, tw - 2 * _scale_x(cw, 6))
        peek_h = len(_wrap_cjk(body_font, disp, inner_tw)) * lh + 2 * pad_y
        is_last = oi == n_opt - 1
        # 題幹較長時勿略過最後一項；前三項仍可在空間耗盡時略過（極端版面）
        if not is_last and y + peek_h > y_limit:
            break
        y = _blit_event_style_choice_cell_questionnaire(
            canvas,
            cw,
            ch,
            mx,
            y,
            tw,
            body_font,
            disp,
            oi == choice_index,
            opt_gap_after=opt_gap,
        )

    hint_col = (120, 128, 148)
    hy = ch - foot_h
    for fl in foot_lines:
        canvas.blit(body_font.render(fl, True, hint_col), (mx, hy))
        hy += _line_step_for_font(body_font)


def draw_adopter_questionnaire_result_screen(
    canvas: pygame.Surface,
    intro_font: pygame.font.Font,
    small_font: pygame.font.Font,
    judgment_zh: str,
    merged_deltas: dict[str, int],
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製問卷結束後之判讀；底部「數值變化：」列與頁尾位置對齊突發餘韻（``intro_font``／``small_font`` 分工）。

    Args:
        canvas: 邏輯畫布。
        intro_font: 判讀正文與數值變化列（同餘韻層級）。
        small_font: 頁尾操作說明。
        judgment_zh: ``questionnaire_judgment_zh`` 產出（``\\n\\n`` 分段；不含數值列）。
        merged_deltas: 已套用之合併增量。
        star_xy: 星空座標。
        tick: 影格。
    """
    cw, ch = canvas.get_size()
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(cw, 14)
    tw = cw - 2 * mx
    nav_raw = "Enter 繼續　簽署監護備忘與印鑑"
    stat_full_line = _adopter_result_stat_full_line(merged_deltas)
    y_limit = _adopter_narrative_bottom_y_with_bottom_stat(
        small_font, intro_font, tw, stat_full_line, ch, nav_raw
    )
    footer_top = _adopter_result_footer_top_px(small_font, tw, nav_raw, ch)
    y = _scale_y(ch, 8)
    pgap = _paragraph_gap_adopter_judgment(ch)

    paras = [p.strip() for p in judgment_zh.split("\n\n") if p.strip()]
    for pi, para in enumerate(paras):
        if y >= y_limit:
            break
        if pi > 0:
            y += pgap
        is_rubric = para.startswith("聖堂紀錄")
        col = (255, 210, 175) if is_rubric else (230, 232, 240)
        lstep = _line_step_for_font(intro_font)
        fh = intro_font.get_height()
        for raw in para.split("\n"):
            seg = raw.strip()
            if not seg:
                y += max(2, lstep // 3)
                continue
            for wl in _wrap_cjk(intro_font, seg, tw):
                if y + fh > y_limit:
                    break
                canvas.blit(intro_font.render(wl, True, col), (mx, y))
                y += lstep

    if stat_full_line.strip():
        gap_stat_above_nav = _logical_y_to_canvas_px(ch, _GAP_BEFORE_HINT_LOGICAL_Y)
        fh_stat = intro_font.get_height() + 2
        stat_lines = _wrap_cjk(intro_font, stat_full_line, tw)
        stat_block_h = len(stat_lines) * fh_stat
        sy = footer_top - gap_stat_above_nav - stat_block_h
        for i, sl in enumerate(stat_lines):
            canvas.blit(
                intro_font.render(sl, True, _ADOPTER_STAT_COLOR),
                (mx, sy + i * fh_stat),
            )

    nav_lines = _wrap_cjk(small_font, nav_raw, tw)
    lh_s = small_font.get_height()
    nav_gap = 2
    fy = footer_top
    for i, fl in enumerate(nav_lines):
        canvas.blit(small_font.render(fl, True, (140, 150, 170)), (mx, fy))
        fy += lh_s + (nav_gap if i + 1 < len(nav_lines) else 0)
