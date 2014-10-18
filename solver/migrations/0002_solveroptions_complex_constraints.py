# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='solveroptions',
            name='complex_constraints',
            field=models.CharField(default='', max_length=1000),
            preserve_default=False,
        ),
    ]
