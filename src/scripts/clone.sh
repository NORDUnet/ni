#!/usr/bin/env bash
set -e

pushd `dirname $0` > /dev/null
SCRIPT_DIR="$(pwd)"
popd > /dev/null
VIRTUAL_ENV="/var/opt/norduni/norduni_environment"
ENV_FILE="/var/opt/norduni/norduni/src/niweb/.env"
NOCLOOK_DIR="/var/opt/norduni/norduni/src/scripts"
NISTORE_DIR="/var/opt/norduni/nistore"
SQL_DUMP="/var/opt/norduni/nistore/producers/noclook/sql"
NI_PULL_CMD="/usr/local/bin/ni-pull.sh"
DB_NAME=$(grep DB_NAME $ENV_FILE | sed -e 's/^[^=]*=\s*//')
NEO4J_PASSWORD=$(grep NEO4J_PASSWORD $ENV_FILE | sed -e 's/^[^=]*=\s*//')

function now (){
  date +"%Y-%m-%d %H:%M:%S"
}

function msg(){
  echo "> $1 - $(now)"
}

msg "Pulling new nistore data"
$NI_PULL_CMD -r $NISTORE_DIR


msg "Removing neo4j data"
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n:Node) OPTIONAL MATCH (n)-[r]-() DELETE n,r;"


msg "Drop DB"
dropdb $DB_NAME
createdb $DB_NAME


msg "Import SQL DB"
gunzip -c $SQL_DUMP/postgres.sql.gz | psql --quiet norduni


msg "Reset DB sequences"
psql --quiet -f "$NOCLOOK_DIR/sql/reset-sequences-noclook.sql" norduni


msg "Importing data from json"
. $VIRTUAL_ENV/bin/activate
cd $NOCLOOK_DIR
python noclook_consumer.py -C $SCRIPT_DIR/restore.conf -I


msg "Restore done."
