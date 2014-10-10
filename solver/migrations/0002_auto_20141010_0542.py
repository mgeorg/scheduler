# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solverrun',
            name='score',
            field=models.IntegerField(null=True),
        ),
    ]
