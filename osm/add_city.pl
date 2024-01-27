#!/usr/bin/env perl

# 262714<2018-12-07T09:55:55Z<917436<51.0359<-0.805651<Rising Sun<addr:city=Liphook|addr:postcode=GU30 7NA|addr:street=Milland Road|addr:suburb=Milland|amenity=pub|fhrs:id=147913|food=yes|real_ale=yes|gcp|gcp6|gcp6m|gcp6md<gcp6mdv3dvr1

if (not defined $ENV{DB_URL}) {
  die 'Environment variable DB_URL must be defined; e.g.
  
    export DB_URL="postgres://user:passwd@127.0.0.1:26257/db_name?sslmode=require&sslrootcert=./ca.crt

  ';
}

# "\timing on" in .psqlrc will break this
$psqlrc = "$ENV{HOME}/.psqlrc";
$s = -s $psqlrc;
if ($s and $s > 0) {
  rename $psqlrc, "$psqlrc.BAK";
}

$db_url = $ENV{DB_URL};

$psql_templ = "psql '" . $db_url . "' -tAc " . q["WITH c AS (
      SELECT city, COUNT(*)
      FROM osm_names
      WHERE geohash5 = 'GEOHASH5'
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 1
    )
    SELECT city FROM c;"];

#print "psql_templ: $psql_templ\n";

while (<>)
{
  chomp;
  @a = split /</;
  unless ($a[6] =~ /addr:city=/) {
    @b = split /\|/, $a[6];
    # TODO: Look up city using geohash5, which is $b[-2]
    #print "No City.  Geohash5: $b[-2]\n";
    ($psql = $psql_templ) =~ s/GEOHASH5/$b[-2]/;
    chomp($city = `$psql`);
    #print "City: $city\n";
    unshift @b, "addr:city=$city";
    $a[6] = join('|', @b);
    print join('<', @a) . "\n";
  } else {
    print "$_\n";
  }
}

