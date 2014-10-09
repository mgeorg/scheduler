from django.contrib import admin
from solver.models import *

admin.site.site_header = 'Solver Admin'
admin.site.site_title = 'Solver'
admin.site.index_title = 'Solver Site Administration'

admin.site.register(Availability)
admin.site.register(SolverOptions)
admin.site.register(SolverRun)
admin.site.register(Schedule)
