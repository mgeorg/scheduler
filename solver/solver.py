#!/usr/bin/python3
# Copyright (c) 2014 Manfred Georg
#
# Author: Manfred Georg <manfred.georg@gmail.com>
#
# This file is part of session-scheduler.
#
# session-scheduler is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# session-scheduler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with session-scheduler.  If not, see <http://www.gnu.org/licenses/>.

import ast
import collections
import csv
import logging
import os
import re
import select
import subprocess
import sys
import tempfile
import time

from solver.models import *

version_number = 'v0.5'

logger = logging.getLogger(__name__)
SlotTimeSpec = collections.namedtuple('SlotTimeSpec', 'day time length')

def ValFromXVar(var_str):
  m = re.match(r'^\s*~?x(\d+)\s*$', var_str)
  assert m
  return int(m.group(1))


kTimeStringReString = r'\d+\s*:\s*\d+\s*(?:am|pm)?'
kTimeStringReCapture = r'(\d+)\s*:\s*(\d+)\s*(am|pm)?'


def TimeStringToMinInDay(string):
  m = re.match(r'^\s*'+kTimeStringReCapture+r'\s*$', string.lower())
  assert m
  minutes = int(m.group(1)) * 60 + int(m.group(2))
  if m.group(3) == 'pm':
    minutes += 12*60
  return minutes


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
    self.day_range = [(0, 24*60) for _ in range(7)]
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
    with open(file_name, newline='') as csvfile:
      return ParseIterator(csv.reader(csvfile))

  def ParseIterator(self, sched_reader):
    for row in sched_reader:
      if not row:
        continue
      row = [x.strip() for x in row]
      if row[0] == 'Schedule':
        self.ParseTimeRow(row)
      elif row[0] == 'Instructor1':
        self.ParseAvailableRow(row)
      elif row[0] == 'Instructor1 Restrictions':
        self.ParseRestrictionsRow(row)
      else:
        self.ParsePupilRow(row)
    self.DetermineDayStartEndTimes()
    self.DetermineSlotOcclusion()

  def ParseTimeRow(self, row):
    assert row[0] == 'Schedule', 'The first row must start with \'Schedule\'.'
    self.num_slots = len(row) - 1
    self.slot_name = [None] * self.num_slots
    self.slot_time = [None] * self.num_slots
    last_day_time = None
    for slot in range(self.num_slots):
      slot_name = row[slot+1]
      self.slot_name[slot] = slot_name
      m = re.match(r'^\s*([MTWRFSU])\s*(\d+):(\d+)$', slot_name)
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
      # TODO(mgeorg) Add a penalty term for scheduling lessons on
      # consecutive days.
      self.pupil_num_lessons.append(int(m.group(2)))
    else:
      self.pupil_num_lessons.append(1)

    self.ParsePreferenceRow(row)

  def ParsePreferenceRow(self, row):
    self.num_pupils += 1
    self.pupil_slot_preference.append([0] * self.num_slots)
    for i in range(self.num_slots):
      if row[i+1].isdigit():
        self.pupil_slot_preference[-1][i] = int(row[i+1])
      elif row[i+1] in ['x', 'X']:
        self.pupil_slot_preference[-1][i] = -1

  def ParseRestrictionsRow(self, row):
    assert row[0] == 'Instructor1 Restrictions'
    assert self.num_slots > 0, 'The first row was malformed.'
    assert len(row)-1 == self.num_slots, 'All rows must be of the same length (%d vs %d).' % (len(row)-1, self.num_slots)

    for slot in range(self.num_slots):
      row[slot+1] = row[slot+1].strip()
      if not row[slot+1]:
        continue
      for restriction_spec in row[slot+1].split(','):
        restriction_spec = restriction_spec.strip()
        # TODO(mgeorg) Make Complex Restrictions support groups of slots.
        m = re.match(r'^([^_]+)_(\d+)$', restriction_spec)
        assert m, 'Restrictions cell does not have proper format: ' + restriction_spec
        if m.group(1) in self.restrictions:
          self.restrictions[m.group(1)].append(slot)
          assert self.restrictions_num[m.group(1)] == int(m.group(2)), 'Number of slots to leave empty does not match'
        else:
          self.restrictions[m.group(1)] = [slot]
          self.restrictions_num[m.group(1)] = int(m.group(2))

  def DetermineSlotOcclusion(self):
    """Determine the slot occlusions.

    First we determine every slot that a pupil would take up (occlud) if
    it was scheduled at that time.  This information is saved as
    self.pupil_slot_occlusion.  Then we invert this mapping to
    produce self.slot_pupil_occlusion.  Meaning, given a slot and a pupil,
    provide all the slots which would produce an occlusion.
    """
    self.pupil_slot_occlusion = [[None] * self.num_slots for _ in range(self.num_pupils)]
    self.pupil_slot_occlusion[0] = None
    for pupil in range(1, self.num_pupils):
      for day in range(7):
        slots = []
        for slot_index in range(len(self.slots_by_day[day])):
          slot = self.slots_by_day[day][slot_index]
          lesson_length_left = self.pupil_lesson_length[pupil]
          offset = 0
          slots = []
          while (lesson_length_left > 0 and
                 slot_index+offset < len(self.slots_by_day[day])):
            new_slot = self.slots_by_day[day][slot_index+offset]
            slots.append(new_slot)
            assert self.slot_time[new_slot].length
            lesson_length_left -= self.slot_time[new_slot].length
            offset += 1
          if lesson_length_left <= 0:
            self.pupil_slot_occlusion[pupil][slot] = slots
          else:
            # Unable to schedule.
            self.pupil_slot_occlusion[pupil][slot] = []
            self.pupil_slot_preference[pupil][slot] = 0
    self.slot_pupil_occlusion = [[None] * self.num_pupils for _ in range(self.num_slots)]
    for pupil in range(1, self.num_pupils):
      for day in range(7):
        for slot in self.slots_by_day[day]:
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
    for day in range(7):
      self.slots_by_day[day] = [
          i for i in range(self.num_slots) if self.slot_time[i].day == day]
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
  def __init__(self, spec, solver_run):
    pref = solver_run.options

    self.solver_run = solver_run
    self.solver_run.version = version_number

    self.spec = spec
    self.next_var = 1
    self.x_name = dict()
    self.our_name = dict()
    self.available = dict()
    self.fixed_value = dict()
    self.constraints = []
    self.objective = []
    self.all_products = dict()
    self.max_product_size = 0
    self.all_objectives = dict()

    self.arrive_late_bonus = int(pref.arrive_late_bonus)
    self.leave_early_bonus = int(pref.leave_early_bonus)
    self.day_off_bonus = int(pref.day_off_bonus)
    self.pupil_preference_penalty = [
        int(x.strip()) for x in pref.pupil_preference_penalty_list.split(',')]
    self.instructor_preference_penalty = [
        int(x.strip()) for x in pref.instructor_preference_penalty_list.split(',')]
    tmp_values = ast.literal_eval(pref.no_break_penalty)
    self.no_break_penalty = sorted(
        [(int(k),int(v)) for k,v in tmp_values.items() ])

    self.complex_constraints_string = pref.complex_constraints
    self.complex_constraint_intervals = list()
    self.complex_constraints = list()

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
    self.MakeComplexConstraintIntervals()
    self.MakeComplexConstraints()

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
    for pupil in range(self.spec.num_pupils):
      for slot in range(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        if self.available[var_name]:
          self.MakeVariable(var_name)

  def MakeAvailabilityDict(self):
    # Go through availabilities and mark the variables that we need.
    for slot in range(self.spec.num_slots):
      for pupil in range(self.spec.num_pupils):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        # This slot is only available if it is marked as available directly
        # and if all of the slots it would occlud are marked as available
        # for the instructor.
        if pupil == 0:
          self.available[var_name] = (
              self.spec.pupil_slot_preference[pupil][slot] > 0)
          if not self.available[var_name]:
            if self.spec.pupil_slot_preference[pupil][slot] == -1:
              # Consider this slot busy
              self.fixed_value[var_name] = 1
            else:
              self.fixed_value[var_name] = 0
        else:
          self.available[var_name] = False
          if self.spec.pupil_slot_preference[pupil][slot] > 0:
            if (self.spec.pupil_slot_occlusion[pupil] and
                self.spec.pupil_slot_occlusion[pupil][slot]):
              # Check the instructor for each of the slots it would occlud.
              available = True
              for occlud in self.spec.pupil_slot_occlusion[pupil][slot]:
                if self.spec.pupil_slot_preference[0][occlud] <= 0:
                  available = False
                  break
              self.available[var_name] = available

  def MakeSlotConstraints(self):
    """Each lesson needs exactly one teacher per student.

    Notice that a student may fill the lesson because of overflow from
    an earlier slot which has gone past its end time.
    """
    # TODO(mgeorg) There is a bug here with scheduling long lessons at the
    # end of the day.
    # Each session needs an instructor and only has 1 student.
    for slot in range(self.spec.num_slots):
      x_names = []
      if not self.available['p0s'+str(slot)]:
        continue
      for pupil in range(1, self.spec.num_pupils):
        for pupil_slot in self.spec.slot_pupil_occlusion[slot][pupil]:
          # Consider all slots that would occlud this slot if we scheduled them.
          var_name = 'p'+str(pupil)+'s'+str(pupil_slot)
          if self.available[var_name]:
            x_names.append(self.x_name[var_name])
      if x_names:
        self.constraints.append('1 ' + self.x_name['p0s'+str(slot)] + ' -1 ' +
                                ' -1 '.join(x_names) + ' = 0;')

  def MakePupilConstraints(self):
    """Each pupil must have the correct number of sessions."""
    # Remember that pupil 0 is the instructor.
    for pupil in range(1, self.spec.num_pupils):
      x_names = []
      for slot in range(self.spec.num_slots):
        var_name = 'p'+str(pupil)+'s'+str(slot)
        if self.available[var_name]:
          x_names.append(self.x_name[var_name])
      assert x_names, ('pupil ' + self.spec.pupil_name[pupil] +
                       ' has no available slots.')
      self.constraints.append('1 ' + ' +1 '.join(x_names) + ' = ' +
                              str(self.spec.pupil_num_lessons[pupil]) + ';')
      if self.spec.pupil_num_lessons[pupil] > 1:
        # Restrict multiple lessons to different days.
        for day in range(7):
          x_names = []
          for slot in self.spec.slots_by_day[day]:
            var_name = 'p'+str(pupil)+'s'+str(slot)
            if self.available[var_name]:
              x_names.append(self.x_name[var_name])
          if x_names:
            self.constraints.append('-1 ' + ' -1 '.join(x_names) + ' >= -1;')
                                   

  def MakeRestrictionsConstraints(self):
    for restriction_name, slots in self.spec.restrictions.items():
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
        x_names.sort(key=ValFromXVar)
        self.constraints.append(
            '1 ~' + ' +1 ~'.join(x_names) + ' >= ' + str(num) + ';')

  def MakeComplexConstraintIntervals(self):
    self.complex_constraint_intervals = list()
    for constraint in self.complex_constraints_string.split(','):
      self.complex_constraint_intervals.append(list())
      for term in constraint.split(' OR '):
        if not term:
          continue
        m = re.match(r'^\s*(?:(\d+)(min(?:ute)?s?|hours?)\s*)?([mtwrfsu])\s*('+
                     kTimeStringReString+r')(?:-('+kTimeStringReString+'))?$',
                     term.lower())
        assert m, (
            'Complex constraint "%s" does not have correct format.' % term)
        if m.group(1):
          minutes = int(m.group(1))
          if m.group(2).startswith('hour'):
            minutes *= 60
        else:
          minutes = 0
        day = self.spec.day_to_number[m.group(3).upper()]
        time_in_day1 = TimeStringToMinInDay(m.group(4))
        if m.group(5):
          time_in_day2 = TimeStringToMinInDay(m.group(5))
        else:
          assert minutes, (
              'Define length of slot or length of interval "%s"' % term)
          time_in_day2 = time_in_day1 + minutes
        if minutes == 0:
          minutes = time_in_day2 - time_in_day1
        assert time_in_day1 + minutes <= time_in_day2, (
            'Length of slot is longer than length of interval "%s"' % term)
        self.complex_constraint_intervals[-1].append(
            (day, minutes, time_in_day1, time_in_day2))

  def MakeComplexConstraints(self):
    self.complex_constraints = []
    for constraint_interval_list in self.complex_constraint_intervals:
      self.complex_constraints.append([])
      for day, minutes, start_time, end_time in constraint_interval_list:
        slots = []
        for slot in self.spec.slots_by_day[day]:
          if (start_time < self.spec.slot_time[slot].time + 
                           self.spec.slot_time[slot].length and
              end_time > self.spec.slot_time[slot].time):
            slots.append(slot)
        for slot_index in range(len(slots)):
          slot = slots[slot_index]
          slot_set = []
          interval = minutes
          for slot_index2 in range(slot_index, len(slots)):
            slot2 = slots[slot_index2]
            slot_set.append(slot2)
            interval -= self.spec.slot_time[slot].length
            if interval <= 0:
              break
          if interval <= 0:
            self.complex_constraints[-1].append(slot_set)
    print(self.complex_constraints)

  def MakeProd(self, penalty, slots, pupil=0, negations=False):
    if isinstance(negations, list):
      assert len(slots) == len(negations)
    else:
      negations = [negations for i in range(len(slots))]
    if penalty == 0:
      # Whether true or not this term is irrelevant.
      return (0, '')
    x_names = []
    for i in range(len(slots)):
      slot = slots[i]
      var_name = 'p'+str(pupil)+'s'+str(slot)
      if not self.available[var_name]:
        # fixed == 1 and negation means prod has value 0
        # and fixed == 0 and not negation means prod has value 0
        # otherwise the value for this term is 1 and the sum goes on.
        if self.fixed_value[var_name] == negations[i]:
          # Product is false.
          return (0, '')
        else:
          continue
      if negations[i]:
        x_names.append('~'+self.x_name[var_name])
      else:
        x_names.append(self.x_name[var_name])

    if not x_names:
      # Product is always true.
      return (penalty, '')

    if penalty > 0:
      penalty_str = '+' + str(penalty)
    else:
      penalty_str = str(penalty)

    x_names.sort(key=ValFromXVar)

    product = ' '.join(x_names)
    if len(x_names) > 1:
      self.all_products[product] = 1
      self.max_product_size = max(self.max_product_size, len(x_names))
    return penalty_str + ' ' + product

  def MakePreferencePenalty(self):
    instructor_objective = list()
    pupil_objective = list()
    self.all_objectives['instructor preference'] = instructor_objective
    self.all_objectives['pupil preference'] = pupil_objective
    for pupil in range(self.spec.num_pupils):
      for slot in range(self.spec.num_slots):
        if self.spec.pupil_slot_preference[pupil][slot] > 1:
          var_name = 'p'+str(pupil)+'s'+str(slot)
          if not self.available[var_name]:
            continue
          x = self.x_name[var_name]
          if pupil == 0:
            penalty = (self.instructor_preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]-2] *
                self.spec.slot_time[slot].length)
          else:
            penalty = (self.pupil_preference_penalty[
                self.spec.pupil_slot_preference[pupil][slot]-2] *
                self.spec.slot_time[slot].length)
          if pupil == 0:
            instructor_objective.append(' +' + str(penalty) + ' ' + x)
          else:
            pupil_objective.append(' +' + str(penalty) + ' ' + x)
    self.objective.extend(instructor_objective)
    self.objective.extend(pupil_objective)

  def MakeArriveLateBonus(self):
    objective = list()
    self.all_objectives['arrive late'] = objective
    # Assign a bonus for every minute the instructor comes in late.
    for day in range(7):
      slots = []
      for slot in self.spec.slots_by_day[day]:
        slots.append(slot)
        if len(slots) >= 2:
          bonus = self.arrive_late_bonus * (self.spec.slot_time[slot].time-
                                            self.spec.slot_time[slots[0]].time)
          negations = [1] * (len(slots)-1) + [0]
          (unused_penalty, term) = self.MakeProd(-bonus, slots, 0, negations)
          if term:
            objective.append(term)
    self.objective.extend(objective)

  def MakeLeaveEarlyBonus(self):
    objective = list()
    self.all_objectives['leave early'] = objective
    # Assign a bonus for every minute the instructor leaves early.
    # TODO(mgeorg) This isn't perfect, it assumes that the entire slot
    # is used, when a lesson might have just barely used some time up.
    for day in range(7):
      slots = []
      for slot in reversed(self.spec.slots_by_day[day]):
        slots.append(slot)
        if len(slots) >= 2:
          bonus = self.arrive_late_bonus * (
              +self.spec.slot_time[slots[0]].time
              +self.spec.slot_time[slots[0]].length
              -self.spec.slot_time[slot].time
              -self.spec.slot_time[slot].length)
          negations = [1] * (len(slots)-1) + [0]
          (unused_penalty, term) = self.MakeProd(-bonus, slots, 0, negations)
          if term:
            objective.append(term)
    self.objective.extend(objective)

  def MakeNoBreakPenalty(self):
    length_to_penalty = dict()

    k,v = self.no_break_penalty[0]
    diff = 0
    for i in range(k):
      length_to_penalty[i] = float(v)
    for index in range(len(self.no_break_penalty)-1):
      k1,v1 = self.no_break_penalty[index]
      k2,v2 = self.no_break_penalty[index+1]
      r = k2 - k1
      diff = (1/float(r))*(float(v2)-float(v1))
      for i in range(r):
        length_to_penalty[k1 + i] = float(i)*diff + float(v1)
    if diff < 0:
      diff = 0
    k,v = self.no_break_penalty[-1]
    for i in range(k, 24*60):
      v = float(v) + diff
      length_to_penalty[i] = v
      
    objective = list()
    self.all_objectives['no break'] = objective
    # Assign a penalty for every minute the instructor doesn't have a
    # break past some allowable threshold.
    for day in range(7):
      for first_slot_index in range(len(self.spec.slots_by_day[day])):
        first_slot = self.spec.slots_by_day[day][first_slot_index]
        start_time = self.spec.slot_time[first_slot].time
        slots = []
        for slot_index in range(first_slot_index,
                                len(self.spec.slots_by_day[day])):
          slot = self.spec.slots_by_day[day][slot_index]
          slots.append(slot)
          end_time = (self.spec.slot_time[slot].time + 
                      self.spec.slot_time[slot].length)
          if slots:
            penalty = round(length_to_penalty[end_time - start_time] *
                            float(end_time - start_time) / float(len(slots)))
          else:
            continue
          negations = [0]*len(slots)
          all_slots = slots[:]
          if first_slot_index != 0:
            negations = [1] + negations
            all_slots = [
                self.spec.slots_by_day[day][first_slot_index-1]] + all_slots
          if slot_index != len(self.spec.slots_by_day[day])-1:
            negations = negations + [1]
            all_slots = all_slots + [self.spec.slots_by_day[day][slot_index+1]]
          (unused_penalty, term) = self.MakeProd(
              penalty, all_slots, 0, negations)
          if term:
            objective.append(term)
    self.objective.extend(objective)

  def MakeDayOffBonus(self):
    """Assign a bonus for missing the entire day."""

    objective = list()
    self.all_objectives['day off'] = objective
    for day in range(7):
      if not self.spec.slots_by_day[day]:
        continue
      workday_time = self.spec.day_range[day][1] - self.spec.day_range[day][0]
      bonus = self.day_off_bonus * workday_time

      (unused_penalty, term) = self.MakeProd(
          -bonus, self.spec.slots_by_day[day], 0, 1)
      if term:
        objective.append(term)
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
    time_limit = 60
    total_time_limit = 600
    self.solver_run.scheduler_output += (
        ('Solving with a time limit of ' + str(time_limit) +
        ' seconds of not improving the solution or a total time limit of ' +
        str(total_time_limit) + ' seconds\n' + self.header))
    # print(self)
    p = subprocess.Popen(
        ['clasp', '-t8', '--time-limit='+str(total_time_limit), self.opb_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    lines = []
    current_time = time.time()
    last_activity = current_time
    last_save = current_time
    self.solver_run.state = self.solver_run.RUNNING
    self.solver_run.save()

    poll_obj = select.poll()
    poll_obj.register(p.stdout, select.POLLIN)   
    output = []
    chars = []
    while p.poll() == None and current_time - last_activity <= time_limit:
      if poll_obj.poll(0):
        last_activity = time.time()
        char = p.stdout.read(1).decode('ascii')
        if char == '\n':
          line = ''.join(chars) + '\n'
          m = re.match(r'^o (-?\d+)', line)
          if m:
            last_save = current_time
            self.solver_run.score = -int(m.group(1))
            self.solver_run.solution = self.solver_run.SOLUTION
            self.solver_run.solver_output = ''.join(output)
            self.solver_run.save()
          output.append(line)
          chars = []
        else:
          chars.append(char)
      else:
        if current_time - last_save > 1.0:
          last_save = current_time
          self.solver_run.solver_output = ''.join(output)
          self.solver_run.save()
        time.sleep(.1)
      current_time = time.time()
    if chars:
      output.append(''.join(chars))
    if p.poll() == None:
      p.terminate()
    (remaining_output, unused_stderr) = p.communicate()
    remaining_output = remaining_output.decode('ascii')
    output.append(remaining_output)
    self.solver_run.solver_output = ''.join(output)
    self.solver_run.save()
    return self.ParseSolverOutput()

  def PaddedSlotName(self, slot):
    slot_name = self.spec.slot_name[slot]
    return '%-6s' % slot_name

  def ParseSolverOutput(self):
    self.output_schedule = None
    x_names = []
    for line in self.solver_run.solver_output.splitlines():
      m = re.match('^v(?:\s+-?x\d+)+$', line)
      if m:
        curr_vars = line.split(' ')
        assert curr_vars[0] == 'v'
        x_names.extend(curr_vars[1:])
      m = re.match('^s (.*)$', line)
      if m:
        solution = m.group(1)
        if solution == 'OPTIMUM FOUND':
          self.solver_run.solution = self.solver_run.OPTIMAL
        elif solution == 'UNSATISFIABLE':
          self.solver_run.solution = self.solver_run.IMPOSSIBLE
        elif solution == 'SATISFIABLE':
          self.solver_run.solution = self.solver_run.SOLUTION
        else:
          assert False, 'Unable to parse solution line of clasp output.'
      m = re.match('^s (.*)$', line)
      if m:
        solution = m.group(1)
        if solution == 'OPTIMUM FOUND':
          self.solver_run.solution = self.solver_run.OPTIMAL
        elif solution == 'UNSATISFIABLE':
          self.solver_run.solution = self.solver_run.IMPOSSIBLE
        elif solution == 'SATISFIABLE':
          self.solver_run.solution = self.solver_run.SOLUTION
        elif solution == 'UNKNOWN':
          self.solver_run.solution = self.solver_run.NO_SOLUTION
        else:
          assert False, 'Unable to parse solution line of clasp output.'
      m = re.match('^o (-?\d+)$', line)
      if m:
        self.solver_run.score = -int(m.group(1))

    text_schedule = 'Pupil Session Times.\n'
    if(self.solver_run.solution in
           [self.solver_run.SOLUTION, self.solver_run.OPTIMAL]):
      self.x_solution = dict()
      var_names = []
      for x in x_names:
        m = re.match('^(-)?(x\d+)$', x)
        assert m
        if not m.group(1):
          self.x_solution[m.group(2)] = 1
          var_name = self.our_name[m.group(2)]
          var_names.append(var_name)

      self.solver_run.scheduler_output += '\n'
   
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
      for pupil in range(1, self.spec.num_pupils):
        text_schedule += (
            (self.spec.pupil_name[pupil] + ' -- ' +
             ', '.join(pupil_schedule[pupil])) + '\n')
      text_schedule += '\n\n'
      text_schedule += 'Instructor Schedule.\n'
      text_schedule += 'For reference the first column is the instructor preference value (i1, i2, i3, etc).\n'
      text_schedule += 'The second column is the pupil preference value (p1, p2, p3, etc).\n'
      text_schedule += 'The third column is the session time.\n'
      text_schedule += 'And the fourth column is the pupil name.\n'
      for day in range(7):
        for slot in self.spec.slots_by_day[day]:
          pupil = self.schedule[slot]
          pref = self.spec.pupil_slot_preference[0][slot]
          if pref >= 0:
            instructor_preference = str(pref)
          else:
            instructor_preference = 'X'
          extra = 'i' + instructor_preference + ' '
          if pupil:
            pupil_preference = str(self.spec.pupil_slot_preference[pupil][slot])
            extra += 'p' + pupil_preference + ' '
            text_schedule += (
                extra + self.PaddedSlotName(slot) + ' ' +
                self.spec.pupil_name[pupil] + '\n')
          else:
            extra += '   '
            if self.busy[slot]:
              text_schedule += (
                  extra + self.PaddedSlotName(slot) + ' ---Lesson Ongoing---\n')
            else:
              if self.spec.pupil_slot_preference[0][slot] > 0:
                text_schedule += (
                    extra + self.PaddedSlotName(slot) + '\n')
              else:
                if instructor_preference == 'X':
                  text_schedule += (
                      extra + self.PaddedSlotName(slot) + ' ***Forced to be Busy***\n')
                else:
                  text_schedule += (
                      extra + self.PaddedSlotName(slot) + ' ***Forced to be Free***\n')
        text_schedule += '\n'
      self.EvaluateAllObjectives()
      self.output_schedule = Schedule()
      self.output_schedule.score = self.solver_run.score
      self.output_schedule.schedule = text_schedule
      self.output_schedule.created_by = self.solver_run
      self.output_schedule.save()
    self.solver_run.state = self.solver_run.DONE
    self.solver_run.save()
    return self.output_schedule

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
    for name, objective in self.all_objectives.items():
      penalty = self.EvaluateObjective(objective)
      total_penalty += penalty
      self.solver_run.scheduler_output += (
          'Penalty ' + str(penalty) + ' for term \"' + name + '\"\n')
    self.solver_run.scheduler_output += (
        'Total Penalty ' + str(total_penalty) + '\n')


def ExecuteSolverRun(solver_run):
  # Run the solver on the data.
  parser = csv.reader(solver_run.availability.csv_data.splitlines(True))
  table_data = []
  for row in parser:
    if not row:
      continue
    table_data.append([x.strip() for x in row])

  constraints = solver.Constraints()
  constraints.ParseIterator(table_data)

  scheduler = Scheduler(constraints, solver_run)
  scheduler.Prepare()
  scheduler.Solve()


def RunSolve(availability_id, solver_options_id):
  availability = Availability.objects.get(pk=availability_id)
  solver_options = SolverOptions.objects.get(pk=solver_options_id)

  solver_run = SolverRun()
  solver_run.solver_version = solver.version_number
  solver_run.options = solver_options
  solver_run.availability = availability
  solver_run.score = None
  solver_run.state = SolverRun.IN_QUEUE
  solver_run.solution = SolverRun.NO_SOLUTION
  # Don't save yet, since we want to solve it immediately, not place it into
  # the queue.

  ExecuteSolverRun(solver_run)


if __name__ == "__main__":
  if len(sys.argv) != 4:
    sys.exit(1)
  availability_id = int(sys.argv[1])
  solver_options_id = int(sys.argv[2])
  sys.exit(RunSolve(availability_id, solver_options_id))

