#!/bin/bash

years=(2009 2010 2011 2012 2013 2014 2015 2016)
months=(01 02 03 04 05 06 07 08 09 10 11 12)
monthints=(1 2 3 4 5 6 7 8 9 10 11 12)
dayends=(31 28 31 30 31 30 31 31 30 31 30 31)

for year in ${years[@]}
do
  for monthint in ${monthints[@]}
  do
    if [ $year -eq 2016 -a $monthint -ge 7 ]; then
      break
    fi
    let "monthidx = $monthint - 1"
    dayend=${dayends[$monthidx]}
    month=${months[$monthidx]}
    if [ $year -eq 2012 -a $monthint -eq 2 -o $year -eq 2016 -a $monthint -eq 2 ]; then
      dayend=29 # leap year Feb
    fi
    cat exportSpeeds_template.cpp | sed "s/<<year>>/$year/g" | sed "s/<<monthint>>/$monthint/g" | sed "s/<<month>>/$month/g" | sed "s/<<dayend>>/$dayend/g" > exportSpeeds.cpp
    make
    echo $year, $monthint
    ./exportSpeeds
  done
done
