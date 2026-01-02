from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_charactersheet_source_scenario'),
    ]

    operations = [
        migrations.AddField(
            model_name='characterdicerollsetting',
            name='character_sheet',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='character_dice_roll_settings',
                to='accounts.charactersheet',
            ),
        ),
    ]
