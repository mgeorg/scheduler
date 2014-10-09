from django.conf.urls import patterns, url
from solver import views

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^availability/(?P<availability_id>\d+)/$', views.availability, name='availability'),
)

