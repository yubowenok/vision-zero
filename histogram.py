#!/usr/bin/env python

# Process the generated histogram bin counts and produce histogram plots.

import sys, datetime, re, os
import argparse

parser = argparse.ArgumentParser(
  description='Plot the aggregated histogram bin counts.')
parser.add_argument('--data_list', dest='data_list', type=str, required=True,
                    help='file listing the data paths')
parser.add_argument('--type', dest='type', type=str, default='speed',
                    help='histogram type: speed/distance')
parser.add_argument('--output', dest='output', type=str, required=True,
                    help='output directory')

args = parser.parse_args()

if args.type != 'speed' and args.type != 'distance':
  print >> sys.stderr, 'unsupported histogram type "%s"' % args.type
  sys.exit(1)

histogram_type = args.type

if not os.path.exists(args.output):
  os.mkdir(args.output)

from ggplot import *
import pandas as pd

bins, bins_sp, bins_diff = {}, {}, {}
bin_count = None
f_data = open(args.data_list, 'r')

def write_bin(line, bins, bin_id):
  count_tokens = line.strip().split(' ')
  counts = [int(x) for x in count_tokens[:-1]]
  exceptions = int(count_tokens[-1])

  if bin_id not in bins:
    bins[bin_id] = {
      'counts': counts,
      'exceptions': exceptions
    }
  else:
    bins[bin_id]['counts'] = [x + y for x, y in zip(bins[bin_id]['counts'], counts)]
    bins[bin_id]['exceptions'] += exceptions

for data_file in f_data.readlines():
  if data_file.strip() == '':
    continue
  print >> sys.stderr, 'processing %s' % data_file.strip()
  f = open(data_file.strip(), 'r')
  lines, line_index = f.readlines(), 0
  num_lines = len(lines)
  while line_index < num_lines:
    dt_tokens = [int(x) for x in re.split('-|_', lines[line_index].strip())]
    year, month, day, hour, minute, second = dt_tokens
    bin_id = (year, month)
    write_bin(lines[line_index+1], bins, bin_id)
    line_index += 2

    if histogram_type == 'distance':
      write_bin(lines[line_index], bins_sp, bin_id)
      write_bin(lines[line_index+1], bins_diff, bin_id)
      line_index += 2

def norm_date(y, m):
  return str(y) + '-' + ('0' + str(m) if m < 10 else str(m))

def bin_id_formatter(x):
  # The first two attrs are year, month and are formatted as YYYY-MM
  elements = [norm_date(x[0], x[1])] + [str(s) for s in x[2:]]
  return ','.join(elements)

if histogram_type == 'speed':
  for bin_id, val in bins.iteritems():
    counts, exceptions = val['counts'], val['exceptions']
    df = pd.DataFrame({'speed': range(100), 'count': counts})
    dt = bin_id_formatter(bin_id)
    plot = ggplot(aes(x='speed', weight='count'), df) + geom_bar() + \
           scale_x_continuous(breaks=range(0,20,1), labels=range(0,20,1), limits=(0,20)) + \
           xlab('%s (total = %d, exceptions = %d)' % (dt, sum(counts), exceptions))
    img_path = os.path.join(args.output, dt + '.png')
    plot.save(img_path)
elif histogram_type == 'distance':
  breaks = range(0,120,10)
  ticks = [float(x)/10. for x in range(0,120,10)]
  limits = (0,120)
  for bin_id, val in bins.iteritems():
    counts, exceptions = val['counts'], val['exceptions']
    df = pd.DataFrame({'speed': range(300), 'count': counts})
    dt = bin_id_formatter(bin_id)
    plot = ggplot(aes(x='speed', weight='count'), df) + geom_bar() + \
           scale_x_continuous(breaks=breaks, labels=ticks, limits=limits) + \
           xlab('%s (total = %d, exceptions = %d)' % (dt, sum(counts), exceptions))
    img_path = os.path.join(args.output, dt + '_real_dist.png')
    plot.save(img_path)
  for bin_id, val in bins_sp.iteritems():
    counts, exceptions = val['counts'], val['exceptions']
    df = pd.DataFrame({'speed': range(300), 'count': counts})
    dt = bin_id_formatter(bin_id)
    plot = ggplot(aes(x='speed', weight='count'), df) + geom_bar() + \
           scale_x_continuous(breaks=breaks, labels=ticks, limits=limits) + \
           xlab('%s (total = %d, exceptions = %d)' % (dt, sum(counts), exceptions))
    img_path = os.path.join(args.output, dt + '_sp_dist.png')
    plot.save(img_path)
  for bin_id, val in bins_diff.iteritems():
    counts, exceptions = val['counts'], val['exceptions']
    df = pd.DataFrame({'speed': range(600), 'count': counts})
    dt = bin_id_formatter(bin_id)
    plot = ggplot(aes(x='speed', weight='count'), df) + geom_bar() + \
           scale_x_continuous(breaks=range(300-50,300+50,10),
                              labels=[float(x)/10.-30 for x in range(300-50,300+50,10)],
                              limits=(300-50,300+50)) + \
           xlab('%s (total = %d, exceptions = %d)' % (dt, sum(counts), exceptions))
    img_path = os.path.join(args.output, dt + '_diff_dist.png')
    plot.save(img_path)