#!/usr/bin/env python

# Process the generated speed files and aggregate the speeds based on 
# street, hour, time of day, etc.

import sys, datetime, re
import road_network, sign_installation, speed_limit
import argparse

parser = argparse.ArgumentParser(
  description='Aggregate the estimated speed/volume of TLC trip records for yellow cabs.')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='file listing the data paths')
parser.add_argument('--type', dest='type', type=str, required=True,
                    help='aggregation type: year, month, day_of_month, time_of_day, day_of_week, is_weekday, hour, speed_limit')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path')
parser.add_argument('--segment_id', dest='segment_id', default=True, action='store_true',
                    help='group by segment id')
parser.add_argument('--sign', dest='sign', default=False, action='store_true',
                    help='group by with/without signs')
parser.add_argument('--data_type', dest='data_type', default='speed', type=str,
                    help='aggregated data type: speed, volume, sample_count (only affect csv header)')

args = parser.parse_args()

aggregation_type = args.type
include_segment_id = args.segment_id

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
if args.sign:
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
    day_of_week = day_of_week_names[dt.weekday()]
    is_weekday = True if dt.weekday() <= 4 else False

    speeds = [float(x) for x in line_tokens[1:]]
    for edge_index, speed in enumerate(speeds):
      if speed == -1:
        continue # Skip roads without computed speeds.
      sign = network.edges[edge_index].sign
      speed_limit = network.edges[edge_index].speed_limit

      #if sign == 'conflict' or sign == 'unknown':
      #  continue # Skip conflict and unknown signs

      #bin_id = ','.join([sign, 'before' if dt < announcement_date else 'after'])
      bin_id = '' if not include_segment_id else str(edge_index) + ','

      if args.sign:
        bin_id += sign + ','

      if aggregation_type == 'year':
        bin_id += ','.join([str(x) for x in [year]])
      elif aggregation_type == 'month':
        bin_id += ','.join([str(x) for x in [year, month]])
      elif aggregation_type == 'day_of_month':
        bin_id += ','.join([str(x) for x in [year, month, day]])
      elif aggregation_type == 'time_of_day':
        bin_id += ','.join([str(x) for x in [year, month, time_of_day]])
      elif aggregation_type == 'day_of_week':
        bin_id += ','.join([str(x) for x in [year, month, day_of_week]])
      elif aggregation_type == 'hour':
        bin_id += ','.join([str(x) for x in [year, month, hour]])
      elif aggregation_type == 'speed_limit':
        bin_id += ','.join([str(x) for x in [year, month, speed_limit]])
      elif aggregation_type == 'is_weekday':
        bin_id += ','.join([str(x) for x in [year, month, is_weekday]])

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
  sort_list = []
  if include_segment_id:
    sort_list.append(tokens[0]) # segment id
    tokens = tokens[1:]
  if args.sign:
    sort_list.append(tokens[0]) # sign
    tokens = tokens[1:]

  if aggregation_type == 'year':
    # year
    sort_list += [int(tokens[0])]
  elif aggregation_type == 'month':
    # year, month
    sort_list += [int(tokens[0]), int(tokens[1])]
  elif aggregation_type == 'day_of_month':
    # year, month, day
    sort_list += [int(tokens[0]), int(tokens[1]), int(tokens[2])]
  elif aggregation_type == 'time_of_day':
    # year, month, time_of_day
    sort_list += [int(tokens[0]), int(tokens[1]), times_of_day_rank[tokens[2]]]
  elif aggregation_type == 'day_of_week':
    # year, month, day_of_week
    sort_list += [int(tokens[0]), int(tokens[1]), day_of_week_rank[tokens[2]]]
  elif aggregation_type == 'hour':
    # year, month, hour
    sort_list += [int(tokens[0]), int(tokens[1]), int(tokens[2])]
  elif aggregation_type == 'speed_limit':
    # year, month, speed_limit
    sort_list += [int(tokens[0]), int(tokens[1]), int(tokens[2])]
  elif aggregation_type == 'is_weekday':
    # year, month, is_weekday
    sort_list += [int(tokens[0]), int(tokens[1]), 0 if tokens[2] == 'True' else 1]
  return sort_list

def norm_date(y, s):
  return y + '/' + ('0' + s if len(s) == 1 else s)

def bin_id_formatter(x):
  tokens = x.split(',')
  elements = []
  if include_segment_id:
    elements.append(tokens[0]) # segment id
    tokens = tokens[1:]
  if args.sign:
    elements.append(tokens[0]) # sign
    tokens = tokens[1:]

  if aggregation_type == 'year':
    # year
    elements += [tokens[0]]
  elif aggregation_type == 'month':
    # year, month
    elements += [norm_date(tokens[0], tokens[1])]
  elif aggregation_type == 'day_of_month':
    # year, month, day
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  elif aggregation_type == 'time_of_day':
    # year, month, time_of_day
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  elif aggregation_type == 'day_of_week':
    # year, month, day_of_week
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  elif aggregation_type == 'hour':
    # year, month, hour
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  elif aggregation_type == 'speed_limit':
    # year, month, speed_limit
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  elif aggregation_type == 'is_weekday':
    # year, month, is_weekday
    elements += [norm_date(tokens[0], tokens[1]), tokens[2]]
  return ','.join(elements)

sorted_results = sorted(results, key=results_sorter)

f_output = open(args.output, 'w')

# CSV header line.
header_line = '' if not include_segment_id else 'segment_id,'
if args.sign:
  header_line += 'sign,'

if aggregation_type == 'year':
  header_line += 'year'
elif aggregation_type == 'month':
  header_line += 'year_month'
elif aggregation_type == 'day_of_month':
  header_line += 'year_month,day'
elif aggregation_type == 'time_of_day':
  header_line += 'year_month,time_of_day'
elif aggregation_type == 'day_of_week':
  header_line += 'year_month,day_of_week'
elif aggregation_type == 'hour':
  header_line += 'year_month,hour'
elif aggregation_type == 'speed_limit':
  header_line += 'year_month,speed_limit'
elif aggregation_type == 'is_weekday':
  header_line += 'year_month,is_weekday'

header_line += ',' + args.data_type + '\n'

f_output.write(header_line)

for res in sorted_results: 
  f_output.write('%s,' % bin_id_formatter(res[0]))
  if res[1] < 0:
    f_output.write('-1\n')
  else:
    f_output.write('%.6f\n' % res[1])
