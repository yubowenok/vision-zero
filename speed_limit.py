#!/usr/bin/env python

# Process the speed limit data and write into the edge objects.

import sys, re
import numpy as np
from dateutil import parser

def process(input_path, output_path, network):
  """Parses the raw speed limit file and generates a new file that contains
  mapped node id's and only the relative information.
  
  Args:
    input_path: Path to the speed limit file.
    output_path: Path to the output speed limit CSV.
    network: RoadNetwork returned by road_network.
  """
  
  print 'reading raw speed limits'
  f_in = open(input_path, 'r')
  f_out = open(output_path, 'w')
  
  # New CSV header.
  f_out.write('id_from,id_to,from_lat,from_lon,to_lat,to_lon,')
  f_out.write('sl110714,sg110714,sl120415,sg120415,postvz_sl,postvz_sg,')
  f_out.write('street\n')
  
  header = f_in.readline().split(',')
  idx_from_x, idx_from_y = header.index('Start_X'), header.index('Start_Y')
  idx_to_x, idx_to_y = header.index('End_X'), header.index('End_Y')
  idx_sl110714, idx_sg110714 = header.index('sl110714'), header.index('sg110714')
  idx_sl120415, idx_sg120415 = header.index('sl120415'), header.index('sg120415')
  idx_postvz_sl, idx_postvz_sg = header.index('postvz_sl'), header.index('postvz_sg')
  idx_street = header.index('street')
  
  total = 0
  lines = f_in.readlines()
  for line in lines:
    if line.strip() == '':
      break
    total += 1
    if total % 10 == 0:
      print '\rprocessing speed limit %.2f%%' % (1.0 * total  / len(lines) * 100),
      sys.stdout.flush()

    line = re.sub('"[^"]+"', '', line)
    tokens = line.split(',')
    from_x, from_y = float(tokens[idx_from_x]), float(tokens[idx_from_y])
    to_x, to_y = float(tokens[idx_to_x]), float(tokens[idx_to_y])
    
    source = network.find_intersection((from_y, from_x))
    target = network.find_intersection((to_y, to_x))
    f_out.write('%d,%d,%f,%f,%f,%f,' % (source, target, from_y, from_x, to_y, to_x))
    f_out.write('%s,%s,%s,%s,%s,%s,' % (
        tokens[idx_sl110714], tokens[idx_sg110714],
        tokens[idx_sl120415], tokens[idx_sg120415],
        tokens[idx_postvz_sl], tokens[idx_postvz_sg]
      ))
    f_out.write('%s\n' % tokens[idx_street])
  
  print '\r' + ' ' * 50 + '\r%d speed limit records processed' % total
  f_in.close()
  f_out.close()
  
  
def get_path_length(edges):
  """ Computes the length of a path.
  Args:
    edges: List of edges in a path. 

  Returns: A float giving the total length of the edges in the path.
  """
  ans = 0
  for e in edges:
    ans += e.dist
  return ans


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

  idx_source, idx_target = header.index('id_from'), header.index('id_to')
  idx_sg110714, idx_sl110714 = header.index('sg110714'), header.index('sl110714')
  idx_sg120415, idx_sl120415 = header.index('sg120415'), header.index('sl120415')
  idx_postvz_sg, idx_postvz_sl = header.index('postvz_sg'), header.index('postvz_sl')
  idx_street = header.index('street')
  
  counter, missed = 0, 0
  # not installed: no signs ever installed
  # newly installed: sign changes from no to yes
  # fully installed: sign is always yes
  not_installed, newly_installed, fully_installed = 0, 0, 0
  
  # segments with contradicting sign info
  contradictions = {}

  lines = f_in.readlines()
  line_counter = 0
  for line in lines:
    line = line.strip()
    if line == '':
      break

    line_counter += 1
    if line_counter % 1000 == 0:
      print '\rreading speed limit %.2f%%' % (1.0 * line_counter / len(lines) * 100),
      sys.stdout.flush()

    tokens = line.split(',')
    source, target = int(tokens[idx_source]), int(tokens[idx_target])
    street = tokens[idx_street]
    
    sg110714, sl110714 = tokens[idx_sg110714], int(tokens[idx_sl110714])
    sg120415, sl120415 = tokens[idx_sg120415], int(tokens[idx_sl120415])
    postvz_sg, postvz_sl = tokens[idx_postvz_sg], int(tokens[idx_postvz_sl])
    
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
      # Seek shortest path from source to target, and target to source.
      # Speed limit could be given in the reversed direction of a one-way road.
      edges = network.shortest_path(source, target, street)
      rev_edges = network.shortest_path(target, source, street)

      if (len(edges) == 0 or get_path_length(edges) > get_path_length(rev_edges)):
        # If the reverse path gives a shorter total length, then we use the reverse path.
        edges = rev_edges

      #for e in edges:
      #  print >> sys.stderr, str(network.nodes[e.source]) + ',' + str(network.nodes[e.target])
      #print >> sys.stderr, '--'

      if len(edges) == 0:
        print >> sys.stderr, 'no path ' + str(network.nodes[source]) + ',' + str(network.nodes[target])
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
        #if e.sign == 'conflict':
        #  continue
        if e.sign != 'unknown' and e.sign != sign_state:
          contradictions[e.id] = True
          print >> sys.stderr, 'contradiction in sign of %s [%s->%s] SP: %s, edge: %s' % (
            e.id, e.sign, sign_state, street, e.street)
          print >> sys.stderr, 'edge: ' + str(network.nodes[e.source]) + ',' + str(network.nodes[e.target])
          print >> sys.stderr, \
            'previous: ' + ','.join(e.sign_path) + ' '\
            'current: ' + ','.join(tokens[2:6])
          new_sign = 'yes'
        e.sign = new_sign
        e.speed_limits.append(postvz_sl)
        e.speed_limit = postvz_sl if e.speed_limit == 0 else max(postvz_sl, e.speed_limit)
        e.sign_path = tokens[2:6]
  
  print '%d speed limit entries in Manhattan (%d missed)' % (counter, missed)
  print 'not installed: %d, newly installed: %d, fully installed: %d' % (
    not_installed, newly_installed, fully_installed)
  print 'contradictions: %d' % len(contradictions)
  f_in.close()


def plot_sign(output_path, network):
  """Generates a scatterplot of points for sign information.
  
  Args:
    output_path: Path to the output file.
    network: Road network.
  """
  f_out = open(output_path, 'w')
  
  f_out.write('segment_id,latitude,longitude,speed_limit,sign\n')
  for e in network.edges:
    source, target = network.nodes[e.source], network.nodes[e.target]
    if e.sign == 'conflict' or e.sign == 'unknown': # skip conflict and unknown for now
      continue
    #f_out.write('%s,%s\n' % (str(source), e.sign))
    #f_out.write('%s,%s\n' % (str(target), e.sign))
    m_lat = (source.lat + target.lat) / 2
    m_lon = (source.lon + target.lon) / 2
    f_out.write('%d,%f,%f,%.2f,%s\n' % (e.segment_id, m_lat, m_lon, e.speed_limit, e.sign))
    