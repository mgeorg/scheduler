# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Availability',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('deleted', models.BooleanField(default=False)),
                ('locked', models.BooleanField(default=False)),
                ('slot_times', models.TextField()),
                ('constraints', models.TextField()),
                ('csv_data', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('deleted', models.BooleanField(default=False)),
                ('score', models.IntegerField(null=True, blank=True)),
                ('schedule', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SolverOptions',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('arrive_late_bonus', models.IntegerField()),
                ('leave_early_bonus', models.IntegerField()),
                ('day_off_bonus', models.IntegerField()),
                ('no_break_penalty', models.CharField(max_length=100)),
                ('pupil_preference_penalty_list', models.CommaSeparatedIntegerField(max_length=100)),
                ('instructor_preference_penalty_list', models.CommaSeparatedIntegerField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SolverRequest',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('deleted', models.BooleanField(default=False)),
                ('availability', models.ForeignKey(to='solver.Availability')),
                ('solver_options', models.ForeignKey(to='solver.SolverOptions')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SolverRun',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('solver_version', models.CharField(max_length=10)),
                ('deleted', models.BooleanField(default=False)),
                ('score', models.IntegerField(null=True, blank=True)),
                ('scheduler_output', models.TextField()),
                ('solver_output', models.TextField()),
                ('state', models.CharField(max_length=1, choices=[('n', 'Solver Not Started'), ('q', 'Solver Problem Queued'), ('r', 'Solver Running'), ('d', 'Solver Done')])),
                ('solution', models.CharField(max_length=1, choices=[('n', 'No Solution Found'), ('i', 'Problem is Impossible'), ('s', 'Solution Found'), ('o', 'Optimal Solution Found')])),
                ('options', models.OneToOneField(to='solver.SolverOptions')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='solverrequest',
            name='solver_run',
            field=models.ForeignKey(to='solver.SolverRun'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='schedule',
            name='created_by',
            field=models.ForeignKey(to='solver.SolverRun'),
            preserve_default=True,
        ),
    ]
