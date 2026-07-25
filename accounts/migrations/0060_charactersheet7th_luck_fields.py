from django.db import migrations, models


def preserve_existing_7th_luck(apps, schema_editor):
    CharacterSheet7th = apps.get_model("accounts", "CharacterSheet7th")
    for character in CharacterSheet7th.objects.filter(luck_current=0).iterator():
        legacy_luck = character.pow_value or 0
        character.luck_starting = legacy_luck
        character.luck_current = legacy_luck
        character.luck_max = legacy_luck
        character.save(update_fields=["luck_starting", "luck_current", "luck_max"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0059_remove_legacy_character_related_tables")]

    operations = [
        migrations.AddField(
            model_name="charactersheet7th",
            name="luck_current",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="charactersheet7th",
            name="luck_max",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="charactersheet7th",
            name="luck_starting",
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(preserve_existing_7th_luck, migrations.RunPython.noop),
    ]
