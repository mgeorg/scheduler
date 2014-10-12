from django.conf.urls import patterns, url
from solver import views

urlpatterns = patterns('',
  url(r'^index/$', views.index, name='index'),
  url(r'^$', views.availability_initial, name='availability_initial'),
  url(r'^availability/(?P<availability_id>\d+)/$', views.availability, name='availability'),
  url(r'^run/(?P<pk>\d+)/$', views.SolverRunView.as_view(), name='solver_run'),
  url(r'^start/$', views.start_run, name='start_run'),
  url(r'^schedule/(?P<pk>\d+)/$', views.ScheduleView.as_view(), name='schedule'),
)

