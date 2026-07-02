import uuid

from django.db import migrations, models


def populate_character_share_tokens(apps, schema_editor):
    CharacterSheet = apps.get_model("accounts", "CharacterSheet")
    for character in CharacterSheet.objects.filter(share_token__isnull=True).only("id"):
        CharacterSheet.objects.filter(pk=character.pk).update(share_token=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0047_alter_charactersheet_access_scope_sharelink"),
    ]

    operations = [
        migrations.AddField(
            model_name="charactersheet",
            name="share_token",
            field=models.UUIDField(blank=True, db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_character_share_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="charactersheet",
            name="share_token",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
