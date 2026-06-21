from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0037_premiumauditlog_actor'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='charactersheet',
            name='access_scope',
            field=models.CharField(
                choices=[
                    ('private', 'Private'),
                    ('group', 'Group'),
                    ('public', 'Public'),
                ],
                default='group',
                max_length=10,
                verbose_name='Access scope',
            ),
        ),
        migrations.AddField(
            model_name='charactersheet',
            name='allowed_users',
            field=models.ManyToManyField(
                blank=True,
                related_name='readable_character_sheets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Allowed users',
            ),
        ),
    ]
