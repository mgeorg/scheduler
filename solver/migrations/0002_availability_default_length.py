# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='availability',
            name='default_length',
            field=models.IntegerField(default=30),
            preserve_default=True,
        ),
    ]
