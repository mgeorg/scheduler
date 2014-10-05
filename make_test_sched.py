import csv
import random

with open('sched.csv', 'wb') as csvfile:
  csvwriter = csv.writer(csvfile, delimiter=',',
                         quotechar='\"', quoting=csv.QUOTE_MINIMAL)
  slot_times = ['Schedule']
  i1_available = ['Instructor1']
  for day in ['M', 'T', 'W', 'R', 'F', 'S', 'U']:
    for time in [x*30+7*60 for x in xrange(8*2)]:
      slot_times.append(day + ' ' + str(time/60) + ':%02d' % (time % 60))
      r = random.random()
      if r < .9:
        val = '1'
      elif r < .95:
        val = '2'
      else:
        val = '3'
      i1_available.append(val)
    i1_available[-1] = ''
  csvwriter.writerow(slot_times)
  csvwriter.writerow(i1_available)
  for pupil in xrange(int((len(slot_times)-1)*.9)):
    pupil_available = ['P'+str(pupil)]
    for slot in xrange(len(slot_times)-1):
      r = random.random()
      if r < .9:
        val = ''
      elif r < .95:
        val = '1'
      elif r < .97:
        val = '2'
      else:
        val = '3'
      pupil_available.append(val)
    csvwriter.writerow(pupil_available)
