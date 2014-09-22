#!/usr/bin/python

import re
import os
import csv
import subprocess
import tempfile

max_var = 1
student_index = 0
constrainsts = []
variables = dict()
constraints = []
reverse_variables = dict()

with open(r'sched.csv', 'rb') as csvfile:
  sched_reader = csv.reader(csvfile)
  for row in sched_reader:
    if row[0] == 'Schedule':
      sched_row = row
    elif row[0] == 'Available':
      assert sched_row, 'The first row must start with \'Schedule\''
      assert len(row) == len(sched_row), 'All rows must be of the same length.'
      for i in xrange(len(row)-1):
        var_name = 't'+str(i)
        x_name = 'x'+str(max_var)
        variables[var_name] = x_name
        reverse_variables[x_name] = var_name
        max_var += 1
        if row[i+1] != 'y':
          constraints.append('1 '+x_name+' = 0;')
    else:
      assert sched_row, 'The first two rows were not formatted correctly.'
      assert len(row) == len(sched_row), 'All rows must be of the same length.'
      for i in xrange(len(row)-1):
        var_name = 's'+str(student_index)+'t'+str(i)
        x_name = 'x'+str(max_var)
        variables[var_name] = x_name
        reverse_variables[x_name] = var_name
        max_var += 1
        if row[i+1] != 'y':
          constraints.append('1 '+x_name+' = 0;')
      student_index += 1

# Each student only has 1 class.
for i in xrange(student_index):
  x_names = []
  for t in xrange(len(sched_row)-1):
    var_name = 's'+str(i)+'t'+str(t)
    x_name = variables[var_name]
    x_names.append(x_name)
  constraints.append('1 ' + ' +1 '.join(x_names) + ' = 1;')

# Each session only has 1 student.
for t in xrange(len(sched_row)-1):
  x_names = []
  for i in xrange(student_index):
    var_name = 's'+str(i)+'t'+str(t)
    x_name = variables[var_name]
    x_names.append(x_name)
  constraints.append('1 ' + variables['t'+str(t)] + ' -1 ' +
                     ' -1 '.join(x_names) + ' = 0;')

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


(handle_int, file_name) = tempfile.mkstemp()
print file_name
handle = os.fdopen(handle_int, 'w')
handle.write(
    '* #variable= '+str(max_var-1)+' #constraint= '+str(len(constraints))+
    ' #product= '+str(len(all_products))+
    ' sizeproduct= '+str(len(sched_row)-1)+'\n')
handle.write('min: ' + ''.join(objective) + ';\n')
handle.write('\n'.join(constraints) + '\n')
handle.close()

p = subprocess.Popen(['clasp', file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
(stdout, unused_stderr) = p.communicate()

print stdout

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

