#!/usr/bin/env python

# Process the generated speed files and aggregate the speeds based on 
# street, hour, time of day, etc.

import sys, datetime, re
import road_network, sign_installation, speed_limit

num_args = len(sys.argv)

if num_args < 3:
  print "Usage: python aggregate.py <speed file list> <output file>"
  exit(1)

# Parse the processed road network.
#network_simple = road_network.read_simple_network('network/manhattan_with_distances_clean.txt')
#network_full = road_network.read('network/Node.csv', 'network/Edge.csv')

#network_pruned = road_network.prune_network(network_full, network_simple)

#road_network.write_lion_csv(network_pruned, 'network/lion_nodes.csv', 'network/lion_edges.csv')
#road_network.write_clean_network(network_pruned, 'network/lion_network_pruned.txt')

network_lion = road_network.read_lion('network/lion_nodes.csv', 'network/lion_edges.csv')

# Parse the sign installation.
#sign_installation.process('corridors_sign_installation.csv', 'sign_installation.csv', network)
#sign_installation.read('sign_installation.csv', network)
# Parse the speed limit data.

network = network_lion
#speed_limit.process('Speed_limit_manhattan_verified.csv', 'speed_limit.csv', network)
speed_limit.read('speed_limit.csv', network)
speed_limit.plot_sign('sign_locations_lion_maxsl.csv', network)

sys.exit(0)

# Time of day definition.
times_of_day = {
  'morning-peak':   [datetime.time(06, 00, 00), datetime.time(9, 59, 59)],
  'mid-day':        [datetime.time(10, 00, 00), datetime.time(15, 59, 59)],
  'afternoon-peak': [datetime.time(16, 00, 00), datetime.time(19, 59, 59)],
  # Left is larger than right. This is left for the 'else' case.
  #'off-peak':       [datetime.time(20, 00, 00), datetime.time(05, 59, 59)],
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
announcement_date = datetime.datetime(2014, 11, 7)

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
    time_of_day = 'off-peak' # If not in other time_of_day bins, then it's off peak.
    for t_of_day, t_range in times_of_day.iteritems():
      if t_range[0] <= dt.time() and dt.time() <= t_range[1]:
        time_of_day = t_of_day
        break
    #day_of_week = days_of_week[dt.weekday()]

    speeds = [float(x) for x in line_tokens[1:]]
    for edge_index, speed in enumerate(speeds):
      if speed == -1:
        continue # Skip roads without computed speeds.
      #sign = network.edges[edge_index].sign
      #speed_limit = network.edges[edge_index].speed_limit
      #if sign == 'conflict' or sign == 'unknown':
      #  continue # Skip conflict and unknown signs

      #bin_id = ','.join([sign, 'before' if dt < announcement_date else 'after'])
      #, time_of_day
      bin_id = ','.join([str(x) for x in [edge_index, year, month]])

      if not bin_id in bins:
        bins[bin_id] = [0, 0] # [sum of speed, count]
      
      bins[bin_id][0] += speed
      bins[bin_id][1] += 1
      
results = []
for bin_id, val in bins.iteritems():
  speed = -1 if val[1] == 0 else (val[0] / val[1]) # avg = sum / count
  results.append([bin_id, speed])

def results_sorter(x):
  tokens = x[0].split(',')
  # year, month, time_of_day_rank, edge_index
  # times_of_day_rank[tokens[3]],
  return [int(tokens[1]), int(tokens[2]), int(tokens[0])]

def bin_id_formatter(x):
  segment_id, year, month = x.split(',') #, time_of_day
  return segment_id + ',' + year + '/' +  month # + ',' + time_of_day

sorted_results = sorted(results, key=results_sorter)

f_output = open(sys.argv[2], 'w')

# CSV header line.
f_output.write('segment_id,year_month,speed\n')#,time_of_day
#f_output.write('Sign,Announcement,Speed\n')

for res in sorted_results: 
  f_output.write('%s,' % bin_id_formatter(res[0]))
  if res[1] < 0:
    f_output.write('-1\n')
  else:
    f_output.write('%.6f\n' % res[1])
