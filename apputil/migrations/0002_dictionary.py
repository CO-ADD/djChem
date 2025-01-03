# Generated by Django 4.2.2 on 2024-12-18 06:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('apputil', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dictionary',
            fields=[
                ('astatus', models.IntegerField(db_index=True, default=0, editable=False, verbose_name='Status')),
                ('acreated_at', models.DateTimeField(editable=False, verbose_name='Created at')),
                ('aupdated_at', models.DateTimeField(editable=False, null=True, verbose_name='Updated at')),
                ('adeleted_at', models.DateTimeField(editable=False, null=True, verbose_name='Deleted at')),
                ('dict_value', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True, verbose_name='Value')),
                ('dict_class', models.CharField(max_length=30, verbose_name='Class')),
                ('dict_app', models.CharField(max_length=30, verbose_name='Application')),
                ('dict_desc', models.CharField(blank=True, max_length=140, verbose_name='Description')),
                ('dict_sort', models.IntegerField(default=0, verbose_name='Order')),
                ('acreated', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_acreated_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('adeleted', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_adeleted_by', to=settings.AUTH_USER_MODEL, verbose_name='Deleted by')),
                ('aupdated', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_aupdated_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'db_table': 'app_dictionary',
                'ordering': ['dict_class', 'dict_value'],
                'indexes': [models.Index(fields=['dict_class'], name='dict_class_idx')],
            },
        ),
    ]
