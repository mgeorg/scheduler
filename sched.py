#!/usr/bin/python
#
# Author: Manfred Georg <manfred.georg@gmail.com>
#
# LEGAL WARNING: Manfred Georg is an employee of Google, Inc.
#                The copyright ownership of this piece of code has
#                has not been evaluated by a Google lawyer yet.
#
# You may not use this code.  You do not have a license to use this
# code.

import re
import os
import csv
import subprocess
import tempfile


class Scheduler:
  def __init__(self):
    self.next_var = 1
    self.slot_day = []
    self.slot_time = []
    self.day_slot = dict()
    self.variables = dict()
    self.reverse_variables = dict()
    self.constraints = []
    self.num_students = 0


  def ParseTimeRow(self, row):
    assert row[0] == 'Schedule', 'The first row must start with \'Schedule\'.'
    for i in xrange(len(row)-1):
      slot = row[i+1]
      m = re.match(r'(\S+)\s+(\d+):(\d+)', slot)
      assert m, 'Slot did not match pattern'
      day = m.group(1)
      time = m.group(2)*60+m.group(3)
      self.slot_day[i] = day
      self.day_slot[day].append(i)
      self.slot_time[i] = time


  def ParseFile(self, file_name):
    with open(file_name, 'rb') as csvfile:
      sched_reader = csv.reader(csvfile)
      for row in sched_reader:
        if row[0] == 'Schedule':
          self.ParseTimeRow(row)
        elif row[0] == 'Available':
          assert len(self.slot_day), 'The first row must start with \'Schedule\''
          assert len(row)-1 == len(self.slot_day), 'All rows must be of the same length.'
          for i in xrange(len(row)-1):
            var_name = 't'+str(i)
            x_name = 'x'+str(self.next_var)
            self.variables[var_name] = x_name
            self.reverse_variables[x_name] = var_name
            self.next_var += 1
            if row[i+1] != 'y':
              self.constraints.append('1 '+x_name+' = 0;')
        else:
          assert len(self.slot_day), 'The first two rows were not formatted correctly.'
          assert len(row)-1 == len(self.slot_day), 'All rows must be of the same length.'
          for i in xrange(len(row)-1):
            var_name = 's'+str(self.num_students)+'t'+str(i)
            x_name = 'x'+str(self.next_var)
            self.variables[var_name] = x_name
            self.reverse_variables[x_name] = var_name
            self.next_var += 1
            if row[i+1] != 'y':
              self.constraints.append('1 '+x_name+' = 0;')
          self.num_students += 1


  # TODO(mgeorg) Make this function set all the constraints based on local variables.  Hold full data for each slot and each student within the class.
  def MakeConstraints(self):
    # Each student only has 1 class.
    # TODO(mgeorg) Add timed constraints.
    for i in xrange(self.num_students):
      x_names = []
      for t in xrange(len(sched_row)-1):
        var_name = 's'+str(i)+'t'+str(t)
        x_name = variables[var_name]
        x_names.append(x_name)
      self.constraints.append('1 ' + ' +1 '.join(x_names) + ' = 1;')
    
    # Each session only has 1 student.
    for t in xrange(len(sched_row)-1):
      x_names = []
      for i in xrange(self.num_students):
        var_name = 's'+str(i)+'t'+str(t)
        x_name = variables[var_name]
        x_names.append(x_name)
      self.constraints.append('1 ' + variables['t'+str(t)] + ' -1 ' +
                              ' -1 '.join(x_names) + ' = 0;')


  def MakeObjective(self):
    all_products = dict()
    objective = []
    vars = []
    for t in xrange(len(sched_row)-1):
      var_name = 't'+str(t)
      x_name = variables[var_name]
      vars.append(x_name)
      vars.sort()
      product = '~' + ' ~'.join(vars)
      all_products[product] = 1
      objective.append(' ' + str(-100-10*(t)) + ' ' + product)

    vars = []
    for t in xrange(len(sched_row)-1):
      var_name = 't'+str(len(sched_row)-2-t)
      x_name = variables[var_name]
      vars.append(x_name)
      vars.sort()
      product = '~' + ' ~'.join(vars)
      all_products[product] = 1
      objective.append(' ' + str(-150-15*(t)) + ' ' + product)


  def MakeHeader(self):
    self.header = (
        '* #variable= '+str(max_var-1)+' #constraint= '+str(len(constraints))+
        ' #product= '+str(len(all_products))+
        ' sizeproduct= '+str(len(sched_row)-1))
    

  def WriteFile(self):
    (handle_int, self.opb_file) = tempfile.mkstemp()
    print self.opb_file
    handle = os.fdopen(handle_int, 'w')
    handle.write(self.header + '\n')
    handle.write('min: ' + ''.join(objective) + ';\n')
    handle.write('\n'.join(constraints) + '\n')
    handle.close()


  def RunSolver(self):
    p = subprocess.Popen(['clasp', file_name], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    (self.solver_output, unused_stderr) = p.communicate()
    print self.solver_output


  def ParseSolverOutput(self):
    vars = []
    for line in stdout.splitlines():
      m = re.match('v(?:\s+-?x\d+)*', line)
      if m:
        curr_vars = line.split(' ')
        assert curr_vars[0] == 'v'
        vars.extend(curr_vars[1:])
  
    # print ' '.join(vars)

    xs = []
    for v in vars:
      m = re.match('(-)?(x\d+)', v)
      assert m
      if not m.group(1):
        x = reverse_variables[m.group(2)]
        xs.append(x)

    print ' '.join(xs)


s = Scheduler()
s.ParseFile(r'sched.csv')
s.MakeConstraints()
s.MakeObjective()
s.MakeHeader()
s.WriteFile()
s.RunSolver()
s.ParseSolverOutput()

