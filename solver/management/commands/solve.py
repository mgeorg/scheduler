import os
import csv
import time

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun, SolverRequest
import solver.solver
import scheduler.settings

class Command(BaseCommand):
  args = '<availability_id solver_options_id solver_run_id>'
  help = 'solves the given problem'

  def handle(self, *args, **options):
    first_sleep = True
    if scheduler.settings.PRODUCTION:
      os.setgid(33)
      os.setuid(33)
    while True:
      all_requests = SolverRequest.objects.order_by('creation_time')
      if not all_requests:
        if first_sleep:
          print('sleeping')
          first_sleep = False
        time.sleep(1)
        continue
      first_sleep = True

      availability = all_requests[0].availability
      solver_options = all_requests[0].solver_options
      solver_run = all_requests[0].solver_run

      print('Starting request ' + str(all_requests[0].id) +
            ' availability ' + str(availability.id) +
            ' solver_options ' + str(solver_options.id) +
            ' solver_run ' + str(solver_run.id))
     
      solver.solver.RunSolveOnObjects(availability, solver_options, solver_run)

      all_requests[0].delete()
