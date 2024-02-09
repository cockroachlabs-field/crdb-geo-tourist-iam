#!/usr/bin/env python3

import sys, json

# Based on output from this UI: https://geojson.io/

"""
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "coordinates": [
          [
            [
              -78.56547596094232,
              37.982301102053285
            ],
            ...
"""

top = -1000
left = 1000
bottom = left
right = top

obj = json.load(sys.stdin)
for latlon in obj["features"][0]["geometry"]["coordinates"][0]:
  lat = latlon[1]
  if lat > top:
    top = lat
  if lat < bottom:
    bottom = lat
  lon = latlon[0]
  if lon < left:
    left = lon
  if lon > right:
    right = lon

print("  --bounding-box top={} left={} bottom={} right={}".format(top, left, bottom, right))

