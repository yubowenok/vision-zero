#!/usr/bin/env python

# Process the generated speed files and aggregate the speeds based on 
# street, hour, time of day, etc.

import sys, datetime, re
import road_network, sign_installation, speed_limit
import argparse

supported_bin_attrs = [
  'segment',
  'day_of_month',
  'time_of_day',
  'day_of_week',
  'is_weekday',
  'hour',
  'speed_limit',
  'sign',
  'season'
]

parser = argparse.ArgumentParser(
  description='Aggregate the estimated speed/volume of TLC trip records for yellow cabs.')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='file listing the data paths')
parser.add_argument('--bin', dest='bin', type=str, required=True,
                    help='bin attributes as a comma separated string of the following:' +
                         ','.join(supported_bin_attrs))
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path')
parser.add_argument('--with_sign', dest='with_sign', action='store_true',
                    help='include only segments with signs')
parser.add_argument('--without_sign', dest='with_sign', action='store_false',
                    help='include only segments without signs')
parser.add_argument('--total', dest='total', action='store_true',
                    help='compute total rather than average')
parser.add_argument('--data_type', dest='data_type', default='speed', type=str,
                    help='aggregated data type: speed, volume, count (only affect csv header)')
parser.set_defaults(with_sign=None)

args = parser.parse_args()

bin_attrs = args.bin.split(',')
for attr in bin_attrs:
  if attr not in supported_bin_attrs:
    print >> sys.stderr, 'unsupported bin attribute "%s"' % attr
    sys.exit(1)

with_sign = args.with_sign
compute_total = args.total

# Parse the processed road network.

# Read the simple network from previous speed estimation work.
#network_simple = road_network.read_simple_network('network/manhattan_with_distances_clean.txt')
# Read the full LION network.
#network_full = road_network.read_lion('network/Node.csv', 'network/Edge.csv')

# Generate a pruned network for nodes in Manhattan only from the full LION network.
#network_pruned = road_network.prune_network(network_full, network_simple)
# Write the pruned network to node/edge files.
#road_network.write_lion_csv(network_pruned, 'network/lion_nodes.csv', 'network/lion_edges.csv')
# Write the pruned network to a clean network file used by speed estimation (without attributes irrelevant to speed estimation).
#road_network.write_clean_network(network_pruned, 'network/lion_network_pruned.txt')

# Read the lion network.
network_lion = road_network.read_lion('network/lion_nodes.csv', 'network/lion_edges.csv')

# Set network
network = network_lion

# Parse the sign installation. We do not have complete information and the precise installation dates
# for now. The following lines generate and read the (incomplete) sign installation information.
#sign_installation.process('corridors_sign_installation.csv', 'network/sign_installation.csv', network)
#sign_installation.read('network/sign_installation.csv', network)


# If speed limit information is needed, then place the speed_limit.csv file
# within the running directory and uncomment the line that generates/reads it.
# Generate speed limit
#speed_limit.process('Speed_limit_manhattan_verified.csv', 'speed_limit.csv', network)
# Read speed limit
speed_limit.read('network/speed_limit.csv', network)
# Plot speed limit (for visualization only)
#speed_limit.plot_sign('sign_locations_lion_maxsl.csv', network)


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
days_of_week_names = {
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
day_of_week_names = {
  0: 'Mon',
  1: 'Tue',
  2: 'Wed',
  3: 'Thu',
  4: 'Fri',
  5: 'Sat',
  6: 'Sun'
}
day_of_week_rank = {
  'Mon': 0,
  'Tue': 1,
  'Wed': 2,
  'Thu': 3,
  'Fri': 4,
  'Sat': 5,
  'Sun': 6
}
seasons = {
  'Spring': [3, 4, 5],
  'Summer': [6, 7, 8],
  'Fall': [9, 10, 11],
  'Winter': [12, 1, 2]
}

# Stores the bin sum and count.
# Bin id is a concatenation of attributes, such as '<segment_id>,<year>,<month>,<day of week>'
bins = {}
announcement_date = datetime.datetime(2014, 11, 7)

# Process the speed files.
f_speeds = open(args.data_list, 'r')
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
    season = ''
    for season_name, season_months in seasons.iteritems():
      if month in season_months:
        season = season_name
    day_of_week = day_of_week_names[dt.weekday()]
    is_weekday = True if dt.weekday() <= 4 else False

    speeds = [float(x) for x in line_tokens[1:]]
    for edge_index, speed in enumerate(speeds):
      if speed == -1:
        continue # Skip roads without computed speeds.
      sign = network.edges[edge_index].sign

      if (with_sign == True and sign != 'yes') or (with_sign == False and sign != 'no'):
        continue

      speed_limit = network.edges[edge_index].speed_limit

      #bin_id = ','.join([sign, 'before' if dt < announcement_date else 'after'])
      bin_arr = [year, month]
      #bin_arr = [] # used for non year/month computation

      for attr in bin_attrs:
        if attr == 'segment':
          bin_arr.append(edge_index)
        elif attr == 'day_of_month':
          bin_arr.append(day)
        elif attr == 'time_of_day':
          bin_arr.append(time_of_day)
        elif attr == 'day_of_week':
          bin_arr.append(day_of_week)
        elif attr == 'hour':
          bin_arr.append(hour)
        elif attr == 'speed_limit':
          bin_arr.append(speed_limit)
        elif attr == 'is_weekday':
          bin_arr.append(is_weekday)
        elif attr == 'season':
          bin_arr.append(season)

      bin_id = tuple(bin_arr)

      if not bin_id in bins:
        bins[bin_id] = [0, 0] # [sum of speed, count]
      
      bins[bin_id][0] += speed
      bins[bin_id][1] += 1
      
results = []
for bin_id, val in bins.iteritems():
  if not compute_total:
    value = -1 if val[1] == 0 else (val[0] / val[1]) # avg = sum / count
    results.append([bin_id, value])
  else:
    results.append([bin_id, val[0]])


def results_sorter(x):
  return x[0]

def norm_date(y, m):
  return str(y) + '/' + ('0' + str(m) if m < 10 else str(m))

def bin_id_formatter(x):
  # The first two attrs are year, month and are formatted as YYYY/MM
  elements = [norm_date(x[0], x[1])] + [str(s) for s in x[2:]]

  #elements = [str(s) for s in x] # used for non year/month computation
  return ','.join(elements)

sorted_results = sorted(results, key=results_sorter)

f_output = open(args.output, 'w')

# CSV header line.
header_line = 'year_month'
#header_line = '' # used for non year/month computation
for attr in bin_attrs:
  header_line += ',' + str(attr)
header_line += ',' + args.data_type + '\n'

f_output.write(header_line)

for res in sorted_results: 
  f_output.write('%s,' % bin_id_formatter(res[0]))
  if res[1] < 0:
    f_output.write('-1\n')
  else:
    if compute_total:
      f_output.write('%d\n' % res[1])
    else: # average
      f_output.write('%.6f\n' % res[1])
