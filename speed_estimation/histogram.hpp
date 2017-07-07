#ifndef HISTOGRAM_HPP
#define HISTOGRAM_HPP

typedef unsigned int uint;

enum HistogramDomainType {
  INT,
  FLOAT
};

class Histogram {
public:
  Histogram() {}
  Histogram(HistogramDomainType _domainType): domainType(_domainType) {}
  Histogram(double _minValue, double _maxValue, int _binCount) {
    setBins(_minValue, _maxValue, _binCount);
  }

  inline int getBinCount() {
    return counts.size();
  }

  inline int getCount(int index) {
    return counts[index];
  }

  inline double getMinValue() {
    return minValue;
  }

  inline double getMaxValue() {
    return maxValue;
  }

  // This will reset bin counts.
  void setBins(double _minValue, double _maxValue, int _binCount) {
    domainType = FLOAT;
    minValue = _minValue;
    maxValue = _maxValue;
    stepSize = (maxValue - minValue) / _binCount;
    counts = std::vector<int>(_binCount, 0);
  }

  void addSample(double val) {
    if (val < minValue || val > maxValue) {
      exceptionCount++;
      return;
    }
    int bin = (val - minValue) / stepSize;
    bin = std::min(bin, (int)counts.size() - 1); // put maxValue in the last bin
    counts[bin]++;
  }

  void mergeCounts(Histogram &ano) {
    assert(ano.getBinCount() == counts.size() &&
           ano.getMinValue() == minValue &&
           ano.getMaxValue() == maxValue);
    for (int i = 0; i < counts.size(); i++) {
      counts[i] += ano.getCount(i);
    }
  }

  void exportCounts(std::ofstream &out) {
    for (int i = 0; i < counts.size(); i++) {
      out << counts[i] << " ";
    }
    out << exceptionCount << "\n";
  }

private:
  HistogramDomainType domainType;
  double minValue, maxValue, stepSize;
  int exceptionCount; // # samples that fall outside the bins
  std::vector<int> counts;
};

#endif
