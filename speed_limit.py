#!/usr/bin/env python

# Process the speed limit data and write into the edge objects.

import sys, re
from dateutil import parser

def process(input_path, output_path, network):
  """Parses the raw speed limit file and generates a new file that contains
  mapped node id's and only the relative information.
  
  Args:
    input_path: Path to the speed limit file.
    output_path: Path to the output speed limit CSV.
    network: RoadNetwork returned by road_network.
  """
  
  print >> sys.stderr, 'reading raw speed limits'
  f_in = open(input_path, 'r')
  f_out = open(output_path, 'w')
  
  # New CSV header.
  f_out.write('id_from,id_to,from_lat,from_lon,to_lat,to_lon,')
  f_out.write('postvz_sl,postvz_sg,sl120415,sg120415,sl110714,sg110714\n')
  
  header = f_in.readline().split(',')
  idx_from_x, idx_from_y = header.index('Start_X'), header.index('Start_Y')
  idx_to_x, idx_to_y = header.index('End_X'), header.index('End_Y')
  idx_sl110714, idx_sg110714 = header.index('sl110714'), header.index('sg110714')
  idx_sl120415, idx_sg120415 = header.index('sl120415'), header.index('sg120415')
  idx_postvz_sl, idx_postvz_sg = header.index('postvz_sl'), header.index('postvz_sg')
  
  total = 0
  for line in f_in.readlines():
    if line.strip() == '':
      break
    total += 1
    line = re.sub('"[^"]+"', '', line)
    tokens = line.split(',')
    from_x, from_y = float(tokens[idx_from_x]), float(tokens[idx_from_y])
    to_x, to_y = float(tokens[idx_to_x]), float(tokens[idx_to_y])
    
    source = network.find_intersection((from_y, from_x))
    target = network.find_intersection((to_y, to_x))
    f_out.write('%d,%d,%f,%f,%f,%f,' % (source, target, from_y, from_x, to_y, to_x))
    f_out.write('%s,%s,%s,%s,%s,%s\n' % (
        tokens[idx_sl110714], tokens[idx_sg110714],
        tokens[idx_sl120415], tokens[idx_sg120415],
        tokens[idx_postvz_sl], tokens[idx_postvz_sg]
      ))
  
  print '%d speed limit records processed' % total
  f_in.close()
  f_out.close()


def read(input_path, network):
  """ Parses a processed speed limit file and writes sign information to the road segments
  in the road network object.
  
  Args:
    input_path: Path to the processed speed limit file.
    network: RoadNetwork returned by road_network.
  """
  
  print >> sys.stderr, 'reading processed speed limit CSV'
  f_in = open(input_path, 'r')
  header = f_in.readline().strip().split(',')
  
  idx_sg110714 = header.index('sg110714')
  idx_sg120415 = header.index('sg120415')
  idx_postvz_sg = header.index('postvz_sg')
  
  counter, missed = 0, 0
  # not installed: no signs ever installed
  # newly installed: sign changes from no to yes
  # fully installed: sign is always yes
  not_installed, newly_installed, fully_installed = 0, 0, 0
  
  # segments with contradicting sign info
  contradictions = {}
  
  for line in f_in.readlines():
    line = line.strip()
    if line == '':
      break
    tokens = line.split(',')
    source, target = int(tokens[0]), int(tokens[1])
    
    sg110714 = tokens[idx_sg110714]
    sg120415 = tokens[idx_sg120415]
    postvz_sg = tokens[idx_postvz_sg]
    
    sign_state = 'no'
    if sg110714 == 'YES' or sg120415 == 'YES' or postvz_sg == 'YES':
      sign_state = 'yes'
    
    if sg110714 == 'YES' and sg120415 == 'YES' and postvz_sg == 'YES':
      fully_installed += 1
    if sg110714 != sg120415 or sg120415 != postvz_sg or sg110714 != postvz_sg:
      newly_installed += 1
    if sign_state == 'no':
      not_installed += 1
    
    solvable = False
    if (source, target) not in network.edge_dict:
      if source == -1 and target == -1:
        continue
      if source == -1 or target == -1:
        print >> sys.stderr, 'only a single endpoint is in Manhattan (%d, %d)' % (source, target)

        continue
      # Both endpoints are found but endpoints are not neighbors.
      # Seek shortest path from source to target.
      edges = network.shortest_path(source, target)
      if len(edges) == 0:
        missed += 1
      solvable = True
    else:
      # Road segment with neighboring endpoints in Manhattan (unexpected)
      # This is a single edge in the road network.
      edges = [network.edge_dict[(source, target)]]
      solvable = True
   
    if solvable:
      counter += 1
      for e in edges:
        new_sign = sign_state
        if e.sign == 'conflict':
          continue
        if e.sign != 'unknown' and e.sign != sign_state:
          contradictions[e.id] = True
          print >> sys.stderr, 'contradiction in sign of %s [%s->%s]' % (
            e.id, e.sign, sign_state)
          print >> sys.stderr, 'edge: ' + str(network.nodes[e.source]) + ',' + str(network.nodes[e.target])
          print >> sys.stderr, \
            'previous: ' + ','.join(e.sign_path) + ' '\
            'current: ' + ','.join(tokens[2:6])
          new_sign = 'conflict'
        e.sign = new_sign
        e.sign_path = tokens[2:6]
  
  print '%d speed limit entries in Manhattan (%d missed)' % (counter, missed)
  print 'not installed: %d, newly installed: %d, fully installed: %d' % (
    not_installed, newly_installed, fully_installed)
  print 'contradictions: %d' % len(contradictions)
  f_in.close()
