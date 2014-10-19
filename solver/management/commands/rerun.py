import os
import csv
import time

from django.core.management.base import BaseCommand, CommandError
from solver.models import Availability, SolverOptions, SolverRun
from solver import solver
from scheduler import settings

class Command(BaseCommand):
  args = '<solver_run_id>'
  help = 'resolve the given problem'

  def handle(self, *args, **options):
    original_solver_run = SolverRun.objects.get(pk=int(args[0]))

    solver_run = SolverRun()
    solver_run.solver_version = solver.version_number
    solver_run.options = original_solver_run.options
    solver_run.availability = original_solver_run.availability
    solver_run.score = None
    solver_run.state = SolverRun.IN_QUEUE
    solver_run.solution = SolverRun.NO_SOLUTION
    solver_run.save()
