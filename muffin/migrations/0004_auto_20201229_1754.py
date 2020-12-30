# Generated by Django 3.1.4 on 2020-12-29 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('muffin', '0003_auto_20201227_0440'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='article',
            name='text',
        ),
        migrations.AddField(
            model_name='article',
            name='num_words',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='feed',
            name='is_bozo',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='feed',
            name='title',
            field=models.CharField(db_index=True, max_length=64),
        ),
    ]
