#ifndef CITY_MAP_HPP
#define CITY_MAP_HPP

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string>
#include <vector>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <fstream>
#include <unordered_map>
#include <unordered_set>

#ifndef Q_MOC_RUN
#include <boost/filesystem.hpp>
#include <boost/graph/graph_traits.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/dijkstra_shortest_paths.hpp>
#include <boost/iostreams/device/mapped_file.hpp>
#endif // Q_MOC_RUN

class CityMap
{
public:
  struct Location {
    Location() {}
    Location(double la, double lo): lat(la), lon(lo) {}
    double lat, lon;
    
    double & operator[](int i) { return ((double*)this)[i]; }
    const double & operator[](int i) const { return ((double*)this)[i]; }
  };

  struct Vec {
    int   dir;
    float speedMean;
    float speedStd;
    float speedCustom;
    int   numSamples;
    float totalWeight;
    float tempT;

    Vec():speedMean(0), speedStd(0), speedCustom(0), numSamples(0), totalWeight(0), tempT(0) {}
  };

  struct IntersectionProperty {
    std::unordered_map<int, Vec> vectors;
    int                          totalNumSamples;

    IntersectionProperty():totalNumSamples(0) {}

    void addSampleVec(int edgeId, float speed, float weight) {
      Vec &vec = vectors[edgeId];
      vec.dir = edgeId;
      if (vec.numSamples==0) { // Initialize
        vec.speedCustom = speed;
        vec.dir         = edgeId;
        vec.speedMean   = speed;
        vec.speedStd    = 0;
        vec.numSamples  = 1;
        vec.totalWeight = weight;
        vec.tempT       = 0;
      } else { // Update mean and counter
        float M = vec.speedMean;
        vec.speedCustom += speed;
        vec.tempT       += weight*(speed-M)*(speed-M)*vec.totalWeight/(vec.totalWeight+weight);
        vec.speedMean   += weight*(speed-M)/(vec.totalWeight+weight);
        vec.totalWeight += weight;
        vec.numSamples++;
        vec.speedStd     = sqrt(vec.tempT/( (vec.numSamples-1)*vec.totalWeight/vec.numSamples ) );
      }
      totalNumSamples++;
    }
  };

  struct EdgeProperty {
    EdgeProperty() {}
    EdgeProperty(float l, int idx): weight(l), index(idx) {}
    float weight;
    int   index;
  };

  typedef std::pair<int,int> IntPair;
  typedef std::vector<int> IntVec;
  typedef std::vector<float> FloatVec;
  typedef boost::unordered_set<int> IntSet;
  typedef boost::unordered_map<int,int> IntMap;
  typedef boost::unordered_map<int,IntMap> Int2Map;
  typedef IntVec Path;
  typedef IntPair Street;
  typedef boost::unordered_map<CityMap::Street, int> StreetMap;

public:
  CityMap(): GRID_DEGREE(0.001) {}
  
  CityMap(const char * filename): GRID_DEGREE(0.001), timeStamp(0)
  {
    this->loadFromFile(filename);
  }

  inline void setIntersection(int idx, const Location &L)
  {
    this->intersections[idx] = L;
    if (L.lat<this->bounds[0].lat) this->bounds[0].lat = L.lat;
    if (L.lat>this->bounds[1].lat) this->bounds[1].lat = L.lat;
    if (L.lon<this->bounds[0].lon) this->bounds[0].lon = L.lon;
    if (L.lon>this->bounds[1].lon) this->bounds[1].lon = L.lon;
  }

  inline void setStreet(int idx, const Street &S, float weight)
  {
    this->streets[idx] = S;
    this->streetId[S] = idx;
    this->streetProps[idx] = EdgeProperty(weight, idx);
  }

  inline void initCity(int nV, int nE)
  {
    this->intersections.resize(nV);
    this->streets.resize(nE);
    this->streetId.rehash(nE/ceil(this->streetId.max_load_factor())+1);
    this->streetProps.resize(nE);
    this->intersectionProps.resize(nV);
    this->bounds[0] = Location(1e36, 1e36);
    this->bounds[1] = Location(-1e36, -1e36);
  }

  void loadFromText(const char *filename)
  {
    FILE *fi = fopen(filename, "r");
    int nV, nE;
    bool hasWeight;
    fscanf(fi, "%d %d", &nV, &nE);
    hasWeight = nE<0;
    if (nE<0)
      nE = -nE;
    this->initCity(nV, nE);
    for (int i=0; i<nV; i++) {
      Location L;
      fscanf(fi, "%lf %lf", &L.lat, &L.lon);
      this->setIntersection(i, L);
    }
    char line[100];
    fgets(line, sizeof(line), fi);
    for (int i=0; i<nE; i++) {
      int idx[2];
      float weight;
      fgets(line, sizeof(line), fi);
      // skip weight from text file and compute distances
      sscanf(line, "%d %d %f", idx, idx+1, &weight);
      weight = CityMap::distance(this->intersections[idx[0]], this->intersections[idx[1]]);
      this->setStreet(i, Street(idx[0], idx[1]), weight);
    }
    fclose(fi);
  }

  void loadFromBinary(const char *filename)
  {
    FILE *fi = fopen(filename, "rb");
    int nV, nE;
    bool hasWeight;
    fread(&nV, sizeof(nV), 1, fi);
    fread(&nE, sizeof(nE), 1, fi);
    hasWeight = nE<0;
    if (nE<0)
      nE = -nE;
    this->initCity(nV, nE);
    for (int i=0; i<nV; i++) {
      Location L;
      fread(&L, sizeof(double), 2, fi);
      this->setIntersection(i, L);
    }
    for (int i=0; i<nE; i++) {
      int idx[2];
      float weight;
      fread(idx, sizeof(int), 2, fi);
      if (hasWeight) {
        fread(&weight, sizeof(float), 1, fi);
      }
      else
        weight = CityMap::distance(this->intersections[idx[0]], this->intersections[idx[1]]);
      this->setStreet(i, Street(idx[0], idx[1]), weight);
    }
    fclose(fi);
  }
    
#pragma pack(push,1)
  struct OSRMNode
  {
    int lat;
    int lon;
    int id;
    uint8_t bollard;
    uint8_t traffic;
    uint8_t unused[2];
  };

  struct OSRMEdge
  {
    uint32_t src;
    uint32_t dst;
    int distance;
    uint16_t oneway;
    int weight;
    uint16_t edgeType;
    int nameIndex;
    uint8_t roundabout;
    uint8_t ignoreInGrid;
    uint8_t accessRestricted;
  };
#pragma pack(pop)

  void loadFromOSRM(const char *filename)
  {
    FILE *fi = fopen(filename, "rb");
    int nV, nE, cnt;
    std::vector<OSRMNode> nodes;
    std::vector<OSRMEdge> edges;
    
    boost::unordered_map<int,int> nodeMap;
    fread(&nV, sizeof(int), 1, fi);
    nodes.resize(nV);
    fread(&nodes[0], sizeof(OSRMNode), nV, fi);
    for (int i=0; i<nV; i++)
      nodeMap[nodes[i].id] = i;
        
    fread(&nE, sizeof(int), 1, fi);
    edges.resize(nE);
    nE = fread(&edges[0], sizeof(OSRMEdge), nE, fi);
    fclose(fi);
    cnt = 0;
    for (int i=0; i<nE; i++)
      cnt += !edges[i].oneway;
    this->initCity(nV, cnt+nE);
    for (int i=0; i<nV; i++)
      this->setIntersection(i, Location(nodes[i].lat*1e-5, nodes[i].lon*1e-5));
    for (int i=0, cnt=0; i<nE; i++) {
      this->setStreet(cnt++, Street(nodeMap[edges[i].src], nodeMap[edges[i].dst]), edges[i].weight);
      if (!edges[i].oneway)
        this->setStreet(cnt++, Street(nodeMap[edges[i].dst], nodeMap[edges[i].src]), edges[i].weight);
    }
  }
    
  void loadFromFile(const char *filename)
  {
    std::string ext = boost::filesystem::extension(filename);
    if (ext==".txt")
      this->loadFromText(filename);
    else if (ext==".osrm")
      this->loadFromOSRM(filename);
    else
      this->loadFromBinary(filename);
  
    this->city = Graph(this->streets.begin(), this->streets.end(), this->streetProps.begin(), this->intersections.size());

    this->center.lat = (this->bounds[0].lat+this->bounds[1].lat)*0.5;
    this->center.lon = (this->bounds[0].lon+this->bounds[1].lon)*0.5;
    double dLat = CityMap::distance(Location(this->center.lat-0.5, this->center.lon),
                                    Location(this->center.lat+0.5, this->center.lon));
    double dLon = CityMap::distance(Location(this->center.lat, this->center.lon-0.5),
                                    Location(this->center.lat, this->center.lon+0.5));
    this->ratioLatLon = dLat/dLon;

    this->buildIndex();
  }

  void loadVectors(const char *vectorFilename)
  {
    std::ifstream inFile(vectorFilename);
    std::string line;
    int numVectors;
    int dir, numSamples;
    float mean, sd;
    int nodeId = 0;
    this->globalNumberOfSamples = 0;
    while(std::getline(inFile, line)) {
      CityMap::IntersectionProperty &iProp = this->intersectionProps[nodeId++];

      std::istringstream in(line);
      in >> numVectors;
      int totalNumSamples = 0;
      for (int i=0; i<numVectors; ++i) {
        in >> dir >> mean >> sd >> numSamples;

        CityMap::Vec &vec = iProp.vectors[dir];
        vec.dir = dir;
        vec.speedMean = mean;
        vec.speedStd  = sd;
        vec.numSamples = numSamples;
        totalNumSamples += numSamples;
      }
      iProp.totalNumSamples = totalNumSamples;
      this->globalNumberOfSamples += totalNumSamples;
    }
    inFile.close();
  }

  void saveToText(const char *filename)
  {
    // save graph
    std::ofstream out(filename);
    out.precision(6);
    out << numIntersections() << " " << numStreets() << std::endl;
    for (auto &loc: this->intersections) {
      out << std::fixed << loc.lat << " " << loc.lon << std::endl;
    }
    for (auto &edge: this->streets) {
      out << edge.first << " " << edge.second << " " << getStreetWeight(edge) << std::endl;
    }
    out.close();
  }

  void saveVectors(const char *vectorFilename)
  {
    // save vectors in a text file
    // row number is the vertex id
    // Format:
    //  numVectors    dir1 mean1 std1 numSamples1    dir2 mean2 std2 numSamples2 .... dirn meann stdn numSamplesn
    //   ...
    std::ofstream out(vectorFilename);
    for (int nId=0; nId<numIntersections(); ++nId) {
      CityMap::IntersectionProperty &iProp = getIntersectionProperty(nId);
      out << iProp.vectors.size() << " ";
      for (auto pVec: iProp.vectors) {
        const CityMap::Vec &vec = pVec.second;
        out << vec.dir << " " << vec.speedMean << " " << vec.speedStd << " " << vec.numSamples << " ";
      }
      out << std::endl;
    }
    out.close();
  }

  // Merge the speed from another CityMap instance.
  void mergeSpeed(CityMap &ano) {
    for (int i = 0; i < (int)streets.size(); i++) {
      auto &edge = streets[i];
      CityMap::IntersectionProperty &iProp = getIntersectionProperty(edge.first);
      int eid = getStreetId(Street(edge.first, edge.second));
      if (iProp.vectors.count(eid) != 0) {
        CityMap::Vec &vec = iProp.vectors[eid];

        // Get corresponding street in the other CityMap
        auto &anoEdge = ano.getStreet(i);
        CityMap::IntersectionProperty &iPropAno = ano.getIntersectionProperty(anoEdge.first);
        const CityMap::Vec &anoVec = iPropAno.vectors[eid];

        vec.speedMean = (vec.speedMean * vec.totalWeight + anoVec.speedMean * anoVec.totalWeight) /
            (vec.totalWeight + anoVec.totalWeight);
        vec.speedCustom += anoVec.speedCustom;
      }
    }
  }

  void exportSpeeds(std::ofstream &out, std::string timestamp) {
    out << timestamp << " ";
    for (auto &edge: this->streets) {
      CityMap::IntersectionProperty &iProp = getIntersectionProperty(edge.first);

      int eid = getStreetId(Street(edge.first, edge.second));
      if (iProp.vectors.count(eid)==0) {
        out << "-1 ";
      } else {
        const CityMap::Vec &vec = iProp.vectors[eid];
        // Average speed
        //out.precision(4);
        //out << vec.speedMean << " ";
        out << vec.speedCustom << " ";
      }
    }
    out << "\n";
  }

  inline void getBounds(double rect[4]) const
  {
    rect[0] = this->bounds[0].lat;
    rect[1] = this->bounds[0].lon;
    rect[2] = this->bounds[1].lat;
    rect[3] = this->bounds[1].lon;
  }

  inline size_t numIntersections() const
  {
    return this->intersections.size();
  }
  
  inline const Location & getIntersection(int idx) const
  {
    return this->intersections[idx];
  }

  inline size_t numStreets() const
  {
    return this->streets.size();
  }
  
  inline const Street & getStreet(int idx) const
  {
    return this->streets[idx];
  }

  inline float getStreetWeight(const Street &S) const
  {
    StreetMap::const_iterator it = this->streetId.find(S);
    if (it!=this->streetId.end())
      return this->streetProps[it->second].weight;
    return 0;
  }

  inline bool setStreetWeight(const Street &S, float weight)
  {
    StreetMap::const_iterator it = this->streetId.find(S);
    if (it!=this->streetId.end()) {
      this->streetProps[it->second].weight = weight;
      return true;
    }
    return false;
  }

  inline int getStreetId(const Street &S) const
  {
    StreetMap::const_iterator it = this->streetId.find(S);
    if (it!=this->streetId.end())
      return this->streetProps[it->second].index;
    return -1;
  }
  
  inline IntersectionProperty& getIntersectionProperty(int idx)
  {
    return this->intersectionProps[idx];
  }

  int mapToIntersection(const Location &loc) const
  {
    int X = this->gridX(loc.lat);
    int Y = this->gridY(loc.lon);
    if (X<0 || X>=this->gridSize[0] || Y<0 || Y>=this->gridSize[1])
      return -1;
    int minInter = -1;
    double len = 1e30;
    for (int dy=-1; dy<=1; dy++) {
      for (int dx=-1; dx<=1; dx++) {
        if (X+dx>=0 && X+dx<this->gridSize[0] &&
            Y+dy>=0 && Y+dy<this->gridSize[1]) {
          int gid = (Y+dy)*this->gridSize[0]+(X+dx);
          for (int i=0; i<this->gridCount[gid]; i++) {
            int inter = this->gridIntersections[this->gridIndex[gid]+i];
            double dis = CityMap::pseudo_distance(loc, this->intersections[inter], this->ratioLatLon);
            if (minInter<0 || dis<len) {
              minInter = inter;
              len = dis;
            }
          }
        }
      }
    }
    if (minInter==-1) {
      int idx = this->nearestIntersection(loc);
      len = CityMap::distance(loc, this->intersections[idx]);
      if (len<0.35)
        minInter = idx;
    }
    return minInter;
  }

  int nearestIntersection(const Location &p) const
  {
    int minInter = -1;
    double minDis = 1e36;
    this->searchKdNearestIntersection(p, 0, 0, minInter, minDis);
    return minInter;
  }

  inline int shortestPath(int src, int dst, int *prev, float *dist) const
  {
    CityMap::dijkstra_exit_on_dst visitor(dst);
    try {
      boost::dijkstra_shortest_paths(this->city, src,
                                     boost::predecessor_map(prev)
                                     .distance_map(dist)
                                     .weight_map(boost::get(&EdgeProperty::weight, this->city))
                                     .visitor(visitor)
                                     );
    } catch (const CityMap::dijkstra_exit_exception) {
      return 1;
    }
    return 0;
  }
  
  inline int shortestPaths(int src, IntSet &dst, int *prev, float *dist) const
  {
    CityMap::dijkstra_exit_on_dst_set visitor(&dst);
    int dstCount = dst.size();
    try {
      boost::dijkstra_shortest_paths(this->city, src,
                                     boost::predecessor_map(prev)
                                     .distance_map(dist)
                                     .weight_map(boost::get(&EdgeProperty::weight, this->city))
                                     .visitor(visitor)
                                     );
    } catch (const CityMap::dijkstra_exit_exception) {
    }
    return dstCount-dst.size();
  }

  inline void shortestPaths(int src, int *prev, float *dist) const
  {
    boost::dijkstra_shortest_paths(this->city, src,
                                   boost::predecessor_map(prev)
                                   .distance_map(dist)
                                   .weight_map(boost::get(&EdgeProperty::weight, this->city))
                                   );
  }

  inline void buildAllShortestPaths()
  {
    this->allPaths.resize(3*this->numIntersections()*this->numIntersections());
    this->allPrev = &this->allPaths[0];
    this->allDist = (float*)(this->allPrev + this->numIntersections()*this->numIntersections());
    this->allRDist = this->allDist + this->numIntersections()*this->numIntersections();
    fprintf(stderr, "Compute all shortest paths...\n");
    for (int src=0; src<this->numIntersections(); src++) {
      fprintf(stderr, "\r%d/%lu", src, this->numIntersections()-1);
      boost::dijkstra_shortest_paths(this->city, src,
                                     boost::predecessor_map(&this->allPrev[src*this->numIntersections()])
                                     .distance_map(&this->allDist[src*this->numIntersections()])
                                     .weight_map(boost::get(&EdgeProperty::weight, this->city))
                                     );
    }
    fprintf(stderr, "Compute reversed distances...\n");
    for (int src=0; src<this->numIntersections(); src++)
      for (int dst=0; dst<this->numIntersections(); dst++)
        this->allRDist[src*this->numIntersections()+dst] = this->allDist[dst*this->numIntersections()+src];
    fprintf(stderr, "\n");
  }

  double getShortestPathDistance(int src, int dst) {
    return this->allDist[src*this->numIntersections() + dst];
  }

  void topK(int k, int src, int dst, float distance, std::vector<Path> &paths) const
  {
    float *ds = this->allDist + src*this->numIntersections();
    if (src==dst || src==-1 || dst==-1 || ds[dst]>1e38) {
      paths.clear();
      return;
    }
    int *prev = this->allPrev + src*this->numIntersections();
    float *dd = this->allRDist + dst*this->numIntersections();
    std::vector< std::pair<int, int> > V;
    boost::unordered_set<uint32_t> found;
    for (int mid=0; mid< this->numIntersections(); mid++) {
      float w = (prev[mid]!=mid)?fabs(ds[mid]+dd[mid]-distance):1e30;
      if (w<1e30) {
        int iw  = (int)(w*100);
        if (found.find(iw)==found.end()) {
          V.push_back(std::make_pair(iw, mid));
          found.insert(iw);
        }
      }
    }
    k = std::min(k, (int)V.size());
    std::partial_sort(V.begin(), V.begin()+k, V.end());
    paths.resize(k);
    for (int i=0; i<k; i++) {
      paths[i].clear();
      this->findShortestPath(V[i].second, dst, paths[i]);
      this->findShortestPath(src, V[i].second, paths[i]);
      paths[i].push_back(src);
      std::reverse(paths[i].begin(), paths[i].end());
    }
  }

  inline void topK(int k, const Location &p1, const Location &p2, float distance, std::vector<Path> &paths) const
  {
    return this->topK(k, this->mapToIntersection(p1), this->mapToIntersection(p2), distance, paths);
  }

  inline bool findShortestPath(int src, int dst, Path &path, float *cost=0) const
  {
    int *prev = this->allPrev + src*this->numIntersections();
    float *dist = this->allDist + src*this->numIntersections();
    if (cost) *cost = dist[dst];
    while (prev[dst]!=dst) {
      path.push_back(dst);
      dst = prev[dst];
    }
    return src==dst;
  }
  
  inline bool computeShortestPath(int src, int dst, Path &path, float *cost=0)
  {
    IntVec prev(this->numIntersections());
    FloatVec dist(this->numIntersections());
    int numFound = this->shortestPath(src, dst, &prev[0], &dist[0]);
    if (numFound) {
      if (cost) *cost = dist[dst];
      path.clear();
      while (prev[dst]!=dst) {
        path.push_back(dst);
        dst = prev[dst];
      }
      return true;
    }
    return false;
  }

  // This function return the complete path including the src node.
  // Path's order is from src to dst
  inline bool findShortestPath(int src, int dst, Path &path, float &cost) {
    if (findShortestPath(src, dst, path, &cost)) {
      path.push_back(src);
      std::reverse(path.begin(), path.end());
      return true;
    }
    return false;
  }

  // This function return the complete path including the src node.
  // Path's order is from src to dst
  inline bool computeShortestPath(int src, int dst, Path &path, float &cost) {
    if (computeShortestPath(src, dst, path, &cost)) {
      path.push_back(src);
      std::reverse(path.begin(), path.end());
      return true;
    }
    return false;
  }

  inline static double pseudo_distance(const Location &src, const Location &dst, double ratio=1.0)
  {
    const double d0 = src.lat-dst.lat;
    const double d1 = (src.lon-dst.lon)*ratio;
    return d0*d0+d1*d1;
  }

  inline static double distance(const Location &src, const Location &dst)
  {
    const double lat1 = src.lat*M_PI/180.0;
    const double lat2 = dst.lat*M_PI/180.0;
    const double dLat = sin((lat2-lat1)/2);
    const double dLon = sin((dst.lon-src.lon)*M_PI/180.0/2);
    const double a = dLat*dLat + dLon*dLon*cos(lat1)*cos(lat2);
    return 2*3961*atan2(sqrt(a), sqrt(1-a));
  }

  void savePaths(const char *filename)
  {
    FILE *fo = fopen(filename, "wb");
    fwrite(allPaths.data(), sizeof(int), allPaths.size(), fo);
    fclose(fo);
  }

  void loadPaths(const char *filename)
  {
    this->pathFile.open(filename);
    this->allPrev = (int*)this->pathFile.data();
    this->allDist = (float*)(this->allPrev + this->numIntersections()*this->numIntersections());
    this->allRDist = this->allDist + this->numIntersections()*this->numIntersections();
  }

  uint getGlobalNumberOfSamples() { return this->globalNumberOfSamples; }
  uint getTimeStamp() { return this->timeStamp; }
  void setTimeStamp(uint val) { this->timeStamp = val; }

protected:
  typedef boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS, boost::no_property, EdgeProperty> Graph;
  class dijkstra_exit_exception {};
  class dijkstra_exit_on_dst : public boost::dijkstra_visitor<>
  {
  public:
    dijkstra_exit_on_dst(int d): dst(d) {}
    template<class VType, class GType>
    void finish_vertex(VType v, GType &)
    {
      if (static_cast<int>(v)==dst) throw dijkstra_exit_exception();
    }
  private:
    int dst;
  };
  class dijkstra_exit_on_dst_set : public boost::dijkstra_visitor<>
  {
  public:
    dijkstra_exit_on_dst_set(IntSet *d): dst(d) {}
    template<class VType, class GType>
    void finish_vertex(VType v, GType &)
    {
      IntSet::iterator it = this->dst->find(v);
      if (it!=this->dst->end()) {
        this->dst->erase(it);
        if (this->dst->size()==0)
          throw dijkstra_exit_exception();
      }
    }
  private:
    IntSet *dst;
  };

  void buildIndex()
  {
    this->gridSize[0] = (int)(ceil((this->bounds[1].lat-this->bounds[0].lat)/GRID_DEGREE));
    this->gridSize[1] = (int)(ceil((this->bounds[1].lon-this->bounds[0].lon)/GRID_DEGREE));
    int N = this->gridSize[0]*this->gridSize[1];
    this->gridIndex.resize(N, 0);
    this->gridCount.resize(N, 0);
    this->gridIntersections.resize(this->intersections.size());
  
    for (unsigned i=0; i<this->intersections.size(); i++) {
      int gid = this->gridLocation(this->intersections[i]);
      this->gridIndex[gid]++;
    }

    int last = 0;
    for (int i=0; i<N; i++) {
      int tmp = this->gridIndex[i];
      this->gridIndex[i] = last;
      last += tmp;
    }

    for (unsigned i=0; i<this->intersections.size(); i++) {
      int gid = this->gridLocation(this->intersections[i]);
      int index = this->gridCount[gid]++;
      this->gridIntersections[this->gridIndex[gid]+index] = i;
    }

    this->createKdTree();
  }
  
  inline int gridX(double lat) const
  {
    return (int)((lat-this->bounds[0].lat)/(this->bounds[1].lat-this->bounds[0].lat)*(this->gridSize[0]-1)+0.49);
  }

  inline int gridY(double lon) const
  {
    return (int)((lon-this->bounds[0].lon)/(this->bounds[1].lon-this->bounds[0].lon)*(this->gridSize[1]-1)+0.49);
  }

  inline int gridLocation(const Location &loc) const
  {
    return this->gridY(loc.lon)*this->gridSize[0]+this->gridX(loc.lat);
  }
  
  typedef struct
  {
    double median;
    int   index;
  } KdNode;

  void buildKdTree(double *tmp, int *indices, int n, int depth, int thisNode, int &freeNode) {
    KdNode *node = &this->kdNodes[thisNode];
    if (n<2) {
      node->index = -indices[0];
      return;
    }
    int keyIndex = depth%2;
    int medianIndex = n/2-1;
    for (int i=0; i<n; i++)
      tmp[i] = this->intersections[indices[i]][keyIndex];
    std::nth_element(tmp, tmp+medianIndex, tmp+n);
    node->median = tmp[medianIndex];
    int l = 0;
    int r = n-1;
    while (l<r) {
      while (l<n && this->intersections[indices[l]][keyIndex]<node->median) l++;
      while (r>l && this->intersections[indices[r]][keyIndex]>=node->median) r--;
      if (l<r)
        std::swap(indices[l], indices[r]);
    }
    medianIndex = r;

    int child_index = freeNode;
    node->index = child_index;
    freeNode += 2;
    this->kdNodes.resize(freeNode);
    buildKdTree(tmp, indices, medianIndex+1, depth+1, child_index, freeNode);
    if (medianIndex<n-1)
      buildKdTree(tmp, indices + medianIndex+1, n-medianIndex-1, depth+1, child_index+1, freeNode);
    else
      this->kdNodes[child_index+1].index = INT_MIN;
  }

  void createKdTree() {
    std::vector<double> tmp(this->numIntersections());
    std::vector<int> indices(this->numIntersections());
    for (unsigned i=0; i<indices.size(); i++)
      indices[i] = i;
 
    int freeNode = 1;
    this->kdNodes.resize(freeNode);
    buildKdTree(&tmp[0], &indices[0], this->numIntersections(), 0, 0, freeNode);
  }

  void searchKdNearestIntersection(const Location &p, int root, int depth, int &minInter, double &minDis) const
  {
    const KdNode *node = &this->kdNodes[root];
    if (node->index<=0) {
      if (node->index==INT_MIN) return;
      int inter = -node->index;
      double dis = CityMap::pseudo_distance(p, this->intersections[inter], this->ratioLatLon);
      if (dis<minDis) {
        minDis = dis;
        minInter = inter;
      }
      return;
    }
    double v = ((const double*)(&p))[depth%2];
    if (v-this->GRID_DEGREE<=node->median)
      searchKdNearestIntersection(p, node->index, depth+1, minInter, minDis);
    if (v+this->GRID_DEGREE>node->median) {
      searchKdNearestIntersection(p, node->index+1, depth+1, minInter, minDis);
    }
  }

private:
  const double              GRID_DEGREE;
  double                    ratioLatLon;
  Location                  bounds[2];
  Location                  center;
  int                       gridSize[2];
  std::vector<int>          gridIndex;
  std::vector<int>          gridCount;
  std::vector<int>          gridIntersections;

  std::vector<Location>     intersections;
  std::vector<Street>       streets;
  std::vector<EdgeProperty> streetProps;
  std::vector<IntersectionProperty> intersectionProps;
  Graph                     city;
  StreetMap                 streetId;
  std::vector<KdNode>       kdNodes;
  
  boost::iostreams::mapped_file_source pathFile;
  const int *               pathData;
  Int2Map                   paths;

  IntVec                    allPaths;
  int                      *allPrev;
  float                    *allDist;
  float                    *allRDist;

  uint                      globalNumberOfSamples;
  uint                      timeStamp;
};

#endif
