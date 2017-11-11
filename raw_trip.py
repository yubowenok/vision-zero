import datetime, re, sys
from geopy.distance import vincenty

# indices for every year are the same, except for 2016 second half
trip_indices = {
  'pickup_time': 1,
  'dropoff_time': 2,
  'pickup_lon': 5,
  'pickup_lat': 6,
  'dropoff_lon': 9,
  'dropoff_lat': 10,
  'distance': 4
}

class Polygon:
  def __init__(self):
    """
    Initializes an empty polygon.
    """
    self.points = []
    self.min_lon, self.max_lon = float('inf'), float('-inf')
    self.min_lat, self.max_lat = float('inf'), float('-inf')

  def add_point(self, lon, lat):
    """
    Points must be added in cc/ccw order!
    """
    self.points.append((lon, lat))
    self.min_lon, self.max_lon = min(self.min_lon, lon), max(self.max_lon, lon)
    self.min_lat, self.max_lat = min(self.min_lat, lat), max(self.max_lat, lat)

  def contains(self, lon, lat):
    if lon < self.min_lon or lon > self.max_lon or lat < self.min_lat or lat > self.max_lat:
       return False # outside bounding box
    first_x, first_y = self.points[0][0], self.points[0][1]
    test_x, test_y = lon, lat
    c = False
    j, i, n = 0, 1, len(self.points)
    while i < n:
      vi, vj = self.points[i], self.points[j]
      if (((vi[1] > test_y) != (vj[1] > test_y)) and
         (test_x < (vj[0] - vi[0]) * (test_y - vi[1]) / (vj[1] - vi[1]) + vi[0])):
        c = not c

      if vi[0] == first_x and vi[1] == first_y:
        i += 1
        if i < n:
          vi = self.points[i]
          first_x, first_y = vi[0], vi[1]
      j = i
      i += 1
    return c


class ZoneLocator:
  def __init__(self, zone_file):
    self.zone_polygon = {}
    print 'parsing polygons...'
    with open(zone_file, 'r') as f:
      lines = f.readlines()[1:]
      for line in lines:
        tokens = line.rstrip().split(',')

        # ODzones_simp_vertices.csv uses Long, Latt
        # ODzones_vertices.csv uses Latt, Long
        zone, lat, lon = int(tokens[2]), float(tokens[4]), float(tokens[3])

        if zone not in self.zone_polygon:
          self.zone_polygon[zone] = Polygon()
        self.zone_polygon[zone].add_point(lon, lat)
    print 'finished parsing polygons'

  def locate(self, lon, lat):
    for zone, polygon in self.zone_polygon.iteritems():
      if polygon.contains(lon, lat):
        return zone
    return -1


class RawTrip:
  def __init__(self, line, zone_locator, stats, logger):
    """
    Args:
      line: Line of string containing the trip record.
    """
    tokens = line.rstrip().split(',')
    for key, index in trip_indices.iteritems():
      value = tokens[index]
      if key.find('time') != -1:
        year, month, day, hour, minute, second = [int(x) for x in re.split('[ :-]', value)]
        value = datetime.datetime(year, month, day, hour, minute, second)
      else:
        try:
          value = float(value)
          if value == 0 and (key.find('lon') != -1 or key.find('lat') != -1):
            value = None
        except Exception:
          value = None

        if value == None: # value is zero if the data is wrong or no value is present
          if key.find('pickup') != -1:
            stats.add_counter('missing_pickup')
            raise Exception('missing pickup location')
          elif key.find('dropoff') != -1:
            stats.add_counter('missing_dropoff')
            raise Exception('missing dropoff location')
          else:
            print >> sys.stderr, 'FATAL ERROR'
      setattr(self, key, value)

    if self.distance < .1:
      stats.add_counter('short_distance')
      raise Exception('short distance < .1 miles')
    elif self.distance > 20:
      stats.add_counter('long_distance')
      raise Exception('long distance > 20 miles')

    self.trip_time = (self.dropoff_time - self.pickup_time).total_seconds() # in seconds
    if self.trip_time <= 0:
      stats.add_counter('invalid_duration')
      raise Exception('invalid duration <= 0 seconds')
    elif self.trip_time < 60:
      stats.add_counter('short_duration')
      raise Exception('short duration < 60 seconds')
    elif self.trip_time > 7200:
      stats.add_counter('long_duration')
      raise Exception('long duration > 2 hours')

    self.speed = self.distance / self.trip_time * 3600 # mph
    if self.speed < 1:
      stats.add_counter('slow_speed')
      raise Exception('slow speed < 1 mph')
    elif self.speed > 100:
      stats.add_counter('fast_speed')
      raise Exception('fast speed > 100 mph')

    vincenty_distance = vincenty((self.pickup_lat, self.pickup_lon),
                                 (self.dropoff_lat, self.dropoff_lon)).miles
    if vincenty_distance < .1:
      stats.add_counter('short_euclidean_distance')
      raise Exception('Euclidean distance < .1 miles')

    #if self.distance >= 3 * vincenty_distance and self.distance <= 10 * vincenty_distance:
    #  logger.add_line('%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n' %
    #                  (self.distance, vincenty_distance, self.distance / vincenty_distance,
    #                   self.pickup_lon, self.pickup_lat,
    #                   self.dropoff_lon, self.dropoff_lat))

    if self.distance < .9 * vincenty_distance:
      stats.add_counter('impossible_short_distance')
      raise Exception('distance < .9 x Euclidean distance')
    elif self.distance > 3. * vincenty_distance:
      stats.add_counter('impossible_long_distance')
      raise Exception('distance > 3 x Euclidean distance')

    self.pickup_zone = zone_locator.locate(self.pickup_lon, self.pickup_lat)
    if self.pickup_zone == -1:
      stats.add_counter('pickup_nozone')
      raise Exception('pickup location not in any zone')
    self.dropoff_zone = zone_locator.locate(self.dropoff_lon, self.dropoff_lat)
    if self.dropoff_zone == -1:
      stats.add_counter('dropoff_nozone')
      raise Exception('dropoff location not in any zone')

    stats.add_counter()


class TripStats:
  def __init__(self):
    # total trip counts
    self.total = 0

    # does not have pickup location
    self.missing_pickup = 0
    # does not have dropoff location
    self.missing_dropoff = 0

    # duration <= 0 seconds
    self.invalid_duration = 0
    # duration < 60 seconds
    self.short_duration = 0
    # duration > 2 hours
    self.long_duration = 0

    # distance < .1 miles
    self.short_distance = 0
    # distance > 20 miles
    self.long_distance = 0
    # Euclidean distance < .1 miles
    self.short_euclidean_distance = 0
    # distance < .5 x Euclidean distance
    self.impossible_short_distance = 0
    # distance > 10 x Euclidean distance
    self.impossible_long_distance = 0

    # speed < 1 mph
    self.slow_speed = 0
    # speed > 100 mph
    self.fast_speed = 0

    # pickup location not in any zone
    self.pickup_nozone = 0
    # dropoff location not in any zone
    self.dropoff_nozone = 0

  def add_counter(self, counter=''):
    self.total += 1
    if counter != '':
      setattr(self, counter, getattr(self, counter) + 1)

  def report(self):
    entries = [
      'missing_pickup',
      'missing_dropoff',
      'invalid_duration',
      'short_duration',
      'long_duration',
      'short_distance',
      'long_distance',
      'short_euclidean_distance',
      'impossible_short_distance',
      'impossible_long_distance',
      'slow_speed',
      'fast_speed',
      'pickup_nozone',
      'dropoff_nozone'
    ]
    print 'total: %d' % self.total
    regular = self.total
    for key in entries:
      count = getattr(self, key)
      regular -= count
      print '%s: %d (%.2f%%)' % (key, count, 1. * count / self.total * 100)
    print 'regular: %d (%.2f%%)' % (regular, 1. * regular / self.total * 100)


class Logger:
  def __init__(self):
    self.logs = []

  def add_line(self, line):
    self.logs.append(line.rstrip())

  def report(self, file='', header=''):
    if file == '':
      if header != '':
        print header + '\n'
      print '\n'.join(self.logs)
    else:
      with open(file, 'w') as f:
        if header != '':
          f.write(header + '\n')
        f.write('\n'.join(self.logs))
