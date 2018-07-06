# Bin: yyyy-mm, hour
# Value: mean, std, percentile_85, count

from raw_trip import *
import re
import argparse
import numpy as np

parser = argparse.ArgumentParser(
  description='Aggregation of TLC yellow cab trips')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='list of data file paths')
parser.add_argument('--output_dir', dest='output_dir', type=str, required=True,
                    help='output directory')
args = parser.parse_args()
output_dir = args.output_dir

class Aggregator:
  def __init__(self, year_month):
    self.year_month = year_month
    self.bins = {}

  def add_trip(self, trip):
    t = trip.pickup_time
    bin_id = (self.year_month, t.hour)
    if bin_id not in self.bins:
      self.bins[bin_id] = []
    self.bins[bin_id].append(trip.speed)

  def report(self, filename):
    with open(filename, 'w') as f:
      f.write(','.join([
        'year_month',
        'hour',
        'mean',
        'std',
        'percentile_85',
        'count'
      ]) + '\n')
      bin_ids = sorted(self.bins.keys())
      for bin_id in bin_ids:
        speeds = self.bins[bin_id]
        if len(speeds) == 0: continue

        f.write('%s,%d,%.9f,%.9f,%.9f,%d\n' % (
          bin_id[0], # yyyy-mm
          bin_id[1], # hour
          np.average(speeds),
          np.std(speeds),
          np.percentile(speeds, 85),
          len(speeds)
        ))

def process_raw_data(file, aggregator, stats):
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

    try:
      trip = RawTrip(line=line, stats=stats)
    except Exception:
      continue

    aggregator.add_trip(trip)

  print 'finished processing %s' % file


f_data_list = open(args.data_list, 'r')
for filename in f_data_list.readlines():
  filename = filename.rstrip()
  if filename == '':
    continue

  year_month = re.match('^.*(\d\d\d\d-\d\d)\.csv$', filename).group(1)

  aggregator = Aggregator(year_month)
  stats = TripStats()
  process_raw_data(filename, aggregator, stats)

  aggregator.report(output_dir + '/%s.txt' % year_month)

  stats_txt = 'stats/%s_stats.txt' % year_month
  stats.report(stats_txt)
