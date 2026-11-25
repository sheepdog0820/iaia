from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="CreationReceipt",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("object_id", models.PositiveBigIntegerField(null=True)),
            ],
        ),
    ]
