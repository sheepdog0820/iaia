from django.db import migrations


def migrate_public_flag_to_access_scope(apps, schema_editor):
    CharacterSheet = apps.get_model("accounts", "CharacterSheet")
    CharacterSheet.objects.filter(is_public=True).exclude(access_scope="public").update(access_scope="public")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0049_character_secret_ho_background_pdf_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_public_flag_to_access_scope, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="charactersheet",
            name="is_public",
        ),
    ]
