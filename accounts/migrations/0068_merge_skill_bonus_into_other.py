"""Consolidate adjustments without changing any stored skill total."""

from django.db import migrations, models


def merge_bonus_into_other(apps, schema_editor):
    for model_name in ("CharacterSkill6th", "CharacterSkill7th"):
        skill_model = apps.get_model("accounts", model_name)
        skill_model.objects.using(schema_editor.connection.alias).exclude(bonus_points=0).update(
            other_points=models.F("other_points") + models.F("bonus_points"),
            bonus_points=0,
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0067_billing_email_delivery")]

    # The old application also accepts other_points. On rollback, retain the
    # consolidated adjustments rather than guessing their original split.
    operations = [migrations.RunPython(merge_bonus_into_other, migrations.RunPython.noop)]
