import sys
from raw_trip import *
from const import *
import re
import argparse
import numpy as np

zone_locator = ZoneLocator('/data/taxi/ODzones_simp_vertices.csv')
logger = Logger()

parser = argparse.ArgumentParser(
  description='Zone-based aggregation of TLC yellow cab trips')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='list of data file paths')
#parser.add_argument('--output', dest='output', type=str, required=True,
#                    help='output path') # name, without file type suffix
args = parser.parse_args()

NUM_ZONES = len(zone_names)
NUM_DAYS = 31
NUM_HOURS = 24

DAY_BASE = NUM_HOURS * NUM_ZONES * NUM_ZONES
HOUR_BASE = NUM_ZONES * NUM_ZONES

class Aggregator:
  def __init__(self, year_month):
    self.year_month = year_month
    self.bins = [[] for _ in range(NUM_DAYS * DAY_BASE)]

  def add_trip(self, trip):
    t = trip.pickup_time
    # use compressed integer index for (day, hour, pickup_zone, dropoff_zone)
    bin_id = (t.day - 1) * DAY_BASE + t.hour * HOUR_BASE + trip.pickup_zone * NUM_ZONES + trip.dropoff_zone

    #bin_id = ('%d/%02d/%02d' % (t.year, t.month, t.day), t.hour, trip.pickup_zone, trip.dropoff_zone)
    #if bin_id not in self.bins:
    #  self.bins[bin_id] = []
    self.bins[bin_id].append(trip.speed)

  def report(self, file=''):
    with open(file, 'w') as f:
      f.write(','.join([
        'date',
        'hour',
        'pickup_zone',
        'dropoff_zone',
        'mean',
        'std',
        'percentile_85',
        'count'
      ]) + '\n')

      for bin_id, speeds in enumerate(self.bins):
        if len(speeds) == 0: continue
        day = bin_id / DAY_BASE + 1
        hour = bin_id / HOUR_BASE % NUM_HOURS
        pickup_zone = bin_id / NUM_ZONES % NUM_ZONES
        dropoff_zone = bin_id % NUM_ZONES
        f.write('%s,%d,%d,%d,%.9f,%.9f,%.9f,%d\n' % (
          '%s-%02d' % (self.year_month, day), # date
          hour,
          pickup_zone, #zone_names[bin_id[2]],
          dropoff_zone, #zone_names[bin_id[3]],
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
      trip = RawTrip(line=line, zone_locator=zone_locator, stats=stats, logger=logger)
    except Exception:
      continue

    aggregator.add_trip(trip)

  print 'finished processing %s' % file


f_data_list = open(args.data_list, 'r')
for filename in f_data_list.readlines():
  filename = filename.rstrip()
  if filename == '':
    continue
  month = re.match('^.*(\d\d\d\d-\d\d)\.csv$', filename).group(1)

  aggregator = Aggregator(month)
  stats = TripStats()
  process_raw_data(filename, aggregator, stats)

  output_csv = 'day_%s.csv' % month
  stats_txt = 'day_%s_stats.txt' % month
  aggregator.report(output_csv)
  stats.report(stats_txt)