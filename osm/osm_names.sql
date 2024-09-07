/*
 * $Id: osm_names.sql,v 1.1 2022/09/08 13:35:20 mgoddard Exp mgoddard $
 */

DROP TABLE IF EXISTS osm_names;
CREATE TABLE osm_names
(
  /*  0 */ name TEXT NOT NULL
  /*  1 */, alternative_names TEXT
  /*  2 */, osm_type TEXT
  /*  3 */, osm_id TEXT
  /*  4 */, osm_class TEXT
  /*  5 */, the_type TEXT
  /*  6 */, lon FLOAT NOT NULL
  /*  7 */, lat FLOAT NOT NULL
  /*  8 */, place_rank TEXT
  /*  9 */, importance TEXT
  /* 10 */, street TEXT
  /* 11 */, city TEXT NOT NULL
  /* 12 */, county TEXT
  /* 13 */, state TEXT
  /* 14 */, country TEXT
  /* 15 */, country_code TEXT
  /* 16 */, display_name TEXT
  /* 17 */, west TEXT
  /* 18 */, south TEXT
  /* 19 */, east TEXT
  /* 20 */, north TEXT
  /* 21 */, wikidata TEXT
  /* 22 */, wikipedia TEXT
  , geohash5 CHAR(5) /* ± 2.4 km */
  , geohash6 CHAR(6) /* ± 610 m */
  , geohash7 CHAR(7) /* ± 76 m */
  , PRIMARY KEY (geohash5, geohash6, geohash7, city, name)
);

