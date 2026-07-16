from django.db import migrations

COC6_ONLY_BASIC_SKILL_NAMES = {
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
COC7_ONLY_BASIC_SKILL_NAMES = {
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


def remove_cross_edition_basic_skills(apps, schema_editor):
    CharacterSkill = apps.get_model("accounts", "CharacterSkill")
    CharacterSkill.objects.filter(character_sheet__edition="7th", skill_name__in=COC6_ONLY_BASIC_SKILL_NAMES).delete()
    CharacterSkill.objects.filter(character_sheet__edition="6th", skill_name__in=COC7_ONLY_BASIC_SKILL_NAMES).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0053_charactersheet_name_kana")]
    operations = [migrations.RunPython(remove_cross_edition_basic_skills, migrations.RunPython.noop)]
