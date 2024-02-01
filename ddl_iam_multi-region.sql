/*
  DDL for the tables in the CRDB Geo Tourist app with IAM
  Tables are multi-region
 */
ALTER DATABASE defaultdb PRIMARY REGION "gcp-us-east1";
ALTER DATABASE defaultdb ADD REGION "gcp-europe-west1";
ALTER DATABASE defaultdb ADD REGION "gcp-us-central1";

ALTER DATABASE defaultdb SURVIVE REGION FAILURE;

SET enable_auto_rehoming = on;

/* RBR by SUBSTRING(geohash4 FROM 1 FOR 1) */
DROP TABLE IF EXISTS public.osm;
CREATE TABLE public.osm
(
  geohash4 STRING NOT NULL,
  amenity STRING NOT NULL,
  id INT8 NOT NULL,
  date_time TIMESTAMPTZ NULL,
  uid STRING NULL,
  name STRING NOT NULL,
  lat FLOAT8 NOT NULL,
  lon FLOAT8 NOT NULL,
  key_value STRING[] NULL,
  search_hints STRING NULL,
  rating FLOAT8 NULL,
  rating_ts TIMESTAMP NULL,
  ref_point GEOGRAPHY NULL AS (st_makepoint(lon, lat)::GEOGRAPHY) STORED,
  CONSTRAINT "primary" PRIMARY KEY (geohash4 ASC, amenity ASC, id ASC),
  INVERTED INDEX osm_geo_idx (ref_point)
);

ALTER TABLE public.osm SET LOCALITY REGIONAL BY ROW;

ALTER TABLE public.osm ADD COLUMN region crdb_internal_region AS
(
  CASE
    WHEN SUBSTRING(geohash4 FROM 1 FOR 1) IN ('9') THEN 'gcp-us-central1'
    WHEN SUBSTRING(geohash4 FROM 1 FOR 1) IN ('u', 'g', 'e', 's') THEN 'gcp-europe-west1'
  END
) STORED;

/* Global */
CREATE TABLE public.tourist
(
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  username VARCHAR(64) NOT NULL,
  email VARCHAR(120) NOT NULL,
  password_hash VARCHAR(256) NULL,
  CONSTRAINT tourist_pkey PRIMARY KEY (id ASC),
  UNIQUE INDEX ix_tourist_username (username ASC),
  UNIQUE INDEX ix_tourist_email (email ASC)
)
LOCALITY GLOBAL;

/* Global */
CREATE TABLE public.tourist_locations
(
  name STRING NULL,
  lat FLOAT8 NULL,
  lon FLOAT8 NULL,
  enabled BOOL NULL DEFAULT true,
  geohash CHAR(9) NOT NULL
    AS (st_geohash(st_setsrid(st_makepoint(lon, lat), 4326:::INT8), 9:::INT8)) STORED,
  CONSTRAINT "primary" PRIMARY KEY (geohash ASC)
)
LOCALITY GLOBAL;

