from django.conf.urls import patterns, include, url
from django.contrib import admin

import solver.views

urlpatterns = patterns('',
    url(r'^$', solver.views.home, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^solver/', include('solver.urls', namespace='solver')),
)
