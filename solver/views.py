from django.shortcuts import render
from django.http import HttpResponse

def index(request):
  return HttpResponse("Hello, world.")

def availability(request, availability_id):
  return HttpResponse("You're looking at availability problem %s." % availability_id)
