from django.db import models

class Constraints:
  creation_time = models.DateTimeField()
  deleted = models.BooleanField()
  csv_table_data = models.CharField(max_length=65535, widget=models.Textarea)

class Schedule:
  creation_time = models.DateTimeField()
  deleted = models.BooleanField()
  score = models.IntegerField()
  schedule = models.CharField(max_length=65535, widget=models.Textarea)
  created_by = models.ForeignKey(SolverRun)

class SolverRun:
  creation_time = models.DateTimeField()
  deleted = models.BooleanField()
  options = models.ForeignKey(SolverOptions)
  state = models.ChoiceField(choices=[
      ('i','Initialized'),
      ('r','Running'),
      ('n','No Solution'),
      ('s','Solution'),
      ('o','Optimal')])

class SolverOptions:
  arrive_late_bonus = models.IntegerField()
  leave_early_bonus = models.IntegerField()
  day_off_bonus = models.IntegerField()
  preference_penalty_list = models.CommaSeparatedIntegerField(max_length=100)
  no_break_penalty = models.CharField(max_length=1000)

