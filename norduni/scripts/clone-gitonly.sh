#!/usr/bin/env bash
set -e

pushd `dirname $0` > /dev/null
SCRIPT_DIR="$(pwd)"
popd > /dev/null
NORDUNI_DIR="/var/opt/norduni/norduni"
NISTORE_DIR="/var/opt/norduni/nistore"
VIRTUAL_ENV="/var/opt/norduni/norduni_environment"

usage="Usage: $0 [-r <nistore>] [-n <norduni>] [-e <virtualenv>]"
while getopts ":r:n:e:" options; do
  case $options in
    r) NISTORE_DIR=$OPTARG;;
    n) NORDUNI_DIR=$OPTARG;;
    e) VIRTUAL_ENV=$OPTARG;;
    *) echo $usage
        exit 1;;
  esac
done

# Pre checks
if [ ! -d "$NISTORE_DIR/producers" ]; then
  echo "Error: no nistore repository @ $NISTORE_DIR"
  ERROR=true
fi

if [ ! -d "$NORDUNI_DIR/src" ]; then
  echo "Error: no norduni @ $NORDUNI_DIR"
  ERROR=true
fi

if [ ! -d "$VIRTUAL_ENV/bin" ]; then
  echo "Error: no virtual env @ $VIRTUAL_ENV"
  ERROR=true
fi

if [ $ERROR ]; then
  exit 1
fi

ENV_FILE="$NORDUNI_DIR/src/niweb/.env"
NOCLOOK_DIR="$NORDUNI_DIR/src/scripts"
SQL_DUMP="$NISTORE_DIR/producers/noclook/sql"
NI_PULL_CMD="$SCRIPT_DIR/git-scripts/ni-pull.sh"
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

msg "Reset last modified"
psql --quiet -f "$NOCLOOK_DIR/sql/fix-last-modified.sql" norduni

msg "Restore done."
