#!/usr/bin/env python

# Process the TLC taxi data CSVs and generate a subset of the data with only relative
# columns for speed analysis.

import sys

numArgs = len(sys.argv)

if numArgs < 3:
    print "Usage: python process.py <trips data> <output file>"
    exit(1)

tripFileName = sys.argv[1]
tripsFile    = open(tripFileName)
tripsHeader  = tripsFile.readline()

outputFileName = sys.argv[2]
outputFile     = open(outputFileName,"w")

# Output header
outputFile.write(\
  'pickup_time,dropoff_time,pickup_long,pickup_lat,dropoff_long,dropoff_lat,' + \
  'id_taxi,distance,fare_amount,surcharge,mta_tax,tip_amount,tolls_amount,payment_type,passengers,' + \
  'field1,field2,field3,field4\n')

# 2009-2014
# 0-4: vendor_id, pickup_datetime, dropoff_datetime, passenger_count, trip_distance
# 5-9: pickup_longitude, pickup_latitude, rate_code, store_and_fwd_flag, dropoff_longitude
# 10-14: dropoff_latitude, payment_type, fare_amount, surcharge, mta_tax
# 15-17: tip_amount, tolls_amount, total_amount
# 2015, 2016 Jan-June
# 0-4: VendorID,tpep_pickup_datetime,tpep_dropoff_datetime,passenger_count,trip_distance
# 5-9: pickup_longitude,pickup_latitude,RateCodeID,store_and_fwd_flag,dropoff_longitude
# 10-14: dropoff_latitude,payment_type,fare_amount,[c]extra,mta_tax
# 15-18: tip_amount,tolls_amount,[+]improvement_surcharge,total_amount
# 2016 July-Dec
# 0-4: VendorID,tpep_pickup_datetime,tpep_dropoff_datetime,passenger_count,trip_distance
# 5-9: RatecodeID,store_and_fwd_flag,PULocationID,DOLocationID,payment_type
# 10-14: fare_amount,extra,mta_tax,tip_amount,tolls_amount
# 15-16: improvement_surcharge,total_amount

# indices for every year are the same, except for 2016 second half
indices = [1, 2, 5, 6, 9, 10, -1, 4, 12, 13, 14, 15, 16, 11, 3]

count = 1
for (tripLine) in tripsFile:
  if tripLine.strip() == '':
    continue
  if count % 100000 == 0:
    print 'Processed %d trips' % (count)
  trip_tokens = [t.strip() for t in tripLine.split(',')]
  index_list = indices
  line = ''
  for i in index_list:
    if i == -1:
      line += 't' + str(count) + ','
    else:
      line += trip_tokens[i] + ','
  line += '0,0,0,0\n'
  outputFile.write(line)
  count += 1
