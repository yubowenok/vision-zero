#!/usr/bin/env python

# Process the control and treatment results into one file.

import sys, argparse
import road_network

parser = argparse.ArgumentParser(
  description='Merge the control and treatment results into one csv.')
parser.add_argument('--control', dest='control_file', type=str, required=True,
                    help='path to control speed file')
parser.add_argument('--treatment', dest='treatment_file', type=str, required=True,
                    help='path to treatment speed file')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path')

args = parser.parse_args()

network = road_network.read_lion('network/lion_nodes.csv', 'network/lion_edges.csv')

control_results = {}
first_line = True
f_control = open(args.control_file, 'r')
for line in f_control.readlines():
  line = line.strip()
  if line == '':
    continue
  if first_line:
    first_line = False
    continue # skip header

  tokens = line.split(',')
  segment_id, season, is_weekday, time_of_day, speed = tokens
  bin_id = (int(segment_id), season, is_weekday, time_of_day)
  control_results[bin_id] = float(speed)

treatment_results = {}
first_line = True
f_treatment = open(args.treatment_file, 'r')
for line in f_treatment.readlines():
  line = line.strip()
  if line == '':
    continue
  if first_line:
    first_line = False
    continue # skip header

  tokens = line.split(',')
  segment_id, season, is_weekday, time_of_day, speed = tokens
  bin_id = (int(segment_id), season, is_weekday, time_of_day)
  treatment_results[bin_id] = float(speed)


sorted_results = []

control_but_not_treatment = 0
for bin_id, speed in control_results.iteritems():
  if bin_id not in treatment_results:
    #print 'has control but no treatment', bin_id
    segment_id = int(bin_id[0])
    sys.stdout.write('%f,%f\n' % network.edge_center(segment_id))
    control_but_not_treatment += 1
  else:
    sorted_results.append(list(bin_id) + [speed, treatment_results[bin_id]])

treatment_but_not_control = 0
for bin_id, speed in treatment_results.iteritems():
  if bin_id not in control_results:
    #print 'has treatment but no control', bin_id
    segment_id = int(bin_id[0])
    sys.stdout.write('%f,%f\n' % network.edge_center(segment_id))
    treatment_but_not_control += 1

print '# has control but no treatment = %d' % control_but_not_treatment
print '# has treatment but no control = %d' % treatment_but_not_control

sorted_results = sorted(sorted_results)

f_output = open(args.output, 'w')
f_output.write('segment,season,is_weekday,time_of_day,control,treatment\n')

for row in sorted_results:
  f_output.write('%d,%s,%s,%s,%f,%f\n' % tuple(row))


