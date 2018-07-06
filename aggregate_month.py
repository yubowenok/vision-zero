import sys
from const import *
import re
import argparse
import datetime
import numpy as np

# Process daily zone-to-zone aggregation and generate monthly speed aggregation.
# Bin: yyyy-mm, hour
# Values: speed, count

parser = argparse.ArgumentParser(
  description='Monthly speed aggregation of TLC yellow cab trips')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='list of data file paths')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path') # name, without file type suffix
args = parser.parse_args()

class Aggregator:
  def __init__(self):
    self.bins = {}

  def add_record(self, year, month, hour, mean, count):
    bin_id = (year, month, hour)
    if bin_id not in self.bins:
      self.bins[bin_id] = [0, 0] # sum, count
    self.bins[bin_id][0] += mean * count
    self.bins[bin_id][1] += count

  def report(self, file):
    with open(file, 'w') as f:
      f.write(','.join([
        'year_month',
        'hour',
        'mean',
        'count'
      ]) + '\n')

      bin_ids = sorted(self.bins.keys())

      for bin_id in bin_ids:
        sum, count = self.bins[bin_id]
        assert count > 0
        f.write('%s,%d,%.9f,%d\n' % (
          '%s-%02d' % (bin_id[0], bin_id[1]), # yyyy-mm
          bin_id[2],
          sum / count,
          count
        ))

def process_data(file, aggregator):
  f = open(file, 'r')
  print 'processing %s...' % file
  lines = f.readlines()[1:]
  line_counter, num_lines = 0, len(lines)
  for line in lines:
    line_counter += 1
    if line_counter % 1000 == 0:
      print '\r%.2f%%' % (1.0 * line_counter / num_lines * 100),
      sys.stdout.flush()
    if line == '':
      continue

    #date,hour,pickup_zone,dropoff_zone,mean,std,percentile_85,count
    #2009-01-01,0,0,0,17.464400259,6.139807473,25.620456343,8

    tokens = line.split(',')
    year, month, day = [int(x) for x in re.split('-', tokens[0])]
    hour = int(tokens[1])
    count = int(tokens[-1])
    mean = float(tokens[4])
    aggregator.add_record(year, month, hour, mean, count)

  print 'finished processing %s' % file

aggregator = Aggregator()

f_data_list = open(args.data_list, 'r')
for filename in f_data_list.readlines():
  filename = filename.rstrip()
  if filename == '':
    continue
  process_data(filename, aggregator)

aggregator.report(args.output)
