/*
  DDL for the tables in the CRDB Geo Tourist app with IAM
  Tables are multi-region
 */

ALTER DATABASE defaultdb PRIMARY REGION "gcp-us-central1";
ALTER DATABASE defaultdb ADD REGION "gcp-europe-west1";
ALTER DATABASE defaultdb ADD REGION "gcp-us-east1";

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

/*
  ERROR:  incompatible value type: gateway_region(): context-dependent operators are not
  allowed in STORED COMPUTED COLUMN
 */
ALTER TABLE public.osm ADD COLUMN crdb_region crdb_internal_region NOT NULL AS
(
  CASE
    WHEN SUBSTRING(geohash4 FROM 1 FOR 1) IN ('9') THEN 'gcp-us-central1' /* Austin, TX */
    WHEN SUBSTRING(geohash4 FROM 1 FOR 1) IN ('u', 'g', 'e', 's') THEN 'gcp-europe-west1'
    /* ELSE gateway_region() */
    ELSE 'gcp-us-east1'
  END
) STORED;

ALTER TABLE public.osm SET LOCALITY REGIONAL BY ROW;

/* The other tables will be global */
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

CREATE TABLE public."role"
(
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  name VARCHAR(64) NOT NULL,
  CONSTRAINT role_pkey PRIMARY KEY (id ASC),
  UNIQUE INDEX ix_role_name (name ASC)
)
LOCALITY GLOBAL;

INSERT INTO public."role" (name) VALUES ('Tourist'), ('Grand Tourist');

CREATE TABLE public.tourist_role
(
  tourist_id UUID NOT NULL,
  role_id UUID NOT NULL,
  CONSTRAINT tourist_role_pkey PRIMARY KEY (tourist_id ASC, role_id ASC),
  CONSTRAINT tourist_role_tourist_id_fkey FOREIGN KEY (tourist_id) REFERENCES public.tourist(id),
  CONSTRAINT tourist_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES public."role"(id)
)
LOCALITY GLOBAL;

CREATE TABLE public.way_point
(
  tourist_id UUID NOT NULL,
  ts TIMESTAMP NOT NULL DEFAULT now():::TIMESTAMP,
  lat FLOAT8 NOT NULL,
  lon FLOAT8 NOT NULL,
  CONSTRAINT way_point_pkey PRIMARY KEY (tourist_id ASC, ts ASC),
  CONSTRAINT way_point_tourist_id_fkey FOREIGN KEY (tourist_id) REFERENCES public.tourist(id)
)
LOCALITY REGIONAL BY ROW;

