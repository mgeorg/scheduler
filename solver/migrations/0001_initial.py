# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Constraints',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
                ('csv_table_data', models.CharField(max_length=65535)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
                ('score', models.IntegerField()),
                ('schedule', models.CharField(max_length=65535)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SolverOptions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('arrive_late_bonus', models.IntegerField()),
                ('leave_early_bonus', models.IntegerField()),
                ('day_off_bonus', models.IntegerField()),
                ('pupil_preference_penalty_list', models.CommaSeparatedIntegerField(max_length=100)),
                ('instructor_preference_penalty_list', models.CommaSeparatedIntegerField(max_length=100)),
                ('no_break_penalty', models.CharField(max_length=1000)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SolverRun',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
                ('state', models.CharField(max_length=1, choices=[('i', 'Solver Initialized'), ('r', 'Solver Running'), ('n', 'No Solution'), ('s', 'Solution Found'), ('o', 'Optimal Solution Found')])),
                ('options', models.ForeignKey(to='solver.SolverOptions')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='schedule',
            name='created_by',
            field=models.ForeignKey(to='solver.SolverRun'),
            preserve_default=True,
        ),
    ]
