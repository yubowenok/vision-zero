#!/usr/bin/env python

# Process the sign installation records and write into the edge objects.

import sys, re
from dateutil import parser

def process(input_path, output_path, network):
  """Parses the raw sign installation file and generate a new file that contains
  mapped node id's and only the relative information.
  
  Args:
    input_path: Path to the sign installation file.
    output_path: Path to the output sign installation CSV.
    network: RoadNetwork returned by road_network.
  """
  
  print >> sys.stderr, 'reading raw sign installation'
  f_in = open(input_path, 'r')
  f_out = open(output_path, 'w')
  
  # New CSV header.
  f_out.write('id_from,id_to,from_lat,from_lon,to_lat,to_lon,date_inst\n')
  
  header = f_in.readline().split(',')
  idx_from_x, idx_from_y, idx_to_x, idx_to_y, idx_date_inst = header.index('From_X'), header.index('From_Y'), header.index('To_X'), header.index('To_Y'), header.index('Date_Inst')
  
  total = 0
  for line in f_in.readlines():
    if line.strip() == '':
      break
    total += 1
    line = re.sub('"[^"]+"', '', line)
    tokens = line.split(',')
    from_x, from_y = float(tokens[idx_from_x]), float(tokens[idx_from_y])
    to_x, to_y = float(tokens[idx_to_x]), float(tokens[idx_to_y])
    #date_inst = parser.parse(tokens[idx_date_inst])
    date_inst = tokens[idx_date_inst]
    
    source = network.find_intersection((from_y, from_x))
    target = network.find_intersection((to_y, to_x))
    f_out.write('%d,%d,%f,%f,%f,%f,%s\n' % (source, target, from_y, from_x, to_y, to_x, date_inst))
  
  print '%d sign installation records processed' % total
  f_in.close()
  f_out.close()


def read(input_path, network):
  """ Parses a processed sign installation file and writes installation dates to the road segments
  in the road network object.
  
  Args:
    input_path: Path to the processed sign installation file.
    network: RoadNetwork returned by road_network.
  """
  
  print >> sys.stderr, 'reading raw sign installation'
  f_in = open(input_path, 'r')
  header = f_in.readline()
  
  for line in f_in.readlines():
    if line.strip() == '':
      break
    tokens = line.split(',')
    source, target = int(tokens[0]), int(tokens[1])
    
    if (source, target) not in network.edge_dict:
      if source == -1 and target == -1:
        continue
      if source == -1 or target == -1:
        print >> sys.stderr, 'only a single endpoint is in Manhattan (%d, %d)' % (source, target) 
        continue
      # Both endpoints are found but endpoints are not neighbors.
      # Seek shortest path from source to target.
      edges = network.shortest_path(source, target)
      
    else:
      print 'road segment with neighboring endpoints in Manhattan (unexpected)'
  
  f_in.close()
