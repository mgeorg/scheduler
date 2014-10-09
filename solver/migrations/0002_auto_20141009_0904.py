# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solver', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='availability',
            name='csv_table_data',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='schedule',
            field=models.TextField(),
        ),
    ]
