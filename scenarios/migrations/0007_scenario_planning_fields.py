from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scenarios", "0006_scenario_semi_recommended_handouts"),
    ]

    operations = [
        migrations.AddField(
            model_name="scenario",
            name="public_info",
            field=models.TextField(blank=True, default="", help_text="PL向け公開情報"),
        ),
        migrations.AddField(
            model_name="scenario",
            name="gm_notes",
            field=models.TextField(blank=True, default="", help_text="GM向け非公開メモ"),
        ),
        migrations.AddField(
            model_name="scenario",
            name="investigator_requirements",
            field=models.TextField(blank=True, default="", help_text="推奨探索者条件"),
        ),
        migrations.AddField(
            model_name="scenario",
            name="scenario_tags",
            field=models.CharField(blank=True, default="", help_text="タグ（カンマ区切り）", max_length=255),
        ),
        migrations.AddField(
            model_name="scenario",
            name="content_warnings",
            field=models.TextField(blank=True, default="", help_text="注意事項・地雷チェック"),
        ),
        migrations.AddField(
            model_name="scenario",
            name="setting_era",
            field=models.CharField(blank=True, default="", help_text="時代", max_length=100),
        ),
        migrations.AddField(
            model_name="scenario",
            name="setting_location",
            field=models.CharField(blank=True, default="", help_text="舞台・地域", max_length=100),
        ),
        migrations.AddField(
            model_name="scenario",
            name="scenario_style",
            field=models.CharField(blank=True, default="", help_text="形式（クローズド/シティ等）", max_length=100),
        ),
        migrations.AddField(
            model_name="scenario",
            name="lost_rate",
            field=models.CharField(blank=True, default="", help_text="ロスト率", max_length=50),
        ),
        migrations.AddField(
            model_name="scenario",
            name="combat_level",
            field=models.CharField(blank=True, default="", help_text="戦闘有無・頻度", max_length=50),
        ),
        migrations.AddField(
            model_name="scenario",
            name="pvp_level",
            field=models.CharField(blank=True, default="", help_text="PvP有無", max_length=50),
        ),
        migrations.AddField(
            model_name="scenario",
            name="min_players",
            field=models.PositiveIntegerField(blank=True, help_text="最小人数", null=True),
        ),
        migrations.AddField(
            model_name="scenario",
            name="max_players",
            field=models.PositiveIntegerField(blank=True, help_text="最大人数", null=True),
        ),
    ]
