#!/usr/bin/env python

# Process the control and treatment results into one file.

import argparse
from const import *

parser = argparse.ArgumentParser(
  description='Merge the control and treatment results into one csv.')
parser.add_argument('--control', dest='control_file', type=str, required=True,
                    help='path to control speed file')
parser.add_argument('--treatment', dest='treatment_file', type=str, required=True,
                    help='path to treatment speed file')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path')

args = parser.parse_args()

control_results = {}
with open(args.control_file, 'r') as f_control:
  for line in f_control.readlines()[1:]:
    line = line.strip()
    if line == '':
      continue
    pickup_zone, dropoff_zone, season, is_weekday, time_of_day, mean, std, percentile_85, count = line.split(',')
    bin_id = (pickup_zone, dropoff_zone, season, is_weekday, time_of_day)
    control_results[bin_id] = (float(mean), float(std), float(percentile_85), int(count))

treatment_results = {}
with open(args.treatment_file, 'r') as f_treatment:
  for line in f_treatment.readlines()[1:]:
    line = line.strip()
    if line == '':
      continue

    pickup_zone, dropoff_zone, season, is_weekday, time_of_day, mean, std, percentile_85, count = line.split(',')
    bin_id = (pickup_zone, dropoff_zone, season, is_weekday, time_of_day)
    treatment_results[bin_id] = (float(mean), float(std), float(percentile_85), int(count))

with open('missing.csv', 'w') as f_log:
  f_log.write(','.join([
    'pickup_zone',
    'dropoff_zone',
    'season',
    'is_weekday',
    'time_of_day',
    'has_control',
    'has_treatment'
  ]) + '\n')
  with open(args.output, 'w') as f_output:
    f_output.write(','.join([
      'pickup_zone',
      'dropoff_zone',
      'season',
      'is_weekday',
      'time_of_day',
      'control_mean',
      'control_std',
      'control_percentile_85',
      'control_count',
      'treatment_mean',
      'treatment_std',
      'treatment_percentile_85',
      'treatment_count'
    ]) + '\n')
    for pickup_zone_id in range(9):
      pickup_zone = zone_names[pickup_zone_id]
      for dropoff_zone_id in range(9):
        dropoff_zone = zone_names[dropoff_zone_id]
        for season_id in range(4):
          season = season_names[season_id]
          for is_weekday in ['True', 'False']:
            for time_of_day_id in range(4):
              time_of_day = time_of_day_names[time_of_day_id]
              bin_id = (pickup_zone, dropoff_zone, season, is_weekday, time_of_day)

              has_control, has_treatment = bin_id in control_results, bin_id in treatment_results

              if not has_control or not has_treatment:
                f_log.write('%s,%s,%s,%s,%s,%s,%s\n' % (bin_id + (has_control, has_treatment)))
                continue

              control_values, treatment_values = control_results[bin_id], treatment_results[bin_id]
              f_output.write('%s,%s,%s,%s,%s,' % bin_id)
              f_output.write('%.9f,%.9f,%.9f,%d,' % control_values)
              f_output.write('%.9f,%.9f,%.9f,%d\n' % treatment_values)
