import os
import csv
import time

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun
from solver import solver
from scheduler import settings

class Command(BaseCommand):
  args = '<availability_id solver_options_id solver_run_id>'
  help = 'solves the given problem'

  def handle(self, *args, **options):
    first_sleep = True
    if settings.PRODUCTION:
      os.setgid(33)
      os.setuid(33)
    while True:
      all_requests = SolverRun.objects.filter(
          state=SolverRun.IN_QUEUE).order_by('creation_time')
      if not all_requests:
        if first_sleep:
          print('sleeping')
          first_sleep = False
        time.sleep(1)
        continue
      first_sleep = True

      solver_run = all_requests[0]

      print('Starting run ' + str(solver_run.id) +
            ' availability ' + str(solver_run.availability.id) +
            ' solver_options ' + str(solver_run.options.id))
     
      solver.ExecuteSolverRun(solver_run)
