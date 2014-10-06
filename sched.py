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

import collections
import csv
import os
import re
import select
import subprocess
import tempfile
import time


SlotTimeSpec = collections.namedtuple('SlotTimeSpec', 'day time length')

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
    self.restrictions = dict()
    self.restrictions_num = dict()

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
        elif row[0] == 'Instructor1':
          self.ParseAvailableRow(row)
        elif row[0] == 'Instructor1 Restrictions':
          self.ParseRestrictionsRow(row)
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
    self.slot_time = [None] * self.num_slots
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
        self.slot_time[slot-1] = SlotTimeSpec(
            self.slot_time[slot-1].day,
            self.slot_time[slot-1].time,
            last_lesson_length)
      self.slot_time[slot] = SlotTimeSpec(day, time, None)
      last_day_time = (day, time)

  def ParseAvailableRow(self, row):
    assert row[0] == 'Instructor1', 'The second row must start with \'Instructor1\'.'
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length.'
    assert len(self.pupil_slot_preference) == 0, 'The second row must be the instructors preferences.'

    self.pupil_name.append(row[0])
    self.pupil_num_lessons.append(None)
    self.pupil_lesson_length.append(None)
    self.ParsePreferenceRow(row)

  def ParsePupilRow(self, row):
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(self.pupil_slot_preference) > 0, 'The second row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length.'

    self.pupil_name.append(row[0])
    m = re.match(r'(.*)\[\s*(\d+)\s*min\s*\]\s*(.*)', row[0])
    if m:
      row[0] = m.group(1)+m.group(3)
      row[0] = row[0].strip()
      self.pupil_lesson_length.append(int(m.group(2)))
    else:
      self.pupil_lesson_length.append(30)
    m = re.match(r'(.*)\[\s*x\s*(\d+)\s*\]\s*(.*)', row[0])
    if m:
      row[0] = m.group(1)+m.group(3)
      row[0] = row[0].strip()
      self.pupil_num_lessons.append(int(m.group(2)))
    else:
      self.pupil_num_lessons.append(1)

    self.ParsePreferenceRow(row)

  def ParsePreferenceRow(self, row):
    self.num_pupils += 1
    self.pupil_slot_preference.append([0] * self.num_slots)
    for i in xrange(self.num_slots):
      if row[i+1].isdigit():
        self.pupil_slot_preference[-1][i] = int(row[i+1])

  def ParseRestrictionsRow(self, row):
    assert row[0] == 'Instructor1 Restrictions'
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length.'

    for slot in xrange(self.num_slots):
      row[slot+1] = row[slot+1].strip()
      if not row[slot+1]:
        continue
      for restriction_spec in row[slot+1].split(','):
        restriction_spec = restriction_spec.strip()
        m = re.match(r'^([^_]+)_(\d+)$', restriction_spec)
        assert m, 'Restrictions cell does not have proper format: ' + restriction_spec
        if m.group(1) in self.restrictions:
          self.restrictions[m.group(1)].append(slot)
          assert self.restrictions_num[m.group(1)] == int(m.group(2)), 'Number of slots to leave empty does not match'
        else:
          self.restrictions[m.group(1)] = [slot]
          self.restrictions_num[m.group(1)] = int(m.group(2))

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
          if self.slot_time[slot + offset].length:
            lesson_length_left -= self.slot_time[slot + offset].length
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
          i for i in xrange(self.num_slots) if self.slot_time[i].day == day]
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
      start_time = self.slot_time[self.slots_by_day[day][0]].time
      end_slot = self.slots_by_day[day][-1]
      assert (self.slot_time[end_slot].length == None or
              self.slot_time[end_slot].time + 
              self.slot_time[end_slot].length <= 24*60), (
              'The instructor is available for the last session of day ' +
              'with index %d, this is not allowed (add an extra session ' +
              'after the last of the day).') % day
      end_time = self.slot_time[end_slot].time + self.slot_time[end_slot].length
      self.day_range[day] = (start_time, end_time)


class Scheduler:
  def __init__(self, spec):
    self.spec = spec
    self.next_var = 1
    self.x_name = dict()
    self.our_name = dict()
    self.available = dict()
    self.constraints = []
    self.objective = []
    self.arrive_late_bonus = 310
    self.leave_early_bonus = 320
    self.day_off_bonus = 10000
    self.all_products = dict()
    self.max_product_size = 0
    self.preference_penalty = [0, 0, 100, 200, 400, 800]
    self.instructor_preference_penalty = [
        3*x+3 for x in self.preference_penalty]
    self.no_break_penalty = dict()
    for i in xrange(23*2):
      self.no_break_penalty[i*30+60] = (i+1)*2
    self.all_objectives = dict()

  def __str__(self):
    return ('self.x_name: ' + str(self.x_name) +
            '\nself.our_name: ' + str(self.our_name) +
            '\nself.constraints:\n' + '\n'.join(self.constraints) +
            '\n\n\nself.objective:\n' + '\n'.join(self.objective))

  def Prepare(self):
    self.MakeAvailabilityDict()
    self.MakeAllVariables()
    self.MakeRestrictionsConstraints()
    self.MakeSlotConstraints()
    self.MakePupilConstraints()
    self.MakePreferencePenalty()
    self.MakeArriveLateBonus()
    self.MakeLeaveEarlyBonus()
    self.MakeNoBreakPenalty()
    self.MakeDayOffBonus()

  def MakeVariable(self, var_name):
    x_name = 'x'+str(self.next_var)
    self.x_name[var_name] = x_name
    self.our_name[x_name] = var_name
    self.next_var += 1
    return x_name

  def MakeAllVariables(self):
    for pupil in xrange(self.spec.num_pupils):
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        if self.available[var_name]:
          self.MakeVariable(var_name)

  def MakeAvailabilityDict(self):
    # Each session only has 1 student.
    for slot in xrange(self.spec.num_slots):
      for pupil in xrange(self.spec.num_pupils):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        self.available[var_name] = (
            self.spec.pupil_slot_preference[pupil][slot] > 0 and
            self.spec.pupil_slot_preference[0][slot] > 0)

  def MakeSlotConstraints(self):
    """Each slot can only be filled once.

    Notice that a slot may be filled because an earlier slot was filled
    with a session which has gone past its end time.
    """
    # Each session needs an instructor and only has 1 student.
    for slot in xrange(self.spec.num_slots):
      x_names = []
      for pupil in xrange(1, self.spec.num_pupils):
        for pupil_slot in self.spec.slot_pupil_occlusion[slot][pupil]:
          # Consider all slots that would occlud this slot if we scheduled them.
          var_name = 'p'+str(pupil)+'s'+str(pupil_slot)
          if self.available[var_name]:
            x_names.append(self.x_name[var_name])
      if self.available['p0s'+str(slot)] and x_names:
        self.constraints.append('1 ' + self.x_name['p0s'+str(slot)] + ' -1 ' +
                                ' -1 '.join(x_names) + ' = 0;')

  def MakePupilConstraints(self):
    """Each pupil must have the correct number of sessions."""
    # Remember that pupil 0 is the instructor.
    for pupil in xrange(1, self.spec.num_pupils):
      x_names = []
      for slot in xrange(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        if self.available[var_name]:
          x_names.append(self.x_name[var_name])
      assert x_names, ('pupil ' + self.spec.pupil_name[pupil] +
                       ' has no available slots.')
      self.constraints.append('1 ' + ' +1 '.join(x_names) + ' = ' +
                              str(self.spec.pupil_num_lessons[pupil]) + ';')
      if self.spec.pupil_num_lessons[pupil] > 1:
        # Restrict multiple lessons to different days.
        for day in xrange(7):
          x_names = []
          for slot in self.spec.slots_by_day[day]:
            var_name = 'p'+str(pupil)+'s'+str(slot)
            if self.available[var_name]:
              x_names.append(self.x_name[var_name])
          if x_names:
            self.constraints.append('-1 ' + ' -1 '.join(x_names) + ' >= -1;')
                                   

  def MakeRestrictionsConstraints(self):
    for restriction_name, slots in self.spec.restrictions.iteritems():
      num = self.spec.restrictions_num[restriction_name]
      x_names = []
      for slot in slots:
        var_name = 'p0s'+str(slot)
        if not self.available[var_name]:
          num -= 1
          continue
        x = self.x_name[var_name]
        x_names.append(x)
      if x_names and num > 0:
        x_names.sort(key=lambda y: int(y[1:]))
        self.constraints.append(
            '1 ~' + ' +1 ~'.join(x_names) + ' >= ' + str(num) + ';')

  def MakePreferencePenalty(self):
    objective = list()
    self.all_objectives['preference'] = objective
    for pupil in xrange(self.spec.num_pupils):
      for slot in xrange(self.spec.num_slots):
        if self.spec.pupil_slot_preference[pupil][slot] > 1:
          var_name = 'p'+str(pupil)+'s'+str(slot)
          if not self.available[var_name]:
            continue
          x = self.x_name[var_name]
          if pupil == 0:
            penalty = (self.instructor_preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]] *
                self.spec.slot_time[slot].length)
          else:
            penalty = (self.preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]] *
                self.spec.slot_time[slot].length)
          objective.append(' +' + str(penalty) + ' ' + x)
    self.objective.extend(objective)

  def MakeArriveLateBonus(self):
    objective = list()
    self.all_objectives['arrive late'] = objective
    # Assign a bonus for every minute the instructor comes in late.
    for day in xrange(7):
      x_names = []
      for slot in self.spec.slots_by_day[day]:
        var_name = 'p0s'+str(slot)
        x = self.x_name[var_name]
        if self.available[var_name]:
          x_names.append(x)
          x_names.sort(key=lambda y: int(y[1:]))
        if x_names:
          product = '~' + ' ~'.join(x_names)
          if len(x_names) > 1:
            self.all_products[product] = 1
            self.max_product_size = max(self.max_product_size, len(x_names))
          # This bonus is only the additional bonus from the latest slot.
          bonus = self.arrive_late_bonus * self.spec.slot_time[slot].length
          bonus_str = str(-bonus)
          if bonus_str[0] != '-':
            bonus_str = '+' + bonus_str
          objective.append(bonus_str + ' ' + product)
    self.objective.extend(objective)

  def MakeLeaveEarlyBonus(self):
    objective = list()
    self.all_objectives['leave early'] = objective
    # Assign a bonus for every minute the instructor leaves early.
    # TODO(mgeorg) This isn't perfect, it assumes that the entire slot
    # is used, when a lesson might have just barely used some time up.
    for day in xrange(7):
      x_names = []
      for slot in reversed(self.spec.slots_by_day[day]):
        var_name = 'p0s'+str(slot)
        x = self.x_name[var_name]
        if self.available[var_name]:
          x_names.append(x)
          x_names.sort(key=lambda y: int(y[1:]))
        if x_names:
          product = '~' + ' ~'.join(x_names)
          if len(x_names) > 1:
            self.all_products[product] = 1
            self.max_product_size = max(self.max_product_size, len(x_names))
          # This bonus is only the additional bonus from the latest slot.
          bonus = self.leave_early_bonus * self.spec.slot_time[slot].length
          bonus_str = str(-bonus)
          if bonus_str[0] != '-':
            bonus_str = '+' + bonus_str
          objective.append(bonus_str + ' ' + product)
    self.objective.extend(objective)

  def MakeNoBreakPenalty(self):
    objective = list()
    self.all_objectives['no break'] = objective
    # Assign a penalty for every minute the instructor doesn't have a
    # break past some allowable threshold.
    for day in xrange(7):
      for no_break_penalty_tuple in sorted(self.no_break_penalty.items()):
        for slot_in_day_index in xrange(len(self.spec.slots_by_day[day])):
          slot = self.spec.slots_by_day[day][slot_in_day_index]
          start_time = self.spec.slot_time[slot].time
          var_name = 'p0s'+str(slot)
          if not self.available[var_name]:
            continue
          x_names = [self.x_name[var_name]]
          for end_slot in self.spec.slots_by_day[day][(slot_in_day_index+1):]:
            var_name = 'p0s'+str(end_slot)
            if not self.available[var_name]:
              break
            x = self.x_name[var_name]
            x_names.append(x)
            if (self.spec.slot_time[end_slot].time +
                self.spec.slot_time[end_slot].length -
                start_time > no_break_penalty_tuple[0]):
              # Notice that we use the entire length of the slot not just the
              # time in excess of the break penalty.  This is because for longer
              # runs of no break it gives the correct value.  It only gives
              # the incorrect value for the minimal no break run.  People
              # should use aligned slots anyway.
              penalty = (no_break_penalty_tuple[1] *
                         self.spec.slot_time[end_slot].length)
              x_names.sort(key=lambda y: int(y[1:]))
              product = ' '.join(x_names)
              if len(x_names) > 1:
                self.all_products[product] = 1
                self.max_product_size = max(self.max_product_size, len(x_names))
              objective.append('+' + str(penalty) + ' ' + product)
              break
    self.objective.extend(objective)

  def MakeDayOffBonus(self):
    """Assign a bonus for missing the entire day."""
    # Note that we don't allow double counting as both arriving late
    # and leaving early.  However, this bonus does stack with the larger
    # of the other two bonuses.

    objective = list()
    self.all_objectives['day off correction'] = objective
    for day in xrange(7):
      if not self.spec.slots_by_day[day]:
        continue
      workday_time = self.spec.day_range[day][1] - self.spec.day_range[day][0]
      arrive_late_bonus = self.arrive_late_bonus * workday_time
      leave_early_bonus = self.leave_early_bonus * workday_time
      # TODO(mgeorg) Put this bonus on the same scale as the other bonuses.
      bonus = self.day_off_bonus * workday_time - min(arrive_late_bonus, leave_early_bonus)

      x_names = []
      for slot in self.spec.slots_by_day[day]:
        var_name = 'p0s'+str(slot)
        if self.available[var_name]:
          x = self.x_name[var_name]
          x_names.append(x)

      if x_names:
        x_names.sort(key=lambda y: int(y[1:]))
        product = '~' + ' ~'.join(x_names)
        if len(x_names) > 1:
          self.all_products[product] = 1
          self.max_product_size = max(self.max_product_size, len(x_names))
        bonus_str = str(-bonus)
        if bonus_str[0] != '-':
          bonus_str = '+' + bonus_str
        objective.append(bonus_str + ' ' + product)
    self.objective.extend(objective)

  def WriteFile(self):
    self.header = (
        '* #variable= '+str(self.next_var - 1)+
        ' #constraint= '+str(len(self.constraints))+
        ' #product= '+str(len(self.all_products))+
        ' sizeproduct= '+str(self.max_product_size))
    (handle_int, self.opb_file) = tempfile.mkstemp()
    handle = os.fdopen(handle_int, 'w')
    handle.write(self.header + '\n')
    handle.write('min: ' + ' '.join(self.objective) + ';\n')
    handle.write('\n'.join(self.constraints) + '\n')
    handle.close()

  def Solve(self):
    self.WriteFile()
    time_limit = 5
    total_time_limit = 600
    print ('Solving with a time limit of ' + str(time_limit) +
           ' seconds of not improving the solution or a total time limit of ' +
           str(total_time_limit) + ' seconds')
    print self.header
    p = subprocess.Popen(
        ['clasp', '-t8', '--time-limit='+str(total_time_limit), self.opb_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    lines = []
    current_time = time.time()
    last_activity = current_time

    poll_obj = select.poll()
    poll_obj.register(p.stdout, select.POLLIN)   
    output = []
    chars = []
    while p.poll() == None and current_time - last_activity <= time_limit:
      if poll_obj.poll(0):
        last_activity = time.time()
        char = p.stdout.read(1)
        if char == '\n':
          output.append(''.join(chars) + '\n')
          print ''.join(chars)
          chars = []
        else:
          chars.append(char)
      else:
        time.sleep(.1)
      current_time = time.time()
    if chars:
      output.append(''.join(chars))
    if p.poll() == None:
      p.terminate()
    (remaining_output, unused_stderr) = p.communicate()
    print remaining_output
    output.append(remaining_output)
    self.solver_output = ''.join(output)
    self.ParseSolverOutput()

  def ParseSolverOutput(self):
    x_names = []
    for line in self.solver_output.splitlines():
      m = re.match('^v(?:\s+-?x\d+)+$', line)
      if m:
        curr_vars = line.split(' ')
        assert curr_vars[0] == 'v'
        x_names.extend(curr_vars[1:])

    self.x_solution = dict()
    var_names = []
    for x in x_names:
      m = re.match('^(-)?(x\d+)$', x)
      assert m
      if not m.group(1):
        self.x_solution[m.group(2)] = 1
        var_name = self.our_name[m.group(2)]
        var_names.append(var_name)

    print '\n'
    self.schedule = [None] * self.spec.num_slots
    self.busy = [None] * self.spec.num_slots
    pupil_schedule = dict()
    for var_name in var_names:
      m = re.match('^p(\d+)s(\d+)$', var_name)
      assert m
      pupil = int(m.group(1))
      slot = int(m.group(2))
      if pupil > 0:
        self.schedule[slot] = pupil
        if pupil not in pupil_schedule:
          pupil_schedule[pupil] = [self.spec.slot_name[slot]]
        else:
          pupil_schedule[pupil].append(self.spec.slot_name[slot])
      else:
        self.busy[slot] = True
    for pupil in xrange(1, self.spec.num_pupils):
      print (self.spec.pupil_name[pupil] + ' -- ' +
             ', '.join(pupil_schedule[pupil]))
    print '\n\n'
    for day in xrange(7):
      for slot in self.spec.slots_by_day[day]:
        pupil = self.schedule[slot]
        instructor_preference = str(self.spec.pupil_slot_preference[0][slot])
        extra = 'i' + instructor_preference + ' '
        if pupil:
          pupil_preference = str(self.spec.pupil_slot_preference[pupil][slot])
          extra += 'p' + pupil_preference + ' '
          print (extra + self.spec.slot_name[slot] + ' ' +
                 self.spec.pupil_name[pupil])
        else:
          extra += '   '
          if self.busy[slot]:
            print extra + self.spec.slot_name[slot] + ' ---Lesson Ongoing---'
          else:
            if self.spec.pupil_slot_preference[0][slot] > 0:
              print extra + self.spec.slot_name[slot]
            else:
              print extra + self.spec.slot_name[slot] + ' ***Busy***'
      print ''

  def EvaluateObjective(self, objective):
    total_penalty = 0
    for term in objective:
      m = re.match(r'^ *((?:-|\+)\d+)((?: +~?x\d+)+) *$', term)
      assert m, 'failed to parse: ' + term
      penalty = int(m.group(1))
      apply_penalty = True
      for x in m.group(2).split():
        x = x.strip()
        neg = False
        if x[0] == '~':
          neg = True
          x = x[1:]
        in_solution = x in self.x_solution
        if in_solution == neg:
          apply_penalty = False
          break
      if apply_penalty:
        total_penalty += penalty
    return total_penalty

  def EvaluateAllObjectives(self):
    total_penalty = 0
    for name, objective in self.all_objectives.iteritems():
      penalty = self.EvaluateObjective(objective)
      total_penalty += penalty
      print 'Penalty ' + str(penalty) + ' for term \"' + name + '\"'
    print 'Total Penalty ' + str(total_penalty)


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
s.EvaluateAllObjectives()
# TODO(mgeorg) Add automatic solution diversity based on changing
# the penalty terms, or removing certain days.
# TODO(mgeorg) make all the configuration information accessible.
