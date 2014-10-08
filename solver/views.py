from django.shortcuts import render
from django.http import HttpResponse

def index(request):
  return HttpResponse("Hello, world.")

def constraints(request, constraints_id):
  return HttpResponse("You're looking at constraint problem %s." % constraints_id)
