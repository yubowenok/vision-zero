# Hourly aggregation for segments

To run the aggregation:
- Place the network files at network/lion_nodes.csv, network/lion_edges.csv
- Place the speed limit data at network/speed_limit.csv
- List the data file paths in a data list file, such as speed_files.txt
- Run the aggregate script:
```bash
python2 aggregate.py --data_list={speed_files.txt} --output={output.csv}
    --bin={hour,is_weekday} [--with_sign/--without_sign]
```

**data_list:** A file listing the data file paths. See speed_files.txt for example.
Edit this list to reflect the actual data paths on your machine.

**output:** Output file path.

**type:** Bin attributes, which is a comma separated string of the following:
"segment", "day_of_month", "time_of_day", "day_of_week", "is_weekday", "hour", "speed_limit", "sign"

**with_sign:** Only includes road segments with speed signs. Segments with "unknown" sign status are ignored.

**without_sign:** Only includes road segments without speed signs. Segments with "unknown" sign status are ignored.
