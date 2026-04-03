"""
奇遇事件：與《葬送的芙莉蓮》向 NPC 偶遇並作答，答對獎勵較高、答錯仍有小幅成長。

排程於新局建立時寫入 ``GameState``；**全劇固定三次**——幼年／少年／青年期各一次；
僅在該曆年內的 **3 月／6 月／9 月**（完成該季後之月相，**不含 0 月**／滿歲當月）觸發。

夥伴 CG（``assets/cg/companions/``）檔名慣例：

- **主圖**（畫廊縮圖／全螢幕／奇遇人物子畫廊）：``{slug}.jpg`` 等，``slug`` 與 ``WhimEncounter.cg_basename`` 一致。
- **奇遇流程左側小圖**（可選）：``{slug}_friend.jpg`` 等；若存在則奇遇頁優先使用，否則回退主圖。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final

from game_state import START_AGE_MONTHS, TOTAL_TRAINING_QUARTERS, GameState
from whim_questions import WHIM_QUESTIONS, whim_question_by_index


@dataclass(frozen=True)
class WhimEncounter:
    """
    單一奇遇 NPC 與其專屬文案（題目由排程時指定題號）。

    Attributes:
        key: 畫廊／存檔用鍵（英文 slug）。
        display_name: 介面顯示名稱。
        epithet: 稱號一行。
        location_zh: 導引頁第二行「地點　…」之地點名（不含前綴）。
        preamble_para1: 導引第一段（與第二段合計，換行後須能落在 **9～11 行**）。
        preamble_para2: 導引第二段（兩段合計 **9～11** 行；顯示時超出截斷、不足補空行）。
        chat: 測驗前 NPC 閒聊（敘事用，可與開場呼應；非導引正文）。
        quiz_opening_zh: 測驗題幹前開場敘述（單段；顯示時固定 **4** 行，不足補空行）。
        aftermath_correct_para1: 答對餘韻第一段（承接「你答對了。」之後）。
        aftermath_correct_para2: 答對餘韻第二段（點綴收束）。
        aftermath_wrong_para1: 答錯餘韻第一段（承接「你答錯了。」之後）。
        aftermath_wrong_para2: 答錯餘韻第二段（點綴收束）。
        deltas_correct: 答對五維增量。
        deltas_wrong: 答錯五維增量。
        cg_basename: 主圖檔名主鍵（``assets/cg/companions/{basename}.jpg``）；奇遇左欄可另備 ``{basename}_friend.*``。
        gallery_footer_zh: 畫廊全螢幕底欄專用短敘（單段連續、勿依賴長文＋程式硬切）。請寫成一則語意自足、讀完能收束的短文（約兩行版面），勿堆「逗號串聯未完句」指望換行補完。
    """

    key: str
    display_name: str
    epithet: str
    location_zh: str
    preamble_para1: str
    preamble_para2: str
    chat: str
    quiz_opening_zh: str
    aftermath_correct_para1: str
    aftermath_correct_para2: str
    aftermath_wrong_para1: str
    aftermath_wrong_para2: str
    deltas_correct: dict[str, int]
    deltas_wrong: dict[str, int]
    cg_basename: str
    gallery_footer_zh: str


_WHIM_ENCOUNTER_DEFS: tuple[WhimEncounter, ...] = (
    WhimEncounter(
        key="stoltz",
        display_name="修特爾茲",
        epithet="劍之村的前衛／修塔爾克之兄",
        location_zh="邊境小徑",
        preamble_para1=(
            "你在商路歇腳處遇見揹巨斧的青年戰士——修塔爾克口中那位兄長；木棚乾草與鐵鏽味混著，車塵未落，柱上旅人刻痕有新有舊。"
            "風裡話題輕鬆，他卻把每句話說得像在試刀。他願分你乾糧與水，聊旅途見聞，語氣像請你烤火。"
        ),
        preamble_para2=(
            "他背夕照斧泛冷線，披風潔如未沾泥；村人傳他戰魔亦能滴血不沾，他只笑稱運氣好。"
            "戰士村慣以巨漢堡排犒拚命歸來者，疲憊與榮譽同煎一盤；他正要回村，願分乾糧與水聊幾句路，語氣像在請你烤火。"
        ),
        chat=(
            "「我弟……嗯，別看他現在這樣，小時候可倔了。」他撓頭，「我還說他會變很強。你也看勇者傳說？答對借訓練筆記參考。」"
        ),
        quiz_opening_zh=(
            "剛才聊的傳說，我想再聽聽你的看法。風裡有乾草味，像烤火一樣好聊。"
            "不用背，想到什麼答什麼；答錯也不少你一口水。"
            "我想確認你對故事的印象，是否與腳步一樣踏實。若你願意，就當作路上閒聊。"
        ),
        aftermath_correct_para1=(
            "他把筆記塞進你手裡紙邊磨毛墨仍清。「強不是拿來欺負人的。」他揮手沒入塵；頁角粗線小人與劍旁「別逞強」。哥悄藏愛。"
        ),
        aftermath_correct_para2=(
            "風轉冷，遠村狗吠一聲又靜，只剩腳步與心跳；你把筆記貼胸收好，像多帶一塊會說話的護符上路，遠方車鈴細響如問候夜色。"
        ),
        aftermath_wrong_para1=(
            "他愣了隨即大笑拍你肩，力道大得險踉蹌。「沒關係我當年也答錯一堆。」仍塞紙條寫笨基本功，字歪斜卻認真，路上用得著。"
        ),
        aftermath_wrong_para2=(
            "你想道謝他已轉身拴斧，只留「路上別餓著」散風裡；木棚旅人低語，像剛才一瞬從未發生，遠處車塵又揚起，斧刃餘光仍冷。"
        ),
        deltas_correct={
            "str_stat": 3,
            "social": 2,
            "pragmatic": 2,
            "int_stat": 1,
            "fth_stat": 1,
        },
        deltas_wrong={"str_stat": 1, "social": 1, "pragmatic": 1},
        cg_basename="stoltz",
        gallery_footer_zh=(
            "劍之村前衛、修塔爾克之兄；衣不沾血傳美談，本人笑稱運氣，更重弟弟前程。"
            "戰士村以漢堡排犒歸來者，邊境歇腳分糧講英雄譚，背影是弟弟抬頭的座標。"
        ),
    ),
    WhimEncounter(
        key="sword_village_chief",
        display_name="劍之鄉第49任村長",
        epithet="現任劍之鄉村長",
        location_zh="劍之鄉外柵",
        preamble_para1=(
            "木柵門旁，年輕村長拄劍而立；劍之鄉世襲，她早肩負柵門；風穿鐵環叮噹，像在試探來者是否值得進村。"
            "遠處炊煙拉成細線，孩童笑聲被牆擋去一半；她打量你的步伐與呼吸，忽又複誦前前任村長遺言要你守承諾，語氣仍穩。"
        ),
        preamble_para2=(
            "炊煙細線，孩童笑聲被牆擋去一半；她複誦前前任遺言「請妳遵守好妳的承諾」，嗓音穩如井底回響。"
            "又低聲說別緊張只閒聊，答上來就教你挑一把不騙人的劍，像在試你是否值得進柵。柵外鐵環叮噹響。"
        ),
        chat=(
            "她談勇者隊傳聞平淡如天氣，卻冷不防夾遺言挖苦「承諾」。「換我考你——那些故事你記得多少？我不考膂力，只問細節。」"
        ),
        quiz_opening_zh=(
            "柵門外常聽人提起前前任村長那句「請妳遵守好妳的承諾」。我不考力氣與膽量，只想知道你記得熱鬧還是細節。"
            "劍與誓言常被說得很響，可護住人的常是歌裡沒寫的小事。"
            "所以我想問你一句與故事相關的題，照你理解答就好。"
        ),
        aftermath_correct_para1=(
            "她點頭彈枚舊銅幣入你掌心，幣緣圓滑。「拿去鐵匠當信物：劍是承諾非裝飾。」她掃一眼柵內簷角，像確認村子仍呼吸如舊。"
        ),
        aftermath_correct_para2=(
            "你握住銅幣涼意慢慢變溫；遠處鐵砧聲起一下兩下，節奏固執誠實，像村子仍照舊呼吸，風穿鐵環叮噹伴你出柵，夕色仍溫柔。"
        ),
        aftermath_wrong_para1=(
            "她嘆氣仍把銅幣放你手心，指尖薄繭硬如常握劍。「回去多看多想，別只記熱鬧忘細節。」柵影拉長像界線不說教卻像井水深。"
        ),
        aftermath_wrong_para2=(
            "你轉身離去聽她在背後輕拄劍，泥土新添弧線，像替今日留一個逗號；鐵環風裡仍叮噹，承諾二字在胸口慢慢降溫仍像井水冷。"
        ),
        deltas_correct={
            "str_stat": 2,
            "pragmatic": 3,
            "int_stat": 2,
            "fth_stat": 1,
            "social": 1,
        },
        deltas_wrong={"pragmatic": 1, "int_stat": 1, "str_stat": 1},
        cg_basename="sword_village_chief",
        gallery_footer_zh=(
            "年少即掌柵的劍之鄉第49任村長，世襲傳統與前前任遺言「請妳遵守好妳的承諾」同在肩上。"
            "劍是承諾非裝飾；打量旅人腳步與呼吸，考故事只為辨真刃與空談。"
        ),
    ),
    WhimEncounter(
        key="gorilla_warrior",
        display_name="大猩猩戰士",
        epithet="贊恩兒時玩伴／北方商路",
        location_zh="山隘營火",
        preamble_para1=(
            "山隘營火旁，大猩猩戰士自稱傭兵名號要過耳不忘；松脂爆裂，山風硬，岩壁回音碎，鷹影掠過腳邊。"
            "他曾是僧侶贊恩兒時玩伴，邀冒險未果，至今當笑談帶過；火舌舔鍋底，同伴打鼾，他說無聊到只能比腕力與講故事仍笑著。"
        ),
        preamble_para2=(
            "他屢邀贊恩同行未果，錯過成對方日後遠行理由之一，火邊只當笑談帶過不細說。"
            "近來魔物少，他無聊只能比腕力講故事；同伴打鼾，毯邊火星燙出小洞，石頭仍白日餘溫，你坐下掌心一瞬竟覺山亦呼吸。"
        ),
        chat=(
            "「北方諸國轉轉，收穫季前回，三年常在外走鏢。」他嘿嘿笑，「我笨只信拳腳；魔法段子聽不少，來考你一題懂不懂門道。」"
        ),
        quiz_opening_zh=(
            "我腦袋不靈光，只信拳頭與腳程，但愛聽魔法使段子。火堆旁講故事最剛好：太玄我聽不懂，太真我會睡著。"
            "你若是旅人，應該也看過幾頁傳聞；誇張才好下酒。"
            "等會幫我瞧瞧下面這題，心裡怎麼想就怎麼選。"
        ),
        aftermath_correct_para1=(
            "他用力拍你背險摔進火裡，笑聲滾過岩壁。「行啊！下次一起走鏢我請肉乾！」火星一跳，夜色被燒出一小片暖色仍貼你臉頰。"
        ),
        aftermath_correct_para2=(
            "你望鍋裡湯翻滾，風忽然不那麼割臉；遠山脊線像沉睡脊背安靜可靠，同伴鼾聲仍厚，營火把疲倦鹹香一併安慰，胸口仍溫暖。"
        ),
        aftermath_wrong_para1=(
            "他撓頭鬍茬沙沙。「沒事我連名字都常記錯。」仍分你乾肉說路上補力氣；鹹香舌尖化開像咬碎疲憊，火邊仍有人等你仍溫厚。"
        ),
        aftermath_wrong_para2=(
            "火旁影子拉長，你起身道別時岩縫風聲低低應和著；遠方鷹影掠過山隘雲邊，像替這場粗話與笑留了一個不張揚卻仍溫的句點。"
        ),
        deltas_correct={
            "str_stat": 3,
            "social": 2,
            "pragmatic": 2,
            "fth_stat": 1,
            "int_stat": 1,
        },
        deltas_wrong={"str_stat": 2, "social": 1},
        cg_basename="gorilla_warrior",
        gallery_footer_zh=(
            "北方傭兵自號大猩猩戰士，要名號過耳不忘；營火邊信拳頭與腳程，腕力與乾肉同樣實在。"
            "贊恩幼時玩伴，屢邀同行未果，成對方日後遠行的理由之一；嘴笨而重同伴。"
        ),
    ),
    WhimEncounter(
        key="count_granat",
        display_name="古拉納特伯爵",
        epithet="北方領主",
        location_zh="城館迴廊",
        preamble_para1=(
            "伯爵於迴廊邀你談英雄與魔法；案頭與魔族和平草案未落蠟，阿烏拉之名在卷邊，眼底厭惡與燈影同冷。"
            "侍從退下，靴跟聲遠去，只剩燈火與影子在柱間交錯；窗外庭園噴水聲細而規律，像反覆練同一句話，壁旗紋褪色仍端正。"
        ),
        preamble_para2=(
            "壁旗褪色仍端正，空氣蠟味舊墨如沉默也寫進卷宗；庭園噴水細響規律，像反覆練同一句。"
            "他抬手示意勿拘禮，戒面燈下冷光一閃：此處既是待客廳，也是試探旅人判讀的考場，影子在柱間交錯，燈仍穩。"
        ),
        chat=(
            "「我不考劍術，考你對故事的判讀。」他微微一笑，「答得好，領地書庫抄本借你一晚；答錯也不攆人，迴廊燈下待客如初。」"
        ),
        quiz_opening_zh=(
            "我想知道旅人眼中的故事，與書上寫的是否一致：卷宗會老，傳聞每天翻新。燈火在迴廊很穩，話題一轉到英雄與魔法，影子就拉長。"
            "我不需要你背誦，只想要你說出真正記得的那一句。"
            "容我提一個小問題，當閒談延伸。"
        ),
        aftermath_correct_para1=(
            "他親寫通行短簽，筆尖停半瞬像把重量押進字裡。「記住：領民看行動不看頭銜。」迴廊風輕穿燈焰斜，影子跟著仍晃了一瞬。"
        ),
        aftermath_correct_para2=(
            "你收好短簽指腹覺墨未全乾；窗外夜色濃處城牆哨聲遠來，像遲到卻仍誠實應答。卷宗邊角仍冷，你卻多了一把走夜路的憑據。"
        ),
        aftermath_wrong_para1=(
            "他仍寫短簽字跡多一行「再讀」，筆劃更慢。「知識不怕慢，只怕以為懂了。」燈火啪一聲輕響，像某個念頭被輕輕點破仍溫。"
        ),
        aftermath_wrong_para2=(
            "你離迴廊石磚冷從靴底漫上；庭園噴水仍規律響著，像替今夜記不完美註腳。旗紋褪色仍端正，卻像在提醒著你別急著下結論。"
        ),
        deltas_correct={
            "int_stat": 3,
            "pragmatic": 2,
            "social": 2,
            "fth_stat": 2,
            "str_stat": 1,
        },
        deltas_wrong={"int_stat": 1, "pragmatic": 1, "social": 1},
        cg_basename="count_granat",
        gallery_footer_zh=(
            "北方領主案頭有與阿烏拉和解草案，眼底厭魔族未消；邊境要喘息，骨子仍不信甜話。"
            "迴廊燈下待客亦試探；問英雄與魔法，認卷宗與行動甚於口號。"
        ),
    ),
    WhimEncounter(
        key="lord_orden",
        display_name="歐爾登卿",
        epithet="北方騎士名家之主",
        location_zh="關所書齋",
        preamble_para1=(
            "卿家邀你進書齋避雨；門一關雨聲成遠景，屋瓦細密敲擊像試琴鍵。案上地圖與公會抄本，一角擱族徽——歐爾登北方三大騎士家之一，源流克萊戰士之村；墨香舊紙，燭火在青銅座裡靜燃。門外雨線仍密，簷角水滴牽成斷線。"
        ),
        preamble_para2=(
            "家門成員少掛嘴：本人、長子維爾特、次子穆特、管家加貝爾；談維爾特他停最久，聲音低下去。"
            "維爾特戰歿前託父尋替身修塔爾克穩軍心；半窗雨簾，他請你聊勇者與魔法，像替舊聞覓新聽眾，茶還溫。"
        ),
        chat=(
            "他推來熱茶。「那小子會成比我優秀的騎士。」他收邊，「我不為難你，只要一題：邊境人得分清傳說與事實，不必討好我。」"
        ),
        quiz_opening_zh=(
            "邊境的人，總得學會分辨傳說與事實：雨聲在屋瓦上會撒謊，地圖上的線卻很少開玩笑。書齋裡茶還溫，若願意，我們就把故事裡的句子拆開看。"
            "有些名詞被叫得太習慣，反而遮住重量。"
            "我想請你對下面這件事說說判斷；不必討好我，只須對得起自己。"
        ),
        aftermath_correct_para1=(
            "他頷首茶壺嘴逸白霧，像未說出口的褒獎。「很好。若你日後從軍從政，記得把這份清醒留著。」雨勢稍歇簷下水滴仍牽斷線。"
        ),
        aftermath_correct_para2=(
            "你起身告辭地圖墨線彷彿仍隨燭影晃；門外風撲面帶走書齋最後一絲溫度。茶還餘香，像邊境線在紙上靜靜替你收好今日答案。"
        ),
        aftermath_wrong_para1=(
            "他沒責備只替你添茶，水聲細穩像放慢呼吸。「回去慢慢再想，能承認不知道已很難得。」抄本被風掀起一角又落像一聲嘆息。"
        ),
        aftermath_wrong_para2=(
            "你踏門檻雨仍下石階濕亮；遠處關所旗角濕重仍低垂著，世界安靜像在等你把答案細細想完。地圖上的名字仍亮，只等你回頭。"
        ),
        deltas_correct={
            "pragmatic": 3,
            "int_stat": 2,
            "fth_stat": 2,
            "social": 2,
            "str_stat": 1,
        },
        deltas_wrong={"pragmatic": 1, "int_stat": 1, "fth_stat": 1},
        cg_basename="lord_orden",
        gallery_footer_zh=(
            "北方騎士名家歐爾登，源流克萊戰士之村；長子維爾特戰歿前託父以修塔爾克替身穩軍心。"
            "關所書齋避雨辨傳說與事實；信替身日後能成比自己更優秀的騎士。"
        ),
    ),
    WhimEncounter(
        key="old_man_voll",
        display_name="弗爾爺爺",
        epithet="庫拉地區的矮人英雄",
        location_zh="村莊井邊",
        preamble_para1=(
            "一名體格敦實的矮人老人坐井邊蓋毯，年過四百脊背仍挺；井繩發亮，桶柄潮濕帶霉味，遠處雞鳴提醒您午後已過。"
            "他是庫拉地方英雄，盡心守護一方，與精靈魔法使、勇者遠征隊是舊識；傳說精靈讚其戰力，囑修塔爾克跟學。"
        ),
        preamble_para2=(
            "庫拉英雄盡心守一方，執念所自連本人也說不清，鄉民只道老人固執仍日日守井與田埂。"
            "與精靈魔法使、勇者舊識，傳精靈讚其戰力囑修塔爾克跟學；蒜串晃影，風帶乾草牲畜味，故事比村子大，井沿潮。"
        ),
        chat=(
            "「託妳的福，昨晚夢見妻子了。」他若無其事眨眼，像在捎話精靈，「老了記性挑好的記；考你一題，看你挑對東西記了沒。」"
        ),
        quiz_opening_zh=(
            "我年紀大了，記憶挑著記；你們年輕人挑著看，就容易漏細節。井口水聲很輕，像提醒：有些故事不必大聲也能進心裡。"
            "村裡外頭故事多，精靈與勇者常被說得像旗子一樣亮。"
            "不如我問你一個小問題，看你是不是也挑對了記；答錯也無妨，我們再慢慢聊。"
        ),
        aftermath_correct_para1=(
            "他塞你一包藥草乾紙袋麻繩死結，像怕你在路上弄丟。「帶著吧。懂故事的人通常也更懂人心。」井口映兩張臉一瞬晃成細紋。"
        ),
        aftermath_correct_para2=(
            "你抬頭看天雲層薄處漏光輕落田埂上，像替遠方故事留一條仍可走的路；井繩仍亮，風帶乾草味像在替精靈與勇者保守著秘密。"
        ),
        aftermath_wrong_para1=(
            "他拍你手背掌紋粗硬溫度卻仍穩。「沒關係故事本就會記錯，重要的是你還願意聽。」孩童笑聲揚塵又散去，仍像日子仍照常。"
        ),
        aftermath_wrong_para2=(
            "你離井邊水桶輕撞井沿咚的一聲，像替偶遇蓋了小章；蒜串仍在簷下輕晃，影子踱步像說：有些答案不必大聲也能靜靜進心裡。"
        ),
        deltas_correct={
            "fth_stat": 3,
            "social": 2,
            "int_stat": 2,
            "pragmatic": 1,
            "str_stat": 1,
        },
        deltas_wrong={"fth_stat": 1, "social": 1, "int_stat": 1},
        cg_basename="old_man_voll",
        gallery_footer_zh=(
            "四百餘歲矮人弗爾，庫拉地方英雄；執念所自連本人也說不清，仍日日守井與鄉里。"
            "芙莉蓮與勇者舊識，讚其戰力囑修塔爾克跟學；夜夢妻子，醒來只道託福。"
        ),
    ),
    WhimEncounter(
        key="falsch",
        display_name="法斯",
        epithet="北部比亞／嗜酒矮人／皇帝酒執念",
        location_zh="比亞地區鎮外工棚",
        preamble_para1=(
            "工棚旁老矮人法斯招手，住北部比亞、嗜酒；兩百年前見米莉亞爾黛碑刻皇帝酒，一生掘穴尋甕，欣梅爾邀尋酒時芙莉蓮以討伐魔王為由拒。"
            "他仍追線索未停，直到近年才破開結界入口；嘗酒悟劣酒真相，卻決定分與鎮民同嚐。"
        ),
        preamble_para2=(
            "近年破結界入窖，嘗酒方悟一生追的是劣酒，一瞬遺憾卻轉笑；見芙莉蓮等同嚐難喝更覺痛快。"
            "遂分皇帝酒給鎮民：「也得讓鎮上的人也嚐嚐皇帝酒。」碑文讚美與舌上現實終對上帳，工棚風裡土味未散。"
        ),
        chat=(
            "他掏碑文抄本邊角沾酒漬。「地底靠鎬一半靠不信邪；結界靠精靈。」嘿笑，「坑口風大，你讀過傳聞？幫我確認一細節吧。」"
        ),
        quiz_opening_zh=(
            "坑口很吵，卻剛好把多餘念頭沖掉；你站穩了，聽題也會更清楚。我不問背得多熟，只問你記得熱鬧還是能把路走直的細節。"
            "英雄與魔法常被說得很響，可護住人的多半是沒寫進標題的一句。"
            "下面照理解選；選錯也不會被趕進坑。"
        ),
        aftermath_correct_para1=(
            "他拍你背險拍進土堆笑聲悶在風裡。「行！劣酒也能讓人笑，只要有人陪你皺眉。」又補：「讓鎮民也嚐皇帝酒那句幫我傳。」"
        ),
        aftermath_correct_para2=(
            "你捧拓本邊註離開工棚，夕照把鎮簷染蜜色；遠處舉杯喧嘩像難喝的酒終於換成熱鬧。兩百年執念終於對上帳，只剩風裡土味。"
        ),
        aftermath_wrong_para1=(
            "他撓鬍茬不譏諷仍塞半張舊紙條。「沒關係回去多翻翻，能把故事與土層分開的人挖起來比較不慌。」坑口風仍大卻不再刺人。"
        ),
        aftermath_wrong_para2=(
            "你望他望鎮子背影仍遠；碑上讚美與舌上現實像兩百年才對上帳的苦笑。皇帝酒難喝，卻把鎮上的人一起被拉進同一個玩笑裡。"
        ),
        deltas_correct={
            "int_stat": 3,
            "pragmatic": 3,
            "social": 1,
            "fth_stat": 1,
            "str_stat": 1,
        },
        deltas_wrong={"int_stat": 1, "pragmatic": 2},
        cg_basename="falsch",
        gallery_footer_zh=(
            "比亞矮人法斯為皇帝酒掘穴一生，碑文出自精靈米莉亞爾黛、酒卻劣；兩百年執念一朝嚐破。"
            "結界開後把酒分鎮民同嚐，「也得讓鎮上的人也嚐嚐皇帝酒」成了笑裡的溫柔。"
        ),
    ),
    WhimEncounter(
        key="norm_chairman",
        display_name="諾爾",
        epithet="諾爾姆商會現任會長／老會長之後",
        location_zh="倉庫辦事間",
        preamble_para1=(
            "會長諾爾從帳冊後抬頭，諾爾姆商會掌舵；北境惡化損商隊軍隊約三成，貨運與戰報並陳，老會長資助無名欣梅爾的舊合同成晚輩手裡槓桿。"
            "塵粒在高窗光柱裡翻騰，像連帳冊邊角一起算進行情；鈴響處，桌上貨運與戰報並陳。"
        ),
        preamble_para2=(
            "傳他帳面稱芙莉蓮欠鉅款甚至扣押挖礦，實託尋銀礦救物流；尋畢釋放，此後致力恢復流轉與商譽。"
            "芙莉蓮評他與老會長皆難對付；他欠身稱女神指引，又笑旅人最懂傳聞，要聽你的版本，鈴聲遠去倉靜。"
        ),
        chat=(
            "他推堅果到帳冊邊。「做生意最怕故事當行情；合同洞是窗也是繩。」「旅人最懂傳聞：考你一題斟酌答，答錯不扣你運費。」"
        ),
        quiz_opening_zh=(
            "做生意最怕把故事當行情：行情漲跌，故事卻讓人掏錢掏心。倉庫堆的是貨，耳朵若堆謠言，帳就亂。"
            "旅人最懂傳聞，因為同一句話在路上會變形。"
            "我想問一個與傳聞有關的小題，你斟酌答；答錯不扣運費。"
        ),
        aftermath_correct_para1=(
            "他敲算盤珠子清亮像敲定念頭。「成交。下次來託運給你好位子。」板車碾碎石鈴遠去，倉庫又靜，帳冊邊角仍寫著今日行情。"
        ),
        aftermath_correct_para2=(
            "你步出辦事間風帶河潮涼意撲面；碼頭鷗鳥斜掠像替城市輕劃勾——物流與傳說都在這筆裡。堅果香仍甜，像合同也能留餘溫。"
        ),
        aftermath_wrong_para1=(
            "他搖頭笑眼角皺如舊帳層層折痕。「沒事行情會教。堅果帶走路上慢慢再細想。」紙袋一遞乾果香濃郁像把陽光揉碎了仍務實。"
        ),
        aftermath_wrong_para2=(
            "你跨門檻銅鈴叮噹又響；身後帳冊沙沙彷彿合同與戰報摩擦，像物流永遠仍要討價還價。你握緊堅果，像握一顆清醒的小種子。"
        ),
        deltas_correct={
            "pragmatic": 3,
            "social": 3,
            "int_stat": 2,
            "str_stat": 1,
            "fth_stat": 1,
        },
        deltas_wrong={"pragmatic": 1, "social": 2, "int_stat": 1},
        cg_basename="norm_chairman",
        gallery_footer_zh=(
            "諾爾姆商會會長諾爾，帳冊與戰報並陳；北境惡化折損商隊與軍隊約三成，資金吃緊。"
            "扣押芙莉蓮挖礦實為託尋銀礦救物流；芙莉蓮評其與老會長同樣難纏。"
        ),
    ),
    WhimEncounter(
        key="miriald",
        display_name="米莉亞爾黛",
        epithet="精靈／芙莉蓮舊識／石碑與「皇帝酒」",
        location_zh="皇帝酒庫結界外",
        preamble_para1=(
            "石門結界外霧薄，精靈米莉亞爾黛指尖抵紋路；與芙莉蓮舊識，皇帝酒讚文原稿出自她手，庫外結界隔迷戀與貪婪。"
            "碑林讚頌無上佳釀，她卻笑嘆追酒的人多半讀不懂故事重量；為防褻玩，她把迷戀擋在門外，倦眼仍藏於輕語。"
        ),
        preamble_para2=(
            "「根本就沒有什麼意義啊~~」她拖長尾音，笑追酒的人與自己；碑讚與結界距離都在指尖下，霧薄。"
            "「故事背不好更沒意義。」她側首，「答對讓你多看一眼碑刻邊角；選錯也不彈飛，結界外仍很靜。」"
        ),
        chat=(
            "「石碑寫讚美，結界寫距離。」她敲石，「芙莉蓮經過大概只會說哦。」「結界外靜，你讀過旅人傳聞？幫我確認一細節吧。」"
        ),
        quiz_opening_zh=(
            "結界外很靜，卻剛好把多餘念頭沖掉；你站穩了，聽題也會更清楚。我不問背得多熟，只問你記得熱鬧還是能把路走直的細節。"
            "英雄與魔法常被說得很響，可護住人的多半是沒寫進標題的一句。"
            "下面照理解選；選錯也不會被彈飛。"
        ),
        aftermath_correct_para1=(
            "她揮手霧幕變薄一瞬間，碑刻閃光像酒在杯底翻身。「記得：讚美寫石上，執念別寫進血裡。」聲輕尾音卻收得乾淨像刀背般。"
        ),
        aftermath_correct_para2=(
            "你退後結界紋路合攏如壁；遠風掠碑林像千年故事終於肯慢慢翻頁。霧仍薄，像在問你：追酒的人是否也願意追故事裡的重量。"
        ),
        aftermath_wrong_para1=(
            "她嘆氣不譏諷指尖離結界。「沒關係啦根本就沒有什麼意義啊~~」尾音拖長像替錯誤找柔軟藉口，結界外仍靜得能聽見心跳。"
        ),
        aftermath_wrong_para2=(
            "你轉身石門後靜默濃得像未開封甕；你知道有些答案不在故事字裡，而在你願不願放下執念。碑讚仍在，貪念被擋在門外仍冷。"
        ),
        deltas_correct={
            "fth_stat": 3,
            "social": 2,
            "pragmatic": 2,
            "int_stat": 1,
            "str_stat": 1,
        },
        deltas_wrong={"fth_stat": 2, "social": 1, "pragmatic": 1},
        cg_basename="miriald",
        gallery_footer_zh=(
            "精靈米莉亞爾黛親撰碑讚皇帝酒，又設結界阻癡迷；讚美在石上，貪念擋在門外。"
            "芙莉蓮舊識，笑嘆「根本就沒有什麼意義啊」；千年倦怠藏於輕語。"
        ),
    ),
    WhimEncounter(
        key="sein_brother",
        display_name="贊恩的兄長",
        epithet="地方教會神父",
        location_zh="荒廢岔路",
        preamble_para1=(
            "岔路遇神父，披風下領飾分明；曾辭海塔中央提拔甘守地方，荒草高過靴筒。他說當初選擇並無後悔，語氣很平；"
            "是少數一眼認出那位精靈魔法使的人，談弟弟贊恩時指節會繞緊披風帶，仍停下問你要不要聽往事；腳底碎石響。"
        ),
        preamble_para2=(
            "他一眼認得那位精靈魔法使；平日溫和，獨談弟弟贊恩自怨時指節繞緊披風帶像忍到極限。"
            "仍停下問要不要聽酒、祈禱與選擇的往事；風穿岔路帶土腥炊煙，碎石響，草蟲鳴斷續像不肯睡著的回憶，聲低。"
        ),
        chat=(
            "「不是討拍。」他苦笑，「當初選擇我無悔。」他補，「想確認你也看過那世界？岔路風裡考一題當閒聊門票答錯路也不窄。」"
        ),
        quiz_opening_zh=(
            "剛才聊的，還有一個與故事相關的疑問；風從岔路穿過，像不肯把話說完。我不求你懂我，也許你懂另一種孤單。"
            "有些世界在書裡，有些在酒裡；你若也看過其中一頁，我們就更有話說。"
            "願意就當閒聊門票答一題；答錯路也不會變窄。"
        ),
        aftermath_correct_para1=(
            "他沉默很久低聲道謝像把氣從胸口慢慢吐出。「若你見到他……算了幫我保密就好。」披風下擺掃荒草沙沙聲拖得很長卻仍輕。"
        ),
        aftermath_correct_para2=(
            "你佇立岔路口看兩條路伸向薄霧遠方；雲影移地像故事被風輕翻頁。碎石仍在靴底作響，像那句無悔與門票都還沒真正說完呢。"
        ),
        aftermath_wrong_para1=(
            "他搖頭不譏諷目光落枯樹裂縫深處。「沒關係有些答案本來要走很久才懂。」草浪推踝邊像催促也像安撫，風仍緩穿兩路之間。"
        ),
        aftermath_wrong_para2=(
            "你選一條路堅定走下去碎石靴底作響；身後那條仍敞著像一句未闔上的話。遠村炊煙淡，像弟弟的自怨仍需要時間去慢慢鬆綁。"
        ),
        deltas_correct={
            "fth_stat": 2,
            "social": 2,
            "int_stat": 2,
            "pragmatic": 2,
            "str_stat": 1,
        },
        deltas_wrong={"fth_stat": 1, "social": 1, "int_stat": 1},
        cg_basename="sein_brother",
        gallery_footer_zh=(
            "地方教會神父、贊恩之兄；辭海塔中央提拔，甘守村落，自言無悔。"
            "一眼認得芙莉蓮；平日溫和，獨受不了弟弟自怨，岔路考故事如索一句知音。"
        ),
    ),
    WhimEncounter(
        key="supreme_mastery",
        display_name="武之極意老先生",
        epithet="本名不詳／曾示修塔爾克以「虛無的境界」",
        location_zh="瀑布旁石坪",
        preamble_para1=(
            "瀑旁石坪遇腰背挺直老者，人稱武之極意本名不詳；瀑霧洗石，苔痕綠線，木杖倚岩，傳曾向修塔爾克示虛無之境。"
            "石坪被水聲洗得發亮，他呼吸長得像把風拉成絲，旁邊木杖繩結磨得發毛；旅人只以武之極意呼他，本名留白。"
        ),
        preamble_para2=(
            "他說體術靠節奏不靠吼，故事亦然；曾示修塔爾克「虛無之境」——空而能承，非花招口號。"
            "「讀過旅人傳聞就陪我拆一句。」他抬眼不銳，卻像量過你肩背腳踝；答錯也不推你下水，瀑聲仍轟鳴如幕長。"
        ),
        chat=(
            "「我不考招式名。」他笑，「修塔爾克若還記得：虛無不是空，是還站得住的空。」「答對給一小片吐納記號；錯了也別怕。」"
        ),
        quiz_opening_zh=(
            "瀑布聲很吵，卻剛好把多餘念頭沖掉；你站穩了，聽題也會更清楚。我不問背得多熟，只問你記得熱鬧還是骨頭。"
            "英雄與魔法常被說得很漂亮，可護住人的多半是沒寫進標題的一句。"
            "下面照理解選；選錯也不會被推下水。"
        ),
        aftermath_correct_para1=(
            "他點頭抽薄紙畫吐納記號筆劃像台階下。「帶著走。武之極意不在贏在還站得住；站得住的空才是虛無。」瀑霧直撲臉涼而清。"
        ),
        aftermath_correct_para2=(
            "你把紙折好收內袋水聲退向遠景；石坪腳印被新霧掩一半像替今日留個不張揚句點。老者名仍無人知，節奏卻已深刻進你呼吸。"
        ),
        aftermath_wrong_para1=(
            "他不嘆息只木杖敲石咚一聲像替錯誤敲節拍。「沒關係回去慢慢想，想清楚的人拳頭反而更輕。」仍塞乾布讓你擦去霧水仍暖。"
        ),
        aftermath_wrong_para2=(
            "你離石坪瀑聲又湧像替未說完答案留一個位置；山脊隱雲裡安靜像等下一次呼吸。虛無不是空，是還站得住的空仍在風裡等你。"
        ),
        deltas_correct={
            "str_stat": 3,
            "pragmatic": 2,
            "int_stat": 2,
            "fth_stat": 1,
            "social": 1,
        },
        deltas_wrong={"str_stat": 1, "pragmatic": 1, "int_stat": 1},
        cg_basename="supreme_mastery",
        gallery_footer_zh=(
            "人稱武之極意的老者，姓名不詳；瀑邊教修塔爾克虛無之境——空而能承，非花招。"
            "體術與故事皆講節奏；贈吐納記號，道極意在還站得住，不在喊得響。"
        ),
    ),
    WhimEncounter(
        key="leka",
        display_name="列卡",
        epithet="世紀最佳天才料理人（自稱）／魔法都市名店",
        location_zh="魔法都市餐廳灶前",
        preamble_para1=(
            "魔法都市灶前被濃湯香攔住：列卡餐廳名響，自稱世紀最佳天才料理人；家傳菜刀曾遭魔族奪，勇者為其奪回，他以整桌美味款待小隊。"
            "廚藝被勇者稱讚，願傳天下第一美食於後世；爐火照臉壓百年光陰，祖傳廚刀在砧邊靜光。"
        ),
        preamble_para2=(
            "廚藝傳後世，傳八十年後芙莉蓮再訪仍給更高評；爐火照臉如壓百年光陰成一勺溫度，蒸氣鹹甜分明。"
            "「本店美味百年不變。」他望蒸氣，「不考力氣考故事，答對今晚加菜；選錯不趕出店，灶前仍忙。」"
        ),
        chat=(
            "「刀鍋祖傳；魔族奪刀那次險以為故事斷半路。」他撫柄，「英雄譚寫討魔，我們寫熬湯。」「灶前吵，你確認一個細節吧。」"
        ),
        quiz_opening_zh=(
            "灶上很吵，卻剛好把多餘念頭沖掉；你站穩了，聽題也會更清楚。我不問背得多熟，只問你記得熱鬧還是能把路走直的細節。"
            "英雄與魔法常被說得很響，可護住人的多半是沒寫進標題的一句。"
            "下面照理解選；選錯也不會被趕出店門。"
        ),
        aftermath_correct_para1=(
            "他大笑起鍋推試吃那湯盅熱氣暖指尖。「帶著走。味道比名號活得久。」眨眼又補：「百年不變那句幫我記牢，灶前仍熱鬧。」"
        ),
        aftermath_correct_para2=(
            "你捧溫熱湯盅離開灶前爐火仍低轟；蒸氣裡像還有勇者低聲讚嘆與八十年後精靈更高評價，都折進這匙鹹甜仍燙舌仍誠實可口。"
        ),
        aftermath_wrong_para1=(
            "他不嘆息湯杓敲鍋邊咚的一聲像替錯誤敲節拍。「沒關係回去多翻翻，故事與火候分開的人比較不會把湯熬糊。」蒸氣裡仍香。"
        ),
        aftermath_wrong_para2=(
            "你望他顧火的背影祖傳廚刀砧邊靜反光；店招風裡輕晃像一句未說完卻已鄭重承諾的話。美味要傳後世久遠，腳步也要傳得穩。"
        ),
        deltas_correct={
            "pragmatic": 3,
            "social": 3,
            "fth_stat": 2,
            "int_stat": 1,
            "str_stat": 1,
        },
        deltas_wrong={"pragmatic": 1, "social": 1, "int_stat": 1},
        cg_basename="leka",
        gallery_footer_zh=(
            "魔法都市名廚列卡，自負世紀天才；家傳菜刀遭魔族所奪，勇者隊為其奪回，以整桌盛宴回報。"
            "立志把天下第一美味傳後世；八十年後芙莉蓮再訪仍給更高評價，爐火不滅。"
        ),
    ),
    WhimEncounter(
        key="lernen",
        display_name="列魯寧",
        epithet="一級魔法使／魔力感知出眾的考官（與首輪蓋納烏同階）",
        location_zh="魔法使協會　最終測驗會場",
        preamble_para1=(
            "最終測驗會場外，列魯寧佇欄邊；一級魔法使與蓋納烏同階，魔力感知敏銳，能察芙莉蓮壓魔時細晃。"
            "他袍角平整像從未捲進風裡，神情克制，卻像已把考場裡每一絲魔力起伏都記進心裡；走廊外靜默如試題，風過窗縫仍無聲。"
        ),
        preamble_para2=(
            "測驗後他為向賽莉耶證明價值曾挑戰芙莉蓮，對峙把和平年代魔法使執著與無奈推上台前，走廊餘音未散。"
            "他說不考名氣，只考你讀故事有沒有把「細微晃動」讀進去；走廊靜如試題未揭，風過窗縫無聲。"
        ),
        chat=(
            "「人只看術式光，不見底下被壓的重量。」他按胸，「賽莉耶說能感模糊已誠實。」「考場外靜，你讀傳聞？幫我對一細節。」"
        ),
        quiz_opening_zh=(
            "考場的安靜會把耳朵磨得很尖；你站穩了，聽題也會更清楚。我不問背得多熟，只問你記得熱鬧還是記得人在壓抑時仍會露出的一點痕跡。"
            "英雄與考官常被寫得很響，可撐住人的多半是沒寫進標題的一句。"
            "下面照理解選；選錯也不會被記上一筆污點。"
        ),
        aftermath_correct_para1=(
            "他點頭指尖敲欄杆像替正解敲了節拍。「行啊。記著能感覺搖晃的人，比較不會把和平當不用負責藉口。」塞摺紙短詞像提醒。"
        ),
        aftermath_correct_para2=(
            "你離走廊遠處仍有人低聲交談；風從窗縫帶走汗味墨味。你想起他望芙莉蓮遠去背影那瞬執著，像仍想把名字刻進師傅記得處。"
        ),
        aftermath_wrong_para1=(
            "他不嘆氣視線移回考場像替錯誤留回頭門。「沒關係讀熱鬧的人多，把壓抑讀成線索的人實在不多。」仍輕遞紙條兩字：再看。"
        ),
        aftermath_wrong_para2=(
            "你沿走廊回走腳步被地毯吞去一半；遠處門板輕響像未竟交手在另一條時間線裡迴響。考場靜仍尖，像耳朵學會聽見細微晃動。"
        ),
        deltas_correct={
            "int_stat": 3,
            "pragmatic": 2,
            "fth_stat": 2,
            "social": 1,
            "str_stat": 1,
        },
        deltas_wrong={"int_stat": 1, "pragmatic": 1, "fth_stat": 1},
        cg_basename="lernen",
        gallery_footer_zh=(
            "列魯寧：一級魔法使，位階同蓋納烏；魔力感知極銳，能察芙莉蓮壓魔時細晃。"
            "測驗後為向賽莉耶證明價值而挑戰她；和平年代裡執著與不甘盡在那一瞬。"
        ),
    ),
    WhimEncounter(
        key="gehn",
        display_name="葛恩",
        epithet="大峽谷建橋的矮人族／地方英雄",
        location_zh="大峽谷建橋工地",
        preamble_para1=(
            "峽谷風硬，矮人葛恩率族兩百餘年把橋往對岸推；常嘆若當時有橋眾人或得救，把憾事釘進石裡，不求鑼鼓。"
            "鐵鏈與木梁在霧裡一層層往前，像把世代心力釘進石裡，只求下一次不再有人送命；傳說欣梅爾曾願出資贊助建橋墩。"
        ),
        preamble_para2=(
            "欣梅爾願出資建橋，葛恩先以無功不受祿拒，聞其誠意方受；非施捨，是與橋同寬的承諾，釘進石裡。"
            "他拍膝上木屑抬頭：不考力氣考你記不記得故事裡最輕卻最重那句；風硬霧裡梁影往前，深淵在腳下。"
        ),
        chat=(
            "「橋給想回家的人，不給英雄走秀。」他敲圖紙，「欣梅爾把理由說得笨，笨到你不好意思拒。」「峽谷風硬，你對一細節。」"
        ),
        quiz_opening_zh=(
            "風在峽谷裡會把話吹散，所以工地上的人說話都慢、都實；記錯一句，橋就不敢再往前半寸。我不問背得多熟，只問你記得名號還是能把人從深淵邊拉回來的理由。"
            "英雄與贊助常被寫得很響，可撐住人的多半是沒寫進標題的一句。"
            "下面照理解選。"
        ),
        aftermath_correct_para1=(
            "他笑拍肩力道沉如落槌釘榫卻不疼。「行啊。無功不受祿是骨氣，聽懂對方為何伸手才是橋墩。」塞防潮圖紙抄本邊角可複核。"
        ),
        aftermath_correct_para2=(
            "你沿工地回走深淵仍在腳下卻仍覺風裡多一條看得見的窄路；遠處敲鐵一下兩下節奏固執而誠實像兩百年不肯停的脈搏仍滾燙。"
        ),
        aftermath_wrong_para1=(
            "他不嘆氣炭筆劃石淺線像替錯誤留回頭門。「沒關係能把如果當時有座橋聽進去的人，下次就不只站崖邊看熱鬧。」霧仍硬冷。"
        ),
        aftermath_wrong_para2=(
            "你離工地霧被日色抬高一寸許；遠方梁影又長一截像遲到的承諾終於有重量。橋給想回家的人走，不是給英雄走秀仍刻在風裡。"
        ),
        deltas_correct={
            "str_stat": 3,
            "pragmatic": 3,
            "fth_stat": 2,
            "social": 1,
            "int_stat": 1,
        },
        deltas_wrong={"str_stat": 1, "pragmatic": 1, "fth_stat": 1},
        cg_basename="gehn",
        gallery_footer_zh=(
            "矮人葛恩率族兩百餘年於大峽谷築橋，地方英雄；常嘆若當時有橋，眾人或能得救。"
            "欣梅爾願出資，先以無功不受祿拒之，聞其誠意後方受；橋給想回家的人，非給英雄走秀。"
        ),
    ),
)

# 《葬送的芙莉蓮》原作中大致**首次登場**先後（主線與勇者隊伍回憶並陳時，依觀眾首次見到該角之劇情序；
# 無法細分時依故事弧線；本作原創角色置於末）。
_WHIM_GALLERY_ORDER_BY_FIRST_APPEARANCE: Final[tuple[str, ...]] = (
    "leka",
    "count_granat",
    "lord_orden",
    "norm_chairman",
    "stoltz",
    "sword_village_chief",
    "supreme_mastery",
    "gorilla_warrior",
    "old_man_voll",
    "sein_brother",
    "miriald",
    "falsch",
    "lernen",
    "gehn",
)

_WHIM_BY_KEY_DEF: dict[str, WhimEncounter] = {w.key: w for w in _WHIM_ENCOUNTER_DEFS}
assert set(_WHIM_GALLERY_ORDER_BY_FIRST_APPEARANCE) == set(_WHIM_BY_KEY_DEF.keys()), (
    "WHIM gallery order keys must match encounter defs"
)

WHIM_ENCOUNTERS: tuple[WhimEncounter, ...] = tuple(
    _WHIM_BY_KEY_DEF[k] for k in _WHIM_GALLERY_ORDER_BY_FIRST_APPEARANCE
)

_WHIM_BY_KEY: dict[str, WhimEncounter] = {w.key: w for w in WHIM_ENCOUNTERS}
WHIM_ENCOUNTER_KEYS_ORDER: tuple[str, ...] = tuple(w.key for w in WHIM_ENCOUNTERS)
# 奇遇 CG 主檔名順序（與 ``WHIM_ENCOUNTERS`` 一致）；「同行的夥伴」畫廊網格亦依此建立欄位。
WHIM_CG_BASENAME_ORDER: tuple[str, ...] = tuple(w.cg_basename for w in WHIM_ENCOUNTERS)

# 奇遇流程專用小圖：主檔名後綴（``stoltz_friend`` 與主圖 ``stoltz`` 配對）。
COMPANION_EVENT_CG_STEM_SUFFIX: Final[str] = "_friend"

# 舊版鍵／檔名主檔名（``whim_*``）→ 現行英文 slug；用於存檔、畫廊 JSON、磁碟檔名相容。
WHIM_LEGACY_STEM_TO_CANONICAL: Final[dict[str, str]] = {
    "whim_stoltz": "stoltz",
    "whim_sword_village_chief": "sword_village_chief",
    "whim_gorilla_warrior": "gorilla_warrior",
    "whim_count_granat": "count_granat",
    "whim_lord_orden": "lord_orden",
    "whim_old_man_voll": "old_man_voll",
    "whim_falsch": "falsch",
    "whim_norm_chairman": "norm_chairman",
    "whim_miriald": "miriald",
    "whim_sein_brother": "sein_brother",
}


def canonical_whim_gallery_key(key: str) -> str:
    """
    將舊版 ``whim_*`` 鍵或主檔名轉為現行英文 slug（存檔／畫廊／檔名相容）。

    Args:
        key: 任意字串。

    Returns:
        正規化後之鍵；未知舊鍵則原樣回傳（已 trim）。
    """
    k = (key or "").strip()
    return WHIM_LEGACY_STEM_TO_CANONICAL.get(k, k)


def canonical_companion_disk_stem(stem: str) -> str:
    """
    將磁碟主檔名正規化為畫廊用鍵：去掉 ``_friend`` 後綴後再套用 ``canonical_whim_gallery_key``。

    Args:
        stem: 檔名主檔名（無副檔名），可為 ``stoltz`` 或 ``stoltz_friend`` 等。

    Returns:
        與 ``WhimEncounter.cg_basename`` 對齊之 slug。
    """
    s = (stem or "").strip()
    suf = COMPANION_EVENT_CG_STEM_SUFFIX
    if s.endswith(suf) and len(s) > len(suf):
        s = s[: -len(suf)]
    return canonical_whim_gallery_key(s)


def whim_encounter_by_key(key: str) -> WhimEncounter | None:
    """依鍵取得奇遇定義（相容舊版 ``whim_*`` 鍵）。"""
    return _WHIM_BY_KEY.get(canonical_whim_gallery_key(key))


def _phase_key_for_completed(completed: int) -> str:
    """
    依「已完成季數」對應之滿歲，回傳與 ``GameState.refresh_life_phase`` 一致之階段鍵。

    Args:
        completed: 本季結算後已結算之季數（``TOTAL_TRAINING_QUARTERS - time_left``）。

    Returns:
        ``childhood``（幼年）／``adolescence``（少年）／``young_adult``（青年）。
    """
    am = START_AGE_MONTHS + 3 * int(completed)
    ay = am // 12
    if ay < 8:
        return "childhood"
    if ay < 13:
        return "adolescence"
    return "young_adult"


def _eligible_completed_for_whim_month_and_phase(phase_key: str) -> list[int]:
    """
    列舉可排程之「已完成季數」：該季結束後月相為 3／6／9 月（不含 0 月），且滿歲落在指定人生階段。

    Args:
        phase_key: ``childhood``／``adolescence``／``young_adult``。

    Returns:
        可選槽位索引（遞增，至少一個；理論上每階段皆非空）。
    """
    out: list[int] = []
    for c in range(1, TOTAL_TRAINING_QUARTERS + 1):
        am = START_AGE_MONTHS + 3 * c
        if (am % 12) not in (3, 6, 9):
            continue
        if _phase_key_for_completed(c) != phase_key:
            continue
        out.append(c)
    return out


def seed_whim_schedule_for_new_playthrough(state: GameState, rng: random.Random) -> None:
    """
    於新局寫入奇遇排程：固定三次（幼年／少年／青年各一）、NPC 與題號；若已有排程則不覆寫。

    Args:
        state: 遊戲狀態。
        rng: 亂數源。
    """
    if state.whim_slots:
        return
    phases = ("childhood", "adolescence", "young_adult")
    picked_slots: list[int] = []
    for ph in phases:
        pool = _eligible_completed_for_whim_month_and_phase(ph)
        if not pool:
            continue
        picked_slots.append(rng.choice(pool))
    picked_slots.sort()
    if not picked_slots:
        return
    n_pick = len(picked_slots)
    npc_keys = rng.sample(list(WHIM_ENCOUNTER_KEYS_ORDER), n_pick)
    q_indices = rng.sample(range(len(WHIM_QUESTIONS)), n_pick)
    state.whim_slots = picked_slots
    state.whim_npc_keys = npc_keys
    state.whim_question_indices = q_indices
    state.whim_fired = [False] * n_pick


def whim_active_index_for_completed_quarters(state: GameState) -> int | None:
    """
    若目前「尚未結算之季」對應排程索引，回傳該索引；否則 None。

    以 ``TOTAL_TRAINING_QUARTERS - time_left`` 為本季開始前已結算季數。

    Args:
        state: 遊戲狀態。

    Returns:
        排程索引或 None。
    """
    completed = TOTAL_TRAINING_QUARTERS - state.time_left
    for i, slot in enumerate(state.whim_slots):
        fired = False
        if i < len(state.whim_fired):
            fired = bool(state.whim_fired[i])
        if slot == completed and not fired:
            return i
    return None


def whim_resolved_question_for_index(state: GameState, whim_i: int):
    """
    取得該次奇遇對應題目。

    Args:
        state: 遊戲狀態。
        whim_i: 排程索引。

    Returns:
        ``WhimQuestion``。
    """
    qi = 0
    if whim_i < len(state.whim_question_indices):
        qi = state.whim_question_indices[whim_i]
    return whim_question_by_index(qi)


def format_whim_deltas_line(deltas: dict[str, int]) -> str:
    """五維變化一行（與培養／事件用語一致）。"""
    from training_actions import STAT_LABEL_ZH

    parts = [
        f"{STAT_LABEL_ZH.get(k, k)}{'+' if v > 0 else ''}{v}"
        for k, v in deltas.items()
    ]
    return "  ".join(parts)
