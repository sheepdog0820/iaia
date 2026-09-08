from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0063_friend_requests")]

    operations = [
        migrations.AlterField(
            model_name=model_name,
            name="parent_data",
            field=models.ForeignKey(
                to=f"accounts.{model_name}",
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                related_name="versions",
            ),
        )
        for model_name in ("charactersheet6th", "charactersheet7th")
    ]
