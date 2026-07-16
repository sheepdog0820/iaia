COC6_ONLY_BASIC_SKILL_NAMES = frozenset(
    {
        "こぶし（パンチ）",
        "キック",
        "サブマシンガン",
        "ショットガン",
        "マシンガン",
        "マーシャルアーツ",
        "ライフル",
        "他の言語",
        "値切り",
        "写真術",
        "化学",
        "博物学",
        "地質学",
        "天文学",
        "忍び歩き",
        "拳銃",
        "物理学",
        "生物学",
        "組み付き",
        "芸術",
        "薬学",
        "製作",
        "運転",
        "隠す",
        "隠れる",
        "頭突き",
    }
)

COC7_ONLY_BASIC_SKILL_NAMES = frozenset(
    {
        "ほかの言語",
        "サバイバル",
        "威圧",
        "射撃（ライフル／ショットガン）",
        "射撃（拳銃）",
        "手さばき",
        "科学",
        "自然",
        "芸術／製作",
        "近接戦闘（格闘）",
        "運転（自動車）",
        "鑑定",
        "隠密",
        "魅惑",
    }
)


def incompatible_basic_skill_names(edition):
    if edition == "6th":
        return COC7_ONLY_BASIC_SKILL_NAMES
    if edition == "7th":
        return COC6_ONLY_BASIC_SKILL_NAMES
    return frozenset()
