import csv
import random

with open('sched.csv', 'wb') as csvfile:
  csvwriter = csv.writer(csvfile, delimiter=',',
                         quotechar='\"', quoting=csv.QUOTE_MINIMAL)
  slot_times = ['Schedule']
  i1_available = ['Instructor1']
  i1_restriction = ['Instructor1 Restrictions']
  days = ['M', 'T', 'W', 'R', 'F', 'S', 'U']
  for day_index in xrange(len(days)):
    day = days[day_index]
    for t in [x*30+9*60 for x in xrange(8*2+1)]:
      slot_times.append(day + ' ' + str(t/60) + ':%02d' % (t % 60))
      r = random.random()
      if r < .9:
        val = '1'
      elif r < .95:
        val = '2'
      else:
        val = '3'
      i1_available.append(val)
      restriction = ''
      if t in [x*30+11*60+30 for x in xrange(4)]:
        restriction = 'L-' + day + '_1_3'
      i1_restriction.append(restriction)
    i1_available[-1] = ''
  csvwriter.writerow(slot_times)
  csvwriter.writerow(i1_available)
  csvwriter.writerow(i1_restriction)
  for pupil in xrange(int((len(slot_times)-1)*.8)):
    pupil_available = ['P'+str(pupil)]
    for slot in xrange(len(slot_times)-1):
      r = random.random()
      if r < .7:
        val = ''
      elif r < .8:
        val = '1'
      elif r < .9:
        val = '2'
      else:
        val = '3'
      pupil_available.append(val)
    csvwriter.writerow(pupil_available)
