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
    self.num_pupils = 0
    self.slot_name = []
    self.pupil_name = []
    self.slot_time = []  # Tuples of (day #, minute in day).
    self.pupil_slot_preference = []  # pupil x slot with value 1,2,3.
                                     # pupil zero is the instructor.
    self.pupil_num_lessons = []  # The number of lessons this pupil has.
    self.pupil_lesson_length = []  # The length of the lesson in minutes.
    self.day_to_number = {'M' : 0, 'T' : 1, 'W' : 2, 'R' : 3,
                          'F' : 4, 'S' : 5, 'U' : 6}

  def __str__(self):
    return ('self.slot_name: ' + str(self.slot_name) +
            '\nself.pupil_name: ' + str(self.pupil_name) +
            '\nself.slot_time: ' + str(self.slot_time) +
            '\nself.pupil_slot_preference: ' + str(self.pupil_slot_preference) +
            '\nself.pupil_num_lessons: ' + str(self.pupil_num_lessons) +
            '\nself.pupil_lesson_length: ' + str(self.pupil_lesson_length))

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

  def ParseTimeRow(self, row):
    assert row[0] == 'Schedule', 'The first row must start with \'Schedule\'.'
    self.num_slots = len(row) - 1
    self.slot_name = [None] * self.num_slots
    self.slot_time = [(0, 0)] * self.num_slots
    for i in xrange(self.num_slots):
      slot_name = row[i+1]
      self.slot_name[i] = slot_name
      m = re.match(r'^\s*([MTWRFSU])\s+(\d+):(\d+)$', slot_name)
      assert m, 'Slot "%s" did not match required pattern' % slot_name
      day = self.day_to_number[m.group(1)]
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

    self.pupil_name.append("Instructor")
    self.pupil_num_lessons.append(None)
    self.pupil_lesson_length.append(None)
    self.ParsePreferenceRow(row)

  def ParsePupilRow(self, row):
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(self.pupil_slot_preference) > 0, 'The second row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length.'

    # TODO(mgeorg) Allow the user to specify multiple lessons and lesson length.
    self.pupil_name.append(row[0])
    self.pupil_num_lessons.append(1)
    self.pupil_lesson_length.append(30)
    self.ParsePreferenceRow(row)

  def ParsePreferenceRow(self, row):
    self.num_pupils += 1
    self.pupil_slot_preference.append([0] * self.num_slots)
    for i in xrange(self.num_slots):
      if row[i+1] in ["1", "2", "3"]:
        self.pupil_slot_preference[-1][i] = int(row[i+1])


class Scheduler:
  def __init__(self, spec):
    self.spec = spec
    self.next_var = 1
    self.x_name = dict()
    self.our_name = dict()
    self.constraints = []

  def MakeVariable(self, var_name):
    x_name = 'x'+str(self.next_var)
    self.x_name[var_name] = x_name
    self.our_name[x_name] = var_name
    self.next_var += 1
    return x_name

  def MakeAllVariables(self):
    for slot in xrange(self.spec.num_slots):
      var_name = 's'+str(slot)
      self.MakeVariable(var_name)
    for pupil in xrange(self.num_pupils):
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        self.MakeVariable(var_name)

  def MakeSlotConstraints(self):
    """Each slot can only be filled once.
    
    Notice that a slot may be filled because an earlier slot was filled
    with a session which has gone past its end time.
    """
    # Each session only has 1 student.
    for slot in xrange(self.spec.num_slots):
      x_names = []
      for pupil in xrange(self.num_pupil):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        x_names.append(self.x_name[var_name])
	# TODO(mgeorg) Also include slots that if filled would spill over into
	# this time.
      self.constraints.append('1 ' + self.x_name['s'+str(t)] + ' -1 ' +
                              ' -1 '.join(x_names) + ' = 0;')

  def MakePupilConstraints(self):
    """Each pupil must have the correct number of lessons."""
    # Remember that pupil 0 is the instructor.
    for pupil in xrange(1, self.num_pupils):
      x_names = []
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        x_names.append(x_name[var_name])
      self.constraints.append('1 ' + ' +1 '.join(x_names) + ' = ' +
                              str(self.spec.pupil_num_lessons[pupil]) + ';')
    

  def MakeObjective(self):
    all_products = dict()
    objective = []
    x_names = []
    # Assign a bonus for every minute the instructor comes in late.
    # TODO(mgeorg) Determine how many minutes from the start of each day
    # each slot is.
    for slot in xrange(self.spec.num_slots):
      var_name = 's'+str(slot)
      x = self.x_name[var_name]
      x_names.append(x)
      x_names.sort()
      product = '~' + ' ~'.join(x_names)
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


c = Constraints()
c.ParseFile(r'sched.csv')
print str(c)

# s = Scheduler()
# s.ParseFile(r'sched.csv')
# s.MakeConstraints()
# s.MakeObjective()
# s.MakeHeader()
# s.WriteFile()
# s.RunSolver()
# s.ParseSolverOutput()

