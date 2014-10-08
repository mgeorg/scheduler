from django.conf.urls import patterns, url
from solver import views

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^constraints_(?P<constraints_id>\d+)/$', views.constraints, name='constraints'),
)

