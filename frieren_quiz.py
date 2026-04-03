"""
標題「遊戲設定」內之芙莉蓮測驗：題庫沿用 ``whim_questions``，單次 10 題不重複、可隨時 Esc 離開。
"""

from __future__ import annotations

import json
from enum import Enum, auto
from pathlib import Path
from typing import Final

import pygame

from whim_questions import WHIM_QUESTIONS, WhimQuestion

_ORIG_W = 320
_ORIG_H = 180

FRIEREN_QUIZ_NUM_QUESTIONS: Final[int] = 10
_CERT_FILENAME: Final[str] = "frieren_quiz_certificate.json"
# 題幹區固定恰好此行數（不足底部補空行、超過則併入末行並以「…」截斷），選項列頂緣不因題幹長短而跳動。
_FRIEREN_QUIZ_STEM_LINE_COUNT: Final[int] = 2
# 結算畫面「評級」下方評語正文固定恰好此行數（與 ``_wrap_cjk_exact_lines`` 併用）。
_FRIEREN_QUIZ_RESULT_BODY_LINE_COUNT: Final[int] = 3


class FrierenQuizPhase(Enum):
    """芙莉蓮測驗子階段。"""

    CONFIRM = auto()
    QUESTION = auto()
    FEEDBACK = auto()
    RESULTS = auto()


def _scale_x(canvas_w: int, x: int) -> int:
    """邏輯 x 縮放至畫布寬。"""
    return x * canvas_w // _ORIG_W


def _scale_y(canvas_h: int, y: int) -> int:
    """邏輯 y 縮放至畫布高。"""
    return y * canvas_h // _ORIG_H


def frieren_quiz_certificate_path(userdata_root: Path) -> Path:
    """
    芙莉蓮認證書解鎖紀錄檔路徑。

    Args:
        userdata_root: 使用者資料根目錄。

    Returns:
        JSON 檔完整路徑。
    """
    return userdata_root / _CERT_FILENAME


def load_frieren_quiz_certificate_earned(userdata_root: Path) -> bool:
    """
    是否已取得芙莉蓮認證書（滿分通過測驗至少一次）。

    Args:
        userdata_root: 使用者資料根目錄。

    Returns:
        已解鎖為 True。
    """
    p = frieren_quiz_certificate_path(userdata_root)
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return bool(data.get("earned"))
    except (OSError, ValueError, TypeError):
        return False


def save_frieren_quiz_certificate_earned(userdata_root: Path) -> None:
    """
    寫入已取得芙莉蓮認證書（覆寫為 earned）。

    Args:
        userdata_root: 使用者資料根目錄。
    """
    p = frieren_quiz_certificate_path(userdata_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"earned": True}, ensure_ascii=False, indent=0) + "\n",
        encoding="utf-8",
    )


def _wrap_cjk(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """依字型寬度換行。"""
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


def _fit_one_line_cjk(font: pygame.font.Font, text: str, max_width: int) -> str:
    """單行；過寬則截斷加「…」。"""
    if max_width <= 0:
        return ""
    lines = _wrap_cjk(font, text, max_width)
    first = lines[0] if lines else ""
    if len(lines) == 1 and font.size(first)[0] <= max_width:
        return first
    ell = "…"
    if font.size(first + ell)[0] <= max_width:
        return first + ell
    while len(first) > 0 and font.size(first + ell)[0] > max_width:
        first = first[:-1]
    return first + ell if first else ell


def _wrap_cjk_exact_lines(
    font: pygame.font.Font,
    text: str,
    max_width: int,
    line_count: int,
) -> list[str]:
    """
    單段文字換行後**恰好** ``line_count`` 行；不足底部補空行，超出併入末行並以「…」截斷。

    Args:
        font: 量測用字型。
        text: 全文。
        max_width: 單行最大像素寬。
        line_count: 固定行數（至少為 1）。

    Returns:
        長度等於 ``line_count`` 的各行字串。
    """
    if line_count < 1:
        return []
    stripped = text.strip()
    if not stripped:
        return [""] * line_count
    if line_count == 1:
        return [_fit_one_line_cjk(font, stripped, max_width)]
    lines = _wrap_cjk(font, stripped, max_width)
    if len(lines) >= line_count:
        head = lines[: line_count - 1]
        rest = "".join(lines[line_count - 1 :])
        return head + [_fit_one_line_cjk(font, rest, max_width)]
    return lines + [""] * (line_count - len(lines))


# 底部操作說明字色：與 main 標題／選單底欄一致（見 draw_title_screen、(130,138,155)）。
_FRIEREN_HINT_RGB_DARK_UI = (130, 138, 155)
# 結算襯紙背景上之提示，略淡於正文墨色、與 col_tail 階調相近。
_FRIEREN_HINT_RGB_PAPER = (108, 104, 98)

# 題目／選項／回饋區簡化色盤（少高飽和點，與深藍星空底一致）。
_FQ_TEXT_PRIMARY: tuple[int, int, int] = (235, 232, 242)
_FQ_TEXT_MUTED: tuple[int, int, int] = (168, 174, 188)
_FQ_CELL_BG: tuple[int, int, int] = (26, 29, 40)
_FQ_CELL_BG_SEL: tuple[int, int, int] = (36, 40, 54)
_FQ_CELL_BORDER: tuple[int, int, int] = (66, 72, 88)
# 游標選中項邊框：偏亮灰白，在星空底上須明顯區別未選項之暗框。
_FQ_CELL_BORDER_SEL: tuple[int, int, int] = (210, 216, 232)
# 回饋列：正解藍框；錯選紅調底框；字仍用主色／次要灰。
_FQ_FB_CORRECT_BG: tuple[int, int, int] = (32, 38, 54)
_FQ_FB_CORRECT_BORDER: tuple[int, int, int] = (92, 148, 218)
_FQ_FB_BAD_BG: tuple[int, int, int] = (52, 22, 30)
_FQ_FB_BAD_BORDER: tuple[int, int, int] = (235, 75, 95)
_FQ_VERDICT_OK: tuple[int, int, int] = (140, 195, 255)
_FQ_VERDICT_BAD: tuple[int, int, int] = (255, 130, 140)


def _draw_frieren_hint_bottom_right(
    canvas: pygame.Surface,
    *,
    font: pygame.font.Font,
    text: str,
    cw: int,
    ch: int,
    color: tuple[int, int, int],
) -> None:
    """
    在畫布右下角繪製操作說明（可換行；各行右對齊）。

    Args:
        canvas: 目標畫布。
        font: 說明用字型。
        text: 全文（依寬換行）。
        cw: 畫布寬。
        ch: 畫布高。
        color: 字色。
    """
    pad_r = _scale_x(cw, 14)
    foot_gap = _scale_y(ch, 12)
    wrap_w = max(60, cw - pad_r - _scale_x(cw, 16))
    lines = _wrap_cjk(font, text, wrap_w)
    lh = font.get_height()
    gap = 2
    nav_h = len(lines) * lh + max(0, len(lines) - 1) * gap
    y = ch - foot_gap - nav_h
    for hl in lines:
        surf = font.render(hl, True, color)
        x = cw - pad_r - surf.get_width()
        canvas.blit(surf, (x, y))
        y += lh + gap


def frieren_quiz_result_tier(score: int) -> tuple[str, str]:
    """
    依總分（0～100，10 分一級）回傳評級名稱與單段評語（結算處以 ``_FRIEREN_QUIZ_RESULT_BODY_LINE_COUNT`` 行呈現）。

    Args:
        score: 本輪總分。

    Returns:
        (評級名稱, 評語一段連續正文)。
    """
    total = FRIEREN_QUIZ_NUM_QUESTIONS * 10
    s = max(0, min(total, score))
    idx = min(10, s // 10)
    tiers: list[tuple[str, str]] = [
        (
            "尚需啟程",
            "此輪尚未得分，不妨從第一題重新作答，把角色、魔法與時間軸對照動畫或漫畫情節。複習像芙莉蓮整理魔導書，重點在看清因果，作品裡的伏筆會慢慢浮現。",
        ),
        (
            "初窺門徑",
            "你已踏出第一步，片段會連成線；多看幾集、對照台詞與小道具，知識會像民間魔法一樣累積。錯題當成下次遇見同一橋段的伏筆，回頭看詳解印象更深。",
        ),
        (
            "摸索前行",
            "對世界觀已有輪廓，補齊人名、地名與魔法規則就更穩；芙莉蓮的旅途也充滿試錯。把錯題對回原作段落，因果對上了，分數自然往上走。",
        ),
        (
            "漸入佳境",
            "基礎概念逐漸清晰，與精靈的時間感一樣需要耐心；角色動機與事件順序多對照幾次，記憶會更牢。別衝速度，把細節放進心裡，分數只是遲早的事。",
        ),
        (
            "基礎尚可",
            "你已掌握不少設定，再對照關鍵情節與因果，模糊處就能補滿；距離高分往往只差幾題精準度。針對錯題看詳解，先想場景再選，下一輪會更穩。",
        ),
        (
            "中規中矩",
            "整體表現均衡，看得出你認真看過故事；錯題多半在細節或易混稱謂，回頭對照一次就能鎖定。放慢讀題、把選項連回台詞，通常能再衝一個級距。",
        ),
        (
            "及格之上",
            "知識結構已站穩，足以在酒館裡聊上一整晚劇情；若要衝高分，把易混魔法名與角色關係做成小抄很有幫助。能複述因果，再練一輪就更接近滿分。",
        ),
        (
            "良好表現",
            "對主線與人物關係已有紮實理解，疏漏多半是看漏或記混稱謂，回頭補一眼就好。保持節奏，下一輪把錯題清零不難，相似選項上多停一秒更保險。",
        ),
        (
            "優秀水準",
            "答題準確度很高，幾乎能與費倫的筆記本並駕齊驅；差距常在冷門典故或一字之差。把錯題連回原作、對照台詞，最後一哩路跨過去就是滿分邊緣。",
        ),
        (
            "近乎完美",
            "僅一題之差的頂尖表現；那一題多半是極細的設定或表述陷阱。複習錯題與相鄰選項差異，作答時多停一秒確認主詞，滿分就在眼前。你已站在門檻上，冷靜比死背更能帶你跨過去。",
        ),
        (
            "滿分認證",
            "你對《葬送的芙莉蓮》世界觀、人物與情節已融會貫通，能把時間軸與角色心境串成敘事。這份知識像與芙莉蓮一行人並肩理解故事溫度，值得延續到每一次重溫。",
        ),
    ]
    return tiers[idx]


def frieren_quiz_tier_seal_phrase(score: int) -> str:
    """
    依總分回傳結算用四字印文（與十級距對應）。

    Args:
        score: 本輪總分（0～100）。

    Returns:
        恰好四字之結論用語。
    """
    total = FRIEREN_QUIZ_NUM_QUESTIONS * 10
    s = max(0, min(total, score))
    idx = min(10, s // 10)
    phrases: tuple[str, ...] = (
        "亟待加強",
        "萌芽初學",
        "摸索累積",
        "漸有起色",
        "根基尚可",
        "表現平穩",
        "已達門檻",
        "表現良好",
        "相當優秀",
        "僅差一線",
        "認證合格",
    )
    return phrases[idx]


def _draw_frieren_quiz_results_background(
    canvas: pygame.Surface,
    *,
    cw: int,
    ch: int,
) -> tuple[int, int, int]:
    """
    繪製測驗結算畫面之獎狀式襯底（襯紙、雙框、四角飾線）。

    Args:
        canvas: 目標畫布。
        cw: 畫布寬。
        ch: 畫布高。

    Returns:
        ``(mx, y0, tw, inner)``：正文左緣 x、首行頂 y、正文可用寬度、金框內側矩形（供固定印章錨點）。
    """
    # 外緣：深灰藍襯托紙張
    canvas.fill((36, 34, 44))
    margin_x = max(10, cw // 26)
    margin_y = max(10, ch // 20)
    paper = pygame.Rect(margin_x, margin_y, cw - 2 * margin_x, ch - 2 * margin_y)
    pygame.draw.rect(canvas, (250, 244, 232), paper)
    # 外框：深褐；內框：金褐細線
    bw = max(2, cw // 140)
    pygame.draw.rect(canvas, (92, 68, 46), paper, width=bw)
    inset = max(5, cw // 64)
    inner = paper.inflate(-2 * inset, -2 * inset)
    pygame.draw.rect(canvas, (178, 148, 98), inner, width=1)
    # 四角飾線（自各角沿內框向內之 L 形）
    arm = max(14, min(28, cw // 22))
    t = max(1, bw)
    gold = (150, 118, 72)
    il, ir, it, ib = inner.left, inner.right - 1, inner.top, inner.bottom - 1
    pygame.draw.line(canvas, gold, (il, it), (il + arm, it), t)
    pygame.draw.line(canvas, gold, (il, it), (il, it + arm), t)
    pygame.draw.line(canvas, gold, (ir, it), (ir - arm, it), t)
    pygame.draw.line(canvas, gold, (ir, it), (ir, it + arm), t)
    pygame.draw.line(canvas, gold, (il, ib), (il + arm, ib), t)
    pygame.draw.line(canvas, gold, (il, ib), (il, ib - arm), t)
    pygame.draw.line(canvas, gold, (ir, ib), (ir - arm, ib), t)
    pygame.draw.line(canvas, gold, (ir, ib), (ir, ib - arm), t)
    inner_pad_x = max(10, cw // 28)
    inner_pad_y = max(8, ch // 36)
    mx = margin_x + inset + inner_pad_x
    y0 = margin_y + inset + inner_pad_y
    tw = cw - 2 * margin_x - 2 * inset - 2 * inner_pad_x
    return mx, y0, tw, inner


def _frieren_seal_line_text(text: str) -> str:
    """
    正規化印文為恰好四字（不足右側補全形空白）。

    Args:
        text: 原始字串。

    Returns:
        長度 4 之印文。
    """
    t = text.strip()
    if len(t) < 4:
        return (t + "\u3000" * 4)[:4]
    return t[:4]


def _frieren_quad_seal_outer_size(text_font: pygame.font.Font, text: str) -> tuple[int, int]:
    """
    四字印含框與內距之實際寬高（與 ``_draw_quad_seal`` 繪製一致）。

    Args:
        text_font: 印文字型。
        text: 印文。

    Returns:
        ``(寬, 高)``。
    """
    t = _frieren_seal_line_text(text)
    surf = text_font.render(t, True, (0, 0, 0))
    w, h = surf.get_size()
    pad = max(8, w // 10)
    return w + 2 * pad, h + 2 * pad


def _draw_quad_seal(
    canvas: pygame.Surface,
    *,
    text_font: pygame.font.Font,
    text: str,
    center_x: int,
    center_y: int,
    border_rgb: tuple[int, int, int],
    text_rgb: tuple[int, int, int],
    inner_rgb: tuple[int, int, int],
) -> None:
    """
    繪製四字方印（軸對齊、不旋轉；字體以目標字級直接 render，避免縮放糊邊）。

    Args:
        canvas: 目標畫布。
        text_font: 印文字型（宜為結算專用之較大字級）。
        text: 印文（以四字為準；不足四字則右側補全形空白）。
        center_x: 印章中心 x。
        center_y: 印章中心 y。
        border_rgb: 外框色。
        text_rgb: 字色。
        inner_rgb: 內框細線色。
    """
    t = _frieren_seal_line_text(text)
    surf = text_font.render(t, True, text_rgb)
    w, h = surf.get_size()
    pad = max(8, w // 10)
    bw, bh = w + 2 * pad, h + 2 * pad
    box = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(box, (*border_rgb, 255), box.get_rect(), width=max(2, bw // 28))
    pygame.draw.rect(
        box,
        (*inner_rgb, 220),
        box.get_rect().inflate(-5, -5),
        width=1,
    )
    box.blit(surf, (pad, pad))
    canvas.blit(
        box,
        (center_x - bw // 2, center_y - bh // 2),
    )


def default_explanation_zh(q: WhimQuestion) -> str:
    """
    題庫未附 ``explanation_zh`` 時的預設詳解。

    不標註集數、話數或「動畫／原作」出處；改以正解與錯誤選項的設定差異為主，便於累積可遷移的知識。

    Args:
        q: 題目。

    Returns:
        單段說明文字。
    """
    ok = q.options[q.correct_index]
    wrong = [q.options[i] for i in range(3) if i != q.correct_index]
    w0, w1 = wrong[0], wrong[1]
    return (
        f"正確答案為「{ok}」。"
        f"與「{w0}」「{w1}」相比，正確項在人物、地點、魔法規則、物品或時間軸上的定位不同；釐清選項之間的因果與名詞對應，比記憶單一畫面更能鞏固設定知識。"
    )


def _frieren_feedback_explanation_head_tail(
    question: WhimQuestion,
    *,
    expl_source: str,
) -> tuple[str, str]:
    """
    拆出「正確答案為「…」。」與後續說明；題庫詳解若帶「詳解：」前綴則先去除。

    Args:
        question: 本題。
        expl_source: 詳解全文（預設詳解或題庫 ``explanation_zh``）。

    Returns:
        ``(head, tail)``；``head`` 恒為 ``正確答案為「正解選項」。」``；``tail`` 為其後內文（可空）。
    """
    ok = question.options[question.correct_index]
    prefix = f"正確答案為「{ok}」。"
    t = expl_source.strip()
    for mark in ("詳解：", "詳解:"):
        if t.startswith(mark):
            t = t[len(mark) :].strip()
    if t.startswith(prefix):
        return prefix, t[len(prefix) :].strip()
    return prefix, t


def draw_frieren_quiz_confirm(
    canvas: pygame.Surface,
    *,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製「是否開始測驗」確認畫面。

    Args:
        menu_font: 主文／標題字型；應與 ``small_font`` 為同一固定字級實例。
        small_font: 與 ``menu_font`` 相同（保留參數以維持簽名）。
        hint_font: 右下角操作說明；宜傳入與標題畫面底欄相同之 ``title_hint_font``。
    """
    cw, ch = canvas.get_size()
    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)
    mx = _scale_x(cw, 20)
    tw = cw - 2 * mx
    y = _scale_y(ch, 14)
    hdr = "芙莉蓮測驗"
    for hl in _wrap_cjk(menu_font, hdr, tw):
        canvas.blit(menu_font.render(hl, True, (255, 200, 160)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(ch, 10)
    body = (
        "將從題庫隨機抽出 10 題，每題 10 分，滿分 100。"
        "答題後會顯示正解與詳解。隨時可按 Esc 離開並返回遊戲設定。"
    )
    for bl in _wrap_cjk(menu_font, body, tw):
        canvas.blit(menu_font.render(bl, True, (230, 232, 240)), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(ch, 8)
    ask = "是否開始測驗？"
    for al in _wrap_cjk(menu_font, ask, tw):
        canvas.blit(menu_font.render(al, True, (255, 230, 160)), (mx, y))
        y += menu_font.get_height() + 2
    _draw_frieren_hint_bottom_right(
        canvas,
        font=hint_font,
        text="【Enter】開始　【Esc】返回遊戲設定",
        cw=cw,
        ch=ch,
        color=_FRIEREN_HINT_RGB_DARK_UI,
    )


def draw_frieren_quiz_screen(
    canvas: pygame.Surface,
    *,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    intro_font: pygame.font.Font,
    hint_font: pygame.font.Font,
    seal_font: pygame.font.Font,
    phase: FrierenQuizPhase,
    question: WhimQuestion | None,
    perm: tuple[int, int, int] | None,
    option_index: int,
    q_round_1based: int,
    score: int,
    feedback_correct: bool | None,
    chosen_slot: int | None,
    perm_for_feedback: tuple[int, int, int] | None,
    certificate_earned_before: bool,
    certificate_just_earned: bool,
    star_xy: list[tuple[int, int]],
    tick: int,
) -> None:
    """
    繪製測驗進行中、回饋或結算畫面。

    Args:
        menu_font: 測驗全文主字型（固定字級）。
        small_font: 應與 ``menu_font``、``intro_font`` 傳入同一實例，避免字級混用。
        intro_font: 選項列與正解行；應與 ``menu_font`` 同字級。
        hint_font: 右下角操作說明；宜傳入 ``title_hint_font``，勿與主文同字級。
        seal_font: 結算四字印專用較大字級（``RESULTS`` 以外階段可不繪製但仍須傳入）。
        phase: 子階段。
        question: 目前題目（``QUESTION``／``FEEDBACK`` 用）。
        perm: 選項排列 ``(題庫索引)`` 對應顯示槽 0～2。
        option_index: 游標 0～2。
        q_round_1based: 第幾題（1～10）。
        score: 目前累積分數。
        feedback_correct: 上一答是否正確（``FEEDBACK``）。
        chosen_slot: 玩家選的槽（``FEEDBACK``）。
        perm_for_feedback: 該題排列（與 ``perm`` 相同；結果不為 None 時帶入）。
        certificate_earned_before: 是否曾取得認證書。
        certificate_just_earned: 本輪是否新取得。
        star_xy: 星空座標。
        tick: 影格。

    Note:
        ``RESULTS`` 時為獎狀式襯紙背景；評級下方為**單段連續正文、固定三行**（``_FRIEREN_QUIZ_RESULT_BODY_LINE_COUNT``）且與標題同寬（``tw``）；四字印錨於內框右下。
        ``QUESTION``／``FEEDBACK`` 時題幹固定**恰好兩行**（與 ``_FRIEREN_QUIZ_STEM_LINE_COUNT`` 一致）；
        題庫 ``stem`` 已於 ``whim_questions.json`` 依版面調整為自然兩行寬；此處直接交 ``_wrap_cjk_exact_lines``，過長則末行以「…」收束。
        答題時正解與詳解列於題幹與選項列正下方。
    """
    cw, ch = canvas.get_size()

    if phase is FrierenQuizPhase.RESULTS:
        mx, y, tw, inner = _draw_frieren_quiz_results_background(canvas, cw=cw, ch=ch)
        total = FRIEREN_QUIZ_NUM_QUESTIONS * 10
        tier_name, tier_body = frieren_quiz_result_tier(score)
        tier_phrase = frieren_quiz_tier_seal_phrase(score)
        seal_w, seal_h = _frieren_quad_seal_outer_size(seal_font, tier_phrase)
        col_title = (78, 52, 36)
        col_score = (42, 38, 34)
        if score >= total:
            tier_col = (145, 95, 28)
        elif score >= 60:
            tier_col = (48, 72, 108)
        elif score >= 30:
            tier_col = (85, 78, 68)
        else:
            tier_col = (105, 98, 92)
        col_body = (52, 48, 44)

        hdr = "芙莉蓮測驗　結算"
        for hl in _wrap_cjk(menu_font, hdr, tw):
            canvas.blit(menu_font.render(hl, True, col_title), (mx, y))
            y += menu_font.get_height() + 2
        y += _scale_y(ch, 10)

        score_line = f"總分　{score}／{total}"
        for hl in _wrap_cjk(menu_font, score_line, tw):
            canvas.blit(menu_font.render(hl, True, col_score), (mx, y))
            y += menu_font.get_height() + 2
        y += _scale_y(ch, 6)

        tier_hdr = f"評級：{tier_name}"
        for hl in _wrap_cjk(menu_font, tier_hdr, tw):
            canvas.blit(menu_font.render(hl, True, tier_col), (mx, y))
            y += menu_font.get_height() + 2
        y += _scale_y(ch, 6)

        body_one = tier_body.rstrip()
        if score < total:
            if body_one.endswith("。"):
                body_one = body_one[:-1] + "，可於遊戲設定再次挑戰。"
            else:
                body_one = f"{body_one}，可於遊戲設定再次挑戰。"
        # 單段以全文寬換行，固定恰好三行（與結算標題／總分同可用寬 ``tw``）。
        body_lines = _wrap_cjk_exact_lines(
            small_font,
            body_one,
            tw,
            _FRIEREN_QUIZ_RESULT_BODY_LINE_COUNT,
        )
        for hl in body_lines:
            canvas.blit(small_font.render(hl, True, col_body), (mx, y))
            y += small_font.get_height() + 2

        # 印章：依內框幾何固定（靠右緣、近下緣），不依上文累積 y。
        pad_r = _scale_x(cw, 4)
        pad_b = _scale_y(ch, 14)
        seal_shift_l = _scale_x(cw, 22)
        tier_seal_cx = inner.right - pad_r - seal_w // 2 - seal_shift_l
        tier_seal_cy = inner.bottom - pad_b - seal_h // 2
        _draw_quad_seal(
            canvas,
            text_font=seal_font,
            text=tier_phrase,
            center_x=tier_seal_cx,
            center_y=tier_seal_cy,
            border_rgb=(185, 45, 45),
            text_rgb=(215, 65, 65),
            inner_rgb=(185, 45, 45),
        )

        _draw_frieren_hint_bottom_right(
            canvas,
            font=hint_font,
            text="【Enter】或【Esc】返回遊戲設定",
            cw=cw,
            ch=ch,
            color=_FRIEREN_HINT_RGB_PAPER,
        )
        return

    canvas.fill((18, 22, 34))
    for i, (sx, sy) in enumerate(star_xy):
        if ((tick // 12) + i) % 5 == 0:
            continue
        pygame.draw.circle(canvas, (200, 210, 240), (sx, sy), 1)

    mx = _scale_x(cw, 20)
    tw = cw - 2 * mx
    y = _scale_y(ch, 14)

    hdr = f"芙莉蓮測驗　第 {q_round_1based}／{FRIEREN_QUIZ_NUM_QUESTIONS} 題　目前 {score} 分"
    for hl in _wrap_cjk(menu_font, hdr, tw):
        canvas.blit(menu_font.render(hl, True, _FQ_TEXT_PRIMARY), (mx, y))
        y += menu_font.get_height() + 2
    y += _scale_y(ch, 6)

    if question is None or perm is None:
        return

    fh_menu = menu_font.get_height()
    line_step_stem = fh_menu + 2
    stem_y = y
    stem_lines = _wrap_cjk_exact_lines(
        menu_font,
        question.stem.strip(),
        tw,
        _FRIEREN_QUIZ_STEM_LINE_COUNT,
    )
    for sl in stem_lines:
        canvas.blit(menu_font.render(sl, True, _FQ_TEXT_PRIMARY), (mx, stem_y))
        stem_y += line_step_stem
    y += _FRIEREN_QUIZ_STEM_LINE_COUNT * line_step_stem
    y += _scale_y(ch, 6)

    # 選項列：與奇遇測驗（``whim_draw`` phase 1）相同之底色、框線與內距
    pad_x = _scale_x(cw, 5)
    gap_y = _scale_y(ch, 1)
    fh_opt = intro_font.get_height()
    min_cell_floor = max(_scale_y(ch, 10), fh_opt + 12)
    correct_slot = perm.index(question.correct_index)

    for i in range(3):
        opt_text = question.options[perm[i]]
        label = f"{i + 1}. {opt_text}"
        rect = pygame.Rect(mx, y, tw, min_cell_floor)
        if phase is FrierenQuizPhase.QUESTION:
            selected = i == option_index
            bg = _FQ_CELL_BG_SEL if selected else _FQ_CELL_BG
            border = _FQ_CELL_BORDER_SEL if selected else _FQ_CELL_BORDER
            fg = _FQ_TEXT_PRIMARY if selected else _FQ_TEXT_MUTED
        else:
            assert feedback_correct is not None
            assert chosen_slot is not None
            is_correct = i == correct_slot
            is_wrong_pick = i == chosen_slot and not feedback_correct
            if is_correct:
                bg = _FQ_FB_CORRECT_BG
                border = _FQ_FB_CORRECT_BORDER
                fg = _FQ_TEXT_PRIMARY
            elif is_wrong_pick:
                bg = _FQ_FB_BAD_BG
                border = _FQ_FB_BAD_BORDER
                fg = _FQ_TEXT_PRIMARY
            else:
                bg = _FQ_CELL_BG
                border = _FQ_CELL_BORDER
                fg = _FQ_TEXT_MUTED
        pygame.draw.rect(canvas, bg, rect)
        pygame.draw.rect(
            canvas,
            border,
            rect,
            width=max(1, rect.width // 120),
        )
        one = _fit_one_line_cjk(intro_font, label, tw - 2 * pad_x)
        ty = rect.y + (rect.height - fh_opt) // 2
        canvas.blit(intro_font.render(one, True, fg), (rect.x + pad_x, ty + 1))
        y += min_cell_floor + gap_y

    if phase is FrierenQuizPhase.FEEDBACK:
        assert perm_for_feedback is not None
        assert chosen_slot is not None
        assert feedback_correct is not None
        y += _scale_y(ch, 2)
        verdict = "正確！" if feedback_correct else "錯誤。"
        vc = _FQ_VERDICT_OK if feedback_correct else _FQ_VERDICT_BAD
        canvas.blit(menu_font.render(verdict, True, vc), (mx, y))
        y += menu_font.get_height() + _scale_y(ch, 2)
        expl_raw = (
            question.explanation_zh.strip()
            if question.explanation_zh.strip()
            else default_explanation_zh(question)
        )
        head, tail = _frieren_feedback_explanation_head_tail(
            question,
            expl_source=expl_raw,
        )
        for hl in _wrap_cjk(small_font, head, tw):
            canvas.blit(small_font.render(hl, True, _FQ_TEXT_PRIMARY), (mx, y))
            y += small_font.get_height() + 2
        if tail:
            for hl in _wrap_cjk(small_font, tail, tw):
                canvas.blit(small_font.render(hl, True, _FQ_TEXT_MUTED), (mx, y))
                y += small_font.get_height() + 2

    if phase is FrierenQuizPhase.QUESTION:
        nav_play = "【↑↓】選擇　【Enter】作答　【Esc】離開"
    else:
        nav_play = (
            "【Enter】下一題　【Esc】離開測驗"
            if q_round_1based < FRIEREN_QUIZ_NUM_QUESTIONS
            else "【Enter】查看成績　【Esc】離開測驗"
        )
    _draw_frieren_hint_bottom_right(
        canvas,
        font=hint_font,
        text=nav_play,
        cw=cw,
        ch=ch,
        color=_FRIEREN_HINT_RGB_DARK_UI,
    )
