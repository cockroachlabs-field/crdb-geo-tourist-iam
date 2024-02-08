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
   - The resulting file has rows with this format: ```11198305607<2023-09-17T19:14:15Z<0<38.0350278<-78.486494<Random Row Brewing<addr:city=Charlottesville|addr:housenumber=608|addr:postcode=22903|addr:state=VA|addr:street=Preston Avenue|addr:unit=A|amenity=pub|microbrewery=yes|website=https://randomrow.com|dqb|dqb0|dqb0m|dqb0mu<dqb0mupfh5h66```
1. In a later step, we'll get some ratings to add to the data, one per row.  This involves doing a web
search, so we'll need to provide more context than what we have now, for better accuracy.  To do that,
we'll augment the data with the city name, and the data to use for that is available
[here](https://osmnames.org/download/).  Once that file is downloaded as `planet-latest_geonames.tsv.gz`,
proceed as follows:
   - Use the DDL in `../../crdb-geo-tourist-iam/osm/osm_names.sql` to create the `osm_names` table
   - Run the following to load the data: ```time gzcat ./planet-latest_geonames.tsv.gz | ../crdb-geo-tourist-iam/osm/load_geonames.py```
   - That takes a while on a MacBook (`55m12.335s`), so doing an EXPORT of this would be a good idea.
   - Result: 9444352 rows in the table
   - Next, we use this table to add the city name to each of the rows in the CSV: ```time gzcat osm_cville_02.08.24.txt.gz | ../crdb-geo-tourist-iam/osm/add_city.pl | gzip - > osm_cville_with_city_02.08.24.txt.gz```
   - That took `real	0m35.512s`
1. Final data prep step: add the ratings for the amenities.  The most reliable source of data on this
that I could find was the Brave search API, which is what I'll document here.
   - Sign up for an account and get an API key, from [here](https://brave.com/search/api/)
   - Run `export BRAVE_API_KEY=use_your_key_here`
   - Run ```time gzcat osm_cville_with_city_02.08.24.txt.gz | egrep 'amenity=(bar|pub|cafe|restaurant)' | ../crdb-geo-tourist-iam/osm/add_ratings_to_data_file.py | gzip - > osm_cville_with_ratings_02.08.24.txt.gz```
   - That took `real	3m23.768s` and also produces a newline-delimited JSON file, `brave_api.ndjson`
   containing the Brave search API results.
1. Finally -- we get to load the data into the `osm` table:
   - Run ```time gzcat osm_cville_with_ratings_02.08.24.txt.gz | ../crdb-geo-tourist-iam/load_osm_stdin.py```
   - The data should be in the `osm` table!

