#include <iostream>

#include "CityMap.hpp"
#include "KdTrip.hpp"
#include "util/util.h"

using namespace std;

int main() {
  string kdtripFilename = string(DATA_DIR)+"/kdtrip/yellow_<<year>>-<<month>>.kdtrip";
  string graphFilename  = string(DATA_DIR)+"/manhattan_with_distances_clean.txt";
  string pathsFilename  = string(DATA_DIR)+"/paths.bin";
  string outputFolder   = string(DATA_DIR)+"/speeds_output/";

  // create folder it doesn't exist
  QDir().mkdir(outputFolder.c_str());

  KdTrip kdtrip(kdtripFilename.c_str());

  // load normal graph
  CityMap city(graphFilename.c_str());
  if (!boost::filesystem::exists(pathsFilename)) {
    fprintf(stderr, "First time running, generating shortest paths...\n");
    city.buildAllShortestPaths();
    city.savePaths(pathsFilename.c_str());
  } else {
    fprintf(stderr, "Load precomputed shortest paths\n");
    city.loadPaths(pathsFilename.c_str());
  }

  vector<KdTrip::Trip> trips;
  QDateTime st(QDate(<<year>>, <<monthint>>, 1), QTime(0, 0, 0));
  QDateTime et(QDate(<<year>>, <<monthint>>, <<dayend>>), QTime(23, 59, 59));


  queryTrips(kdtrip, st, et, &trips);

  uint64_t basetime = createTime(st);
  int t1 = createTime(st);
  int t2 = createTime(et);
  int minutes      = 60;
  int deltaTime    = minutes*60; // in seconds
  int totalTime    = t2-t1+1;
  int numTimeSteps = totalTime/deltaTime;
  const int K      = 20;
  vector<CityMap> graphs(numTimeSteps, CityMap(graphFilename.c_str()));

  int numTripsDistanceZero = 0;
  int numTripsWrongTime = 0;
  int numTripsSpeedOver80 = 0;

  int numTrips = 0;
  for (auto &trip: trips) {
    fprintf(stderr, "\rProcessing %d/%lu trips", ++numTrips, trips.size());

    // skip noisy data
    if (trip.distance<0.000001)              { ++numTripsDistanceZero; continue; }
    if (trip.pickup_time>=trip.dropoff_time) { ++numTripsWrongTime;    continue; }

    double realDist = trip.distance*0.01;                          // miles
    double realTime = (trip.dropoff_time-trip.pickup_time)/3600.f; // hours

    int srcId = city.mapToIntersection(CityMap::Location(trip.pickup_lat, trip.pickup_long));
    int dstId = city.mapToIntersection(CityMap::Location(trip.dropoff_lat, trip.dropoff_long));
    if (srcId!=-1 && dstId!=-1 && srcId!=dstId && realDist>1) {

      vector<CityMap::Path> paths;
      city.topK(K, srcId, dstId, realDist, paths);

      for (auto &path: paths) {
        float closestDistance = computeTotalCost(city, path);
        float closeness = fabs(closestDistance-realDist);
        float w = 1.f/(closeness+(closeness==0?0.00001:0));

        double realSpeed     = realDist/realTime;         // miles per hour
        double estimateSpeed = closestDistance/realTime;  // miles per hour

        if (estimateSpeed>80) { ++numTripsSpeedOver80; continue; }

        uint32_t currentTime = trip.pickup_time;
        for (int i=0; i<path.size()-1; ++i) {
          assert(currentTime>=basetime && currentTime<=(basetime+totalTime));
          int edgeId          = city.getStreetId(CityMap::Street(path[i], path[i+1]));
          double edgeDistance = city.getStreetWeight(CityMap::Street(path[i], path[i+1])); // miles
          assert(edgeId!=-1);

          uint position = (currentTime-basetime)/(deltaTime);
          assert(position>=0 && position<graphs.size());
          CityMap::IntersectionProperty &iProp = graphs[position].getIntersectionProperty(path[i]);
          iProp.addSampleVec(edgeId, min(1.0, 1E-2 * w), 1.0);
          //iProp.addSampleVec(edgeId, estimateSpeed, w);

          currentTime += edgeDistance/estimateSpeed*3600;
        } // for road
      } // for paths
    } // if trip valid
  } // for trips
  cerr << "numTripsDistanceZero: " << numTripsDistanceZero << endl;
  cerr << "numTripsWrongTime: " << numTripsWrongTime << endl;
  cerr << "numTripsSpeedOver80: " << numTripsSpeedOver80 << endl;


  QDateTime previousTime = st;
  QDateTime bbasetime = st;

  string filename = outputFolder+"/"+bbasetime.toString("yyyy_MM_dd-HH_mm_ss.txt").toStdString();
  ofstream out(filename);
  for (auto &p: graphs) {
    p.exportSpeeds(out, bbasetime.toString("yyyy_MM_dd-HH_mm_ss").toStdString());

    previousTime = bbasetime;
    bbasetime = bbasetime.addSecs(deltaTime);
    // hack to fix DST on november
    if (previousTime.toString()==bbasetime.toString()) {
       previousTime = bbasetime;
       bbasetime = bbasetime.addSecs(deltaTime);
    }
  }

  return 0;
}
