import ast
import csv

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.views import generic
from django.core.urlresolvers import reverse

from solver.models import *
import solver.solver

class SolverRunView(generic.DetailView):
  model = SolverRun
  template_name = 'solver/solver_run_detail.html'

class ScheduleView(generic.DetailView):
  model = Schedule

def index(request):
  all_availability = Availability.objects.all()
  all_solver_options = SolverOptions.objects.all()
  all_solver_run = SolverRun.objects.all()
  all_schedule = Schedule.objects.all()
  template = loader.get_template('solver/index.html')
  context = RequestContext(request, {
      'all_availability': all_availability,
      'all_solver_options': all_solver_options,
      'all_solver_run': all_solver_run,
      'all_schedule': all_schedule,
  })
  return HttpResponse(template.render(context))

def availability_initial(request):
  template = loader.get_template('solver/availability_initial.html')
  context = RequestContext(request, {})
  return HttpResponse(template.render(context))

def new_availability(request):
  availability = Availability()
  availability.csv_data = request.POST['csv_data']
  availability.save()

  return HttpResponseRedirect(reverse('solver:availability',
                                      args=(availability.id,)))

def availability(request, availability_id):
  availability = get_object_or_404(Availability, pk=availability_id)
  parser = csv.reader(availability.csv_data.splitlines(True))
  table_data = []
  for row in parser:
    if not row:
      continue
    table_data.append([x.strip() for x in row])
  template = loader.get_template('solver/availability_detail.html')
  context = RequestContext(request, {
      'table_data': table_data,
      'availability': availability,
  })
  return HttpResponse(template.render(context))

def start_run(request):
  availability = Availability()
  solver_options = SolverOptions()

  availability.csv_data = request.POST['csv_data']

  solver_options.arrive_late_bonus = request.POST['arrive_late_bonus']
  solver_options.leave_early_bonus = request.POST['leave_early_bonus']
  solver_options.day_off_bonus = request.POST['day_off_bonus']
  solver_options.no_break_penalty = ast.literal_eval(
      request.POST['no_break_penalty'])
  solver_options.pupil_preference_penalty_list = request.POST['pupil_preference_penalty']
  solver_options.instructor_preference_penalty_list = request.POST['instructor_preference_penalty']

  availability.save()
  solver_options.save()

  solver_run = SolverRun()
  solver_run.solver_version = solver.solver.Scheduler.version
  solver_run.options = solver_options
  solver_run.score = None
  solver_run.state = SolverRun.INITIALIZED
  solver_run.solution = SolverRun.NO_SOLUTION
  solver_run.save()

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
    return HttpResponseRedirect(reverse('solver:schedule', args=(schedule.id,)))
  # TODO(mgeorg) Redirect immediately and have the run page ajax the
  # run information as it is being generated.
  return HttpResponseRedirect(reverse('solver:run', args=(solver_run.id,)))

