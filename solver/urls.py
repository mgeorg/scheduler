from django.conf.urls import patterns, url
from solver import views

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^availability/(?P<availability_id>\d+)/$', views.availability, name='availability'),
  url(r'^run/(?P<pk>\d+)/$', views.SolverRunView.as_view(), name='solver_run')
)

