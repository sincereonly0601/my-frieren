"""
滿 8／13／18 歲重大事件：進場前全畫面提示「重大事件」、粗體放大主標與滿歲對應前導句（``main.EVENT_ALERT``）→ 前言 → 三選一（五維合計 +30）→ 結語（每選項固定兩段，含世界後果與內省；``main`` 餘韻畫面**單頁**顯示，Enter 返回養成）。網頁版前言單頁含 ``preamble_merged_zh``、選擇頁含 ``choice_prompt_zh``；敘事基調同突發事件（葬送風奇幻，非原作轉載）。

八／十三／十八歲重大事件：賽莉耶線選項寫入 ``series_milestone_1``～``3``；尤蓓爾線選項寫入 ``ubel_milestone_1``～``3``（與五維一併用於 ``endings.resolve_ending``）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from training_actions import STAT_LABEL_ZH

MAJOR_TRIGGER_YEARS: Final[frozenset[int]] = frozenset({8, 13, 18})

_FIVE: Final[tuple[str, ...]] = ("int_stat", "str_stat", "social", "fth_stat", "pragmatic")


@dataclass(frozen=True)
class MajorEventOption:
    """
    重大事件單一選項。

    Attributes:
        label: 選項標題。
        deltas: 五維增量，加總必為 +30。
        flags_add: 結算時寫入的劇情旗標。
        flags_add_if_male: 僅主角為男性時額外寫入（南方勇者線／克拉福特線等）。
        extra_deltas: 隱藏數值等（不計入五維 30 點）。
    """

    label: str
    deltas: dict[str, int]
    flags_add: frozenset[str] = frozenset()
    flags_add_if_male: frozenset[str] = frozenset()
    extra_deltas: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class MajorEvent:
    """
    單一年齡的一則重大事件。

    Attributes:
        age_year: 滿歲觸發（8／13／18）。
        title: 事件總標題（選擇畫面用）。
        preamble_title: 前言小標（網頁版標題列括號內地點，比照奇遇）。
        preamble_body: 前言段落（多段；桌機版逐段換行）。
        preamble_merged_zh: 網頁版前言單頁用：含地點之濃縮連續正文（約 180 字；寬欄視覺約五行，極窄螢幕可自然多折，不以行數硬裁）；標題列不含括號地點。
        choice_prompt_zh: 網頁版選擇畫面題幹（連續一段；約兩行視覺列，字數與版型對齊）。
        resolution_bodies: 三個選項各自結語段落（每選項兩段字串）。
        options: 三選一。
    """

    age_year: int
    title: str
    preamble_title: str
    preamble_body: tuple[str, ...]
    preamble_merged_zh: str
    choice_prompt_zh: str
    resolution_bodies: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    options: tuple[MajorEventOption, MajorEventOption, MajorEventOption]


def _mo(
    label: str,
    deltas: dict[str, int],
    *,
    flags: frozenset[str] | None = None,
    flags_if_male: frozenset[str] | None = None,
    extra: dict[str, int] | None = None,
) -> MajorEventOption:
    """建立選項並斷言五維加總為 +30。"""
    s = sum(deltas.get(k, 0) for k in _FIVE)
    if s != 30:
        raise ValueError(f"major option must sum +30 on five stats, got {s}: {label!r}")
    for k in deltas:
        if k not in _FIVE:
            raise ValueError(f"invalid key in major deltas: {k}")
    return MajorEventOption(
        label=label,
        deltas={k: int(deltas[k]) for k in _FIVE if k in deltas and deltas[k] != 0},
        flags_add=flags or frozenset(),
        flags_add_if_male=flags_if_male or frozenset(),
        extra_deltas=dict(extra) if extra else {},
    )


_MAJOR_8 = MajorEvent(
    age_year=8,
    title="遺跡邊的一句話",
    preamble_title="邊境石室",
    preamble_body=(
        "村外半塌禮拜堂的地下，有一面刻滿細小符文的石牆。相傳是很久以前某位魔法使路過時隨手留下——沒有署名，也無人敢貿然拓印。"
        "僧侶說：看得懂的，女神會讓她看見；看不懂的，便把紋路當作石頭天生的花紋也好。公會則要妳把任何發現先行登記，免得禁忌術式外流，落到不該接手的人手裡。",
        "滿八歲這天，導師第一次帶妳下去。石階潮冷，火把搖曳，灰塵在光裡像細雪飄墜。石上筆跡映入妳眼底的瞬間，竟比課本上的字更分明，彷彿它們從未沉睡，只是在等一個終於站到此地的讀者。",
    ),
    preamble_merged_zh=(
        "邊境石室藏在村外半塌禮拜堂地底，石牆刻滿小符文，相傳無名魔法使隨手所留，無人敢貿然拓印；僧侶說女神會讓看得懂的人看見，公會則要妳先登記以免禁忌術式落到不該接手的人手裡。"
        "八歲這天導師第一次帶妳下去，潮冷石階上火把搖曳，灰塵在光裡像細雪飄墜，石上筆跡映入妳眼底竟比課本更分明，彷彿它們從未沉睡，只在等妳這位站到此地的讀者。妳把指尖微顫藏好，而仍抬眼把符文讀進心底。"
    ),
    choice_prompt_zh=(
        "石室符文已映入眼底：可自行抄錄追尋、拓本蠟封上繳或祝聖後離開，公會教會各有規矩，此刻妳須擇一承擔並寫進日後之路。"
    ),
    resolution_bodies=(
        (
            "妳把符文抄進筆記，徹夜對照公會與教會的禁書目錄。數年後，邊境開始流傳「有人能讀懂無名者的術式」——那名字常被誤傳，但妳不在乎；妳只在乎句子是否閉合。"
            "王都學會收到過妳匿名寄出的幾頁推導；北方哨站則抱怨「紙上談兵」。無論如何，那面牆再也沒有被當成單純的裝飾。",
            "妳後來才明白：求知並非把世界變成謎題集，而是願意為每一個被說出口的答案承擔後果——包含那些被妳打開、再也關不回去的門。",
        ),
        (
            "妳將拓本交給公會蠟封，自己不再翻閱。十年內，沒有學徒因誤觸而受傷，也沒有人因好奇而失蹤——在檔案室深處，那卷紙成為一串編號，安靜得像冬眠。"
            "有人說妳太謹慎；妳只說：「有些門，該由能負責的人來開。」",
            "妳偶爾自問：若當初選了獨自解讀，今日邊境會不會多一則血色的傳說？妳不執著於假設，只把「延後滿足」當成對眾人耐心的練習。"
            "妳也漸漸把等待當成一種節拍：不是停滯，而是讓蠟封下的沉默在對的時刻開聲。",
        ),
        (
            "妳在祈禱後離開石室，把疑問交給女神與時間。村裡多了一則睡前故事：「石頭會記得，但孩子要先長大。」"
            "後來戰火與歉收輪替，那面牆仍在；偶爾有旅人在此歇腳，抬頭望一眼，便覺得心裡輕了一點。",
            "妳不把它叫作逃避，而稱之為「把重量交出去」：承認自己此刻還扛不動全部意義，並不等於永遠放棄理解。"
            "多年後妳懂了，信仰有時不是答案本身，而是讓妳在沒有答案時仍能繼續走路的那口氣——像石階上的潮冷，提醒妳活著，且仍會成長。",
        ),
    ),
    options=(
        _mo(
            "抄錄並自行追尋語意（可能觸及禁忌知識）",
            {"int_stat": 18, "pragmatic": 12},
            flags=frozenset({"series_milestone_1"}),
            extra={"truth_seek": 8},
        ),
        _mo(
            "將拓本交公會封存，自己不保留副本",
            {"pragmatic": 14, "social": 10, "int_stat": 6},
            flags=frozenset({"ubel_milestone_1"}),
            flags_if_male=frozenset({"hero_south_milestone_1"}),
        ),
        _mo(
            "不再深究，把現場交給僧侶祝聖後離開",
            {"fth_stat": 16, "social": 10, "int_stat": 4},
            flags_if_male=frozenset({"kraft_milestone_1"}),
        ),
    ),
)

_MAJOR_13 = MajorEvent(
    age_year=13,
    title="執照前的倫理試問",
    preamble_title="公會口試廳",
    preamble_body=(
        "取得獨立委託資格前，最後一關不是詠唱，而是問答。石砌的口試廳裡燈火穩定，卻讓人更覺得呼吸太響；"
        "長桌後坐著公會仲裁、教區代表，還有一名自始至終只動筆、不抬眼的紀錄員——妳將來簽下的每一紙委託，都要先通過他們的沉默審視。",
        "題目只有一則：若押送中的魔族俘虜以流利人語求饒，並拋出可驗證的情報，聲稱能動搖邊境防線的判斷——是否該暫停處決，給予審訊、對質、與足以讓謊言不藏身段的時間？"
        "廳外傳來風聲與盔甲摩擦聲，像有人在等你先開口。妳明白此刻沒有「隨便答答」的餘地：任何一句話都會寫進檔案，跟著名字走很久，也會在別人的生死簿邊留下墨痕。",
    ),
    preamble_merged_zh=(
        "公會口試廳裡燈火穩定卻讓呼吸顯得太響，取得獨立委託前最後一關是問答；長桌後坐著公會仲裁、教區代表與紀錄員，妳將來簽下的每一紙委託都要先通過他們沉默審視。"
        "題目是押送中的魔族俘虜以流利人語求饒並拋可驗證情報、聲稱能動搖邊境判斷時，是否暫停處決給審訊與對質；廳外風聲與盔甲摩擦像催促妳先開口，妳明白每一句都會寫進檔案跟著名字走。妳把背脊挺直片刻，預備把定義說清楚了。"
    ),
    choice_prompt_zh=(
        "口試廳裡俘虜人語難辨：分開驗證並公開紀錄、當場斷然或教會監聽短審與告解，妳每句入檔，邊境章程隨妳名走很久仍深遠。"
    ),
    resolution_bodies=(
        (
            "妳要求「語言真偽」與「心智是否同一」分開驗證，並堅持紀錄對外公開摘要。爭議延燒了整個雨季，但此後北境多了一條暫行章程：審訊不得單方黑箱。"
            "反對者罵妳天真；支持者說妳至少沒有把決定權交給恐慌。檔案裡，妳的名字旁邊多了一個小小的註記：「曾質詢定義」。",
            "妳後來常在風雨夜想起口試廳：恐懼會催促人省略步驟，而妳選擇把步驟寫清楚——哪怕慢，也要讓「為什麼」留下痕跡。"
            "多年後妳在更吵的廣場爭辯裡仍會先找紀錄員的筆：你相信紙，勝過相信嗓門。",
        ),
        (
            "妳主張「威脅未解除前不談條件」，並願意親自押送處刑現場。那日沒有演說，只有刀落與風止。"
            "多年後，同一套說法仍被引用——有時為了救更多的人，有時只是為了不再思考。妳不後悔，但也不再提起那天火把的味道。",
            "妳承認自己曾把複雜的道德題簡化成一道口令：先活下來。可每當有人借妳的名去合理化粗暴，妳就知道「果決」也需要被審問。"
            "凍原霧裡巡邏隊擦肩敬禮時眼神複雜，妳收下不語，只把杖握得更穩，像握一條還沒寫完的章程。",
        ),
        (
            "妳請教會主持告解式的監聽，公會負責術式封口令，並給俘虜最後一次陳述。沒能救下每一條命，但至少沒有人在暗室裡獨自死去。"
            "邊境教堂多了一項苦差事：為「來不及赦免的人」點燈。燈火很小，卻徹夜不熄。",
            "妳在燈火旁學到：憐憫不是推翻判決的藉口，而是拒絕把任何人貶成「只配被忘掉的數字」。"
            "多年後你在更北的歇腳處也遇過徹夜不熄的小燈，才懂那光從不打算說服誰，只是替「來不及說完的話」留一個位置。",
        ),
    ),
    options=(
        _mo(
            "要求分開驗證「語言」與「心智」，並留下公開紀錄",
            {"int_stat": 22, "pragmatic": 8},
            flags=frozenset({"series_milestone_2"}),
            extra={"truth_seek": 6},
        ),
        _mo(
            "主張當場斬除威脅，不接受談判拖延",
            {"str_stat": 20, "pragmatic": 10},
            flags=frozenset({"ubel_milestone_2"}),
            flags_if_male=frozenset({"hero_south_milestone_2"}),
        ),
        _mo(
            "支持教會監聽下的短暫審訊與告解程序",
            {"fth_stat": 18, "social": 8, "pragmatic": 4},
            flags_if_male=frozenset({"kraft_milestone_2"}),
        ),
    ),
)

_MAJOR_18 = MajorEvent(
    age_year=18,
    title="北方線徵召令",
    preamble_title="王都告示板",
    preamble_body=(
        "滿十八歲這週，王都與公會同貼徵召：北方遺跡帶缺見習以上的魔法使——任期長、補給薄，紅字標著回報率。人群在雨裡擠著抄寫；紙背有人用炭筆寫滿退路：留校、教區療養、商隊南下——沒一條寫「比較輕鬆」，只寫「先活著把選擇想完」。",
        "監護人把筆與印泥推到妳面前，不替妳選，只說：「長壽種看得太多；短壽種才懂把『現在』當武器——不是衝動，是知道自己沒有無限次重來。」廳裡一時寂靜；妳明白簽與不簽，都會改寫別人地圖上的一條線。",
    ),
    preamble_merged_zh=(
        "王都告示板前紅字與雨絲交錯閃爍，滿十八歲這週王都與公會同貼北境徵召，缺見習以上魔法使，任期長補給薄，紅字標著回報率；人群在雨裡擠著抄寫，紙背用炭筆寫滿留校、教區療養或商隊南下等退路，沒一條寫比較輕鬆，只寫先活著把選擇想完。"
        "監護人把筆與印泥推到妳面前，說短壽種該把現在當武器；妳明白簽與不簽都會改寫旁人地圖上的一條線。妳接過筆，感到紙背雨痕仍溫，呼吸也跟著沉住。"
    ),
    choice_prompt_zh=(
        "王都告示紅字雨中：同時背北境與學會遠距、只上前線戰鬥編制或留教區後勤，簽落筆妳與旁人地圖齊改線，無從假裝沒看見。"
    ),
    resolution_bodies=(
        (
            "妳接下北境觀測副隊，同時保留學會的遠距課題。十年裡，地圖上的紅線退了又進，但妳的筆記本從未停過——別人寫戰報，妳寫風向與魔導殘留。"
            "有人笑妳既不純戰也不純學；妳知道自己在縫兩條線，讓後來的人少跌一次跤。",
            "妳後來把這條路叫作「拒絕單選」：世界逼妳站隊時，妳選擇同時背兩份責任——疲憊是真的，但妳寧可疲憊也不要視野變窄。"
            "學會遠距送來的紙偶偶爾遲到半日，妳反倒安心：那代表有人仍在路上，而不是世界縮成一張會議桌。",
        ),
        (
            "妳只帶一柄法杖與乾粮北上。凍原上的星特別低，魔物的叫聲像裂冰。公會檔案裡，妳的欄位逐漸只剩任務代號與存活勾選。"
            "王都酒館仍傳著「那個沒回來的女孩」——其實妳回來過，只是沒進城，直接去了下一座哨站。",
            "妳清楚自己選了最直接的那條路：把恐懼折成腳程，把猶豫留在身後。可每當夜深，妳仍會問：「我是否也把別人的退路一起燒掉了？」"
            "哨站壁上的地圖補丁愈摞愈厚，妳以為自己在擦去迷霧，卻也在擦去「還能原路折返」的幻覺。",
        ),
        (
            "妳留在教區，負責安置與療癒。傷兵換了一批又一批，妳學會在祈禱詞之間塞進具體的藥草份量與換藥時辰。"
            "某年春天，有人從北方帶回一片融雪下的新芽，插在妳窗邊。妳沒問來歷，只澆了水。",
            "妳曾以為留下代表怯懦，後來才懂：把破碎的人重新拼回能呼吸的形狀，需要與上前線同等的勇氣，只是火光更細、更久。"
            "窗邊新芽某年枯過一次，妳沒拔；妳信土壤裡還藏得下一位春天，就像信傷口會結痂仍會痛。",
        ),
    ),
    options=(
        _mo(
            "同時接下北境觀測與學會遠距研究（兩頭背負）",
            {"int_stat": 16, "pragmatic": 10, "social": 4},
            flags=frozenset({"series_milestone_3"}),
            extra={"truth_seek": 4},
        ),
        _mo(
            "只選北線戰鬥編制，其餘不談",
            {"str_stat": 22, "pragmatic": 8},
            flags=frozenset({"ubel_milestone_3"}),
            flags_if_male=frozenset({"hero_south_milestone_3"}),
        ),
        _mo(
            "留在教區療養與後勤，婉拒遠征",
            {"fth_stat": 16, "social": 9, "pragmatic": 5},
            flags_if_male=frozenset({"kraft_milestone_3"}),
        ),
    ),
)

MAJOR_EVENTS: Final[tuple[MajorEvent, ...]] = (_MAJOR_8, _MAJOR_13, _MAJOR_18)
MAJOR_EVENT_BY_AGE: Final[dict[int, MajorEvent]] = {e.age_year: e for e in MAJOR_EVENTS}


def major_event_for_age(age_years: int) -> MajorEvent | None:
    """
    取得指定滿歲的重大事件定義。

    Args:
        age_years: 滿歲年齡。

    Returns:
        有則回傳事件；否則 None。
    """
    return MAJOR_EVENT_BY_AGE.get(age_years)


def format_major_deltas_brief(deltas: dict[str, int]) -> str:
    """
    將五維增量化為簡短中文（重大事件選項用）。

    Args:
        deltas: 僅五維鍵。

    Returns:
        例如「智力+18  務實+12」。
    """
    bits = [
        f"{STAT_LABEL_ZH.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in sorted(deltas.items())
        if v != 0 and k in STAT_LABEL_ZH
    ]
    return "  ".join(bits) if bits else "（無變化）"


def format_major_extra_brief(extra: dict[str, int]) -> str:
    """
    隱藏數值增量簡述（Toast 附加）。

    Args:
        extra: 如 truth_seek。

    Returns:
        可接在主要五維說明後。
    """
    labels = {"truth_seek": "真理探求", "corruption": "腐化傾向"}
    bits = [
        f"{labels.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in sorted(extra.items())
        if v != 0
    ]
    return "、".join(bits) if bits else ""
