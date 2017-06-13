#!/bin/bash

data_path='/data/taxi'
preprocess_path='/Users/bowen/TaxiVis/src/preprocess'

raw_file=$data_path/raw/yellow_tripdata_$1.csv
csv_file=$data_path/trips/yellow_$1.csv
binary_file=$data_path/trips/yellow_$1.bin
kdtrip_file=$data_path/trips/yellow_$1.kdtrip

echo convert $raw_file to $csv_file
pypy $data_path/process_taxi_csv.py $data_path/raw/yellow_tripdata_$1.csv $data_path/trips/yellow_$1.csv

echo make binary $binary_file
$preprocess_path/csv2binary $data_path/trips/yellow_$1.csv $data_path/trips/yellow_$1.bin

echo build kdtrip $kdtrip_file
$preprocess_path/build_kdtrip $data_path/trips/yellow_$1.bin $data_path/trips/yellow_$1.kdtrip

