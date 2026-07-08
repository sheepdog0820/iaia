from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0050_remove_legacy_character_public_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="charactersheet",
            name="occupation_point_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "未指定"),
                    ("edu20", "EDU×20"),
                    ("edu10app10", "EDU×10＋APP×10"),
                    ("edu10dex10", "EDU×10＋DEX×10"),
                    ("edu10pow10", "EDU×10＋POW×10"),
                    ("edu10str10", "EDU×10＋STR×10"),
                    ("edu10con10", "EDU×10＋CON×10"),
                    ("edu10siz10", "EDU×10＋SIZ×10"),
                    ("edu4", "EDU×4"),
                    ("edu2app2", "EDU×2＋APP×2"),
                    ("edu2dex2", "EDU×2＋DEX×2"),
                    ("edu2pow2", "EDU×2＋POW×2"),
                    ("edu2str2", "EDU×2＋STR×2"),
                    ("edu2con2", "EDU×2＋CON×2"),
                    ("edu2siz2", "EDU×2＋SIZ×2"),
                ],
                default="",
                max_length=20,
                verbose_name="職業技能ポイント計算方式",
            ),
        ),
    ]
