# Generated by Django 3.0.6 on 2020-05-26 15:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('traffic_monitor', '0010_feed_time_zone'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('key', models.BigAutoField(primary_key=True, serialize=False)),
                ('time_stamp', models.DateTimeField()),
                ('class_id', models.CharField(max_length=32)),
                ('count', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Monitor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detector', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detector_log', to='traffic_monitor.Detector')),
            ],
        ),
        migrations.RenameField(
            model_name='feed',
            old_name='id',
            new_name='cam',
        ),
        migrations.DeleteModel(
            name='Log',
        ),
        migrations.AddField(
            model_name='monitor',
            name='feed',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='feed_log', to='traffic_monitor.Feed'),
        ),
        migrations.AddField(
            model_name='logentry',
            name='monitor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='monitor_log', to='traffic_monitor.Monitor'),
        ),
    ]
