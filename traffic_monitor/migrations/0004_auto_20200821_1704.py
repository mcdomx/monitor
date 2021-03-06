# Generated by Django 3.1 on 2020-08-21 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('traffic_monitor', '0003_auto_20200820_1240'),
    ]

    operations = [
        migrations.RenameField(
            model_name='logentry',
            old_name='class_id',
            new_name='class_name',
        ),
        migrations.AddField(
            model_name='monitor',
            name='charting_on',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='monitor',
            name='logging_on',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='notifications_on',
            field=models.BooleanField(default=False),
        ),
    ]
