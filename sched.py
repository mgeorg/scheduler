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


class Constraints:
  def __init__(self):
    self.num_slots = 0
    self.slot_name = []
    self.pupil_name = []
    self.slot_time = []  # Tuples of (day #, minute in day).
    self.pupil_slot_preference = []  # pupil x slot with value 1,2,3.
                                     # pupil zero is the instructor.
    self.pupil_num_lessons = []  # The number of lessons this pupil has.
    self.pupil_lesson_length = []  # The length of the lesson in minutes.
    self.day_to_number = {'M' : 0, 'T' : 1, 'W' : 2, 'R' : 3,
                          'F' : 4, 'S' : 5, 'U' : 6}


  def ParseFile(self, file_name):
    with open(file_name, 'rb') as csvfile:
      sched_reader = csv.reader(csvfile)
      for row in sched_reader:
        if row[0] == 'Schedule':
          self.ParseTimeRow(row)
        elif row[0] == 'Available':
	  self.ParseAvailableRow(row)
        else:
	  # TODO(mgeorg) Add row for Lunch constraints.
	  # TODO(mgeorg) Add a row for complicated constraints.
	  self.ParsePupilRow(row)
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

  def ParseTimeRow(self, row):
    assert row[0] == 'Schedule', 'The first row must start with \'Schedule\'.'
    self.num_slots = len(row) - 1
    self.slot_name = ["INVALID"] * num_slots
    self.slot_time = [(0, 0)] * num_slots
    for i in xrange(self.num_slots):
      slot_name = row[i+1]
      self.slot_name[i] = slot_name
      m = re.match(r'([MTWRFSU])\s+(\d+):(\d+)', slot_name)
      assert m, 'Slot "%s" did not match required pattern' % slot_name
      day = self.day_to_number[m.group(1)], 
      time = int(m.group(2))*60+int(m.group(3))
      assert int(m.group(2)) >= 0, 'Specified hours was invalid.'
      assert int(m.group(2)) < 24, 'Specified hours was invalid.'
      assert int(m.group(3)) >= 0, 'Specified minutes was invalid.'
      assert int(m.group(3)) < 60, 'Specified minutes was invalid.'
      assert time >= 0, 'Specified time was negative.'
      assert time < 24*60, 'Specified time was larger than a day'
      # TODO(mgeorg) check non-decreasing day and increasing time.
      self.slot_time[i] = (day, time)

  def ParseAvailableRow(self, row):
    assert row[0] == 'Available', 'The second row must start with \'Available\'.'
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length.'
    assert len(self.pupil_slot_preference) == 0, 'The second row must be the instructors preferences.'

    self.pupil_slot_preferences.add([0] * self.num_slots)
    for i in xrange(self.num_slots):
      if row[i+1] in ["1", "2", "3"]:
        self.pupil_slot_preferences[0][i] = int(row[i+1])


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


  def MakeVariable(self, var_name):
    x_name = 'x'+str(self.next_var)
    self.x_name[var_name] = x_name
    self.our_name[x_name] = var_name
    self.next_var += 1

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

