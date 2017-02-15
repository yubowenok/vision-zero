#!/usr/bin/env python

# Process the road network file and generate nodes, edges objects.

import sys, datetime, math
from geopy.distance import vincenty
import heapq

class Node:
  def __init__(self, id, lat, lon):
    self.id = id
    self.lat = lat
    self.lon = lon
    self.incident_edges = []
    
  def __str__(self):
    return '%f,%f' % (self.lat, self.lon)


class Edge:
  def __init__(self, source, target, dist):
    self.id = (source, target)
    self.source = source
    self.target = target
    self.dist = dist
    self.date_inst = datetime.date(1, 1, 1) # Year = 1 denotes no information.
    self.date_inst_path = '' # path that sets the date_inst
    self.sign = 'unknown'
    self.sign_path = '' # path that sets the sign
  

class RoadNetwork:
  
  # Maximum tolerance for matching intersection.
  intersection_threshold = 0.1
  
  def __init__(self, nodes=[], edges=[]):
    """
    Args:
      nodes: List of node tuples (lat, lon).
      edges: List of edge tuples (source, target, dist)
    """
    self.nodes = []
    self.edges = []
    self.edge_dict = {}
    for index, node in enumerate(nodes):
      self.nodes.append(Node(index, node[0], node[1]))
    for edge in edges:
      e = Edge(edge[0], edge[1], edge[2])
      self.edges.append(e)
      self.edge_dict[(e.source, e.target)] = e
      self.nodes[e.source].incident_edges.append(e)
  
  def find_intersection(self, point):
    """Finds the intersection that is closest to (lon, lat)
    Returns: Id of the intersection
    """
    best_dist, choice = float('Inf'), -1
    lat, lon = point
    for index, node in enumerate(self.nodes):
      dist = vincenty(point, (node.lat, node.lon)).miles
      #dist = math.sqrt((lat - node[0]) * (lat - node[0]) + (lon - node[1]) * (lon - node[1]))
      #print point, node, dist
      if dist < best_dist:
        best_dist = dist
        choice = index
    if best_dist > self.intersection_threshold:
      #print >> sys.stderr, 'cannot find intersection that matches %s' % (point,)
      return -1
    return choice
    
  def shortest_path(self, source, target):
    """Finds the shortest path from soruce to target.
    
    Args:
      source: Start point of the path.
      target: End point of the path.
      
    Returns: A list of edges describing the shortest path.
    """
    
    dist = [float('Inf')] * len(self.nodes) # distances for all nodes
    dist[source] = 0
    
    prev_edge = [-1] * len(self.nodes)      # incoming edge in the shortest path
    
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

  
def read(file_path):
  """Parses the road network.
  
  Args:
    file_path: Path to the network file.
  
  Returns:
    A dict that contains list of intersections, list of road segments,
    and mapping from road id (source, target) to edge objects.
    {
      'nodes': [(long, lat), ...],
      'edges': [{
        'source': 0,
        'target': 1,
      }, ...],
      'edge_dict': {(0, 1): {...}, ...}
    }
  """
  
  print >> sys.stderr, 'reading road network'
  f = open(file_path, 'r')

  num_nodes, num_edges = [int(x) for x in f.readline().split()]
  nodes, edges = [], []
  edge_dict = {}
  for i in xrange(num_nodes):
    lat, lon = [float(x) for x in f.readline().split()]
    nodes.append((lat, lon))
  for i in xrange(num_edges):
    tokens = f.readline().split()
    source, target, dist = int(tokens[0]), int(tokens[1]), float(tokens[2])
    edges.append((source, target, dist))
  
  print >> sys.stderr, '%d nodes, %d edges' % (num_nodes, num_edges)
  f.close()
  
  return RoadNetwork(nodes, edges)