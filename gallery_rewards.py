"""
組合獎勵 CG：畫廊「獎勵圖片」會列出 ``assets/cg/rewards/`` 內所有合法圖檔；**未達成檔名所列全部結局**時仍顯示外框與角色名，**不顯示 CG 縮圖**；全部達成後縮圖與全螢幕才解鎖。

檔名規則（放在專用資料夾 ``assets/cg/rewards/``）::

    ``{結局key1}[_{結局key2}[_{結局key3}[_{結局key4}]]].{jpg|jpeg|png|webp}``

- 可為**單一**結局 slug（如 ``frieren``），或以半形底線 ``_`` 串接多個 slug（與一般檔名慣例一致）。
- 單一 slug 本身也可能含底線（如 ``hero_south``），故**不是**單純用 ``split("_")`` 切分；程式會對照 ``GALLERY_ENDING_KEYS`` 做由左而右的合法切分（優先比對較長的 key）。
- 同一組合不論檔名中 key 順序為何，皆正規化為同一組（內部以排序後的 key 用 ``+`` 連接作為識別）；**同一組可有多張圖**，檔名可在 key 段之後加 ``_`` + 純數字區分（例：``stark_fern_1``、``stark_fern_2``），解鎖條件仍相同，畫廊會各佔一格。
- 同一檔內 key **不可重複**；支援 **1～4** 個不同結局；磁碟無圖檔則畫廊該分類為空。
- 主檔名與 slug 比對時**不分大小寫**（``casefold``），例如 ``Frieren_Flamme`` 等同 ``frieren_flamme``。
- 畫廊列表排序：所需結局**人數愈少愈前面**（同人數則依內部 token 字串排序）。
- 格內／全螢幕標題之中文名順序：預設依**檔名主檔名由左而右**解析出之 key 順序（與英文檔名一致）；若無對照則退回敘事慣用排序。
- **館藏註解（副標）**：寫在模組內 ``_REWARD_CAPTION_BY_REL_PATH``（鍵為與 ``reward_cg_tables`` 相同之相對路徑，如 ``assets/cg/rewards/frieren_1.jpg``）。全螢幕底欄經 ``reward_gallery_footer_source_zh`` 併成**單段連續**敘述（**不**列角色名；**勿**多句標語分段）。請寫成**一行內**可讀完、結尾自然收束之短文；字量盡量寫滿但**不超過一行可見**（由 main 裁切）。未列鍵則以 ``reward_gallery_scene_fallback_zh``。**同一組合多張圖**請以不同檔名各列一筆，內容可互不相同。
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from ending_gallery import GALLERY_ENDING_KEYS
from endings import ENDINGS

# 內部識別用（畫廊／JSON）；避免以 ``_`` 再切分顯示名時與 ``hero_south`` 衝突。
_INTERNAL_TOKEN_SEP = "+"
_REWARD_MIN_KEYS = 1
_REWARD_MAX_KEYS = 4
# 主檔名尾端 ``_`` + 純數字（如 ``_1``、``_12``）視為同組多圖變體序號，解析 key 時先剝除。
_REWARD_FILENAME_TRAILING_VARIANT_RE = re.compile(r"^(.+)_(\d+)$")
_REWARD_CG_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
# 與一般結局 CG（``assets/cg/`` 根目錄）分開存放。
_REWARD_CG_DIR_PARTS: tuple[str, ...] = ("assets", "cg", "rewards")

# 全螢幕館藏註解：鍵須與掃描產生之 ``rel`` 完全一致（``/`` 分隔）。新增獎勵圖時請在此增列。
_REWARD_CAPTION_BY_REL_PATH: dict[str, str] = {
    "assets/cg/rewards/denken.jpg": (
        "鄧肯：一級魔法使，條文與墓碑同重；雪地覆核代價，慢一步是讓人聽懂輸在哪。"
    ),
    "assets/cg/rewards/eisen.jpg": (
        "艾澤：遠征矮人戰士，巨斧與沉默同重；曾逃故鄉仍站最前，收留修塔爾克像收留年少自己。"
    ),
    "assets/cg/rewards/eisen_himmel_heiter.jpg": (
        "欣梅爾、海塔與艾澤營火夜：酒氣笑聲先於別離，為明天上路預支溫度。"
    ),
    "assets/cg/rewards/fern.jpg": (
        "費倫：海塔收養、芙莉蓮弟子；禮貌與魔杖守日常，底線比咒語直。"
    ),
    "assets/cg/rewards/fern_stark.jpg": (
        "費倫與修塔爾克吵鬧結伴，膽小與逞強互補；開戰背影對齊，伸手確認彼此還在。"
    ),
    "assets/cg/rewards/himmel.jpg": (
        "欣梅爾：帥氣自戀仍真心行善，把戒指與花語留給長壽精靈，當遲到告白。"
    ),
    "assets/cg/rewards/flamme_frieren.jpg": (
        "弗蘭梅與芙莉蓮同框：短命大魔法使把火種交給長壽弟子，也是時間差本身。"
    ),
    "assets/cg/rewards/frieren_1.jpg": (
        "芙莉蓮：葬送魔王的精靈，因欣梅爾遺物再上路；魔杖與箱子補上思念。"
    ),
    "assets/cg/rewards/frieren_2.jpg": (
        "獨旅精靈：咒文輕、腳步把千年折成可走的距離；想念壓在指尖短詠裡。"
    ),
    "assets/cg/rewards/frieren_3.jpg": (
        "遠景天光拉開距離，承認溫度不耽擱；想念折進短咒文，指尖仍向前。"
    ),
    "assets/cg/rewards/frieren_4.jpg": (
        "同一路換季節，光改袖口仍向前；腳印比遠景清楚，精靈還在走。"
    ),
    "assets/cg/rewards/frieren_heiter_fern.jpg": (
        "芙莉蓮、海塔與費倫：酒經文魔杖像一戶怪家，各自護彼此的擔心。"
    ),
    "assets/cg/rewards/frieren_himmel_1.jpg": (
        "雪中欣梅爾與芙莉蓮並肩：話說不出口交給影子貼近，勇者最笨的告白。"
    ),
    "assets/cg/rewards/frieren_himmel_2.jpg": (
        "冬景勇者與精靈：雪落肩像遲來護咒，溫度來不及講完仍留下。"
    ),
    "assets/cg/rewards/frieren_heiter_himmel_eisen.jpg": (
        "遠征四人營火：笑聲酒氣斧背敲地；精靈把餘溫收進千年記憶慢慢翻。"
    ),
    "assets/cg/rewards/frieren_himmel_heiter_eisen.jpg": (
        "門邊四背影：隊伍守的是彼此別再受傷，史詩外仍是怕冷的一隊人。"
    ),
    "assets/cg/rewards/heiter_frieren_himmel_eisen.jpg": (
        "酒經沉默逞強同一格；篝火邊誓願常是明天還一起醒來。"
    ),
    "assets/cg/rewards/hero_south.jpg": (
        "南方勇者線紀念構圖；遠征與牽掛折進同一格，邊緣光像回憶調到剛好看清。"
    ),
    "assets/cg/rewards/laufen_denken.jpg": (
        "拉歐芬快腿撞鄧肯條文眼；撤退與審判都不准拿命換面子。"
    ),
    "assets/cg/rewards/lavine_kanne_frieren.jpg": (
        "拉比涅、康涅與芙莉蓮：冰水同窗考場鬧劇，嬌小膽小互補成膽量。"
    ),
    "assets/cg/rewards/methode_frieren_fern.jpg": (
        "梅特黛與芙莉蓮、費倫：擁抱與紀律同畫，溫柔嚴格並存。"
    ),
    "assets/cg/rewards/methode_serie_genau.jpg": (
        "葛納烏、賽莉耶與梅特黛同框：一級考試背後千年規則與活人執行。"
    ),
    "assets/cg/rewards/sein.jpg": (
        "贊恩：女神官與廢材僧侶雙面，尋大猩猩戰士舊友；女神魔法極高仍狼狽站起陪伴。"
    ),
    "assets/cg/rewards/stark_fern.jpg": (
        "修塔爾克與費倫鬥嘴仍並肩；危險來先伸手，吵鬧後養出信任。"
    ),
    "assets/cg/rewards/stark_frieren_fern.jpg": (
        "芙莉蓮走最前，費倫與修塔爾克補滿兩側；這趟旅途最接近家的隊形。"
    ),
}


def _reward_caption_for_rel(rel: str) -> str | None:
    """
    依相對路徑查詢內建館藏註解（見 ``_REWARD_CAPTION_BY_REL_PATH``）。

    Args:
        rel: 與 ``reward_cg_tables`` 產生之路徑字串相同（``/`` 分隔）。

    Returns:
        非空白字串或 None。
    """
    raw = _REWARD_CAPTION_BY_REL_PATH.get(rel)
    if raw is None:
        return None
    text = raw.strip()
    return text if text else None


# 副標敘事中名字先後：數字愈小愈靠前（其餘 key 預設 200，再以 slug 排序）。
_REWARD_NARR_NAME_ORDER: dict[str, int] = {
    "himmel": 10,
    "frieren": 20,
    "eisen": 30,
    "heiter": 40,
    "stark": 50,
    "fern": 60,
    "flamme": 70,
    "serie": 80,
    "ubel": 90,
    "sense": 100,
    "laufen": 110,
    "kanne": 120,
    "lavine": 130,
    "ehre": 140,
    "methode": 150,
    "sein": 160,
    "denken": 170,
    "land": 180,
    "genau": 190,
    "wirbel": 200,
    "kraft": 210,
    "hero_south": 220,
}

def _reward_keys_sorted_narr(parts: list[str]) -> list[str]:
    """
    依敘事慣用順序排列結局 key（再轉中文名）。

    Args:
        parts: token 拆出之 slug 列表。

    Returns:
        排序後之 key 列表。
    """
    return sorted(
        parts,
        key=lambda k: (_REWARD_NARR_NAME_ORDER.get(k, 200), k),
    )


def _key_order_for_display(
    parts: list[str],
    filename_key_order: tuple[str, ...] | None,
) -> list[str]:
    """
    決定 key 的顯示／敘述順序：優先採檔名由左而右，否則採敘事慣用排序。

    Args:
        parts: token 拆出之 slug 列表（不含空字串）。
        filename_key_order: 掃描檔案時記錄之順序；須與 ``parts`` 集合完全一致。

    Returns:
        供轉中文名或套入泛用副標之 key 列表。
    """
    parts_set = frozenset(parts)
    if (
        filename_key_order
        and frozenset(filename_key_order) == parts_set
        and len(filename_key_order) == len(parts_set)
    ):
        return list(filename_key_order)
    return _reward_keys_sorted_narr(parts)


def sorted_reward_tokens_for_display(tokens: Iterable[str]) -> tuple[str, ...]:
    """
    獎勵組合在畫廊中的排序：**需要解鎖的人數愈少愈前面**；同人數則依 token 字串排序。

    Args:
        tokens: 規範 token 集合。

    Returns:
        排序後元組。
    """
    toks = list(tokens)

    def _key_count(t: str) -> int:
        return len(t.split(_INTERNAL_TOKEN_SEP)) if t else 0

    return tuple(sorted(toks, key=lambda t: (_key_count(t), t)))


def reward_gallery_scene_fallback_zh(
    token: str,
    *,
    filename_key_order: tuple[str, ...] | None = None,
) -> str:
    """
    無館藏註解時，獎勵全螢幕底欄場景描述（**不**列角色名；單段連續，可見至多一行由 main 裁切）。

    Args:
        token: 內部規範 token（``+`` 分隔排序後 slug）。
        filename_key_order: 保留簽名與未來依組合客製文案用。

    Returns:
        單段連續敘述（字量盡量寫滿但不超過一行可見）。
    """
    _ = filename_key_order
    _ = token
    return "多結局交會方解鎖的紀念構圖；長旅與回憶疊成一格靜照。"


def _reward_footer_blob_continuous_zh(text: str) -> str:
    """
    獎勵底欄敘述併成單行連續正文（移除換行與多餘空白，不分段）。

    Args:
        text: 原始文案。

    Returns:
        無換行字串。
    """
    s = (text or "").strip()
    if not s:
        return s
    return "".join(s.split())


def reward_gallery_footer_source_zh(
    rel: str,
    reward_note_zh: str | None,
    token: str,
    *,
    filename_key_order: tuple[str, ...] | None = None,
) -> str:
    """
    獎勵全螢幕底欄用**單段連續**敘述（不列角色名；不以「。」拆句合併或加刪節號硬截；字量盡量寫滿但**不超過一行可見**）。

    優先順序：呼叫端傳入之 ``reward_note_zh`` → ``_REWARD_CAPTION_BY_REL_PATH``（依 ``rel``）
    → ``reward_gallery_scene_fallback_zh``。經 ``_reward_footer_blob_continuous_zh`` 併成單行連續正文後回傳，
    版面裁切交 ``main._gallery_trim_footer_desc_to_one_visible_line``（必要時自尾端縮短，不出現「…」於原文）。

    Args:
        rel: 圖檔相對路徑（``/`` 分隔）。
        reward_note_zh: 畫廊格帶入之註解，可為 None。
        token: 內部規範 token。
        filename_key_order: 與檔名一致之 key 序（保留簽名；底欄敘述**不**顯示姓名）。

    Returns:
        單段中文。
    """
    _ = filename_key_order
    rel_n = rel.replace("\\", "/")
    if reward_note_zh and reward_note_zh.strip():
        raw = reward_note_zh.strip()
    else:
        cap = _reward_caption_for_rel(rel_n)
        if cap:
            raw = cap
        else:
            raw = reward_gallery_scene_fallback_zh(
                token, filename_key_order=filename_key_order
            )
    return _reward_footer_blob_continuous_zh(raw)


def reward_combo_flavor_zh(
    token: str,
    *,
    filename_key_order: tuple[str, ...] | None = None,
) -> str:
    """
    全螢幕獎勵 CG 底部第二段：僅在 ``_REWARD_CAPTION_BY_REL_PATH`` **未**列該圖路徑時使用之短句。

    不述解鎖條件，僅以全形間隔號連接角色名（與標題區分）；無法解析名稱時回傳空白字串。

    Args:
        token: 內部規範 token（``+`` 分隔排序後 slug）。
        filename_key_order: 有則人名順序與檔名由左而右一致。

    Returns:
        說明文字；可為空白。
    """
    parts = [p for p in token.split(_INTERNAL_TOKEN_SEP) if p]
    if not parts:
        return ""
    keys_ord = _key_order_for_display(parts, filename_key_order)
    names = [ENDINGS[k].name for k in keys_ord if k in ENDINGS]
    if not names:
        return ""
    return "・".join(names)


def _segment_filename_stem_to_keys(stem: str) -> list[str] | None:
    """
    將主檔名（不含副檔名）解析為結局 key 列表；底線為分隔，但需符合合法 key 詞典。

    採深度優先：每步由目前位置起，嘗試所有以該處開頭的合法 key（**長度由長到短**），避免
    ``hero`` 誤先於 ``hero_south`` 被吃掉。

    Args:
        stem: 檔案主檔名，例如 ``frieren_flamme`` 或 ``hero_south_frieren``（大小寫不拘）。

    Returns:
        成功且段數介於 ``_REWARD_MIN_KEYS``～``_REWARD_MAX_KEYS``、且各段相異時為 key 列表；
        否則 None。
    """
    valid = frozenset(GALLERY_ENDING_KEYS)
    s = stem.casefold()
    n = len(s)
    found: list[str] | None = None

    def dfs(i: int, acc: list[str]) -> None:
        nonlocal found
        if found is not None:
            return
        if i == n:
            if _REWARD_MIN_KEYS <= len(acc) <= _REWARD_MAX_KEYS and len(set(acc)) == len(acc):
                found = acc.copy()
            return
        if s[i] == "_":
            return
        candidates = [k for k in valid if s.startswith(k, i)]
        candidates.sort(key=len, reverse=True)
        for k in candidates:
            j = i + len(k)
            if j == n:
                dfs(j, acc + [k])
            elif j < n and s[j] == "_":
                dfs(j + 1, acc + [k])
            if found is not None:
                return

    dfs(0, [])
    return found


def _reward_stem_without_trailing_variant_index(stem: str) -> str:
    """
    若主檔名（不含副檔名）尾端為半形底線接純數字，則回傳去掉該尾綴之 stem；否則原樣。

    用於同一角色組合有多張獎勵圖時，以 ``..._1``、``..._2`` 等區分檔名，解析結局 key 時不將數字當 slug。

    Args:
        stem: 檔案主檔名。

    Returns:
        去掉尾綴後之 stem，或原 stem。
    """
    cf = stem.casefold()
    m = _REWARD_FILENAME_TRAILING_VARIANT_RE.fullmatch(cf)
    if m is None:
        return stem
    suffix = "_" + m.group(2)
    if not cf.endswith(suffix):
        return stem
    return stem[: -len(suffix)]


def _segment_reward_filename_stem(stem: str) -> list[str] | None:
    """
    解析獎勵圖主檔名為結局 key 列表；支援尾端 ``_`` + 數字變體序號。

    Args:
        stem: 檔案主檔名。

    Returns:
        成功時為 key 列表；無法解析時為 None。
    """
    keys = _segment_filename_stem_to_keys(stem)
    if keys is not None:
        return keys
    base = _reward_stem_without_trailing_variant_index(stem)
    if base == stem:
        return None
    return _segment_filename_stem_to_keys(base)


def _canonical_token_from_keys(keys: list[str]) -> str:
    """
    將 key 列表轉成內部規範 token（排序後以 ``+`` 連接）。

    Args:
        keys: 結局 slug 列表。

    Returns:
        規範字串。
    """
    return _INTERNAL_TOKEN_SEP.join(sorted(keys))


def reward_cg_tables(
    asset_root: Path,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[tuple[str, ...]]],
    dict[str, list[str | None]],
]:
    """
    掃描 ``assets/cg/rewards/`` 下圖檔；主檔名可解析為 1～4 個合法結局 key 者視為獎勵圖。

    Args:
        asset_root: 內建資源根（與 ``main`` 之 ``_GAME_ASSET_ROOT`` 相同）。

    Returns:
        - ``rels_by_token``：規範 token → 相對路徑列表（同組多檔依路徑字串排序）。
        - ``filename_key_orders_by_token``：與上路徑列表**對齊**之「檔名由左而右」key 序列表
          （供中文顯示；變體序號 ``_1`` 等不影響此序）。
        - ``captions_by_token``：與上路徑對齊；來自 ``_REWARD_CAPTION_BY_REL_PATH``，未列鍵則 None。
    """
    cg_dir = asset_root.joinpath(*_REWARD_CG_DIR_PARTS)
    if not cg_dir.is_dir():
        return {}, {}, {}
    rel_prefix = Path(*_REWARD_CG_DIR_PARTS)
    buckets: dict[str, list[tuple[str, tuple[str, ...], str | None]]] = defaultdict(
        list
    )
    for ext in _REWARD_CG_EXTENSIONS:
        for p in sorted(cg_dir.glob(f"*{ext}")):
            if not p.is_file() or p.name.startswith("."):
                continue
            keys = _segment_reward_filename_stem(p.stem)
            if keys is None:
                continue
            token = _canonical_token_from_keys(keys)
            rel = str(rel_prefix / p.name).replace("\\", "/")
            cap = _reward_caption_for_rel(rel)
            buckets[token].append((rel, tuple(keys), cap))
    rels_by_token: dict[str, list[str]] = {}
    orders_by_token: dict[str, list[tuple[str, ...]]] = {}
    caps_by_token: dict[str, list[str | None]] = {}
    for token in sorted(buckets.keys()):
        items = sorted(buckets[token], key=lambda x: x[0])
        rels_by_token[token] = [x[0] for x in items]
        orders_by_token[token] = [x[1] for x in items]
        caps_by_token[token] = [x[2] for x in items]
    return rels_by_token, orders_by_token, caps_by_token


def reward_cg_rel_paths(asset_root: Path) -> dict[str, str]:
    """
    掃描獎勵圖目錄；同組多檔時取**排序後第一筆**路徑（供只需單一路徑之呼叫端）。

    Args:
        asset_root: 內建資源根。

    Returns:
        規範 token → 相對路徑。
    """
    rels, _, _ = reward_cg_tables(asset_root)
    return {t: paths[0] for t, paths in rels.items() if paths}


def eligible_reward_tokens(ending_unlocked: set[str], asset_root: Path) -> set[str]:
    """
    依目前通關解鎖集合，回傳**應顯示**的獎勵組合 token（檔案存在且所需結局皆已解鎖）。

    Args:
        ending_unlocked: 已解鎖之結局 key 集合。
        asset_root: 內建資源根。

    Returns:
        規範 token 集合。
    """
    rels, _, _ = reward_cg_tables(asset_root)
    ok: set[str] = set()
    for token, paths in rels.items():
        if not paths:
            continue
        parts = token.split(_INTERNAL_TOKEN_SEP)
        if all(pk in ending_unlocked for pk in parts):
            ok.add(token)
    return ok


def all_reward_gallery_slots(
    ending_unlocked: set[str],
    asset_root: Path,
) -> list[tuple[str, str, tuple[str, ...], str | None, bool]]:
    """
    回傳畫廊「獎勵圖片」網格每一格：含磁碟上所有合法獎勵圖（同組多檔各一筆）。

    Args:
        ending_unlocked: 已解鎖之結局 key 集合。
        asset_root: 內建資源根。

    Returns:
        每項為 ``(規範 token, 相對路徑, 檔名由左而右 key 序, 館藏註解或 None, cg_revealed)``。
        ``cg_revealed`` 為 True 表示檔名所列結局**皆**已解鎖，應顯示縮圖並允許全螢幕。
        未排序，請再交 ``sorted_reward_gallery_slots_for_display`` 排序。
    """
    rels, orders, caps = reward_cg_tables(asset_root)
    out: list[tuple[str, str, tuple[str, ...], str | None, bool]] = []
    for token, paths in rels.items():
        if not paths:
            continue
        parts = token.split(_INTERNAL_TOKEN_SEP)
        cg_revealed = all(pk in ending_unlocked for pk in parts)
        ords = orders[token]
        cps = caps[token]
        if len(paths) != len(ords) or len(paths) != len(cps):
            continue
        for rel, ko, cap in zip(paths, ords, cps):
            out.append((token, rel, ko, cap, cg_revealed))
    return out


def sorted_reward_gallery_slots_for_display(
    slots: Iterable[tuple[str, str, tuple[str, ...], str | None, bool]],
) -> tuple[tuple[str, str, tuple[str, ...], str | None, bool], ...]:
    """
    獎勵畫廊格排序：所需結局人數愈少愈前；同人數則依規範 token、再依路徑字串。

    Args:
        slots: ``all_reward_gallery_slots`` 等產生之 slot 集合。

    Returns:
        排序後之不可變序。
    """

    def _sort_key(
        item: tuple[str, str, tuple[str, ...], str | None, bool],
    ) -> tuple[int, str, str]:
        tok, rel, _, _, _ = item
        n = len(tok.split(_INTERNAL_TOKEN_SEP)) if tok else 0
        return (n, tok, rel)

    return tuple(sorted(slots, key=_sort_key))


def reward_token_label_zh(
    token: str,
    *,
    filename_key_order: tuple[str, ...] | None = None,
) -> str:
    """
    將獎勵 token 轉成畫廊格內顯示之中文稱呼（以全形間隔號連接）。

    Args:
        token: 規範 token（如 ``flamme+frieren``，內部 ``+`` 分隔）。
        filename_key_order: 若為掃描該檔時存下之「檔名由左而右」key 序，則中文名依此排列；
            若缺省或與 token 所含 key 集合不一致，則退回 ``_reward_keys_sorted_narr``。

    Returns:
        顯示字串。
    """
    parts = [p for p in token.split(_INTERNAL_TOKEN_SEP) if p]
    order_keys = _key_order_for_display(parts, filename_key_order)
    names: list[str] = []
    for p in order_keys:
        meta = ENDINGS.get(p)
        names.append(meta.name if meta is not None else p)
    return "・".join(names)
