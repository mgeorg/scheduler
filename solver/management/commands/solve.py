import csv

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun
import solver.solver

class Command(BaseCommand):
  args = '<availability_id solver_options_id solver_run_id>'
  help = 'solves the given problem'

  def handle(self, *args, **options):
    availability_id = int(args[0])
    solver_options_id = int(args[1])
    solver_run_id = int(args[2])
   
    availability = Availability.objects.get(pk=availability_id)
    solver_options = SolverOptions.objects.get(pk=solver_options_id)
    solver_run = SolverRun.objects.get(pk=solver_run_id)
   
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

    if schedule:
      self.stdout.write(str(schedule))
