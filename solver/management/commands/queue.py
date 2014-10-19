import os
import csv
import time

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun
from solver import solver
from scheduler import settings

class Command(BaseCommand):
  args = '<availability_id solver_options_id>'
  help = 'solves the given problem'

  def handle(self, *args, **options):
    availability = Availability.objects.get(pk=int(args[0]))
    solver_options = SolverOptions.objects.get(pk=int(args[1]))

    solver_run = SolverRun()
    solver_run.solver_version = solver.version_number
    solver_run.options = solver_options
    solver_run.availability = availability
    solver_run.score = None
    solver_run.state = SolverRun.IN_QUEUE
    solver_run.solution = SolverRun.NO_SOLUTION
    solver_run.save()
