# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0002_auto_20141010_0542'),
    ]

    operations = [
        migrations.AddField(
            model_name='solverrun',
            name='scheduler_output',
            field=models.TextField(default='No Output Available.'),
            preserve_default=False,
        ),
    ]
