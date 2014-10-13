# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0002_auto_20141012_2142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='solverrun',
            name='score',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
