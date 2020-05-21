# Generated by Django 3.0.6 on 2020-05-19 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Class',
            fields=[
                ('class_name', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('detector_name', models.CharField(max_length=64)),
                ('monitor', models.BooleanField(default=True)),
                ('log', models.BooleanField(default=True)),
            ],
        ),
    ]
