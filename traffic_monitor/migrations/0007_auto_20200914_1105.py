# Generated by Django 3.1.1 on 2020-09-14 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('traffic_monitor', '0006_monitor_class_colors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monitor',
            name='class_colors',
            field=models.JSONField(default=dict),
        ),
    ]