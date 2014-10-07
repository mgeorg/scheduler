from django.shortcuts import render

class Constraints:
  creation_time = forms.DateTimeField()
  deleted = models.BooleanField()
  csv_table_data = forms.CharField(widget=forms.Textarea)

class Schedule:
  creation_time = forms.DateTimeField()
  deleted = models.BooleanField()
  score = models.IntegerField()
  schedule = models.BinaryField()
  created_by = models.ForeignKey(SolverRun)

class SolverRun:
  creation_time = forms.DateTimeField()
  deleted = models.BooleanField()
  options = models.ForeignKey(SolverOptions)
  state = forms.CharField()

class SolverOptions:
