from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0048_charactersheet_share_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='charactersheet',
            name='secret_ho_info',
            field=models.TextField(blank=True, default='', verbose_name='秘匿HO情報'),
        ),
        migrations.AddField(
            model_name='characterbackground',
            name='arcane_tomes_spells_artifacts',
            field=models.TextField(blank=True, default='', max_length=2000, verbose_name='魔道書・呪文・アーティファクト'),
        ),
        migrations.AddField(
            model_name='characterbackground',
            name='encounters_with_strange_entities',
            field=models.TextField(blank=True, default='', max_length=2000, verbose_name='遭遇した超自然の存在'),
        ),
    ]
