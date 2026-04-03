"""
遭遇戰：敵人資料、滿歲觸發、參戰／寶物數值與畫廊鍵。

解鎖／畫廊／全螢幕預覽 CG：``assets/cg/encounters/<id>.jpg``。
戰鬥畫面專用 CG（可與畫廊圖分檔）：``assets/cg/encounters/<id>_battle.jpg``；
若缺戰鬥圖則自動退回同一 ``<id>.jpg``。缺檔時介面以程式圖示占位。
實際戰鬥中的敵方生命／攻防由 ``encounter_sim`` 再乘算（含池別係數），與下表
``base_*`` 共同決定畫面上之結算面板與難度。
同池內若干面板明顯偏低之個體已單獨拉高 ``base_*``，以縮小彼此手感差距（不改寶物與敘事）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import random

EncounterTier = Literal["monster", "elite", "boss"]


def encounter_battle_mode_title_zh(tier: EncounterTier) -> str:
    """
    戰鬥畫面左上角：依遭遇階級顯示之模式標題（魔物／強敵／頭目）。

    Args:
        tier: 敵人所屬池別。

    Returns:
        繁中文案。
    """
    return {
        "monster": "遭遇戰 - 魔物戰",
        "elite": "遭遇戰 - 強敵戰",
        "boss": "遭遇戰 - 頭目戰",
    }[tier]


@dataclass(frozen=True)
class EncounterEnemy:
    """
    單一遭遇戰敵人定義。

    Attributes:
        id: 畫廊／存檔用英數鍵。
        tier: 魔物／強敵／頭目，對應 6／11／16 歲池。
        name_zh: 顯示中文名。
        name_en: 英文或常用羅馬字簡稱。
        difficulty: 1～3（魔物／強敵）或 3～5（頭目），影響戰鬥面板與寶物。
        base_hp: 敵方基準生命。
        base_atk: 敵方基準攻擊。
        base_def: 敵方基準防禦。
        move_names: 一般招式台詞池。
        ultimate_zh: 大招顯示名。
        aftermath_win: 勝利餘韻段落（建議兩句／兩段；逾兩段時顯示會併為第二段）。
        aftermath_lose: 敗北餘韻段落（同上）。
        treasure_deltas: 勝利時額外套用（敗北不套用）；鍵限五維（與參戰增量同集合）。
        treasure_name_zh: 該敵固定寶物簡名（建議七字以內；餘韻首行「獲得寶物」用）。
        gallery_intro_zh: 畫廊全螢幕底欄之簡介（**單段連續**、勿換行分段）。請依角色與戰意**改寫**成約兩行內可讀完、結尾自然收束的一句或兩句；勿貼長段劇情後仰賴裁切，亦勿以逗號／分號串未完句。
    """

    id: str
    tier: EncounterTier
    name_zh: str
    name_en: str
    difficulty: int
    base_hp: int
    base_atk: int
    base_def: int
    move_names: tuple[str, ...]
    ultimate_zh: str
    aftermath_win: tuple[str, ...]
    aftermath_lose: tuple[str, ...]
    treasure_deltas: dict[str, int]
    treasure_name_zh: str
    gallery_intro_zh: str


# 滿 6／11／16 歲當季結算後觸發；取代該歲突發事件。
ENCOUNTER_TRIGGER_YEARS: Final[frozenset[int]] = frozenset({6, 11, 16})

# 無論勝敗皆套用（與突發選項相同五維鍵，合計 +10）。
ENCOUNTER_PARTICIPATION_DELTAS: Final[dict[str, int]] = {
    "int_stat": 2,
    "str_stat": 2,
    "fth_stat": 2,
    "pragmatic": 2,
    "social": 2,
}

_P = ENCOUNTER_PARTICIPATION_DELTAS.keys()


def encounter_cg_rel_path(enemy_id: str) -> str:
    """
    解鎖／畫廊／全螢幕預覽用之遭遇 CG 相對路徑（jpg；缺檔時由 UI 占位）。

    Args:
        enemy_id: ``EncounterEnemy.id``。

    Returns:
        例如 ``assets/cg/encounters/einsam.jpg``。
    """
    return f"assets/cg/encounters/{enemy_id}.jpg"


def encounter_cg_battle_rel_path(enemy_id: str) -> str:
    """
    戰鬥畫面專用之敵方 CG 相對路徑（與畫廊圖可分檔製作）。

    Args:
        enemy_id: ``EncounterEnemy.id``（或別名鏈上之鍵，見 ``encounter_cg_try_ids``）。

    Returns:
        例如 ``assets/cg/encounters/einsam_battle.jpg``。
    """
    return f"assets/cg/encounters/{enemy_id}_battle.jpg"


def encounter_cg_battle_try_rel_paths(enemy_id: str) -> tuple[str, ...]:
    """
    戰鬥 CG 載入時依序嘗試之相對路徑：每個候選 id 先 ``_battle``，再共用畫廊 ``<id>.jpg``。

    Args:
        enemy_id: 敵人鍵（可為舊別名，見 ``encounter_cg_try_ids``）。

    Returns:
        去重後、由先到後嘗試之路徑序列。
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for eid in encounter_cg_try_ids(enemy_id):
        for rel in (encounter_cg_battle_rel_path(eid), encounter_cg_rel_path(eid)):
            if rel not in seen:
                seen.add(rel)
                ordered.append(rel)
    return tuple(ordered)


# 舊存檔／畫廊 JSON 曾使用之 id → 現行 ``EncounterEnemy.id``（``ENCOUNTER_BY_ID`` 僅含現行鍵）。
LEGACY_ENCOUNTER_ID_ALIASES: Final[dict[str, str]] = {
    "lernen": "revolte",
    # 幼年期魔物池已移除「隕鐵鳥」；舊存檔／畫廊鍵 ``stille`` 對應至現行魔物以便載入 CG。
    "stille": "red_mirror_dragon",
    # 幼年期魔物池已移除「脫出用哥雷姆」；舊鍵 ``escape_golem`` 對應至現行魔物以便載入 CG。
    "escape_golem": "spiegel",
    # 幼年期魔物池已移除「寶箱怪」；舊鍵 ``mimic`` 對應至現行魔物以便載入 CG。
    "mimic": "spiegel",
    # 強敵 id 已改為 ``zorida``／``hemon``（舊鍵相容存檔與畫廊）。
    "ubel": "zorida",
    "lernen_assassin": "hemon",
}


def resolve_encounter_id(enemy_id: str) -> str:
    """
    將別名對應至現行遭遇敵 id；無別名則原樣回傳。

    Args:
        enemy_id: 畫廊或存檔內之鍵。

    Returns:
        現行 ``EncounterEnemy.id``。
    """
    return LEGACY_ENCOUNTER_ID_ALIASES.get(enemy_id, enemy_id)


def encounter_cg_try_ids(enemy_id: str) -> tuple[str, ...]:
    """
    載入 CG 時依序嘗試的檔名 id（現行鍵優先，再嘗試舊檔名以利遷移）。

    Args:
        enemy_id: ``EncounterEnemy.id`` 或舊別名。

    Returns:
        依序嘗試之 id 元組。
    """
    canonical = resolve_encounter_id(enemy_id)
    if canonical == "revolte":
        return ("revolte", "lernen")
    if enemy_id == "stille":
        return ("red_mirror_dragon", "stille")
    if enemy_id == "escape_golem":
        return ("spiegel", "mimic", "escape_golem")
    if enemy_id == "mimic":
        return ("spiegel", "mimic")
    # 強敵「佐莉妲」現行 id 為 ``zorida``；舊素材檔名可能仍為 ``ubel``。
    if canonical == "zorida":
        return ("zorida", "ubel")
    # 強敵「黑蒙」現行 id 為 ``hemon``；舊素材檔名可能仍為 ``lernen_assassin``。
    if canonical == "hemon":
        return ("hemon", "lernen_assassin")
    return (canonical,)


_MONSTERS: tuple[EncounterEnemy, ...] = (
    EncounterEnemy(
        id="einsam",
        tier="monster",
        name_zh="幻影鬼",
        name_en="Einsam",
        difficulty=2,
        base_hp=59,
        base_atk=13,
        base_def=6,
        move_names=(
            "迷霧撲擊",
            "殘響爪痕",
            "無形絞勒",
            "幻影折步",
        ),
        ultimate_zh="百裂殘象",
        aftermath_win=(
            "幻影鬼的輪廓在咒式餘光裡碎成薄霧，像《葬送的芙莉蓮》裡那些靠恐懼餵養的魔物——牠不執著於血肉，只執著於讓獵物相信自己「孤身一人」。妳收束魔力的指尖比預期更穩，因為妳想起旅途上真正的威脅往往不是爪牙，而是心先退縮。",
            "邊境的童謠會多一則：看見獨行的鬼影，要先看見自己的影子。妳把這場勝利寫進身體記憶裡：下次迷霧再起，妳會先確認腳下仍有路，而不是先聽見耳語。",
        ),
        aftermath_lose=(
            "視線被扯成碎片，妳在最后一刻用障壁換到喘息距離；幻影鬼沒有追擊的腳步聲，只有霧氣貼著後頸退去，像《葬送的芙莉蓮》裡常見的那種結束——敵人未必仁慈，只是對「落單的獵物」另有玩法。",
            "村裡老人只說活著回來就好；可妳知道那一爪在記憶裡留下凹痕。妳開始理解：有些魔族不急着殺人，牠們更擅長讓妳在下一次遭遇前，就先把自己孤立。",
            "回程路上妳刻意放慢腳步，聽自己的靴跟與風聲，像在確認「孤單」只是路況而不是命運。妳把披風拉緊，在筆記邊緣寫下「先找同伴的影子」——下一場迷霧裡，真正要對決的不是鬼影，而是自己先別慌。",
        ),
        treasure_deltas={"int_stat": 2, "pragmatic": 2, "fth_stat": 1},
        treasure_name_zh="孤星霧核",
        gallery_intro_zh=(
            "幻影鬼以孤獨感化霧，獵物往往先自疑；心先退縮時迷霧比爪牙更致命。"
            "先確認腳下仍有路、同伴仍在，再找敵影，勿把孤單當成命運。"
        ),
    ),
    EncounterEnemy(
        id="nameless_juvenile_mazoku",
        tier="monster",
        name_zh="不知名幼年魔族",
        name_en="Nameless juvenile Mazoku",
        difficulty=2,
        base_hp=58,
        base_atk=12,
        base_def=7,
        move_names=(
            "咒式含糊",
            "幼角頂撞",
            "本能撕咬",
            "魔力亂流",
        ),
        ultimate_zh="未名之劫",
        aftermath_win=(
            "那個「不知名」的幼魔族倒下時沒有遺言，只有咒式斷裂的啞響。牠們在傳說裡常被預言成未來的災厄，可此刻不過是想在邊境活下去的個體——妳仍扣下最後一筆，因為妳知道寬容與愚蠢的界線，從來不在年齡。",
            "妳把角屑與殘咒收進袋裡，忽然明白：魔族的名姓不是名字，是契約。還沒學會完整語言的幼崽，反而最危險，因為牠無法說服、也無法被說服；妳只能先讓牠失去繼續攻擊的理由。",
        ),
        aftermath_lose=(
            "幼年的魔族沒有成熟到能嘲諷妳，牠只是用本能的咒式與尖角把距離縮到零；妳退開時才想起，「不知名」不是弱點，是還沒被定義的鋒利。《葬送的芙莉蓮》裡常說魔族與人無法真正互相理解——面對幼崽時，這句話更像詛咒而非藉口。",
            "妳沒有輸給天真，妳輸給了「以為可以談」的那一瞬間猶豫。下次妳會先把退路畫在腳下，再決定要不要聽對方尚未成形的語言。",
            "營火邊妳反覆摸著擦傷的臂甲，忽然覺得好笑：大人總教孩子別欺負弱小，可邊境從不承認誰是「可以放水」的對象。妳在筆記寫下「幼年期＝未定義」，提醒自己未定義的咒式往往最難預讀。",
        ),
        treasure_deltas={"int_stat": 2, "fth_stat": 2, "social": 1},
        treasure_name_zh="未名角屑",
        gallery_intro_zh=(
            "幼年魔族施術未定型，難以預讀；本能已把對方當敵，莫因年幼放水。"
            "先封走位再辨咒式，寬容與愚蠢的界線從不在年齡。"
        ),
    ),
    EncounterEnemy(
        id="red_mirror_dragon",
        tier="monster",
        name_zh="紅鏡龍",
        name_en="Red mirror wyrm",
        difficulty=3,
        base_hp=74,
        base_atk=14,
        base_def=9,
        move_names=(
            "鏡面吐息",
            "熾鱗掃尾",
            "折射焰流",
            "龍威壓迫",
        ),
        ultimate_zh="千面紅劫",
        aftermath_win=(
            "紅鏡龍的瞳裡曾映出妳的倒影——那種「把敵人看進眼裡」的傲慢，與《葬送的芙莉蓮》裡高階魔物共通的殘酷相同。可這次先閉眼的是牠；妳用咒式切斷牠引以為傲的吐息迴路，像切斷一場過度華麗的演出。",
            "餘燼裡拾得的鱗片像一面過小的鏡子，照得出狼狽也照得出活路。妳把它收好：龍與精靈一樣長壽的傳說背後，永遠是短壽者一次次用血寫下的備註。",
        ),
        aftermath_lose=(
            "焰浪把視野染成同一種紅，妳用盡魔力退到岩後，只聽見龍吟漸遠。《葬送的芙莉蓮》裡的撤退從來不是羞恥，而是把「下一次詠唱」留給還能呼吸的肺。",
            "有人會把逃走稱為怯懦；妳稱之為清算。妳摸著燙傷的指尖想起：芙莉蓮若在此，大概只會淡淡說——別死，死了就什麼都學不到。",
            "妳用冷水敷手，看蒸氣裡自己的倒影被紅光染花，忽然明白龍的鏡面不只是攻擊，也是逼妳認清魔力邊界。妳把「折射」當成下一題的關鍵詞：下次要在牠吐息前，先切斷自己對華麗招式的執著。",
        ),
        treasure_deltas={"str_stat": 3, "fth_stat": 3, "int_stat": 2},
        treasure_name_zh="紅鏡熾屑",
        gallery_intro_zh=(
            "紅鏡龍以鏡面吐息與龍威逼你先看見自己的破綻；猶豫是第二層傷。"
            "折射與鱗焰來前先收束魔力邊界，別在華麗招式前輸給動搖。"
        ),
    ),
    EncounterEnemy(
        id="spiegel",
        tier="monster",
        name_zh="水鏡惡魔",
        name_en="Spiegel",
        difficulty=2,
        base_hp=65,
        base_atk=13,
        base_def=8,
        move_names=(
            "鏡像刺擊",
            "水面縫合",
            "惡意倒影",
            "咒式折射",
        ),
        ultimate_zh="溺沒之真名",
        aftermath_win=(
            "水面碎裂，惡魔的笑聲卡在裂紋裡；史佩吉爾這類存在最像《葬送的芙莉蓮》對「魔族語言」的警句——牠們懂得用倒影讓妳以為自己早已敗北。妳看見自己的表情比想像中冷靜，因為妳終於把「自我懷疑」從咒式裡剔除了。",
            "有人說水鏡會偷走名字；妳把名字握回掌心，連同餘波一併掐滅。妳明白魔族最可怕的從不是鏡面，而是牠們總挑妳最願意相信的那個故事下手。",
        ),
        aftermath_lose=(
            "妳的術式被彈回一半，像對著自己揮拳；惡魔鞠躬行禮，像在感謝妳的失誤。《葬送的芙莉蓮》裡的魔族常帶禮貌的笑——那不是善意，是捕食前的儀式感。",
            "這一戰讓妳記住：鏡子從不創造謊言，只放大妳願意相信的那一側。妳咬緊牙把喘息藏好，因為妳知道牠還在等妳的下一個破綻。",
            "妳離開水邊時刻意不看任何反光，直到心跳平穩才允許自己照一下金屬扣——那瞬間妳練習用「旁觀」的眼神看自己的表情。妳把這種抽離寫成短咒式筆記：下次折射來臨前，先確認詠唱不是為了證明什麼，而是為了活著離開。",
        ),
        treasure_deltas={"int_stat": 2, "fth_stat": 2, "social": 1},
        treasure_name_zh="鏡裂真滴",
        gallery_intro_zh=(
            "水鏡惡魔以倒影與名字下手，專挑你願意相信的故事；鏡子只放大心切的那面。"
            "水面一動先穩呼吸，確認真名仍握在掌心；魔族的禮貌往往是捕食前奏。"
        ),
    ),
    EncounterEnemy(
        id="sword_village_lord",
        tier="monster",
        name_zh="劍之村山主",
        name_en="Sword Village lord",
        difficulty=3,
        base_hp=62,
        base_atk=15,
        base_def=8,
        move_names=(
            "山嵐斬",
            "試刃突刺",
            "村守架势",
            "鐵規壓迫",
        ),
        ultimate_zh="名刀演武",
        aftermath_win=(
            "山主收刀入鞘的聲音比任何喝采都乾淨；劍之村是《葬送的芙莉蓮》裡最執著於「名刀與規矩」的地方，對魔法使的偏見像鐵銹一樣厚。可妳用咒式證明：指尖敲出的不一定是花俏，也可以是節制與距離。",
            "這不是結束，是下一道門檻。村民未必立刻改口，但風裡的鐵味會記得——有一個魔法使沒有羞辱劍，也沒有跪拜劍，只是把勝負收束在該停的地方。",
        ),
        aftermath_lose=(
            "刀風掠過髮梢，妳在最后一刻側身——輸了，但沒有倒下。劍之村的山主不擅長安慰，他只擅長把「再來」兩字說得像契約。《葬送的芙莉蓮》裡，戰士與魔法使的摩擦從來不是恨，而是彼此丈量世界的尺不同。",
            "妳把「再來」收起來，像收起一張還沒蓋章的借據。妳知道自己輸在距離與起手，不在意志；而這種清醒，正是村外那位精靈最常留給後輩的東西。",
            "妳在村外溪邊洗淨袖口鐵味，看水流把泡沫帶走，像把屈辱也沖淡一層。妳反覆默念「起手前三步」：不是為了討好劍之村，而是為了下次對上同一把尺時，妳的咒式能先站穩腳跟再說話。",
        ),
        treasure_deltas={"str_stat": 3, "pragmatic": 3, "fth_stat": 2},
        treasure_name_zh="試合木札",
        gallery_intro_zh=(
            "劍之村山主守名刀與規矩，對魔法使偏見如鐵銹；咒式亦可示節制與距離。"
            "把勝負收在該停處，刀風掠髮時先站穩腳跟，勿把刀鳴當聖歌。"
        ),
    ),
    EncounterEnemy(
        id="dokkyoku_dragon",
        tier="monster",
        name_zh="毒極龍",
        name_en="Dokkyoku wyrm",
        difficulty=3,
        base_hp=72,
        base_atk=14,
        base_def=8,
        move_names=(
            "極毒吐息",
            "鱗霧擴散",
            "尾棘掃毒",
            "龍威麻痺",
        ),
        ultimate_zh="萬毒極淵",
        aftermath_win=(
            "毒極龍的紫霧在風裡散成薄絲，像《葬送的芙莉蓮》裡那些把「慢性」當戰術的高階魔物——牠不急著一口咬死獵物，只急著讓對手在數息之內算錯距離。妳用障壁與淨化咒式把毒線逼回牠喉間，像把一場拖長的處刑硬生生掐斷。",
            "邊境會多一則新謠：遇見紫霧先閉氣，再談反擊。妳把鱗粉掃進瓶裡封蠟，提醒自己：有些勝利不是轟烈，是把「還能呼吸」留在下一個黎明。",
        ),
        aftermath_lose=(
            "視野邊緣發紫，膝蓋像被細線纏住；毒極龍沒有追擊，只在遠處收翼，像在等妳自己倒下。《葬送的芙莉蓮》裡的龍類常把耐心當武器——牠們的殺意不必大聲，只要夠慢。",
            "妳用治癒術勉強壓住麻痺，心裡卻更清楚：下次要先切斷霧的來源，而不是硬扛一口氣。妳把失敗寫成配方：淨化、距離、再談吐息。",
            "妳倚著樹幹數心跳，直到指尖恢復知覺才把「紫霧」畫成箭頭：牠的毒不只在肺，也在節奏。妳告訴自己：下次要在牠張口前，先把風向與退路寫進咒式裡，別讓慢性變成妳的習慣。",
        ),
        treasure_deltas={"int_stat": 2, "pragmatic": 3, "fth_stat": 2},
        treasure_name_zh="極毒鱗粉",
        gallery_intro_zh=(
            "毒極龍以紫霧與麻痺拖長戰鬥，慢性毒先亂節奏；先閉氣、淨化再談反擊。"
            "風向與退路寫進咒式，龍的耐心常比牙更致命。"
        ),
    ),
    EncounterEnemy(
        id="chaos_flower_subspecies",
        tier="monster",
        name_zh="混沌花的亞種",
        name_en="Chaos flower subspecies",
        difficulty=2,
        base_hp=63,
        base_atk=12,
        base_def=7,
        move_names=(
            "花粉迷向",
            "瓣刃旋斬",
            "根鬚絆足",
            "亂色孢子",
        ),
        ultimate_zh="混沌盛開",
        aftermath_win=(
            "花瓣在咒式餘光裡碎成亂序的彩屑，像《葬送的芙莉蓮》裡那些不靠蠻力、靠「讓人看錯一步」取勝的魔植——混沌花的亞種不執著於一口咬穿，只執著於讓妳的距離感在下一瞬崩線。妳收束魔力的指尖比預期更穩，因為妳終於把花蕊當成術式節點，而不是風景。",
            "邊境的筆記會多一條：遇見亂色花粉先閉眼半拍，再談詠唱。妳把種子掃進瓶裡封蠟，提醒自己：有些魔物贏在讓妳以為自己還站得直。",
        ),
        aftermath_lose=(
            "視野邊緣的花紋彼此錯位，妳在最后一刻用障壁換到半步；亞種沒有追擊，只在風裡抖動花瓣，像在等妳自己踩進下一圈錯覺。《葬送的芙莉蓮》裡的撤退從來不是羞恥，而是把「下一次詠唱」留給還能對準焦的意識。",
            "妳把眩暈壓進胃裡，心裡卻更清楚：下次要先切斷花粉的來源，而不是硬扛一口氣。妳把失敗寫成配方：定座標、再談花色。",
            "妳靠著樹幹數心跳，直到耳鳴退去才把「亂色」畫成箭頭：牠的威脅不只在瓣刃，也在妳以為自己看見的那條路。妳告訴自己：下次要在花瓣翻飛前，先把視線鎖回腳下，別讓混沌變成習慣。",
        ),
        treasure_deltas={"int_stat": 2, "fth_stat": 2, "pragmatic": 2},
        treasure_name_zh="亂序花蕊",
        gallery_intro_zh=(
            "混沌花亞種以花粉與亂色打亂距離，瓣刃常晚於錯覺；先定腳下座標再詠唱。"
            "別盯旋花忘記起點，最危險是以為自己仍看得準。"
        ),
    ),
)

_ELITES: tuple[EncounterEnemy, ...] = (
    EncounterEnemy(
        id="lugner",
        tier="elite",
        name_zh="琉古納",
        name_en="Lugner",
        difficulty=2,
        base_hp=80,
        base_atk=17,
        base_def=9,
        move_names=(
            "血契束縛",
            "謊言加固",
            "魔族威壓",
            "術式篡寫",
        ),
        ultimate_zh="緋紅誓約",
        aftermath_win=(
            "琉古納的契約符文在空氣中斷成兩截，他仍笑得優雅——那是《葬送的芙莉蓮》裡魔族最典型的天賦：把謊言說得像祝福，把惡意包裝成條款。妳沒有被他激怒，因為芙莉蓮早用千年光陰提醒過後世：聽懂魔族語言的人，第一件事是別相信魔族話裡那份溫度。",
            "妳不給同情，只把「不可信」刻進每一次詠唱前的呼吸。妳明白他的血與誓約都很美，很美常常是陷阱的裝飾邊。",
        ),
        aftermath_lose=(
            "血線勒住手腕的瞬間，妳懂了何謂「語言即術式」——琉古納的話從來不是情緒，是鎖鏈。《葬送的芙莉蓮》裡，魔族的說服力來自牠們根本不理解人類為何會被語言動搖，卻能精準利用那種動搖。",
            "他俯身耳語的氣息像蠟燭將熄；妳推開距離，把失敗當成免疫的第一劑。妳告訴自己：下次要在牠開口前，先把契約的定義寫進自己的咒式裡。",
            "妳在燈下把腕上勒痕描成符文草稿，一筆一劃都像在還原「被說服」的瞬間。妳提醒自己：魔族的溫度是餌，真正要守的是呼吸節奏與詠唱起點——下次聽見好聽的話，先當成術式前搖來處理。",
        ),
        treasure_deltas={"int_stat": 3, "pragmatic": 2, "social": 2},
        treasure_name_zh="緋誓殘箔",
        gallery_intro_zh=(
            "琉古納把契約與謊言寫進血誓，話裡體貼多半是餌；契約未讀完切勿落筆。"
            "魔族語言的溫度不可信，血與誓約愈美愈可能是陷阱邊飾。"
        ),
    ),
    EncounterEnemy(
        id="linie",
        tier="elite",
        name_zh="莉妮耶",
        name_en="Linie",
        difficulty=2,
        base_hp=78,
        base_atk=18,
        base_def=7,
        move_names=(
            "拔刀零式",
            "足音抹除",
            "連斬殘影",
            "刃風迴環",
        ),
        ultimate_zh="一瞬千刃",
        aftermath_win=(
            "莉妮耶的刀尖停在某個將觸未觸的距離——她是人類，卻把拔刀練成近乎魔族的乾淨效率。《葬送的芙莉蓮》裡她讓人背脊發冷的地方不在快，而在她笑著把「殺意」當日常。妳用咒文扣住關節，像扣住時間：妳不是贏在更快，是贏在沒被她帶進她的節拍。",
            "快不是罪，輕敵才是。妳把這句話還給風裡的殘響，心裡補上一句：真正危險的是，她看起來還能更快。",
        ),
        aftermath_lose=(
            "視野被銀線切開又縫合；妳跪地喘息，才發現自己還活著——這已是答案。莉妮耶收刀的姿態像在收一封寫錯地址的信：《葬送的芙莉蓮》裡，她對弱者未必有恨，只是對「跟不上的人」缺乏耐心。",
            "輸給速度並不丟臉；丟臉的是以為自己能硬撐節奏。妳把屈辱折好放進口袋：下一次妳要先買距離，再談勝負。",
            "妳閉眼重播那一瞬的足音與刀鳴，像在腦中把節拍放慢半格。妳在沙地上畫出三步退避線：不是逃，是把「還能詠唱」當成比面子更高的優先序。妳知道她還能更快，所以妳得先學會不被她的笑帶進拍子裡。",
        ),
        treasure_deltas={"str_stat": 3, "int_stat": 2, "pragmatic": 2},
        treasure_name_zh="刃鍔寒息",
        gallery_intro_zh=(
            "莉妮耶拔刀極快、笑臉與殺意並存；先買距離再談節拍，詠唱重於面子。"
            "快不是罪，輕敵才是；節拍被她帶走時，刀鋒已不在你這邊。"
        ),
    ),
    EncounterEnemy(
        id="draht",
        tier="elite",
        name_zh="多拉特",
        name_en="Draht",
        difficulty=2,
        base_hp=78,
        base_atk=18,
        base_def=10,
        move_names=(
            "鋼線陷阱",
            "絞殺周界",
            "遠距穿刺",
            "絲網收束",
        ),
        ultimate_zh="蛛網處刑臺",
        aftermath_win=(
            "多拉特的鋼線鬆弛聲音像豎琴走調；他是琉古納陣營裡最安靜的殺意，把戰場切成幾何問題。《葬送的芙莉蓮》裡，這種敵人從不跟妳辯論正義，只問妳：妳的脖子是否在他計算好的弧線上。妳踏過斷絲，像踏過未完成的樂譜——這次，終止符由妳寫。",
            "空氣裡殘留金屬味，妳知道它會跟很久。那不是榮耀的味道，是提醒：下次進場前，先把「線在哪裡」畫在自己的腦海裡。",
        ),
        aftermath_lose=(
            "細線在皮膚上留下紅色地圖；妳用治癒術抹平傷口，抹不平餘悸。多拉特退入陰影時沒有得意，只有工作結束的空——《葬送的芙莉蓮》裡，這種冷靜比嘲諷更可怕。",
            "妳反而更警惕：他像一張會自己收束的網，失敗不是結束，是他下次起手的參數。妳把呼吸放慢，像芙莉蓮教會世界的那種慢——慢，才能看見線。",
            "妳舉起手指在空中虛描幾何，把剛才的痛感轉成座標：哪一步讓線有機會貼上頸側、哪一次轉身把背暴露給陰影。妳把這張「紅色地圖」收進心裡當教材——下次進場前，先畫完自己的逃生弧線再談反擊。",
        ),
        treasure_deltas={"pragmatic": 3, "fth_stat": 2, "int_stat": 2},
        treasure_name_zh="鋼音斷絲",
        gallery_intro_zh=(
            "多拉特以鋼線佈幾何，只問頸側是否在弧上；慢下來先看線怎麼轉彎。"
            "金屬味會跟很久作提醒，網收束前先在腦中畫好逃生弧。"
        ),
    ),
    EncounterEnemy(
        id="sword_demon",
        tier="elite",
        name_zh="劍之魔族",
        name_en="Sword demon",
        difficulty=3,
        base_hp=88,
        base_atk=19,
        base_def=11,
        move_names=(
            "魔劍共鳴",
            "斬咒連攜",
            "黑鐵突刺",
            "劍氣裂地",
        ),
        ultimate_zh="斷鋼魔宴",
        aftermath_win=(
            "劍之魔族的劍鳴戛然而止；牠屬於那座把「劍」當宗教的村落，也屬於《葬送的芙莉蓮》裡最刺骨的對照——魔族能模仿人類的儀式感，卻沒有人類的悔意。妳的咒式像更冷的規矩壓住狂熱：妳不是否定劍，妳只是否定牠把殺意當榮耀的方式。",
            "天空仍灰，但腥甜少了一縷。妳知道村裡仍會有人瞪妳，可妳也知道，有些勝利只為了讓「下一個孩子」不必在同一把劍前跪下。",
        ),
        aftermath_lose=(
            "妳被劍壓逼到跪地，膝下石裂細紋；對方卻轉身離去，像興致已盡。《葬送的芙莉蓮》裡魔族常這樣：不追殺不是仁慈，是蔑視——妳還不值得牠把時間花完。",
            "那比追殺更羞辱，也更像審判。妳把顫抖藏進袖子，心裡記下：魔族的劍沒有「點到為止」，只有「妳還活著是因為牠允許」。",
            "妳跪到石板的冷意爬進膝蓋才慢慢站起，像用疼痛校準尊嚴的底線。妳把「允許」兩字寫在咒式札記最底：不是求牠施捨，而是逼自己下次站到牠願意認真揮劍的高度——那時蔑視才會變成對等的殺意。",
        ),
        treasure_deltas={"fth_stat": 3, "str_stat": 3, "int_stat": 3},
        treasure_name_zh="斷咒銹粉",
        gallery_intro_zh=(
            "劍之魔族借人類的儀式感揮劍，殺意乾淨卻無悔意；要擋的是把殺戮當榮耀的狂熱。"
            "劍鳴不是聖歌，揮刃前問自己為何而戰。"
        ),
    ),
    EncounterEnemy(
        id="zorida",
        tier="elite",
        name_zh="佐莉妲",
        name_en="Zorida",
        difficulty=3,
        base_hp=80,
        base_atk=20,
        base_def=8,
        move_names=(
            "旋風刃引",
            "長刀掃域",
            "攻守轉圜",
            "風壓逼迫",
        ),
        ultimate_zh="風噬劍嵐",
        aftermath_win=(
            "佐莉妲收刀時眼罩下的線條仍緊繃——她是雷沃戴麾下的女性魔族，好戰無畏，矇眼卻不妨礙她把長刀與「將攻擊轉化為旋風」的術式扣在同一拍裡：旋風不是花俏，是把妳能站穩的半徑一寸寸削掉。妳沒讓她畫完第二圈風。",
            "妳贏的不是比她更瘋，是比她更早讀懂「攻守兼備」也有破綻——當她為擴大範圍而揮得太大時，重心會誠實地偏向刃尖。妳把那一瞬折進咒式裡，像把一場暴風收成一句短詠。",
        ),
        aftermath_lose=(
            "妳被風壓與刀弧逼得後退，沙土在她腳邊捲成小漩渦；佐莉妲沒有多話，只有眼罩上緣那道陰影像在提醒妳：她的劍術紮實，旋風只是讓攻勢變寬的幫手。《葬送的芙莉蓮》世界裡，魔族常把戰鬥當語言——她把語言說得很乾淨，乾淨到讓人來不及生氣。",
            "雷沃戴的部下從不把憐憫當戰術；她只把妳當成下一次能削得更利的一塊砥石。妳把喘息咬住，記下她旋風與劈斬交錯的節奏：範圍大並不可怕，可怕的是她永遠留一手護身的後招。",
            "妳在營火邊對著空氣反覆比劃，瞄準想像中的風眼——若再對上，妳要先搶的不是距離，是她矇眼之下仍成立的節拍感。妳告訴自己：她的風會誤導腳步，肩與腰卻仍會說實話。",
        ),
        treasure_deltas={"int_stat": 3, "str_stat": 3, "social": 3},
        treasure_name_zh="風眼鞘砂",
        gallery_intro_zh=(
            "佐莉妲旋風長刀攻守一體，矇眼仍壓縮你站穩的半徑；讀肩腰勝過吼叫。"
            "大範圍揮砍時重心會偏向刃尖，別被風圈帶偏腳步。"
        ),
    ),
    EncounterEnemy(
        id="hemon",
        tier="elite",
        name_zh="黑蒙",
        name_en="Hemon",
        difficulty=2,
        base_hp=78,
        base_atk=18,
        base_def=9,
        move_names=(
            "迷霧蔽視",
            "錫杖叩擊",
            "霧中匿形",
            "角裂反制",
        ),
        ultimate_zh="霧海噬刃",
        aftermath_win=(
            "黑蒙退入灰霧，斷角在冷光裡像一枚說不完的註腳——雷沃戴麾下的男性魔族，以錫杖與「操控迷霧」的術式作戰：阻擋視線與魔法探測，把自身魔力藏進霧裡，也能察知對手的魔力再一擊收回。妳沒讓他把霧寫成第二層迷宮。",
            "妳知道這種敵人最可怕的不是藏，是他藏的同時仍能「讀」妳。妳把勝利收好，像收起一卷潮濕的地圖：下次進霧，妳要先畫出自己的定位點，別急著找他的錫杖。",
        ),
        aftermath_lose=(
            "霧貼上眼睫，錫杖的寒意擦過肩背；黑蒙的氣息與魔力融在灰白裡，妳的探測術像在對空揮拳。《葬送的芙莉蓮》裡的戰鬥常這樣：輸的不是咒式不夠亮，是資訊被對方先收走。",
            "他沒追，因為迷霧會替追擊；妳摸著肩頭餘顫，心裡把「隱蔽」劃進雷沃戴陣營的標籤——那不是偷襲的藉口，是他把戰場變成只剩他能讀的版本。",
            "妳用布巾一遍遍擦去錫杖留下的濕冷，像在擦拭自己的警覺底線。妳記下：斷角不代表斷刃，反而像提醒他——他早習慣用缺失去換更多勝算。",
        ),
        treasure_deltas={"pragmatic": 3, "int_stat": 3, "social": 2},
        treasure_name_zh="霧角錫灰",
        gallery_intro_zh=(
            "黑蒙以霧藏刃、藏魔力，錫杖聲即前奏；探測落空時先穩呼吸當座標。"
            "最可怕是霧裡他仍能讀你；進霧先定自身方位，再找錫杖。"
        ),
    ),
)

_BOSSES: tuple[EncounterEnemy, ...] = (
    EncounterEnemy(
        id="qual",
        tier="boss",
        name_zh="庫瓦爾",
        name_en="Qual",
        difficulty=5,
        base_hp=120,
        base_atk=22,
        base_def=14,
        move_names=(
            "腐敗咒式",
            "賢者威壓",
            "遲滯領域",
            "骨白荊冠",
        ),
        ultimate_zh="黃昏審判庭",
        aftermath_win=(
            "庫瓦爾的身影在術式餘燼裡淡去，像一本被闔上的禁書；他是《葬送的芙莉蓮》裡背負「腐敗」之名的賢老，與弗蘭梅的傳承形成刺眼的對照——知識若沒有界線，會變成比魔族更長久的災害。妳站在書脊這一側仍活著，不代表妳原諒了一切，只代表妳還能把界線說清楚。",
            "世界沒有因此變溫柔，但妳讓「腐敗」少了一個可借用的名字。妳想起芙莉蓮總用冷淡掩護清醒：真正的慈悲，有時是把錯誤從後代的路口移開。",
        ),
        aftermath_lose=(
            "咒式像鏽一樣爬上意識邊緣；妳勉強撐開視線，只看見庫瓦爾轉身離去的背影。《葬送的芙莉蓮》裡，他代表的並非單純的邪惡，而是「走得太久、太孤獨」的腐化——那讓人更難反駁，也更難不失手。",
            "敗北不是污點，是刻度。妳把此刻的深度記下：下次面對以智慧為名的侵蝕，妳要先問自己——妳想守的是人，還是守著某個不願結束的時代。",
            "妳捧水洗面，看指縫裡殘留的灰白咒痕像霉斑，忽然理解「腐敗」為何讓人著迷又恐懼。妳在筆記上劃清兩欄：可分享的知識與會把人拖進孤獨的執念。妳告訴自己，下次與賢者對坐，先守住界線，再談深淵。",
        ),
        treasure_deltas={"int_stat": 4, "fth_stat": 4, "pragmatic": 4},
        treasure_name_zh="腐界書籤",
        gallery_intro_zh=(
            "庫瓦爾背負「腐敗」之名的賢者，知識無界時災害比魔族更久；與之對坐先畫界線。"
            "慈悲有時是把錯誤從後代路口移開，而非把深淵當成榮耀。"
        ),
    ),
    EncounterEnemy(
        id="aura",
        tier="boss",
        name_zh="斬首的阿烏拉",
        name_en="Aura",
        difficulty=5,
        base_hp=122,
        base_atk=25,
        base_def=13,
        move_names=(
            "服從咒縛",
            "斬首宣告",
            "亡者行軍",
            "王座威嚇",
        ),
        ultimate_zh="絕對隷屬",
        aftermath_win=(
            "阿烏拉的金匣合上的聲音比任何勝利演說都安靜；《葬送的芙莉蓮》裡她把服從當王座，把斬首當儀式，卻在真正的「位階」前露出魔族最原始的驚恐。妳把傲慢留在匣外，把自己留給下一步——妳不是靠嘴贏她，是靠妳拒絕成為她故事裡的臣民。",
            "傳說會改寫妳的名字，或至少妳親手改寫了今夜。妳明白欣梅爾那一類人為何總把玩笑說得很輕：因為重話要留給能把魔王幹部逼到發抖的那一刻。",
        ),
        aftermath_lose=(
            "妳在最后一刻掙脫束縛的餘韻，像從深水抬頭；阿烏拉仍笑著，像在看延長賽。《葬送的芙莉蓮》裡她的殘酷帶著貴族的餘裕：她不急着殺妳，她更享受妳在跪下與站起之間搖晃。",
            "妳把喘息吞回去，因為妳知道她的尊重只給「還能威脅她的人」。這一敗不是結局，是她替妳蓋章：妳還不夠讓她把棋盤掀了。",
            "妳背靠樹幹數心跳，直到膝蓋不再發軟才把「服從」兩字拆開寫：哪些是她的術式、哪些是妳自己嚇自己。妳把尊嚴折成可攜帶的尺寸收進胸口——下次再站到她面前，妳要帶的不是憤怒的吼聲，而是能讓她收起笑容的籌碼。",
        ),
        treasure_deltas={"fth_stat": 4, "str_stat": 4, "int_stat": 4},
        treasure_name_zh="金匣餘燼",
        gallery_intro_zh=(
            "斬首的阿烏拉以金匣與服從寫階級，斬首如儀式；她享受人於跪起之間搖晃。"
            "服從最狠是讓你甘心跪；她的尊重只給還能威脅她的人。"
        ),
    ),
    EncounterEnemy(
        id="revolte",
        tier="boss",
        name_zh="神技的雷沃戴",
        name_en="Revolte",
        difficulty=5,
        base_hp=118,
        base_atk=23,
        base_def=15,
        move_names=(
            "神技演武",
            "考場規則",
            "魔力壓制",
            "術式拆解",
        ),
        ultimate_zh="一級裁決",
        aftermath_win=(
            "雷沃戴點頭的幅度小到幾乎不存在——對妳而言卻比任何獎章都重。《葬送的芙莉蓮》裡他以「神技」複寫對手的術式，像把考場變成鏡屋：妳以為在攻擊他，其實在面對妳自己被放大的破綻。妳贏的不是名號，是把戰鬥變成可複核的過程，讓他沒有空隙把勝負偷換成展示。",
            "鄧肯與他在斷崖上的那一戰會被後人說很久；而妳在自己的斷崖上，先學會了一件事：所謂一級，不是會更多花招，是更不容易被自己的熟練害死。",
        ),
        aftermath_lose=(
            "妳跪地，不是屈服，是承認差距；雷沃戴沒有嘲諷，只把失敗寫進下一題的題幹。《葬送的芙莉蓮》裡他最可怕的不是嘴，是他把「考試」當戰場的冷靜——妳輸了，他仍站在規則內。",
            "這一敗若讓妳更會讀題，便不算浪費。妳想起芙莉蓮看魔族的眼神：別急著生氣，先把對方的術式讀完——讀不完，就會變成下一個考生的教材。",
            "妳在沙地上一遍遍默寫剛才的交鋒順序，像把考卷抄成自己的錯題本。妳把「神技」標成警告色：那不是炫技，是逼妳承認熟練會養成盲點。妳站起身拍掉膝灰，決定下次進場先帶走題幹，再談勝負。",
        ),
        treasure_deltas={"int_stat": 4, "pragmatic": 4, "str_stat": 4},
        treasure_name_zh="裁卷蠟印",
        gallery_intro_zh=(
            "雷沃戴神技複寫術式，考場如鏡屋；你以為在攻他，其實在打自己被放大的破綻。"
            "一級不是更多花招，是更少被熟練害死；讀題比吼叫保命。"
        ),
    ),
    EncounterEnemy(
        id="macht",
        tier="boss",
        name_zh="黃金鄉的馬哈特",
        name_en="Macht",
        difficulty=5,
        base_hp=125,
        base_atk=23,
        base_def=16,
        move_names=(
            "萬物成金",
            "黃金咒式",
            "鄉愁領域",
            "靜默赦免",
        ),
        ultimate_zh="萬象黃昏",
        aftermath_win=(
            "馬哈特的金光像退潮離開視野。《葬送的芙莉蓮》裡他是魔王麾下「七崩賢」的最強者，魔力低於芙莉蓮卻仍能擊敗她的四名魔族之一；拿手的萬物成金魔法能把生物也化為黃金，幾乎不可逆，芙莉蓮稱為「最強的詛咒」，他也因此得名「黃金鄉的馬哈特」。他高傲、不喜爭鬥、服從心弱，對魔王與修拉哈特也不甚上心，卻在無衝突時仍願與人交談，並為理解人類的惡意、罪惡感而研究，試圖與人類達成共存。與奇蹟之格拉奧薩姆相性極差，認為那才是最難對付的對手。妳聽見自己的呼吸像貨幣一樣珍貴——妳剛從一場會把人變成紀念品的術式裡，換到繼續流逝的權利。",
            "黃金鄉仍遠，但妳證明有些門能用意志敲出聲音。妳想起鄧肯門下與維貝爾他們付過的代價：對抗馬哈特從來不只是魔力對撞，而是妳還願不願意相信「人之所以為人」的軟弱與牽絆。",
        ),
        aftermath_lose=(
            "妳在光裡迷失一瞬，醒來世界仍舊，胸口卻多了一塊說不清的空。萬物成金的餘韻不會大聲嘲笑妳，它只會安靜地問：妳要不要把記憶也換成不會碎的黃金。《葬送的芙莉蓮》裡，這種溫柔比刀更致命——而馬哈特本就不熱衷爭鬥，他的殘酷常帶著研究與旁觀的冷。",
            "他不追；他讓妳帶著敗北離開，像帶走一段未完成的旋律。妳咬緊牙把顫抖藏好——妳知道下次再站到他面前，妳要帶的不是勇氣的口號，而是更完整的自己。",
            "妳摸著胸口那塊空，像在確認哪些回憶還溫熱、哪些已被金光擦邊而變薄。妳把「鄉愁」與「詛咒」寫在同一頁兩端，中間留一行給自己：不換黃金，換路。妳沿著夕照走回營地，腳步很慢，卻每一步都踩回人類會痛、會牽掛的那種重量。",
        ),
        treasure_deltas={"fth_stat": 4, "int_stat": 4, "pragmatic": 4},
        treasure_name_zh="鄉愁冷灰",
        gallery_intro_zh=(
            "馬哈特：萬物成金幾乎不可逆，芙莉蓮稱最惡詛咒，世稱黃金鄉；七崩賢最強，生物亦可化金。"
            "魔力不及她仍能重創她；研究惡意與罪疚，試與人類共存。"
        ),
    ),
    EncounterEnemy(
        id="throne_bazart",
        tier="boss",
        name_zh="王座的巴札爾特",
        name_en="Bazart",
        difficulty=5,
        base_hp=121,
        base_atk=24,
        base_def=15,
        move_names=(
            "魔王敕令",
            "御座鎮壓",
            "村落徵伐",
            "冕裂斬",
        ),
        ultimate_zh="王座終幕",
        aftermath_win=(
            "巴札爾特是《葬送的芙莉蓮》中魔王軍的將軍，綽號「王座的巴札爾特」——曾奉魔王之命前去摧毀精靈的村落，傳說最後喪於年幼的芙莉蓮之手。今夜妳面對的不是史書裡的結局，而是同一種「王座」壓在肩上的重量：他把敕令與階級寫進咒式，讓人還沒拔術式就先矮半寸；妳偏把背脊挺直，像拒絕把任何聚落寫成可抹去的座標。",
            "餘燼裡王座的殘響散去。妳想起傳說裡那一戰：精靈的村落沒有被魔王軍的將軍定義成終點。妳把勝利收進胸口——不是奪位，是確認自己仍站得住、仍選擇守哪一側的邊境。",
        ),
        aftermath_lose=(
            "威壓像石階一級級壓上肩頭；魔王軍將軍的氣息裡帶著「摧毀精靈村落」的敕令，冷得像邊界線被畫成刀口。《葬送的芙莉蓮》裡魔族擅長把語言變成武器，而王座型的傲慢最可怕——它讓妳以為順從比反抗更省事。",
            "妳沒有死，但自尊被劃了一道口子。妳舔掉唇邊的血味，告訴自己：下一回先拆他的敕令與座標，再談拆他的術式。",
            "回程妳刻意走直線，像在練習不被任何視線折彎。妳在筆記寫下「村落」兩字，旁邊畫一道線：不是地圖上的點，是還沒被魔王軍寫完的故事。妳知道巴札爾特留給妳的不是羞辱，是一張還沒填完的試卷。",
        ),
        treasure_deltas={"str_stat": 4, "fth_stat": 4, "social": 4},
        treasure_name_zh="王座殘冕",
        gallery_intro_zh=(
            "魔王軍將軍「王座的巴札爾特」曾圖摧精靈村落，傳說敗於年幼芙莉蓮；王座是敕令與階級的壓力。"
            "別先在心底矮半寸；要守的是身後聚落與仍站得直的脊樑。"
        ),
    ),
)

ENCOUNTER_BY_ID: Final[dict[str, EncounterEnemy]] = {
    e.id: e for e in (_MONSTERS + _ELITES + _BOSSES)
}

ALL_ENCOUNTER_IDS: Final[tuple[str, ...]] = tuple(ENCOUNTER_BY_ID.keys())

ENCOUNTER_GALLERY_ORDER: Final[tuple[str, ...]] = ALL_ENCOUNTER_IDS


def pick_random_encounter(age_years: int, rng: random.Random) -> EncounterEnemy | None:
    """
    依滿歲自對應池隨機抽一隻敵人。

    Args:
        age_years: 6、11 或 16。
        rng: 亂數來源。

    Returns:
        敵人；若年齡不屬遭遇戰則 None。
    """
    if age_years == 6:
        pool = _MONSTERS
    elif age_years == 11:
        pool = _ELITES
    elif age_years == 16:
        pool = _BOSSES
    else:
        return None
    return rng.choice(pool)


def is_valid_encounter_id(enemy_id: str) -> bool:
    """
    若 ``enemy_id``（含舊別名）可對應至已知遭遇敵則為 True。

    Args:
        enemy_id: 畫廊或存檔鍵。

    Returns:
        是否為合法鍵或合法別名。
    """
    return resolve_encounter_id(enemy_id) in ENCOUNTER_BY_ID


def get_enemy_by_id(enemy_id: str) -> EncounterEnemy | None:
    """
    由 id 取得敵人定義（舊別名會解析為現行 id）。

    Args:
        enemy_id: ``EncounterEnemy.id`` 或舊別名。

    Returns:
        敵人；未知鍵則 None。
    """
    return ENCOUNTER_BY_ID.get(resolve_encounter_id(enemy_id))


def encounter_protagonist_pronoun_adjust_zh(text: str, protagonist_gender: str) -> str:
    """
    將遭遇戰餘韻等以女性「妳」撰寫的敘事，依主角性別換成男性「你」系用字。

    Args:
        text: 原文。
        protagonist_gender: ``male`` 或 ``female``（與 ``GameState.protagonist_gender`` 同）。

    Returns:
        男性路線時將「妳」替換為「你」；其餘回傳原文。
    """
    if not text or protagonist_gender != "male":
        return text
    return text.replace("妳", "你")


def encounter_aftermath_two_paragraphs(parts: tuple[str, ...]) -> tuple[str, str]:
    """
    將餘韻元組正規化為**恰好兩段**正文，供單頁餘韻顯示。

    超過兩段時，自第二段起全部串成第二段；僅一段時第二段為空字串。

    Args:
        parts: 資料表定義之餘韻段落序列。

    Returns:
        ``(第一段, 第二段)``。
    """
    cleaned = tuple(
        p.strip() for p in parts if isinstance(p, str) and p.strip()
    )
    if not cleaned:
        return ("", "")
    if len(cleaned) == 1:
        return (cleaned[0], "")
    if len(cleaned) == 2:
        return (cleaned[0], cleaned[1])
    return (cleaned[0], "".join(cleaned[1:]))


def format_encounter_deltas_brief(deltas: dict[str, int]) -> str:
    """
    將遭遇戰數值增量化為簡短中文（與突發事件提示同調）。

    Args:
        deltas: 僅含可見五維鍵之增量。

    Returns:
        例如「智力+2  力量+2」。
    """
    from training_actions import STAT_LABEL_ZH

    bits = [
        f"{STAT_LABEL_ZH.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in sorted(deltas.items())
        if v != 0 and k in _P
    ]
    return "  ".join(bits) if bits else "（無變化）"


def encounter_preamble_body_zh(heroine_name: str, enemy: EncounterEnemy) -> str:
    """
    遭遇戰主畫面開場敘述（無選項，僅說明戰況）。

    Args:
        heroine_name: 主角姓名。
        enemy: 當前敵人。

    Returns:
        多行敘述字串。
    """
    who = (heroine_name or "孩子").strip() or "孩子"
    return (
        f"{who}在路途上遭遇「{enemy.name_zh}」。\n"
        "咒文與意志將在接下來的交鋒中受試煉——請觀戰至結束。"
    )
