import sys
from raw_trip import *
from const import *
import argparse
import numpy as np

stats = TripStats()
zone_locator = ZoneLocator('/data/taxi/ODzones_simp_vertices.csv')
logger = Logger()

parser = argparse.ArgumentParser(
  description='Zone-based aggregation of TLC yellow cab trips')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='list of data file paths')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output path')
args = parser.parse_args()

class Aggregator:
  def __init__(self):
    self.bins = {}

  def add_trip(self, trip):
    t = trip.pickup_time

    season = ''
    for months, key in season_months.iteritems():
      if t.month in months:
        season = key
        break

    day_of_week = t.weekday()
    is_weekday = day_of_week <= 4

    time_of_day = 3 # off-peak
    for key, range in time_of_day_ranges.iteritems():
      if range[0] <= t.time() and t.time() <= range[1]:
        time_of_day = key
        break

    bin_id = (trip.pickup_zone, trip.dropoff_zone, season, is_weekday, time_of_day)

    if bin_id not in self.bins:
      self.bins[bin_id] = []
    self.bins[bin_id].append(trip.speed)

  def report(self, file=''):
    with open(file, 'w') as f:
      f.write(','.join([
        'pickup_zone',
        'dropoff_zone',
        'season',
        'is_weekday',
        'time_of_day',
        'mean',
        'std',
        'percentile_85',
        'count'
      ]) + '\n')

      for bin_id, speeds in sorted(self.bins.iteritems()):
        f.write('%s,%s,%s,%s,%s,%.9f,%.9f,%.9f,%d\n' % (
          zone_names[bin_id[0]],
          zone_names[bin_id[1]],
          season_names[bin_id[2]],
          bin_id[3],
          time_of_day_names[bin_id[4]],
          np.average(speeds),
          np.std(speeds),
          np.percentile(speeds, 85),
          len(speeds)
        ))

def process_raw_data(file, aggregator):
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
      trip = RawTrip(line=line, zone_locator=zone_locator, stats=stats, logger=logger)
    except Exception:
      continue

    aggregator.add_trip(trip)

  print 'finished processing %s' % file


aggregator = Aggregator()
f_data_list = open(args.data_list, 'r')
for filename in f_data_list.readlines():
  filename = filename.rstrip()
  if filename == '':
    continue
  process_raw_data(filename, aggregator)

aggregator.report(args.output)
stats.report()
#logger.report(file='/Users/bowen/Desktop/euclids_3-10.csv',
#              header='distance,vincenty,ratio,pickup_lon,pickup_lat,dropoff_lon,dropoff_lat')
