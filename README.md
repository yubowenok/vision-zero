# vision-zero

Source code for the VisionZero project.

To run the aggregation:
- Place the network files at network/lion_nodes.csv, network/lion_edges.csv
- List the data file paths in a data list file, such as speed_files.txt
- Run the aggregate script:
```bash
python2 aggregate.py --data_list={speed_files.txt} --type={time_of_day} --output={output.csv}
    [--segment_id] [--sign]
```

**data_list:** A file listing the data file paths. See speed_files.txt for example.
Edit this list to reflect the actual data paths on your machine.

**type:** Aggregation type, supported values are
"year", "month", "day_of_month", "time_of_day", "day_of_week", "is_weekday", hour", "speed_limit"

**output:** Output file path.

**segment_id:** Whether to additionally group by segments, i.e. bin id includes segment id.
This defaults to True.

**sign:** Whether to additionally group by with/without sign, i.e. bin id includes whether the road segment
has sign (yes) or not (no), or we have no information (unknown). This requires the speed limit data.
Place the speed limit file at network/speed_limit.csv before turning on this flag.