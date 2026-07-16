"""Remove character-specific columns from the registry table permanently."""

from django.db import migrations


LEGACY_CHARACTER_FIELDS = [
    "age",
    "app_value",
    "birthplace",
    "ccfolia_character_id",
    "ccfolia_sync_enabled",
    "character_image",
    "con_value",
    "dex_value",
    "edu_value",
    "gender",
    "hit_points_current",
    "hit_points_max",
    "int_value",
    "is_active",
    "magic_points_current",
    "magic_points_max",
    "name",
    "name_kana",
    "notes",
    "occupation",
    "occupation_multiplier",
    "occupation_point_method",
    "occupation_skills",
    "parent_sheet",
    "player_name",
    "pow_value",
    "recommended_skills",
    "residence",
    "sanity_current",
    "sanity_max",
    "sanity_starting",
    "secret_ho_info",
    "session_count",
    "siz_value",
    "source_scenario",
    "source_scenario_game_system",
    "source_scenario_title",
    "status",
    "str_value",
    "version",
    "version_note",
]


class Migration(migrations.Migration):
    dependencies = [("accounts", "0057_move_registry_metadata_to_system_data")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    [
                        "DROP INDEX IF EXISTS accounts_charactersheet_parent_sheet_id_33a094b8",
                        "DROP INDEX IF EXISTS accounts_charactersheet_source_scenario_id_907c2455",
                    ] + [
                        "ALTER TABLE accounts_charactersheet DROP COLUMN "
                        + {"parent_sheet": "parent_sheet_id", "source_scenario": "source_scenario_id"}.get(field, field)
                        for field in LEGACY_CHARACTER_FIELDS
                    ],
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name="charactersheet", name="age"),
                migrations.RemoveField(model_name="charactersheet", name="app_value"),
                migrations.RemoveField(model_name="charactersheet", name="birthplace"),
                migrations.RemoveField(model_name="charactersheet", name="ccfolia_character_id"),
                migrations.RemoveField(model_name="charactersheet", name="ccfolia_sync_enabled"),
                migrations.RemoveField(model_name="charactersheet", name="character_image"),
                migrations.RemoveField(model_name="charactersheet", name="con_value"),
                migrations.RemoveField(model_name="charactersheet", name="dex_value"),
                migrations.RemoveField(model_name="charactersheet", name="edu_value"),
                migrations.RemoveField(model_name="charactersheet", name="gender"),
                migrations.RemoveField(model_name="charactersheet", name="hit_points_current"),
                migrations.RemoveField(model_name="charactersheet", name="hit_points_max"),
                migrations.RemoveField(model_name="charactersheet", name="int_value"),
                migrations.RemoveField(model_name="charactersheet", name="is_active"),
                migrations.RemoveField(model_name="charactersheet", name="magic_points_current"),
                migrations.RemoveField(model_name="charactersheet", name="magic_points_max"),
                migrations.RemoveField(model_name="charactersheet", name="name"),
                migrations.RemoveField(model_name="charactersheet", name="name_kana"),
                migrations.RemoveField(model_name="charactersheet", name="notes"),
                migrations.RemoveField(model_name="charactersheet", name="occupation"),
                migrations.RemoveField(model_name="charactersheet", name="occupation_multiplier"),
                migrations.RemoveField(model_name="charactersheet", name="occupation_point_method"),
                migrations.RemoveField(model_name="charactersheet", name="occupation_skills"),
                migrations.RemoveField(model_name="charactersheet", name="parent_sheet"),
                migrations.RemoveField(model_name="charactersheet", name="player_name"),
                migrations.RemoveField(model_name="charactersheet", name="pow_value"),
                migrations.RemoveField(model_name="charactersheet", name="recommended_skills"),
                migrations.RemoveField(model_name="charactersheet", name="residence"),
                migrations.RemoveField(model_name="charactersheet", name="sanity_current"),
                migrations.RemoveField(model_name="charactersheet", name="sanity_max"),
                migrations.RemoveField(model_name="charactersheet", name="sanity_starting"),
                migrations.RemoveField(model_name="charactersheet", name="secret_ho_info"),
                migrations.RemoveField(model_name="charactersheet", name="session_count"),
                migrations.RemoveField(model_name="charactersheet", name="siz_value"),
                migrations.RemoveField(model_name="charactersheet", name="source_scenario"),
                migrations.RemoveField(model_name="charactersheet", name="source_scenario_game_system"),
                migrations.RemoveField(model_name="charactersheet", name="source_scenario_title"),
                migrations.RemoveField(model_name="charactersheet", name="status"),
                migrations.RemoveField(model_name="charactersheet", name="str_value"),
                migrations.RemoveField(model_name="charactersheet", name="version"),
                migrations.RemoveField(model_name="charactersheet", name="version_note"),
            ],
        ),
    ]
