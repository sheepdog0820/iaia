# Generated manually after all application paths were switched to edition-specific related models.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0058_minimize_character_sheet_registry"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="DROP TABLE IF EXISTS accounts_characterskill",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="DROP TABLE IF EXISTS accounts_characterequipment",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="DROP TABLE IF EXISTS accounts_characterimage",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(name="CharacterSkill"),
                migrations.DeleteModel(name="CharacterEquipment"),
                migrations.DeleteModel(name="CharacterImage"),
            ],
        ),
    ]
