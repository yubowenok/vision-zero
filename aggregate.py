#!/usr/bin/env python

# Process the generated speed files and aggregate the speeds based on 
# street, hour, time of day, etc.

import sys, datetime, re
import road_network, sign_installation

num_args = len(sys.argv)

if num_args < 3:
  print "Usage: python aggregate.py <speed file list> <output file>"
  exit(1)

# Parse the road network.
network = road_network.read('manhattan_with_distances_clean.txt')
# Parse the sign installation.
#sign_installation.process('corridors_sign_installation.csv', 'sign_installation.csv', network)
sign_installation.read('sign_installation.csv', network)

# Time of day definition.
times_of_day = {
  'morning-peak':   [datetime.time(06, 00, 00), datetime.time(9, 59, 59)],
  'mid-day':        [datetime.time(10, 00, 00), datetime.time(15, 59, 59)],
  'afternoon-peak': [datetime.time(16, 00, 00), datetime.time(19, 59, 59)],
  # Left is larger than right. This is left for the 'else' case.
  'off-peak':       [datetime.time(20, 00, 00), datetime.time(05, 59, 59)],
}
times_of_day_rank = {
  'morning-peak':   0,
  'mid-day':        1,
  'afternoon-peak': 2,
  'off-peak':       3,
}

# Day of week definition.
days_of_week = {
  0: 'Mon',
  1: 'Tue-Thu',
  2: 'Tue-Thu',
  3: 'Tue-Thu',
  4: 'Fri',
  5: 'Sat',
  6: 'Sun',
}
days_of_week_rank = {
  'Mon': 0,
  'Tue-Thu': 1,
  'Fri': 2,
  'Sat': 3,
  'Sun': 4,
}

# Stores the bin sum and count.
# Bin id is '<year>,<month>,<day of week>,<time of day>'
bins = {}

# Process the speed files.
f_speeds = open(sys.argv[1], 'r')
for speed_file in f_speeds.readlines():
  if speed_file.strip() == '':
    continue
  print >> sys.stderr, 'processing %s' % speed_file.strip()
  f = open(speed_file.strip(), 'r')
  for line in f.readlines():
    line_tokens = line.split()
    dt_tokens = [int(x) for x in re.split('-|_', line_tokens[0])]
    year, month, day, hour, minute, second = dt_tokens
    dt = datetime.datetime(year, month, day, hour, minute, second)
    #time_of_day = ''
    #for t_of_day, t_range in times_of_day.iteritems():
    #  # If not in other time_of_day bins, then it's off peak.
    #  if t_of_day == 'off-peak' or (t_range[0] <= dt.time() and dt.time() <= t_range[1]):
    #    time_of_day = t_of_day
    #    break
    #assert(time_of_day != '')
    day_of_week = days_of_week[dt.weekday()]
    
    bin_id = str(hour)
    #bin_id = ','.join([str(x) for x in [year, month, hour]])
    #bin_id = ','.join([str(x) for x in [year, month, day_of_week, time_of_day]])
    if not bin_id in bins:
      bins[bin_id] = [0, 0] # [sum of speed, count]
    
    speeds = [float(x) for x in line_tokens[1:]]
    for speed in speeds:
      if speed == -1:
        continue
      bins[bin_id][0] += speed
      bins[bin_id][1] += 1
      
results = []
for bin_id, val in bins.iteritems():
  speed = -1 if val[1] == 0 else (val[0] / val[1]) # avg = sum / count
  results.append([bin_id, speed])

def results_sorter(x):
  tokens = x[0].split(',')
  # year, month, day_of_week, time_of_day
  #return [int(tokens[0]), int(tokens[1]), days_of_week_rank[tokens[2]], times_of_day_rank[tokens[3]]]
  # year, month, hour
  return [int(x) for x in tokens]

def bin_id_formatter(x):
  #year, month, hour = x.split(',')
  #return year + '/' + ('' if len(month) == 2 else '0') + month + ',' + hour
  return x

sorted_results = sorted(results, key=results_sorter)

f_output = open(sys.argv[2], 'w')

# CSV header line.
#f_output.write('Year,Month,Day_of_Week,Time_of_Day,Speed\n')
#f_output.write('Year/Month,Hour,Speed\n')
f_output.write('Hour,Speed\n')

for res in sorted_results: 
  f_output.write('%s,' % bin_id_formatter(res[0]))
  if res[1] < 0:
    f_output.write('-1\n')
  else:
    f_output.write('%.6f\n' % res[1])
