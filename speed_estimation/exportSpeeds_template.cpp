#include <iostream>

#include "CityMap.hpp"
#include "KdTrip.hpp"
#include "util/util.h"
#include "histogram.hpp"

using namespace std;

int main() {
  string kdtripFilename = string(DATA_DIR)+"/kdtrip/yellow_<<year>>-<<month>>.kdtrip";
  string graphFilename  = string(DATA_DIR)+"/lion_network_pruned.txt";
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
  vector<Histogram> hists(numTimeSteps, Histogram(0., 30., 300));
  vector<Histogram> histSPs(numTimeSteps, Histogram(0., 30., 300));
  vector<Histogram> histDiffs(numTimeSteps, Histogram(-30., 30., 600));

  int numTripsDistanceZero = 0;
  int numTripsWrongTime = 0;
  int numTripsSpeedOver80 = 0;
  int numTripsTooSlow = 0;

  int numTrips = 0;
  for (auto &trip: trips) {
    fprintf(stderr, "\rProcessing %d/%lu trips", ++numTrips, trips.size());

    // skip noisy data
    if (trip.distance<0.000001)              { ++numTripsDistanceZero; continue; }
    if (trip.pickup_time>=trip.dropoff_time) { ++numTripsWrongTime;    continue; }

    double realDist = trip.distance*0.01;                          // miles
    double realTime = (trip.dropoff_time-trip.pickup_time)/3600.f; // hours
    double realSpeed = realDist / realTime;

    int srcId = city.mapToIntersection(CityMap::Location(trip.pickup_lat, trip.pickup_long));
    int dstId = city.mapToIntersection(CityMap::Location(trip.dropoff_lat, trip.dropoff_long));
    if (srcId!=-1 && dstId!=-1 && srcId!=dstId) { // && realDist>1

      /*
      uint32_t currentTime = trip.pickup_time;
      uint position = (currentTime-basetime)/(deltaTime);

      double spDist = city.getShortestPathDistance(srcId, dstId);
      hists[position].addSample(realDist);
      histSPs[position].addSample(spDist);
      histDiffs[position].addSample(realDist - spDist);
      */

      vector<CityMap::Path> paths;
      city.topK(K, srcId, dstId, realDist, paths);

      for (auto &path: paths) {
        float closestDistance = computeTotalCost(city, path);
        float closeness = fabs(closestDistance-realDist);
        float w = 1.f/(closeness+(closeness==0?0.00001:0));

        double realSpeed     = realDist/realTime;         // miles per hour
        double estimateSpeed = closestDistance/realTime;  // miles per hour

        estimateSpeed = realSpeed; // use realSpeed for estimation

        if (estimateSpeed>80) { ++numTripsSpeedOver80; continue; }

        uint32_t currentTime = trip.pickup_time;

        if (currentTime + closestDistance/realSpeed > basetime + totalTime) { ++numTripsTooSlow; continue; }

          for (int i=0; i<path.size()-1; ++i) {
          assert(currentTime>=basetime && currentTime<=(basetime+totalTime));
          int edgeId          = city.getStreetId(CityMap::Street(path[i], path[i+1]));
          double edgeDistance = city.getStreetWeight(CityMap::Street(path[i], path[i+1])); // miles
          assert(edgeId!=-1);

          uint position = (currentTime-basetime)/(deltaTime);
          assert(position>=0 && position<graphs.size());
          CityMap::IntersectionProperty &iProp = graphs[position].getIntersectionProperty(path[i]);
            
          // Compute volume
          //iProp.addSampleVec(edgeId, min(1.0, 1E-2 * w), 1.0);
          // Compute sample count
          //iProp.addSampleVec(edgeId, 1.0, 1.0);
          // Compute speed
          iProp.addSampleVec(edgeId, estimateSpeed, w);

          currentTime += edgeDistance/estimateSpeed*3600;
        } // for road
      } // for paths
    } // if trip valid
  } // for trips
  cerr << "numTripsDistanceZero: " << numTripsDistanceZero << endl;
  cerr << "numTripsWrongTime: " << numTripsWrongTime << endl;
  cerr << "numTripsSpeedOver80: " << numTripsSpeedOver80 << endl;
  cerr << "numTripsTooSlow: " << numTripsTooSlow << endl;

  QDateTime bbasetime = st;
  string filename = outputFolder+"/"+bbasetime.toString("yyyy_MM_dd-HH_mm_ss.txt").toStdString();
  ofstream out(filename);

  /*
     DST in November: the clock rolls back by one hour.
     We merge the two (same) hours and keep using native local time (12am, 1am, [2am, 2am], 3am, ...)
     DST in March: the clock moves forward at 1am and skips 2am.
     We do nothing and just use the native time, and the speed hours will read (12am, 1am, 3am, ...)
   */

  /*
  for (int i = 0; i < (int)hists.size(); i++) {
    auto &h = hists[i];
    auto &hsp = histSPs[i];
    auto &hdiff = histDiffs[i];
    if (i < (int)hists.size() - 1) {
      QDateTime nbasetime = bbasetime.addSecs(deltaTime);
      if (bbasetime.toString() == nbasetime.toString()) {
        h.mergeCounts(hists[i + 1]);
        hsp.mergeCounts(histSPs[i + 1]);
        hdiff.mergeCounts(histDiffs[i + 1]);
      }
    }
    out << bbasetime.toString("yyyy_MM_dd-HH_mm_ss").toStdString() << "\n";
    h.exportCounts(out);
    hsp.exportCounts(out);
    hdiff.exportCounts(out);
    bbasetime = bbasetime.addSecs(deltaTime);
  }
  */

  for (int i = 0; i < (int)graphs.size(); i++) {
    auto &p = graphs[i];
    if (i < (int)graphs.size() - 1) {
      QDateTime nbasetime = bbasetime.addSecs(deltaTime);
      if (bbasetime.toString() == nbasetime.toString())
        p.mergeSpeed(graphs[i + 1]);
    }
    p.exportSpeeds(out, bbasetime.toString("yyyy_MM_dd-HH_mm_ss").toStdString());
    bbasetime = bbasetime.addSecs(deltaTime);
  }
  return 0;
}
