import sys
from raw_trip import *

stats = TripStats()
zone_locator = ZoneLocator('/data/taxi/ODzones_vertices.csv')
logger = Logger()

def process_raw_data(file):
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
      pass

  print 'finished processing %s' % file


process_raw_data('/Users/bowen/Desktop/yellow_tripdata_2014-01.csv')

stats.report()
logger.report('/Users/bowen/Desktop/longs.csv')
