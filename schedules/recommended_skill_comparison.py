import re
import unicodedata

SKILL_DELIMITER_RE = re.compile(r"[\r\n,、，]+")
SPECIALIZED_SKILL_RE = re.compile(r"^(?P<base>.*?)[(（](?P<specialization>.*?)[)）]\s*$")

GENERAL_SKILL_ALIASES = {
    "他国語": "他の言語",
    "ほかの言語": "他の言語",
    "威嚇": "威圧",
}

SEVENTH_EDITION_SKILL_ALIASES = {
    "隠れる": "隠密",
    "忍び歩き": "隠密",
    "隠す": "手さばき",
    "近接戦闘": "近接戦闘（格闘）",
    "格闘技": "近接戦闘（格闘）",
    "キック": "近接戦闘（格闘）",
    "組み付き": "近接戦闘（格闘）",
    "こぶし（パンチ）": "近接戦闘（格闘）",
    "頭突き": "近接戦闘（格闘）",
    "マーシャルアーツ": "近接戦闘（格闘）",
    "拳銃": "射撃（拳銃）",
    "ショットガン": "射撃（ライフル／ショットガン）",
    "ライフル": "射撃（ライフル／ショットガン）",
    "運転": "運転（自動車）",
    "芸術": "芸術／製作",
    "製作": "芸術／製作",
    "他の言語": "ほかの言語",
    "化学": "科学",
    "生物学": "科学",
    "地質学": "科学",
    "天文学": "科学",
    "物理学": "科学",
    "薬学": "科学",
    "博物学": "自然",
}

# Character sheets only persist skills that received points or a custom base.
# These values mirror the skill cards used by the 6th/7th edition creation screens.
COC6_INITIAL_SKILL_VALUES = {
    "キック": 25,
    "組み付き": 25,
    "こぶし（パンチ）": 50,
    "頭突き": 10,
    "投擲": 25,
    "マーシャルアーツ": 1,
    "拳銃": 20,
    "サブマシンガン": 15,
    "ショットガン": 30,
    "マシンガン": 15,
    "ライフル": 25,
    "応急手当": 30,
    "鍵開け": 1,
    "隠す": 15,
    "隠れる": 10,
    "聞き耳": 25,
    "忍び歩き": 10,
    "写真術": 10,
    "精神分析": 1,
    "追跡": 10,
    "登攀": 40,
    "図書館": 25,
    "目星": 25,
    "運転": 20,
    "機械修理": 20,
    "重機械操作": 1,
    "乗馬": 5,
    "水泳": 25,
    "製作": 5,
    "操縦": 1,
    "跳躍": 25,
    "電気修理": 10,
    "ナビゲート": 10,
    "変装": 1,
    "言いくるめ": 5,
    "信用": 15,
    "説得": 15,
    "値切り": 5,
    "他の言語": 1,
    "医学": 5,
    "オカルト": 5,
    "化学": 1,
    "クトゥルフ神話": 0,
    "芸術": 5,
    "経理": 10,
    "考古学": 1,
    "コンピューター": 1,
    "心理学": 5,
    "人類学": 1,
    "生物学": 1,
    "地質学": 1,
    "電子工学": 1,
    "天文学": 1,
    "博物学": 10,
    "物理学": 1,
    "法律": 5,
    "薬学": 1,
    "歴史": 20,
}

COC7_INITIAL_SKILL_VALUES = {
    "近接戦闘（格闘）": 25,
    "投擲": 20,
    "射撃（拳銃）": 20,
    "射撃（ライフル／ショットガン）": 25,
    "応急手当": 30,
    "鍵開け": 1,
    "鑑定": 5,
    "隠密": 20,
    "聞き耳": 20,
    "精神分析": 1,
    "追跡": 10,
    "登攀": 20,
    "図書館": 20,
    "目星": 25,
    "手さばき": 10,
    "運転（自動車）": 20,
    "機械修理": 10,
    "重機械操作": 1,
    "乗馬": 5,
    "水泳": 20,
    "芸術／製作": 5,
    "操縦": 1,
    "跳躍": 20,
    "電気修理": 10,
    "電子工学": 1,
    "ナビゲート": 10,
    "サバイバル": 10,
    "変装": 5,
    "言いくるめ": 5,
    "魅惑": 15,
    "信用": 0,
    "説得": 10,
    "威圧": 15,
    "ほかの言語": 1,
    "医学": 1,
    "オカルト": 5,
    "科学": 1,
    "クトゥルフ神話": 0,
    "経理": 5,
    "考古学": 1,
    "コンピューター": 5,
    "心理学": 10,
    "人類学": 1,
    "自然": 10,
    "法律": 5,
    "歴史": 5,
}


def _clean_display_name(value):
    return " ".join(str(value or "").replace("\u3000", " ").split()).strip()


def _match_key(value):
    return unicodedata.normalize("NFKC", _clean_display_name(value)).casefold()


COC6_INITIAL_SKILL_VALUE_KEYS = {_match_key(name): value for name, value in COC6_INITIAL_SKILL_VALUES.items()}
COC7_INITIAL_SKILL_VALUE_KEYS = {_match_key(name): value for name, value in COC7_INITIAL_SKILL_VALUES.items()}


def _skill_parts(value):
    normalized = unicodedata.normalize("NFKC", _clean_display_name(value))
    match = SPECIALIZED_SKILL_RE.match(normalized)
    if not match:
        return normalized, None
    return match.group("base").strip(), match.group("specialization").strip() or None


def _alias_lookup(mapping, value):
    aliases = {_match_key(source): target for source, target in mapping.items()}
    return aliases.get(_match_key(value))


def _canonical_skill_name(value, edition):
    cleaned = _clean_display_name(value)
    if not cleaned:
        return ""

    alias = _alias_lookup(GENERAL_SKILL_ALIASES, cleaned)
    if alias:
        cleaned = alias

    if edition == "7th":
        alias = _alias_lookup(SEVENTH_EDITION_SKILL_ALIASES, cleaned)
        if alias:
            return alias

    base_name, specialization = _skill_parts(cleaned)
    base_alias = _alias_lookup(GENERAL_SKILL_ALIASES, base_name)
    if base_alias:
        base_name = base_alias
    if edition == "7th" and specialization:
        base_alias = _alias_lookup(SEVENTH_EDITION_SKILL_ALIASES, base_name)
        if base_alias:
            aliased_base, aliased_specialization = _skill_parts(base_alias)
            if not aliased_specialization:
                return f"{aliased_base}（{specialization}）"

    if specialization:
        return f"{base_name}（{specialization}）"
    return base_name


def _scenario_skill_rows(scenario):
    edition = "7th" if scenario.game_system == "coc7" else "6th"
    rows = []
    seen = set()
    for level, raw_value in (
        ("recommended", scenario.recommended_skills),
        ("semi_recommended", scenario.semi_recommended_skills),
    ):
        for token in SKILL_DELIMITER_RE.split(raw_value or ""):
            display_name = _clean_display_name(token)
            if not display_name:
                continue
            key = _match_key(_canonical_skill_name(display_name, edition))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "name": display_name,
                    "level": level,
                    "level_label": "推奨" if level == "recommended" else "準推奨",
                }
            )
    return rows


def _character_skills(character):
    prefetched = getattr(character, "_prefetched_objects_cache", {}).get("skills")
    if prefetched is not None:
        return sorted(prefetched, key=lambda skill: skill.id)
    return list(character.skills.order_by("id"))


def _stored_skill_matches(character, requested_name):
    edition = character.edition or "6th"
    requested_canonical = _canonical_skill_name(requested_name, edition)
    requested_base, requested_specialization = _skill_parts(requested_canonical)
    requested_key = _match_key(requested_canonical)
    requested_base_key = _match_key(requested_base)

    matches = []
    for skill in _character_skills(character):
        stored_canonical = _canonical_skill_name(skill.skill_name, edition)
        stored_base, _ = _skill_parts(stored_canonical)
        if requested_specialization:
            is_match = _match_key(stored_canonical) == requested_key
        else:
            is_match = _match_key(stored_base) == requested_base_key
        if is_match:
            matches.append(
                {
                    "name": skill.skill_name,
                    "value": skill.current_value,
                    "is_initial": False,
                }
            )
    return matches


def _initial_skill_match(character, requested_name):
    edition = character.edition or "6th"
    canonical = _canonical_skill_name(requested_name, edition)
    base_name, _ = _skill_parts(canonical)
    canonical_key = _match_key(canonical)
    base_key = _match_key(base_name)

    if edition == "7th":
        if base_key == _match_key("回避"):
            value = character.dex_value // 2
        elif base_key == _match_key("母国語"):
            value = character.edu_value
        else:
            value = COC7_INITIAL_SKILL_VALUE_KEYS.get(canonical_key)
            if value is None:
                value = COC7_INITIAL_SKILL_VALUE_KEYS.get(base_key)
    else:
        if base_key == _match_key("回避"):
            value = character.dex_value * 2
        elif base_key == _match_key("母国語"):
            value = character.edu_value * 5
        else:
            value = COC6_INITIAL_SKILL_VALUE_KEYS.get(canonical_key)
            if value is None:
                value = COC6_INITIAL_SKILL_VALUE_KEYS.get(base_key)

    if value is None:
        return None

    return {
        "name": requested_name,
        "value": value,
        "is_initial": True,
    }


def _should_show_match_names(character, requested_name, matches):
    if len(matches) > 1:
        return True
    if not matches or matches[0]["is_initial"]:
        return False

    requested_canonical = _canonical_skill_name(requested_name, character.edition or "6th")
    _, requested_specialization = _skill_parts(requested_canonical)
    matched_canonical = _canonical_skill_name(matches[0]["name"], character.edition or "6th")
    _, matched_specialization = _skill_parts(matched_canonical)
    return requested_specialization is None and matched_specialization is not None


def build_recommended_skill_comparison(scenario, participants):
    if not scenario:
        return None

    rows = _scenario_skill_rows(scenario)
    eligible_participants = [participant for participant in participants if participant.character_sheet_id]
    if not rows or not eligible_participants:
        return None

    characters = [
        {
            "participant_id": participant.id,
            "participant_name": participant.display_name,
            "character_id": participant.character_sheet_id,
            "character_name": participant.character_sheet.system_data.name,
        }
        for participant in eligible_participants
    ]

    for row in rows:
        cells = []
        for participant in eligible_participants:
            character = participant.character_sheet.system_data
            matches = _stored_skill_matches(character, row["name"])
            if not matches:
                initial_match = _initial_skill_match(character, row["name"])
                if initial_match:
                    matches = [initial_match]
            cells.append(
                {
                    "matches": matches,
                    "show_match_names": _should_show_match_names(character, row["name"], matches),
                }
            )
        row["cells"] = cells

    return {"characters": characters, "rows": rows}
