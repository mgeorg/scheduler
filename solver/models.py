from django.db import models

class Availability(models.Model):
  creation_time = models.DateTimeField(auto_now_add=True)
  deleted = models.BooleanField(default=False)
  locked = models.BooleanField(default=False)
  slot_times = models.TextField()
  constraints = models.TextField()
  csv_data = models.TextField()

class SolverOptions(models.Model):
  arrive_late_bonus = models.IntegerField()
  leave_early_bonus = models.IntegerField()
  day_off_bonus = models.IntegerField()
  no_break_penalty = models.CharField(max_length=100)
  pupil_preference_penalty_list = models.CommaSeparatedIntegerField(
      max_length=100)
  instructor_preference_penalty_list = models.CommaSeparatedIntegerField(
      max_length=100)

  def __str__(self):
    return ('Arrive Late Bonus: ' + str(self.arrive_late_bonus) +
            '\nLeave Early Bonus: ' + str(self.leave_early_bonus) +
            '\nDay Off Bonus: ' + str(self.day_off_bonus) +
            '\nNo Break Penalty: ' + str(self.no_break_penalty) +
            '\nPupil Preference Penalties: ' + str(self.pupil_preference_penalty_list) +
            '\nInstructor Preference Penalties: ' + str(self.instructor_preference_penalty_list) +
            '')

class SolverRun(models.Model):
  creation_time = models.DateTimeField(auto_now_add=True)
  solver_version = models.CharField(max_length=10)
  deleted = models.BooleanField(default=False)
  options = models.OneToOneField(SolverOptions)
  score = models.IntegerField(null=True, blank=True)
  scheduler_output = models.TextField()
  solver_output = models.TextField()

  INITIALIZED = 'i'
  RUNNING = 'r'
  DONE = 'd'
  SOLVER_STATE_CHOICES = (
      (INITIALIZED, 'Solver Initialized'),
      (RUNNING, 'Solver Running'),
      (DONE, 'Solver Done'),
  )
  state = models.CharField(max_length=1, choices=SOLVER_STATE_CHOICES)

  NO_SOLUTION = 'n'
  IMPOSSIBLE = 'i'
  SOLUTION = 's'
  OPTIMAL = 'o'
  SOLUTION_CHOICES = (
      (NO_SOLUTION, 'No Solution Found'),
      (IMPOSSIBLE, 'Problem is Impossible'),
      (SOLUTION, 'Solution Found'),
      (OPTIMAL, 'Optimal Solution Found'),
  )
  solution = models.CharField(max_length=1, choices=SOLUTION_CHOICES)

class Schedule(models.Model):
  creation_time = models.DateTimeField(auto_now_add=True)
  deleted = models.BooleanField(default=False)
  score = models.IntegerField(null=True, blank=True)
  schedule = models.TextField()
  created_by = models.ForeignKey(SolverRun)

