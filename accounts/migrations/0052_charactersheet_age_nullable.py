import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0051_charactersheet_occupation_point_method"),
    ]

    operations = [
        migrations.AlterField(
            model_name="charactersheet",
            name="age",
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(15),
                    django.core.validators.MaxValueValidator(90),
                ],
                verbose_name="年齢",
            ),
        ),
    ]
