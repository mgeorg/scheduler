# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='availability',
            old_name='csv_table_data',
            new_name='csv_data',
        ),
        migrations.AddField(
            model_name='availability',
            name='constraints',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='availability',
            name='locked',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='availability',
            name='slot_times',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='solveroptions',
            name='no_break_penalty',
            field=models.CharField(max_length=100),
        ),
    ]
