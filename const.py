import datetime

# Time of day definition.
time_of_day_ranges = {
  0: [datetime.time(06, 00, 00), datetime.time(9, 59, 59)],  # morning-peak
  1: [datetime.time(10, 00, 00), datetime.time(15, 59, 59)], # mid-day
  2: [datetime.time(16, 00, 00), datetime.time(19, 59, 59)], # afternoon-peak
  # Left is larger than right. This is left for the 'else' case.
  # 3: [datetime.time(20, 00, 00), datetime.time(05, 59, 59)]  # off-peak
}

time_of_day_names = {
  0: 'morning-peak',
  1: 'mid-day',
  2: 'afternoon-peak',
  3: 'off-peak'
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

season_months = {
  (3, 4, 5): 0,
  (6, 7, 8): 1,
  (9, 10, 11): 2,
  (12, 1, 2): 3
}

season_names = {
  0: 'spring',
  1: 'summer',
  2: 'fall',
  3: 'winter'
}

zone_names = {
  0: 'The Bronx',
  1: 'Staten Island',
  2: 'Brooklyn',
  3: 'Queens',
  4: 'Upper West Side',
  5: 'Downtown Manhattan',
  6: 'Midtown & in-between',
  7: 'Upper East Side',
  8: 'Upper Manhattan'
}
