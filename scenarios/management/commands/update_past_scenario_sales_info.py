from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from scenarios.models import Scenario


@dataclass(frozen=True)
class ScenarioSalesInfo:
    canonical_title: str
    aliases: tuple[str, ...]
    data: dict


def info(canonical_title, aliases, **data):
    return ScenarioSalesInfo(canonical_title, tuple(aliases), data)


SCENARIO_SALES_INFOS = (
    info(
        "静なるテロリスタ",
        [
            "静なるテロリスタ",
            "静なるテロリスタ≪本編≫",
            "静なるテロリスタ【HO 異邦人】導入\n※冒頭録画ミス※ゴメンナサイ",
            "静なるテロリスタ【HO 童子】導入",
            "静なるテロリスタ【HO 美術家】導入",
            "静なるテロリスタ【HO 篤学者】導入",
            "静なるテロリスタ【HO 異邦人】個別導入",
            "静なるテロリスタ【HO童子】個別導入",
        ],
        author="ジャック秘密探偵社",
        url="https://booth.pm/ja/items/3251000",
        summary="芸術都市ミラノのエテルノ美術館を舞台に、4人の秘匿HO探索者が交差するクトゥルフ神話TRPGシナリオ。展示会の最中に美術館が占拠されるところから物語が動き出す。",
        public_info="西暦2021年10月10日。芸術都市ミラノにオープンするエテルノ美術館の招待状を手にした探索者たちは、それぞれの目的を胸に展示会へ向かう。",
        recommended_players="4人",
        min_players=4,
        max_players=4,
        player_count=4,
        estimated_time=12,
        setting_era="現代",
        setting_location="現代イタリア・エテルノ美術館",
        scenario_style="秘匿HO/クローズド",
        recommended_skills="目星、聞き耳、図書館",
        semi_recommended_skills="ほかの言語（英語）または ほかの言語（イタリア語）",
        investigator_requirements="秘匿HOに沿った探索者。公開HOは童子、篤学者、美術家、異邦人。",
        content_warnings="一部グロテスクな表現、クトゥルフ神話的恐怖、暴力的描写、探索者同士の対立が発生する可能性あり。",
        lost_rate="本文参照",
        combat_level="本文参照",
        pvp_level="可能性あり",
        scenario_tags="CoC6,秘匿HO,クローズド,現代イタリア,美術館",
    ),
    info(
        "同じ空には昇れない",
        ["同じ空には昇れない", "同じ空には昇れない【第三陣】"],
        author="多箱屋商会",
        url="https://booth.pm/ja/items/5202796",
        summary="昼に嫌われた吸血鬼と、夜に嫌われた人間を描く、現代日本想定の新規2人固定・秘匿HO型一本道シティシナリオ。",
        public_info="ある日の夕暮れ、勤務先のコンビニへ忘れ物を取りに戻る道中、道端で行き倒れている吸血鬼を見つける。",
        recommended_players="新規2人固定",
        min_players=2,
        max_players=2,
        player_count=2,
        estimated_time=12,
        setting_era="現代",
        setting_location="現代日本",
        scenario_style="秘匿HO型一本道シティ",
        recommended_skills="HOごとに記載",
        semi_recommended_skills="",
        investigator_requirements="新規2人固定。公開HOはHO太陽「君は目覚めたい」、HO月「君は眠りたい」。",
        content_warnings="ロストあり。詳細は販売ページおよび本文参照。",
        lost_rate="有り",
        combat_level="本文参照",
        pvp_level="本文参照",
        scenario_tags="CoC6,秘匿HO,2PL,シティ,吸血鬼",
    ),
    info(
        "グレイブレコード",
        ["グレイブレコード"],
        author="酸味屋",
        url="https://booth.pm/ja/items/7173134",
        summary="2PL・4PCで、2つの時代と4人の探索者を扱う3話構成のキャンペーンシナリオ。現代日本編と架空王国編を含む終末譚。",
        public_info="明日、世界は滅びる。終焉前日の現代日本、そして西暦967年の架空王国を舞台に、探索者たちはそれぞれの時代を歩む。",
        recommended_players="2PL・4PC",
        min_players=2,
        max_players=4,
        player_count=2,
        estimated_time=9,
        setting_era="現代日本 / 西暦967年の架空王国",
        setting_location="現代日本・ミズガリズル王国",
        scenario_style="3話構成キャンペーン",
        recommended_skills="目星、図書館。章により聞き耳、交渉技能、戦闘技能など。",
        semi_recommended_skills="",
        investigator_requirements="PL1人につき2人の探索者を作成。現代日本編は新規・継続可、別章は新規限定の記載あり。",
        content_warnings="章によりロスト率が異なる。詳細は本文参照。",
        lost_rate="低〜中高/高",
        combat_level="章によりあり",
        pvp_level="本文参照",
        scenario_tags="CoC6,2PL,4PC,キャンペーン,終末,現代日本,架空王国",
    ),
    info(
        "狂気山脈",
        ["狂気山脈", "狂気山脈　第一登山隊"],
        author="FORESTLIMIT Shop",
        url="https://booth.pm/ja/items/1071516",
        summary="南極に現れた未知の巨大山脈“狂気山脈”に、登山家たる探索者たちが挑むクトゥルフ神話TRPGシナリオ。CoC6版、7版アップデートパッチ、4人用調整版などが頒布されている。",
        public_info="ニュージーランド航空の南極飛行観光旅客ジェット機が謎の失踪を遂げる。無線信号が途絶えた座標の先には、前人未踏の巨大山脈が立ちはだかっていた。",
        recommended_players="3〜4人程度",
        min_players=3,
        max_players=4,
        player_count=4,
        setting_era="現代",
        setting_location="南極・狂気山脈",
        scenario_style="登山/キャンペーン",
        recommended_skills="登山・探索に関わる技能。詳細はシナリオ本文参照。",
        semi_recommended_skills="",
        investigator_requirements="登山家たる探索者を想定。4人用調整版あり。",
        content_warnings="クトゥルフ神話的恐怖、極地登山、遭難・危険環境を扱う。詳細は本文参照。",
        lost_rate="本文参照",
        combat_level="本文参照",
        pvp_level="本文参照",
        scenario_tags="CoC6,CoC7,登山,南極,キャンペーン,無料",
    ),
    info(
        "モーンガータの魔法使い",
        [
            "モーンガータの魔法使い",
            "モーンガータの魔法使い《前半》",
            "モーンガータの魔法使い《後半》",
            "モーンガーターの魔法使い",
        ],
        author="酸味屋",
        url="https://booth.pm/ja/items/5895208",
        summary="魔法学園を舞台にした、新規限定2PL・秘匿ハンドアウトありの5話構成キャンペーンシナリオ。探索者は魔法学園の生徒として物語に参加する。",
        public_info="魔法学園へようこそ、魔法使い諸君。魔法を学び、魔法を楽しむ唯一つの世界で、善心と勇気の物語が始まる。",
        recommended_players="2PL",
        min_players=2,
        max_players=2,
        player_count=2,
        estimated_time=15,
        setting_era="ファンタジー/魔法学園",
        setting_location="モーンガータ魔法学園",
        scenario_style="5話構成キャンペーン/秘匿HO",
        recommended_skills="目星、聞き耳、図書館、交渉技能",
        semi_recommended_skills="",
        investigator_requirements="新規限定。公開HOはHO1「魔法学園の新入生」、HO2「魔法学園の嫌われ者」。",
        content_warnings="独自解釈、探索者への設定付与、PC/PLの意思が反映されない可能性、PvPの可能性、子どもに対する犯罪行為の描写など。",
        lost_rate="中〜高",
        combat_level="本文参照",
        pvp_level="可能性あり",
        scenario_tags="CoC6,秘匿HO,2PL,キャンペーン,魔法学園",
    ),
    info(
        "犬猫戦争は、終わらせない。",
        ["犬猫戦争は、終わらせない。", "犬猫戦争は終わらせない"],
        author="ろっしなりお電子書店",
        url="https://booth.pm/ja/items/2913315",
        summary="犬猫学園秀才大学を舞台に、犬科と猫科の首席「Ⅱ英傑」が年度末レクリエーション“犬猫祭”に挑む、秘匿HOありの対戦型協力シナリオ。",
        public_info="犬猫学園秀才大学の犬科と猫科は、年度末のレクリエーション“犬猫祭”で勝敗を競う。11回目の戦争で、全ての決着がつく。",
        recommended_players="2人",
        min_players=2,
        max_players=2,
        player_count=2,
        setting_era="現代",
        setting_location="現代日本・犬猫学園秀才大学",
        scenario_style="秘匿HO/対戦型協力",
        recommended_skills="シナリオ本文参照",
        semi_recommended_skills="",
        investigator_requirements="公開HOはHO1「誰よりも優秀な犬」、HO2「誰よりも気高い猫」。",
        content_warnings="秘匿HOあり。対戦型協力シナリオ。詳細は本文参照。",
        lost_rate="低",
        combat_level="本文参照",
        pvp_level="対戦型協力",
        scenario_tags="CoC6,秘匿HO,2PL,対戦型協力,学園",
    ),
    info(
        "怪祓-カイブツ-",
        ["怪祓-カイブツ-"],
        author="はなむけ屋",
        url="https://booth.pm/ja/items/7536096",
        summary="神や怪異を題材にした、2人用・秘匿HOありの連作シナリオ。日本を舞台に、怪祓師と助手を中心とした物語が展開する。",
        public_info="「人成らざるもの」「人間の命を容易く遊ぶ存在」、またその現象を神と称するならば、怪異も神に成れるのではないだろうか。",
        recommended_players="2人",
        min_players=2,
        max_players=2,
        player_count=2,
        estimated_time=45,
        setting_era="現代",
        setting_location="日本",
        scenario_style="秘匿HO/連作",
        recommended_skills="秘匿HOに記載",
        semi_recommended_skills="",
        investigator_requirements="HO1は20〜30歳の新規探索者限定。HO2は18歳以上、継続可だが設定付与や特徴表制限あり。",
        content_warnings="オリジナル世界観、特殊用語、キャラメイク制限、神話的事象や神話生物への独自解釈を含む。",
        lost_rate="本文参照",
        combat_level="本文参照",
        pvp_level="本文参照",
        scenario_tags="CoC6,秘匿HO,2PL,怪異,日本,連作",
    ),
    info(
        "獣人ガストロノミー",
        ["獣人ガストロノミー", "獣人ガストロノミー 事前導入HO3.4", "獣人ガストロノミー 事前導入HO1,2"],
        author="犬小屋スタジオ",
        url="https://booth.pm/ja/items/5844289",
        summary="人間が食料として扱われる世界を舞台に、2人と2匹が恐ろしい世界から逃げる新規限定シナリオ。獣人、葛藤、ダブルバディを扱う。",
        public_info="美味しそうな人間と、傷つけないよう葛藤する獣人。2人と2匹が、恐ろしい世界から逃げる物語。",
        recommended_players="2人と2匹",
        min_players=2,
        max_players=4,
        player_count=2,
        estimated_time=16,
        setting_era="異世界/獣人社会",
        setting_location="人間が食料の世界",
        scenario_style="秘匿HO/ダブルバディ",
        recommended_skills="HO毎に異なる",
        semi_recommended_skills="",
        investigator_requirements="新規限定。4つのHOを扱う。",
        content_warnings="一部のHOが食されることがあります。人間が食料として扱われる設定を含む。",
        lost_rate="中",
        combat_level="本文参照",
        pvp_level="本文参照",
        scenario_tags="CoC6,秘匿HO,2PL,4HO,獣人,ダブルバディ",
    ),
)


class Command(BaseCommand):
    help = "Update imported past-session scenarios with public sales-page metadata."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show matching scenarios without saving changes.")
        parser.add_argument(
            "--create-missing", action="store_true", help="Create canonical records when no scenario matches."
        )
        parser.add_argument("--created-by", default="sheepdog1919", help="Username for --create-missing.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        creator = self._get_creator(options["created_by"]) if options["create_missing"] else None
        stats = {"matched": 0, "updated": 0, "created": 0, "unchanged": 0, "missing": 0}
        with transaction.atomic():
            for sales_info in SCENARIO_SALES_INFOS:
                scenarios = list(self._find_scenarios(sales_info))
                if not scenarios and creator:
                    scenarios = [self._create_scenario(sales_info, creator, dry_run)]
                    stats["created"] += 1
                elif not scenarios:
                    stats["missing"] += 1
                    self.stdout.write(self.style.WARNING(f"missing: {sales_info.canonical_title}"))
                    continue
                for scenario in scenarios:
                    stats["matched"] += 1
                    changed_fields = self._changed_fields(scenario, sales_info.data)
                    if dry_run:
                        self.stdout.write(f"dry-run: {scenario.title} fields={','.join(changed_fields) or '-'}")
                    elif changed_fields:
                        for field in changed_fields:
                            setattr(scenario, field, sales_info.data[field])
                        scenario.save(update_fields=changed_fields)
                        stats["updated"] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"updated: {scenario.title} fields={','.join(changed_fields)}")
                        )
                    else:
                        stats["unchanged"] += 1
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(
            self.style.SUCCESS(
                "scenario sales info complete: "
                f"matched={stats['matched']} updated={stats['updated']} created={stats['created']} "
                f"unchanged={stats['unchanged']} missing={stats['missing']}"
            )
        )

    def _find_scenarios(self, sales_info):
        query = Q(title__in=sales_info.aliases)
        if sales_info.data.get("url"):
            query |= Q(url=sales_info.data["url"])
        return Scenario.objects.filter(query).order_by("id")

    def _changed_fields(self, scenario, data):
        return [field for field, value in data.items() if getattr(scenario, field) != value]

    def _get_creator(self, username):
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"created-by user not found: {username}") from exc

    def _create_scenario(self, sales_info, creator, dry_run):
        scenario = Scenario(title=sales_info.canonical_title, created_by=creator)
        for field, value in sales_info.data.items():
            setattr(scenario, field, value)
        if not dry_run:
            scenario.save()
        return scenario
