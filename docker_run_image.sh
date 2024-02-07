#!/bin/bash

. ./docker_include.sh

img="$docker_id/$img_name"

#export DB_URL="postgres://tourist:tourist@host.docker.internal:26257/defaultdb"
export DB_URL="postgres://test_role:123abc@host.docker.internal:26257/defaultdb?sslmode=require&sslrootcert=/Users/mgoddard/certs/ca.crt"
export USE_GEOHASH=True
export SECRET_KEY="rokee-bickern-rubrician-sinalbin"

docker pull $img:$tag
docker run -e DB_URL -e USE_GEOHASH -e SECRET_KEY --publish 1972:18080 $img

