#!/usr/bin/env python

# Process the road network file and generate nodes, edges objects.

import sys, datetime, math, copy, bisect
from geopy.distance import vincenty
import heapq

class Node:
  def __init__(self, id, lat, lon, virtual=False):
    self.id = id
    self.lat = lat
    self.lon = lon
    self.virtual = virtual
    self.incident_edges = []
    
  def __str__(self):
    return '%f,%f' % (self.lat, self.lon)

  def __cmp__(self, other):
    if self.lat == other.lat:
      return cmp(self.lon, other.lon)
    return cmp(self.lat, other.lat)

  def line_distance(self, other):
    dx, dy = self.lat - other.lat, self.lon - other.lon
    return math.sqrt(dx * dx + dy * dy)


class Edge:
  def __init__(self, edge_id, source, target, dist,
               street='', twoway=False, segment_count=0, segment_id=-1):
    self.id = (source, target)
    self.edge_id = edge_id
    self.source = source
    self.target = target
    self.dist = dist

    self.street = street
    self.twoway = twoway
    self.segment_count = segment_count
    self.segment_id = segment_id

    self.date_inst = datetime.date(1, 1, 1) # Year = 1 denotes no information.
    self.date_inst_path = '' # path that sets the date_inst
    self.sign = 'unknown'
    self.sign_path = '' # path that sets the sign
    self.speed_limit = 0 # speed limit 0 is unknown
    self.speed_limits = [] # all limits identified
  

class RoadNetwork:
  
  # Maximum tolerance for matching intersection.
  intersection_threshold = 0.1
  
  def __init__(self, nodes=[], edges=[]):
    """
    Args:
      nodes: List of nodes.
      edges: List of edges.
    """
    self.nodes = nodes
    self.edges = edges
    self.edge_dict = {}
    for edge in edges:
      self.edge_dict[(edge.source, edge.target)] = edge
      self.nodes[edge.source].incident_edges.append(edge)
  
  def find_intersection(self, point):
    """Finds the intersection that is closest to (lon, lat)
    Returns: Id of the intersection
    """
    best_dist, choice = float('Inf'), -1
    lat, lon = point
    for index, node in enumerate(self.nodes):
      #dist = vincenty(point, (node.lat, node.lon)).miles
      dist = math.sqrt((lat - node.lat) * (lat - node.lat) + (lon - node.lon) * (lon - node.lon))
      #print point, node, dist
      if dist < best_dist:
        best_dist = dist
        choice = index
    best_dist = vincenty(point, (self.nodes[choice].lat, self.nodes[choice].lon)).miles
    if best_dist > self.intersection_threshold:
      #print >> sys.stderr, 'cannot find intersection that matches %s' % (point,)
      return -1
    return choice
    
  def shortest_path(self, source, target, street=''):
    """Finds the shortest path from soruce to target.
    
    Args:
      source: Start point of the path. Node id.
      target: End point of the path. Node id.
      street: Name of the street that should be followed by the path.
      
    Returns: A list of edges describing the shortest path.
    """

    # Shortest path states.
    # Key is (node_id, last_street).
    # Value is an object {
    #   'dist': (change_of_street, distance)
    #   'prev': (previous_state, previous_edge)
    # }
    states = {}
    states[(source, -1)] = {
      'dist': (0, 0),
      'prev': (None, None)  # previous (state, edge_id) in shortest path
    }
    
    heap = []

    heapq.heappush(heap, ((0, 0), (source, -1)))
    
    target_state = None
    while len(heap) > 0:
      cur_dist, cur_state = heapq.heappop(heap)
      if cur_dist > states[cur_state]['dist']:
        continue
      cur_node = cur_state[0]
      if cur_node == target:
        target_state = cur_state
        break
      for e in self.nodes[cur_node].incident_edges:
        street_cost = 1 if cur_state[1] != e.street else 0
        new_dist = (cur_dist[0] + street_cost, cur_dist[1] + e.dist)
        next_state = (e.target, e.edge_id)
        if next_state not in states:
          states[next_state] = {'dist': (int(1e9), float('inf'))}
        if states[next_state]['dist'] > new_dist:
          states[next_state]['dist'] = new_dist
          states[next_state]['prev'] = (cur_state, e.edge_id)
          heapq.heappush(heap, (new_dist, next_state))

    if target_state == None:
      print >> sys.stderr, 'cannot find path from %s/%d to %s/%d' % (
        self.nodes[source], source, self.nodes[target], target)
      return []
    
    source_point = (self.nodes[source].lat, self.nodes[source].lon)
    target_point = (self.nodes[target].lat, self.nodes[target].lon)
    rough_dist = vincenty(source_point, target_point).miles
    if states[target_state]['dist'][1] - rough_dist > 3:
      print >> sys.stderr, 'extra distance > 3 mile, weird path from %s/%d to %s/%d' % (
        self.nodes[source], source, self.nodes[target], target)
      return []
    # Seek shortest path backwards.

    cur_state = target_state
    edges_on_path = []
    while cur_state[0] != source:
      edges_on_path.append(self.edges[states[cur_state]['prev'][1]])
      cur_state = states[cur_state]['prev'][0]
    edges_on_path.reverse()
    return edges_on_path
    """
    dist = [float('Inf')] * len(self.nodes)  # distances for all nodes
    dist[source] = 0

    prev_edge = [-1] * len(self.nodes)  # incoming edge in the shortest path

    heap = []
    heapq.heappush(heap, (0, source))

    target_reached = False
    while len(heap) > 0:
      cur_dist, cur_node = heapq.heappop(heap)
      if cur_dist > dist[cur_node]:
        continue
      if cur_node == target:
        target_reached = True
        break
      for e in self.nodes[cur_node].incident_edges:
        next_node = e.target
        if dist[next_node] > cur_dist + e.dist:
          dist[next_node] = cur_dist + e.dist
          prev_edge[next_node] = e
          heapq.heappush(heap, (dist[next_node], next_node))

    if target_reached == False:
      print >> sys.stderr, 'cannot find path from %s/%d to %s/%d' % (
        self.nodes[source], source, self.nodes[target], target)
      return []

    source_point = (self.nodes[source].lat, self.nodes[source].lon)
    target_point = (self.nodes[target].lat, self.nodes[target].lon)
    rough_dist = vincenty(source_point, target_point).miles
    if dist[target] - rough_dist > 1:
      print >> sys.stderr, 'extra distance > 1 mile, weird path from %s/%d to %s/%d' % (
        self.nodes[source], source, self.nodes[target], target)
      return []
    # Seek shortest path backwards.
    cur_node = target
    edges_on_path = []
    while cur_node != source:
      edges_on_path.append(prev_edge[cur_node])
      cur_node = prev_edge[cur_node].source
    return edges_on_path
    """


  
def read_simple_network(file_path):
  """Parses the road network.
  
  Args:
    file_path: Path to the network file.
  
  Returns:
    A RoadNetwork instance that represents the network.
  """
  
  print 'reading simple road network'
  f = open(file_path, 'r')

  num_nodes, num_edges = [int(x) for x in f.readline().split()]
  nodes, edges = [], []
  edge_dict = {}
  for i in xrange(num_nodes):
    lat, lon = [float(x) for x in f.readline().split()]
    nodes.append(Node(i, lat, lon))
  for i in xrange(num_edges):
    tokens = f.readline().split()
    source, target, dist = int(tokens[0]), int(tokens[1]), float(tokens[2])
    edges.append(Edge(i, source, target, dist))
  print '%d nodes, %d edges' % (num_nodes, num_edges)
  f.close()
  
  return RoadNetwork(nodes, edges)
  

def read_raw_lion(node_file_path, edge_file_path):
  """Parses the network from original LION nodes and edge files.
  
  Args:
    node_file_path: path to the node file.
    edge_file_path: path to the edge file.
    
  Returns:
    A RoadNetwork instance that represents the network.
  """

  node_list, edge_list = [], []
  
  f = open(node_file_path, 'r')
  header = f.readline().strip().split(',')
  idx_node_id = header.index('NODEID')
  idx_virtual = header.index('VIntersect')
  idx_lat, idx_lon = header.index('Y'), header.index('X')
  lines = f.readlines()
  node_counter = 0
  nodes = {}
  for line in lines:
    tokens = line.strip().split(',')
    id = int(tokens[idx_node_id])
    lat, lon = float(tokens[idx_lat]), float(tokens[idx_lon])
    virtual = True if tokens[idx_virtual] == '1' else False
    node = Node(node_counter, lat, lon, virtual)
    nodes[id] = node
    node_counter += 1

    node_list.append(node)

    if node_counter % 1000 == 0:
      print '\rreading nodes %.2f%%' % (1.0 * node_counter / len(lines) * 100),
      sys.stdout.flush()

  print '\r' + ' ' * 50 + '\rreading nodes 100%'
  f.close()

  f = open(edge_file_path, 'r')
  header = f.readline().strip().split(',')
  edge_counter = 0
  idx_street = header.index('Street')
  idx_twoway = header.index('TwoWay')
  idx_seg_count, idx_segment_id = header.index('SegCount'), header.index('SegmentID')
  idx_source, idx_target = header.index('Node_F'), header.index('Node_T')
  lines = f.readlines()

  edge_map = {}
  for line in lines:
    tokens = line.strip().split(',')
    id_source, id_target = int(tokens[idx_source]), int(tokens[idx_target])
    street = tokens[idx_street]
    twoway = True if tokens[idx_twoway] == '1' else False
    segment_count, segment_id = int(tokens[idx_seg_count]), int(tokens[idx_segment_id])
    source_node, target_node = nodes[id_source], nodes[id_target]

    if (source_node.id, target_node.id) in edge_map: # Skip parallel segments
      continue
    edge_map[(source_node.id, target_node.id)] = True

    dist = vincenty((source_node.lat, source_node.lon), (target_node.lat, target_node.lon)).miles

    edge = Edge(edge_counter, source_node.id, target_node.id, dist,
                street=street, twoway=twoway, segment_count=segment_count, segment_id=segment_id)
    edge_counter += 1

    edge_list.append(edge)

    if edge_counter % 10000 == 0:
      print '\rreading edges %.2f%%' % (1.0 * edge_counter / len(lines) * 100),
      sys.stdout.flush()

  print '\r' + ' ' * 50 + '\rreading edges 100%'
  f.close()

  return RoadNetwork(node_list, edge_list)


def prune_network(network_large, network_small):
  """Compares the large network to the small network and only retains those nodes
  that are within or close to the small network. This is to remove the nodes outside Manhattan.
  
  Args:
      network_large: RoadNetwork for all NYC.
      network_small: RoadNetwork for manhattan

  Returns:
      A pruned RoadNetwork instance.
  """
  dist_threshold = .005
  nodes, edges = [], []

  y_nodes = sorted(copy.copy(network_small.nodes))

  id_map = {}
  node_counter = 0
  for index, node_x in enumerate(network_large.nodes):
    if index % 100 == 0:
      print '\rpruning nodes %.2f%%' % (1.0 * index / len(network_large.nodes) * 100),
      sys.stdout.flush()

    hit = False
    pos = bisect.bisect(y_nodes, node_x)
    l, r = pos, pos
    if l == len(y_nodes):
      l -= 1
    while not hit and (l >= 0 or r < len(y_nodes)):
      if l >= 0:
        if y_nodes[l].lat < node_x.lat - dist_threshold:
          l = -1
        else:
          dist = node_x.line_distance(y_nodes[l])
          if dist <= dist_threshold:
            hit = True
          l -= 1
      if r < len(y_nodes):
        if y_nodes[r].lat > node_x.lat + dist_threshold:
          r = len(y_nodes)
        else:
          dist = node_x.line_distance(y_nodes[r])
          if dist <= dist_threshold:
            hit = True
          r += 1
    if not hit:
      continue
    id_map[node_x.id] = node_counter
    node_x.id = node_counter
    nodes.append(node_x)
    node_counter += 1


  edge_counter = 0
  for index, edge in enumerate(network_large.edges):
    if index % 100 == 0:
      print '\rpruning edges %.2f%%' % (1.0 * index / len(network_large.nodes) * 100),
      sys.stdout.flush()

    if edge.source not in id_map or edge.target not in id_map:
      continue
    edge.source = id_map[edge.source]
    edge.target = id_map[edge.target]
    edge.edge_id = edge_counter
    edges.append(edge)
    edge_counter += 1

  print '\r' + ' ' * 50 + '\r%d nodes, %d edges after pruning' % (len(nodes), len(edges))
  return RoadNetwork(nodes, edges)

def read_lion(node_file_path, edge_file_path):
  """Reads the processed LION network nodes and edges.
  
  Args:
      node_file_path: Path to the node file.
      edge_file_path: Path to the edge file.

  Returns: RoadNetwork instance.
  
  """
  node_list, edge_list = [], []

  f = open(node_file_path, 'r')
  header = f.readline().strip().split(',')
  idx_virtual = header.index('virtual')
  idx_lat, idx_lon = header.index('lat'), header.index('lon')
  lines = f.readlines()
  node_counter = 0
  for line in lines:
    tokens = line.strip().split(',')
    lat, lon = float(tokens[idx_lat]), float(tokens[idx_lon])
    virtual = True if tokens[idx_virtual] == '1' else False
    node = Node(node_counter, lat, lon, virtual)
    node_counter += 1

    node_list.append(node)

    if node_counter % 1000 == 0:
      print '\rreading LION nodes %.2f%%' % (1.0 * node_counter / len(lines) * 100),
      sys.stdout.flush()
  print '\r' + ' ' * 50 + '\rreading LION nodes 100%'
  f.close()

  f = open(edge_file_path, 'r')
  header = f.readline().strip().split(',')
  edge_counter = 0
  idx_source, idx_target = header.index('source'), header.index('target')
  idx_dist = header.index('dist')
  idx_street = header.index('street')
  idx_segment_count = header.index('segment_count')
  idx_twoway = header.index('twoway')
  lines = f.readlines()
  for line in lines:
    tokens = line.strip().split(',')
    id_source, id_target = int(tokens[idx_source]), int(tokens[idx_target])
    dist = float(tokens[idx_dist])
    street = tokens[idx_street]
    twoway = True if tokens[idx_twoway] == '1' else False
    segment_count = int(tokens[idx_segment_count])

    edge = Edge(edge_counter, id_source, id_target, dist,
                street=street, twoway=twoway, segment_count=segment_count)
    edge_counter += 1
    edge_list.append(edge)
    if edge_counter % 10000 == 0:
      print '\rreading LION edges %.2f%%' % (1.0 * edge_counter / len(lines) * 100),
      sys.stdout.flush()
  print '\r' + ' ' * 50 + '\rreading LION edges 100%'
  f.close()

  return RoadNetwork(node_list, edge_list)


def write_lion_csv(network, node_csv, edge_csv):
  """Writes the network to node and edge csv files.
  
  Args:
      network: RoadNetwork to be written.
      node_csv: Path to node csv file.
      edge_csv: Path to edge csv file.
  """

  f = open(node_csv, 'w')
  f.write('lat,lon,virtual\n')
  for node in network.nodes:
    f.write('%f,%f,%d\n' % (node.lat, node.lon, int(node.virtual)))
  f.close()
  print node_csv + ' written'

  f = open(edge_csv, 'w')
  f.write('source,target,dist,street,segment_count,twoway\n')
  for edge in network.edges:
    twoway = int(edge.twoway)
    f.write('%d,%d,%f,%s,%d,%d\n' % (edge.source, edge.target, edge.dist,
                                     edge.street, edge.segment_count, twoway))
    if (twoway == 1) and ((edge.target, edge.source) not in network.edge_dict):
      print >> std.err, 'missing reverse edge for twoway road'
      f.write('%d,%d,%f,%s,%d,%d\n' % (edge.target, edge.source, edge.dist,
                                       edge.street, edge.segment_count, twoway))
  f.close()
  print edge_csv + ' written'


def write_clean_network(network, output_file_path):
  """Writes the network to a simple network file.
  
  Args:
      network: RoadNetwork instance.
      output_file_path: Path to output file.
  """
  f = open(output_file_path, 'w')
  f.write('%d %d\n' % (len(network.nodes), len(network.edges)))
  for node in network.nodes:
    f.write('%f %f\n' % (node.lat, node.lon))
  for edge in network.edges:
    f.write('%d %d %f\n' % (edge.source, edge.target, edge.dist))

  print output_file_path + ' written'
  f.close()

