# Notes on OpenStreetMap (OSM) data sources and preparation

## Overview

For an overview of the data in the app, see the app's [README](../README.md).  This section
deals with specifics of adding data for an area not already covered in the app's default
data set.  The notes here are current as of today (8 February 2024).

## Process

1. Navigate to [this site](https://app.protomaps.com/) and use the UI to extract data
   for the region you want, or do this:
   - [This site](https://download.geofabrik.de/) has some regional data extracts, so I'll use
     [the one for North America](https://download.geofabrik.de/north-america-latest.osm.pbf) here.
1. Next, we convert the PBF file into the XML format OSM uses.  Why XML?  This is the format
I initally used when building the data pipeline, so that code is based on XML.  Here we go:
   - Download _osmosis_, the converter we'll use, from [here](https://github.com/openstreetmap/osmosis/releases)
   - This is a Java app, so you'll need a JVM installed
   - Unzip that file in your current working directory (where the PBF file is)
   - ```time ./osmosis-0.49.2/bin/osmosis --read-pbf-0.6 file=./north-america-latest.osm.pbf --bounding-box top=38.1400953181691 left=-78.56547596094232 bottom=37.982301102053285 right=-78.3540781573794 --write-xml file=- | gzip - > osm_cville.xml.gz```
   - That took `real	5m29.208s` to produce the XML file, which isn't terrible
1. The data format continues to be a bit odd. The next step is to take the XML file from above
   which spans > 1 row per entry and reformat it to a CSV-like format, where the delimiter is
   the `<` character (logic here: since XML can't contain that char, it's not going to be present
   in the data):
   ```time gzcat ./osm_cville.xml.gz | ../crdb-geo-tourist-iam/osm/extract_points_from_osm_xml.pl | gzip - > osm_cville_02.08.24.txt.gz```


## BELOW IS JUST FOR EXAMPLE MARKUP

![Screenshot pubs](./closest_pubs_osm_iam.jpg)
(App shown running on a laptop)

1. `GEOGRAPHY`: the data type to represent each of the `POINT` data elements associated with the amenity
1. `ST_Distance`: used to calculate the distance from the user to each of these locations
1. `ST_Y` and `ST_X`: are used to retrieve the longitude and latitude of each of these points, for plotting onto the map

One aspect of CockroachDB's spatial capability is especially interesting: the
way the spatial index works.  In order to preserve CockroachDB's unique ability
to scale horizontally by adding nodes to a running cluster, its approach to
spatial indexing is to decompose of the space being indexed into buckets of
various sizes.  Deeper discussion of this topic is available
[in the docs](https://www.cockroachlabs.com/docs/v20.2/spatial-indexes) and
[in this blog post](https://www.cockroachlabs.com/blog/how-we-built-spatial-indexing/).

<img src="./mobile_view_iam.jpg" width="360" alt="Running on iPhone">
(App running in an iPhone, in Safari, maps by OpenStreetMap)

