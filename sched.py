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
    self.slot_time = []  # Tuples of (day #, minute in day, length).
    self.pupil_slot_preference = []  # pupil x slot with value 1,2,3.
                                     # pupil zero is the instructor.
    self.pupil_num_lessons = []  # The number of lessons this pupil has.
    self.pupil_lesson_length = []  # The length of the lesson in minutes.
    self.pupil_slot_occlusion = []  # pupil x slot x slot it would fill.
    self.slot_pupil_occlusion = []  # slot x pupil x slot that if filled would occlud this slot.
    self.day_range = [(0, 24*60) for _ in xrange(7)]
    self.slots_by_day = [None] * 7
    self.day_to_number = {'M' : 0, 'T' : 1, 'W' : 2, 'R' : 3,
                          'F' : 4, 'S' : 5, 'U' : 6}

  def __str__(self):
    return ('self.slot_name: ' + str(self.slot_name) +
            '\nself.pupil_name: ' + str(self.pupil_name) +
            '\nself.slot_time: ' + str(self.slot_time) +
            '\nself.pupil_slot_preference: ' + str(self.pupil_slot_preference) +
            '\nself.pupil_num_lessons: ' + str(self.pupil_num_lessons) +
            '\nself.pupil_lesson_length: ' + str(self.pupil_lesson_length) +
            '\nself.pupil_slot_occlusion: ' + str(self.pupil_slot_occlusion) +
            '\nself.slot_pupil_occlusion: ' + str(self.slot_pupil_occlusion) +
            '\nself.day_range: ' + str(self.day_range) +
            '\nself.slots_by_day: ' + str(self.slots_by_day))

  def ParseFile(self, file_name):
    with open(file_name, 'rb') as csvfile:
      sched_reader = csv.reader(csvfile)
      for row in sched_reader:
        row = [x.strip() for x in row]
        if row[0] == 'Schedule':
          self.ParseTimeRow(row)
        elif row[0] == 'Available':
          self.ParseAvailableRow(row)
        else:
          # TODO(mgeorg) Add row for Lunch constraints.
          # TODO(mgeorg) Add a row for complicated constraints.
          self.ParsePupilRow(row)
    self.DetermineSlotOcclusion()
    self.DetermineDayStartEndTimes()

  def ParseTimeRow(self, row):
    assert row[0] == 'Schedule', 'The first row must start with \'Schedule\'.'
    self.num_slots = len(row) - 1
    self.slot_name = [None] * self.num_slots
    self.slot_time = [(None, None, None)] * self.num_slots
    last_day_time = None
    for slot in xrange(self.num_slots):
      slot_name = row[slot+1]
      self.slot_name[slot] = slot_name
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
      if last_day_time:
        last_lesson_length = (day * 24 * 60 + time) - (
            last_day_time[0] * 24 * 60 + last_day_time[1])
        assert last_lesson_length > 0, (
                'The time slots are not in increasing order.')
        self.slot_time[slot-1] = (self.slot_time[slot-1][0],
                               self.slot_time[slot-1][1],
                               last_lesson_length)
      self.slot_time[slot] = (day, time, None)
      last_day_time = (day, time)

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
    if len(self.pupil_lesson_length) == 5:
      # TODO(mgeorg) This if statement is here just for testing.
      self.pupil_lesson_length.append(60)
    self.ParsePreferenceRow(row)

  def ParsePreferenceRow(self, row):
    self.num_pupils += 1
    self.pupil_slot_preference.append([0] * self.num_slots)
    for i in xrange(self.num_slots):
      if row[i+1].isdigit():
        self.pupil_slot_preference[-1][i] = int(row[i+1])

  def DetermineSlotOcclusion(self):
    self.pupil_slot_occlusion = [[None] * self.num_slots for _ in xrange(self.num_pupils)]
    self.pupil_slot_occlusion[0] = None
    for pupil in xrange(1, self.num_pupils):
      for slot in xrange(self.num_slots):
        lesson_length_left = self.pupil_lesson_length[pupil]
        offset = 0
        slots = []
        while lesson_length_left > 0:
          slots.append(slot + offset)
          if self.slot_time[slot + offset][2]:
            lesson_length_left -= self.slot_time[slot + offset][2]
          else:
            lesson_length_left = 0
          offset += 1
        self.pupil_slot_occlusion[pupil][slot] = slots
    self.slot_pupil_occlusion = [[None] * self.num_pupils for _ in xrange(self.num_slots)]
    for pupil in xrange(1, self.num_pupils):
      for slot in xrange(self.num_slots):
        for occlud in self.pupil_slot_occlusion[pupil][slot]:
          if self.slot_pupil_occlusion[occlud][pupil]:
            self.slot_pupil_occlusion[occlud][pupil].append(slot)
          else:
            self.slot_pupil_occlusion[occlud][pupil] = [slot]

  def DetermineDayStartEndTimes(self):
    """Determine the start and end times of each workday.
    
    Each work day is defined as starting with the first slot that the
    instructor is available for and ending with the last slot that the
    instructor is available for.  We assert that the instructor is not
    available for a slot which spans midnight.
    """
    for day in xrange(7):
      self.slots_by_day[day] = [
          i for i in xrange(self.num_slots) if self.slot_time[i][0] == day]
      while (self.slots_by_day[day] and
             self.pupil_slot_preference[0][self.slots_by_day[day][0]] <= 0):
        # The instructor isn't available for the first slot.
        del self.slots_by_day[day][0]
      while (self.slots_by_day[day] and
             self.pupil_slot_preference[0][self.slots_by_day[day][-1]] <= 0):
        # The instructor isn't available for the last slot.
        del self.slots_by_day[day][-1]
      if not self.slots_by_day[day]:
        continue
      start_time = self.slot_time[self.slots_by_day[day][0]][1]
      end_slot = self.slots_by_day[day][-1]
      assert (self.slot_time[end_slot][2] == None or
              self.slot_time[end_slot][1] + 
              self.slot_time[end_slot][2] <= 24*60), (
              'The instructor is available for the last session of day ' +
              'with index %d, this is not allowed (add an extra session ' +
              'after the last of the day).') % day
      end_time = self.slot_time[end_slot][1] + self.slot_time[end_slot][2]
      self.day_range[day] = (start_time, end_time)


class Scheduler:
  def __init__(self, spec):
    self.spec = spec
    self.next_var = 1
    self.x_name = dict()
    self.our_name = dict()
    self.constraints = []
    self.objective = []
    self.arrive_late_bonus = 6
    self.leave_early_bonus = 10
    self.day_off_bonus = 10000
    self.all_products = dict()
    self.max_product_size = 0
    self.preference_penalty = [0, 0, 5, 10, 20, 40]
    self.instructor_preference_penalty = [3*x+1 for x in self.preference_penalty]

  def __str__(self):
    return ('self.x_name: ' + str(self.x_name) +
            '\nself.our_name: ' + str(self.our_name) +
            '\nself.constraints:\n' + '\n'.join(self.constraints) +
            '\n\n\nself.objective:\n' + '\n'.join(self.objective))

  def Prepare(self):
    self.MakeAllVariables()
    self.MakeAvailabilityConstraints()
    self.MakeSlotConstraints()
    self.MakePupilConstraints()
    self.MakePreferencePenalty()
    self.MakeArriveLateBonus()
    self.MakeLeaveEarlyBonus()
    self.MakeDayOffBonus()

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
    for pupil in xrange(self.spec.num_pupils):
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        self.MakeVariable(var_name)

  def MakeAvailabilityConstraints(self):
    # Each session only has 1 student.
    for slot in xrange(self.spec.num_slots):
      for pupil in xrange(self.spec.num_pupils):
        if self.spec.pupil_slot_preference[pupil][slot] <= 0:
          var_name = 'p'+str(pupil)+'s'+str(slot)
          self.constraints.append('1 ' + self.x_name[var_name] + ' = 0;')

  def MakeSlotConstraints(self):
    """Each slot can only be filled once.
    
    Notice that a slot may be filled because an earlier slot was filled
    with a session which has gone past its end time.
    """
    # Each session only has 1 student.
    for slot in xrange(self.spec.num_slots):
      x_names = []
      for pupil in xrange(1, self.spec.num_pupils):
        for pupil_slot in self.spec.slot_pupil_occlusion[slot][pupil]:
          # Consider all slots that would occlud this slot if we scheduled them.
          var_name = 'p'+str(pupil)+'s'+str(pupil_slot)
          x_names.append(self.x_name[var_name])
      self.constraints.append('1 ' + self.x_name['s'+str(slot)] + ' -1 ' +
                              ' -1 '.join(x_names) + ' = 0;')
      self.constraints.append('1 ' + self.x_name['p0s'+str(slot)] + ' -1 ' +
                              self.x_name['s'+str(slot)] + ' >= 0;')

  def MakePupilConstraints(self):
    """Each pupil must have the correct number of sessions."""
    # Remember that pupil 0 is the instructor.
    for pupil in xrange(1, self.spec.num_pupils):
      x_names = []
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        x_names.append(self.x_name[var_name])
      self.constraints.append('1 ' + ' +1 '.join(x_names) + ' = ' +
                              str(self.spec.pupil_num_lessons[pupil]) + ';')

  def MakePreferencePenalty(self):
    for pupil in xrange(self.spec.num_pupils):
      for slot in xrange(self.spec.num_slots):
        if self.spec.pupil_slot_preference[pupil][slot] > 1:
          var_name = 'p'+str(pupil)+'s'+str(slot)
          x = self.x_name[var_name]
          if pupil == 0:
            penalty = self.instructor_preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]]
          else:
            penalty = self.preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]]
          self.objective.append(' +' + str(penalty) + ' ' + x)

  def MakeArriveLateBonus(self):
    # Assign a bonus for every minute the instructor comes in late.
    for day in xrange(7):
      x_names = []
      for slot in self.spec.slots_by_day[day]:
        if self.spec.slot_time[slot][1] < self.spec.day_range[day][0]:
          # Before end time.
          continue
        if self.spec.slot_time[slot][1] >= self.spec.day_range[day][1]:
          # After end time.
          continue
        var_name = 's'+str(slot)
        x = self.x_name[var_name]
        x_names.append(x)
        x_names.sort()
        product = '~' + ' ~'.join(x_names)
        self.all_products[product] = 1
        self.max_product_size = max(self.max_product_size, len(x_names))
        # This bonus is only the additional bonus from the latest slot.
        bonus = self.arrive_late_bonus * self.spec.slot_time[slot][2]
        self.objective.append(str(-bonus) + ' ' + product)

  def MakeLeaveEarlyBonus(self):
    # Assign a bonus for every minute the instructor leaves early.
    # TODO(mgeorg) This isn't perfect, it assumes that the entire slot
    # is used, when a lesson might have just barely used some time up.
    for day in xrange(7):
      x_names = []
      for slot in reversed(self.spec.slots_by_day[day]):
        if self.spec.slot_time[slot][1] < self.spec.day_range[day][0]:
          # Before end time.
          continue
        if self.spec.slot_time[slot][1] >= self.spec.day_range[day][1]:
          # After end time.
          continue
        var_name = 's'+str(slot)
        x = self.x_name[var_name]
        x_names.append(x)
        x_names.sort()
        product = '~' + ' ~'.join(x_names)
        self.all_products[product] = 1
        self.max_product_size = max(self.max_product_size, len(x_names))
        # This bonus is only the additional bonus from the latest slot.
        bonus = self.leave_early_bonus * self.spec.slot_time[slot][2]
        self.objective.append(str(-bonus) + ' ' + product)

  def MakeDayOffBonus(self):
    """Assign a bonus for missing the entire day."""
    # Note that we don't allow double counting as both arriving late
    # and leaving early.  However, this bonus does stack with the larger
    # of the other two bonuses.

    for day in xrange(7):
      if not self.spec.slots_by_day[day]:
        continue
      workday_time = self.spec.day_range[day][1] - self.spec.day_range[day][0]
      arrive_late_bonus = self.arrive_late_bonus * workday_time
      leave_early_bonus = self.leave_early_bonus * workday_time
      # TODO(mgeorg) Put this bonus on the same scale as the other bonuses.
      bonus = self.day_off_bonus - min(arrive_late_bonus, leave_early_bonus)
        
      x_names = []
      for slot in self.spec.slots_by_day[day]:
        var_name = 's'+str(slot)
        x = self.x_name[var_name]
        x_names.append(x)

      x_names.sort()
      product = '~' + ' ~'.join(x_names)
      self.all_products[product] = 1
      self.max_product_size = max(self.max_product_size, len(x_names))
      self.objective.append(str(-bonus) + ' ' + product)

  def WriteFile(self):
    header = (
        '* #variable= '+str(self.next_var - 1)+
        ' #constraint= '+str(len(self.constraints))+
        ' #product= '+str(len(self.all_products))+
        ' sizeproduct= '+str(self.max_product_size))
    (handle_int, self.opb_file) = tempfile.mkstemp()
    print self.opb_file
    handle = os.fdopen(handle_int, 'w')
    handle.write(header + '\n')
    handle.write('min: ' + ' '.join(self.objective) + ';\n')
    handle.write('\n'.join(self.constraints) + '\n')
    handle.close()


  def Solve(self):
    self.WriteFile()
    p = subprocess.Popen(['clasp', self.opb_file], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    (self.solver_output, unused_stderr) = p.communicate()
    print self.solver_output
    self.ParseSolverOutput()


  def ParseSolverOutput(self):
    x_names = []
    for line in self.solver_output.splitlines():
      m = re.match('v(?:\s+-?x\d+)*', line)
      if m:
        curr_vars = line.split(' ')
        assert curr_vars[0] == 'v'
        x_names.extend(curr_vars[1:])
  
    # print ' '.join(vars)

    var_names = []
    for x in x_names:
      m = re.match('(-)?(x\d+)', x)
      assert m
      if not m.group(1):
        var_name = self.our_name[m.group(2)]
        var_names.append(var_name)

    print ' '.join(var_names)
    
    print '\n\n'
    self.schedule = [None] * self.spec.num_slots
    self.busy = [None] * self.spec.num_slots
    for var_name in var_names:
      m = re.match('p(\d+)s(\d+)', var_name)
      if m:
        pupil = int(m.group(1))
        slot = int(m.group(2))
        if pupil > 0:
          self.schedule[slot] = pupil
          print self.spec.pupil_name[pupil] + ' ' + self.spec.slot_name[slot]
      m = re.match('s(\d+)', var_name)
      if m:
        slot = int(m.group(1))
        self.busy[slot] = True
    print '\n\n'
    for slot in xrange(self.spec.num_slots):
      pupil = self.schedule[slot]
      if pupil:
        print self.spec.slot_name[slot] + ' ' + self.spec.pupil_name[pupil]
      else:
        if self.busy[slot]:
          print self.spec.slot_name[slot] + ' ---Lesson Ongoing---'
        else:
          if self.spec.pupil_slot_preference[0][slot] > 0:
            print self.spec.slot_name[slot]
          else:
            print self.spec.slot_name[slot] + ' ***Busy***'
      


c = Constraints()
c.ParseFile(r'sched.csv')
print str(c)
print "###############################"
print "###############################"
print "###############################"

s = Scheduler(c)
s.Prepare()
print str(s)
s.Solve()

