from django.db import models

class Constraints(models.Model):
  creation_time = models.DateTimeField()
  deleted = models.BooleanField(default=False)
  csv_table_data = models.CharField(max_length=65535)

class SolverOptions(models.Model):
  arrive_late_bonus = models.IntegerField()
  leave_early_bonus = models.IntegerField()
  day_off_bonus = models.IntegerField()
  pupil_preference_penalty_list = models.CommaSeparatedIntegerField(
      max_length=100)
  instructor_preference_penalty_list = models.CommaSeparatedIntegerField(
      max_length=100)
  no_break_penalty = models.CharField(max_length=1000)

class SolverRun(models.Model):
  creation_time = models.DateTimeField()
  deleted = models.BooleanField(default=False)
  options = models.ForeignKey(SolverOptions)

  INITIALIZED = 'i'
  RUNNING = 'r'
  NO_SOLUTION = 'n'
  SOLUTION = 's'
  OPTIMAL = 'o'
  SOLVER_STATE_CHOICES = (
      (INITIALIZED, 'Solver Initialized'),
      (RUNNING, 'Solver Running'),
      (NO_SOLUTION, 'No Solution'),
      (SOLUTION, 'Solution Found'),
      (OPTIMAL, 'Optimal Solution Found'),
  )
  state = models.CharField(max_length=1, choices=SOLVER_STATE_CHOICES)

class Schedule(models.Model):
  creation_time = models.DateTimeField()
  deleted = models.BooleanField(default=False)
  score = models.IntegerField()
  schedule = models.CharField(max_length=65535)
  created_by = models.ForeignKey(SolverRun)

