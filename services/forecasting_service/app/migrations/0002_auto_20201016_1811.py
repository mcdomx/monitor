# Generated by Django 3.1.2 on 2020-10-16 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
            ],
            options={
                'db_table': 'auth_group',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='AuthGroupPermissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'auth_group_permissions',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='AuthPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('codename', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'auth_permission',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='AuthUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('is_superuser', models.BooleanField()),
                ('username', models.CharField(max_length=150, unique=True)),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('email', models.CharField(max_length=254)),
                ('is_staff', models.BooleanField()),
                ('is_active', models.BooleanField()),
                ('date_joined', models.DateTimeField()),
            ],
            options={
                'db_table': 'auth_user',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='AuthUserGroups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'auth_user_groups',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='AuthUserUserPermissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'auth_user_user_permissions',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DjangoAdminLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_time', models.DateTimeField()),
                ('object_id', models.TextField(blank=True, null=True)),
                ('object_repr', models.CharField(max_length=200)),
                ('action_flag', models.SmallIntegerField()),
                ('change_message', models.TextField()),
            ],
            options={
                'db_table': 'django_admin_log',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DjangoContentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_label', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'django_content_type',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DjangoMigrations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('applied', models.DateTimeField()),
            ],
            options={
                'db_table': 'django_migrations',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DjangoSession',
            fields=[
                ('session_key', models.CharField(max_length=40, primary_key=True, serialize=False)),
                ('session_data', models.TextField()),
                ('expire_date', models.DateTimeField()),
            ],
            options={
                'db_table': 'django_session',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TrafficMonitorDetector',
            fields=[
                ('detector_id', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('model', models.CharField(max_length=64)),
            ],
            options={
                'db_table': 'traffic_monitor_detector',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TrafficMonitorFeed',
            fields=[
                ('cam', models.CharField(max_length=256, primary_key=True, serialize=False)),
                ('time_zone', models.CharField(max_length=32)),
                ('url', models.CharField(max_length=1024)),
                ('description', models.CharField(max_length=64)),
            ],
            options={
                'db_table': 'traffic_monitor_feed',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TrafficMonitorLogentry',
            fields=[
                ('key', models.BigAutoField(primary_key=True, serialize=False)),
                ('time_stamp', models.DateTimeField()),
                ('class_name', models.CharField(max_length=32)),
                ('count', models.FloatField()),
            ],
            options={
                'db_table': 'traffic_monitor_logentry',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TrafficMonitorMonitor',
            fields=[
                ('name', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('log_objects', models.JSONField()),
                ('notification_objects', models.JSONField()),
                ('charting_on', models.BooleanField()),
                ('logging_on', models.BooleanField()),
                ('notifications_on', models.BooleanField()),
                ('charting_objects', models.JSONField()),
                ('charting_time_horizon', models.CharField(max_length=8)),
                ('charting_time_zone', models.CharField(max_length=32)),
                ('class_colors', models.JSONField()),
                ('log_interval', models.IntegerField()),
                ('detector_sleep_throttle', models.IntegerField()),
                ('detector_confidence', models.FloatField()),
            ],
            options={
                'db_table': 'traffic_monitor_monitor',
                'managed': False,
            },
        ),
        migrations.DeleteModel(
            name='Feed',
        ),
    ]
