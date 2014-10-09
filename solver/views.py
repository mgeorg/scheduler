import csv

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import RequestContext, loader

from solver.models import *

def index(request):
  return HttpResponse("Hello, world.")

def availability(request, availability_id):
  avail = get_object_or_404(Availability, pk=availability_id)
  parser = csv.reader(avail.csv_table_data.splitlines(True))
  table_data = []
  for row in parser:
    if not row:
      continue
    table_data.append([x.strip() for x in row])
  template = loader.get_template('solver/availability_detail.html')
  context = RequestContext(request, {
      'id': availability_id,
      'table_data': table_data,
      'availability': avail,
  })
  return HttpResponse(template.render(context))
