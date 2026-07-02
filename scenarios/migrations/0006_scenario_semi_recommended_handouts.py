import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def migrate_legacy_coc_to_coc6(apps, schema_editor):
    Scenario = apps.get_model("scenarios", "Scenario")
    Scenario.objects.filter(game_system="coc").update(game_system="coc6")


def migrate_coc6_to_legacy_coc(apps, schema_editor):
    Scenario = apps.get_model("scenarios", "Scenario")
    Scenario.objects.filter(game_system="coc6").update(game_system="coc")


class Migration(migrations.Migration):

    dependencies = [
        ("scenarios", "0005_scenarioimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="scenario",
            name="semi_recommended_skills",
            field=models.TextField(blank=True, default="", help_text="準推奨技能（カンマ区切り）"),
        ),
        migrations.RunPython(migrate_legacy_coc_to_coc6, migrate_coc6_to_legacy_coc),
        migrations.AlterField(
            model_name="scenario",
            name="game_system",
            field=models.CharField(
                choices=[
                    ("coc6", "クトゥルフ神話TRPG 6版"),
                    ("coc7", "クトゥルフ神話TRPG 7版"),
                ],
                default="coc6",
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="ScenarioHandout",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("content", models.TextField(blank=True, default="")),
                ("recommended_skills", models.TextField(blank=True, default="")),
                ("is_secret", models.BooleanField(default=True)),
                (
                    "handout_number",
                    models.IntegerField(
                        blank=True, choices=[(1, "HO1"), (2, "HO2"), (3, "HO3"), (4, "HO4")], null=True
                    ),
                ),
                (
                    "assigned_player_slot",
                    models.IntegerField(
                        blank=True,
                        choices=[(1, "プレイヤー1"), (2, "プレイヤー2"), (3, "プレイヤー3"), (4, "プレイヤー4")],
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "scenario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="handout_templates",
                        to="scenarios.scenario",
                    ),
                ),
            ],
            options={
                "ordering": ["handout_number", "id"],
                "unique_together": {("scenario", "handout_number")},
            },
        ),
    ]
