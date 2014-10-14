import os
import csv
import time

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun, SolverRequest
import solver.solver

class Command(BaseCommand):
  args = '<availability_id solver_options_id solver_run_id>'
  help = 'solves the given problem'

  def handle(self, *args, **options):
    os.setsid()
    os.setgid(33)
    os.setuid(33)
    while True:
      all_requests = SolverRequest.objects.order_by('creation_time')
      if not all_requests:
        time.sleep(1)
        print('sleeping')
        continue

      for request in all_requests:
        if request.solver_run.state != SolverRun.IN_QUEUE:
          request.solver_run.state = SolverRun.IN_QUEUE
          request.solver_run.save()

      availability = all_requests[0].availability
      solver_options = all_requests[0].solver_options
      solver_run = all_requests[0].solver_run

      print('Starting request ' + str(request.id) +
            ' availability ' + str(availability.id) +
            ' solver_options ' + str(solver_options.id) +
            ' solver_run ' + str(solver_run.id))
     
      # Run the solver on the data.
      parser = csv.reader(availability.csv_data.splitlines(True))
      table_data = []
      for row in parser:
        if not row:
          continue
        table_data.append([x.strip() for x in row])
     
      constraints = solver.solver.Constraints()
      constraints.ParseIterator(table_data)
     
      scheduler = solver.solver.Scheduler(constraints, solver_options, solver_run)
      scheduler.Prepare()
      schedule = scheduler.Solve()

      all_requests[0].delete()
