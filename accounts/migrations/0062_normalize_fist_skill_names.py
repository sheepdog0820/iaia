import re

from django.db import migrations

SIXTH_TARGET = "こぶし"
SEVENTH_TARGET = "近接戦闘"
OLD_FIST_NAMES = {"こぶし（パンチ）", "こぶし(パンチ)"}
OLD_SEVENTH_MELEE_NAMES = {"近接戦闘（格闘）", "近接戦闘(格闘)"}
SKILL_VALUE_FIELDS = (
    "base_value",
    "occupation_points",
    "interest_points",
    "bonus_points",
    "other_points",
)
SKILL_TEXT_DELIMITER_RE = re.compile(r"([\r\n,、，]+)")


def normalize_skill_list(values, aliases, target):
    if not isinstance(values, list):
        return values

    normalized = []
    for value in values:
        replacement = target if isinstance(value, str) and value.strip() in aliases else value
        if replacement not in normalized:
            normalized.append(replacement)
    return normalized


def normalize_skill_text(value, aliases, target):
    if not value:
        return value

    parts = SKILL_TEXT_DELIMITER_RE.split(value)
    for index in range(0, len(parts), 2):
        token = parts[index]
        stripped = token.strip()
        if stripped not in aliases:
            continue
        leading = token[: len(token) - len(token.lstrip())]
        trailing = token[len(token.rstrip()) :]
        parts[index] = f"{leading}{target}{trailing}"
    return "".join(parts)


def merge_skill_aliases(skill_model, aliases, target):
    candidate_names = set(aliases) | {target}
    sheet_ids = list(
        skill_model.objects.filter(skill_name__in=aliases).values_list("character_sheet_id", flat=True).distinct()
    )

    for sheet_id in sheet_ids:
        rows = list(
            skill_model.objects.filter(
                character_sheet_id=sheet_id,
                skill_name__in=candidate_names,
            ).order_by("id")
        )
        canonical = next((row for row in rows if row.skill_name == target), None)
        survivor = canonical or max(rows, key=lambda row: (row.current_value, -row.id))

        merged_values = {field: max(getattr(row, field) for row in rows) for field in SKILL_VALUE_FIELDS}
        if sum(merged_values.values()) > 999:
            winner = max(
                rows,
                key=lambda row: (
                    row.current_value,
                    sum(getattr(row, field) for field in SKILL_VALUE_FIELDS),
                    -row.id,
                ),
            )
            merged_values = {field: getattr(winner, field) for field in SKILL_VALUE_FIELDS}

        notes = []
        for row in rows:
            note = (row.notes or "").strip()
            if note and note not in notes:
                notes.append(note)

        categories = [
            row.category for row in rows if row.category and row.category not in {"その他・独自", "特殊・その他"}
        ]

        skill_model.objects.filter(pk__in=[row.pk for row in rows if row.pk != survivor.pk]).delete()
        survivor.skill_name = target
        for field, value in merged_values.items():
            setattr(survivor, field, value)
        survivor.current_value = sum(merged_values.values())
        if categories:
            survivor.category = categories[0]
        survivor.notes = "\n".join(notes)
        survivor.save(
            update_fields=[
                "skill_name",
                *SKILL_VALUE_FIELDS,
                "current_value",
                "category",
                "notes",
            ]
        )


def normalize_sheet_metadata(sheet_model, aliases, target):
    for sheet in sheet_model.objects.all().iterator():
        recommended = normalize_skill_list(sheet.recommended_skills, aliases, target)
        occupation = normalize_skill_list(sheet.occupation_skills, aliases, target)
        update_fields = []
        if recommended != sheet.recommended_skills:
            sheet.recommended_skills = recommended
            update_fields.append("recommended_skills")
        if occupation != sheet.occupation_skills:
            sheet.occupation_skills = occupation
            update_fields.append("occupation_skills")
        if update_fields:
            sheet.save(update_fields=update_fields)


def normalize_scenario_data(apps):
    Scenario = apps.get_model("scenarios", "Scenario")
    ScenarioRecommendedSkill = apps.get_model("scenarios", "ScenarioRecommendedSkill")
    ScenarioHandout = apps.get_model("scenarios", "ScenarioHandout")
    ScenarioHandoutRecommendedSkill = apps.get_model("scenarios", "ScenarioHandoutRecommendedSkill")

    for scenario in Scenario.objects.all().iterator():
        if scenario.game_system == "coc7":
            aliases = OLD_FIST_NAMES | OLD_SEVENTH_MELEE_NAMES | {SIXTH_TARGET}
            target = SEVENTH_TARGET
        else:
            aliases = OLD_FIST_NAMES
            target = SIXTH_TARGET

        recommended = normalize_skill_text(scenario.recommended_skills, aliases, target)
        semi_recommended = normalize_skill_text(scenario.semi_recommended_skills, aliases, target)
        update_fields = []
        if recommended != scenario.recommended_skills:
            scenario.recommended_skills = recommended
            update_fields.append("recommended_skills")
        if semi_recommended != scenario.semi_recommended_skills:
            scenario.semi_recommended_skills = semi_recommended
            update_fields.append("semi_recommended_skills")
        if update_fields:
            scenario.save(update_fields=update_fields)

        ScenarioRecommendedSkill.objects.filter(
            scenario_id=scenario.id,
            name__in=aliases,
        ).update(name=target)

        for handout in ScenarioHandout.objects.filter(scenario_id=scenario.id).iterator():
            recommended = normalize_skill_text(handout.recommended_skills, aliases, target)
            if recommended != handout.recommended_skills:
                handout.recommended_skills = recommended
                handout.save(update_fields=["recommended_skills"])
            ScenarioHandoutRecommendedSkill.objects.filter(
                handout_id=handout.id,
                name__in=aliases,
            ).update(name=target)


def count_old_sheet_metadata(sheet_model, aliases):
    remaining = 0
    for sheet in sheet_model.objects.all().iterator():
        for values in (sheet.recommended_skills, sheet.occupation_skills):
            if not isinstance(values, list):
                continue
            remaining += sum(1 for value in values if isinstance(value, str) and value.strip() in aliases)
    return remaining


def count_old_scenario_data(apps):
    Scenario = apps.get_model("scenarios", "Scenario")
    ScenarioRecommendedSkill = apps.get_model("scenarios", "ScenarioRecommendedSkill")
    ScenarioHandout = apps.get_model("scenarios", "ScenarioHandout")
    ScenarioHandoutRecommendedSkill = apps.get_model("scenarios", "ScenarioHandoutRecommendedSkill")

    remaining = 0
    for scenario in Scenario.objects.all().iterator():
        aliases = OLD_FIST_NAMES | (
            OLD_SEVENTH_MELEE_NAMES | {SIXTH_TARGET} if scenario.game_system == "coc7" else set()
        )
        for value in (scenario.recommended_skills, scenario.semi_recommended_skills):
            parts = SKILL_TEXT_DELIMITER_RE.split(value or "")
            remaining += sum(1 for token in parts[::2] if token.strip() in aliases)
        remaining += ScenarioRecommendedSkill.objects.filter(
            scenario_id=scenario.id,
            name__in=aliases,
        ).count()
        for handout in ScenarioHandout.objects.filter(scenario_id=scenario.id).iterator():
            parts = SKILL_TEXT_DELIMITER_RE.split(handout.recommended_skills or "")
            remaining += sum(1 for token in parts[::2] if token.strip() in aliases)
            remaining += ScenarioHandoutRecommendedSkill.objects.filter(
                handout_id=handout.id,
                name__in=aliases,
            ).count()
    return remaining


def normalize_fist_skill_names(apps, schema_editor):
    CharacterSkill6th = apps.get_model("accounts", "CharacterSkill6th")
    CharacterSkill7th = apps.get_model("accounts", "CharacterSkill7th")
    CharacterSheet6th = apps.get_model("accounts", "CharacterSheet6th")
    CharacterSheet7th = apps.get_model("accounts", "CharacterSheet7th")
    CharacterEquipment6th = apps.get_model("accounts", "CharacterEquipment6th")
    CharacterEquipment7th = apps.get_model("accounts", "CharacterEquipment7th")
    SkillGrowthRecord = apps.get_model("accounts", "SkillGrowthRecord")

    merge_skill_aliases(CharacterSkill6th, OLD_FIST_NAMES, SIXTH_TARGET)
    seventh_aliases = OLD_FIST_NAMES | OLD_SEVENTH_MELEE_NAMES | {SIXTH_TARGET}
    merge_skill_aliases(CharacterSkill7th, seventh_aliases, SEVENTH_TARGET)

    normalize_sheet_metadata(CharacterSheet6th, OLD_FIST_NAMES, SIXTH_TARGET)
    normalize_sheet_metadata(CharacterSheet7th, seventh_aliases, SEVENTH_TARGET)

    CharacterEquipment6th.objects.filter(skill_name__in=OLD_FIST_NAMES).update(skill_name=SIXTH_TARGET)
    CharacterEquipment7th.objects.filter(skill_name__in=seventh_aliases).update(skill_name=SEVENTH_TARGET)
    SkillGrowthRecord.objects.filter(
        growth_record__character_sheet__edition="6th",
        skill_name__in=OLD_FIST_NAMES,
    ).update(skill_name=SIXTH_TARGET)
    SkillGrowthRecord.objects.filter(
        growth_record__character_sheet__edition="7th",
        skill_name__in=seventh_aliases,
    ).update(skill_name=SEVENTH_TARGET)

    normalize_scenario_data(apps)

    remaining = {
        "6th_skills": CharacterSkill6th.objects.filter(skill_name__in=OLD_FIST_NAMES).count(),
        "7th_skills": CharacterSkill7th.objects.filter(skill_name__in=seventh_aliases).count(),
        "6th_equipment": CharacterEquipment6th.objects.filter(skill_name__in=OLD_FIST_NAMES).count(),
        "7th_equipment": CharacterEquipment7th.objects.filter(skill_name__in=seventh_aliases).count(),
        "6th_sheet_metadata": count_old_sheet_metadata(CharacterSheet6th, OLD_FIST_NAMES),
        "7th_sheet_metadata": count_old_sheet_metadata(CharacterSheet7th, seventh_aliases),
        "6th_growth_records": SkillGrowthRecord.objects.filter(
            growth_record__character_sheet__edition="6th",
            skill_name__in=OLD_FIST_NAMES,
        ).count(),
        "7th_growth_records": SkillGrowthRecord.objects.filter(
            growth_record__character_sheet__edition="7th",
            skill_name__in=seventh_aliases,
        ).count(),
        "scenario_data": count_old_scenario_data(apps),
    }
    if any(remaining.values()):
        raise RuntimeError(f"技能名の正規化後も旧表記が残っています: {remaining}")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0061_background_removal_jobs"),
        ("scenarios", "0010_scenario_share_token"),
    ]

    operations = [
        migrations.RunPython(normalize_fist_skill_names, migrations.RunPython.noop),
    ]
