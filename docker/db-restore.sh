#!/bin/bash
set -e
pushd `dirname $0` > /dev/null
SCRIPT_DIR="$(pwd)"
popd > /dev/null

usage="Usage: $0 [-h] [-o] [-f <postgres.sql.gz>] [-d <ni_store>] [-c <ni-data-conf>]"
while getopts ":f:d:c:o" opt; do
  case $opt in
    f) SQL_DUMP="$OPTARG";;
    d) NI_STORE="$OPTARG";;
    c) NI_DATA_CONF="$OPTARG";;
    o) OVERWRITE_NI_DATA=true;;
    *) echo "$usage"
       exit 1;;
  esac
done

if [ ! -d "$NI_STORE" ] && [ -z "$NI_DATA_CONF" ]; then
  echo "Error: NI_STORE is not defined, use -d <ni_store> or -c <ni-data-conf>"
  exit 1
fi

if [ -z "$NI_DATA_CONF" ]; then
  if [ -z "$SQL_DUMP" ]; then
    SQL_DUMP="$NI_STORE/producers/noclook/sql/postgres.sql.gz"
  fi

  if [ ! -f "$SQL_DUMP" ]; then
    echo "Error: $SQL_DUMP does not exist, use -f <postgres.sql.gz>"
    exit 1
  fi
  NI_DUMP="$NI_STORE/producers/noclook/json/"
else
  NI_DATA_URL=$(awk -F'=' '/url=/ {print $2}' "$NI_DATA_CONF")
  NI_DATA_AUTH=$(awk -F'=' '/auth=/ {print $2}' "$NI_DATA_CONF")
  NI_TMP="$SCRIPT_DIR/data/nidata"
  mkdir -p "$NI_TMP"

  if [ ! -f "$NI_TMP/postgres.sql.gz" ] || [ ! -z "$OVERWRITE_NI_DATA" ]; then
    curl -u "$NI_DATA_AUTH" -o "$NI_TMP/postgres.sql.gz" "$NI_DATA_URL/postgres.sql.gz"
  else
    echo "Skipping postgres download"
  fi
  SQL_DUMP="$NI_TMP/postgres.sql.gz"

  if [ ! -f "$NI_TMP/ni_data.tar.gz" ] || [ ! -z "$OVERWRITE_NI_DATA" ]; then
    curl -u "$NI_DATA_AUTH" -o "$NI_TMP/ni_data.tar.gz" "$NI_DATA_URL/ni_data.tar.gz"
  else
    echo "Skipping ni_data.tar.gz download"
  fi
  NI_DUMP="$NI_TMP/dump"
  test -d "$NI_DUMP" && rm -r "$NI_DUMP"
  mkdir -p "$NI_DUMP"
  cd "$NI_DUMP"
  echo "Exctracting ni_data.tar.gz"
  tar xf "$NI_TMP/ni_data.tar.gz"
fi


function now() {
  date +"%Y-%m-%d %H:%M:%S"
}

function msg() {
  echo "> $1 - $(now)"
}

function duration {
  local T=$1
  local H=$((T/60/60%24))
  local M=$((T/60%60))
  local S=$((T%60))
  printf '%02d:%02d:%02d' $H $M $S
}

SECONDS=0

msg "Stopping norduni"
docker-compose -f $SCRIPT_DIR/compose-dev.yml stop norduni

set +e
msg "Stopping neo4j"
docker-compose -f $SCRIPT_DIR/compose-dev.yml stop neo4j

msg "Removing neo4j data"
rm -r $SCRIPT_DIR/data/neo4j/databases

set -e

msg "Starting neo4j again"
docker-compose -f  $SCRIPT_DIR/compose-dev.yml start neo4j

postgres_id=$(docker ps | awk '/postgres/ {print $1}')

msg "Drop, Create DB"
cat << EOM | docker exec -i $postgres_id psql -q -U ni postgres
DROP DATABASE norduni;
CREATE DATABASE norduni;
GRANT ALL PRIVILEGES ON DATABASE norduni to ni;
ALTER USER ni CREATEDB;
EOM

msg "Copy db-dump to postgres"
docker cp $SQL_DUMP $postgres_id:/sqldump.sql.gz

msg "Import DB from $SQL_DUMP"
docker exec -i $postgres_id bash -c "gunzip /sqldump.sql.gz; psql -q -o /dev/null norduni ni -f /sqldump.sql; rm /sqldump.*"

msg "Django migrate"
docker-compose -f $SCRIPT_DIR/compose-dev.yml  run --rm norduni manage migrate


msg "Import neo4j data from json"
cat << EOM | docker-compose -f $SCRIPT_DIR/compose-dev.yml  run --rm -v $NI_DUMP:/opt/noclook norduni consume
# Set after how many days data should be considered old.
[data_age]
juniper_conf = 30

# Set if the consumer should check for old data and delete it.
[delete_data]
juniper_conf = false

# All producers need to be listed here with a path to their data
[data]
juniper_conf =
nmap_services_py =
alcatel_isis =
nagios_checkmk =
cfengine_report =
# noclook is used to import a already made backup
noclook = /opt/noclook
EOM

msg "Reset postgres sequences"
cat <<EOM | docker exec -i $postgres_id psql -q -o /dev/null norduni ni
BEGIN;
SELECT setval(pg_get_serial_sequence('"noclook_nodetype"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_nodetype";
SELECT setval(pg_get_serial_sequence('"noclook_nodehandle"','handle_id'), coalesce(max("handle_id"), 1), max("handle_id") IS NOT null) FROM "noclook_nodehandle";
SELECT setval(pg_get_serial_sequence('"noclook_uniqueidgenerator"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_uniqueidgenerator";
SELECT setval(pg_get_serial_sequence('"noclook_nordunetuniqueid"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_nordunetuniqueid";
COMMIT;
EOM

msg "Reset last modified"
cat <<EOM | docker exec -i $postgres_id psql -q -o /dev/null norduni ni
BEGIN;
UPDATE noclook_nodehandle
SET modified=upd.timestamp
FROM (SELECT MAX(timestamp) as timestamp, action_object_object_id FROM actstream_action GROUP BY action_object_object_id) as upd
WHERE upd.action_object_object_id=noclook_nodehandle.handle_id::varchar;
COMMIT;
EOM

echo ""
echo "> Finished db-restore in $(duration $SECONDS )"
echo "" 

# Cleanup

if [ -z "$NI_DATA_CONF" ]; then
  rm -r "$NI_DUMP"
fi

msg "Create superuser"
echo -e "\a" # play bell
docker-compose -f $SCRIPT_DIR/compose-dev.yml  run --rm norduni manage createsuperuser

