#!/usr/bin/env bash
set -e

pushd `dirname $0` > /dev/null
SCRIPT_DIR="$(pwd)"
popd > /dev/null
NORDUNI_DIR="/var/opt/norduni/norduni"
DATA_DIR="/var/opt/norduni/nibackup"
VIRTUAL_ENV="/var/opt/norduni/norduni_environment"
BACKUPURL="https://ni-data.nordu.net"
. $SCRIPT_DIR/.scriptenv

usage="Usage: $0 [-r <datadir>] [-n <norduni>] [-e <virtualenv>] [-u <backup_url]"
while getopts ":r:n:e:u:" options; do
  case $options in
    r) DATA_DIR=$OPTARG;;
    n) NORDUNI_DIR=$OPTARG;;
    e) VIRTUAL_ENV=$OPTARG;;
    u) BACKUPURL=$OPTARG;;
    *) echo $usage
        exit 1;;
  esac
done

# Pre checks
if [ ! -d "$DATA_DIR" ]; then
  echo "Creating data dir $DATA_DIR"
  mkdir -p $DATA_DIR
fi

if [ ! -d "$NORDUNI_DIR/src" ]; then
  echo "Error: no norduni @ $NORDUNI_DIR"
  ERROR=true
fi

if [ ! -d "$VIRTUAL_ENV/bin" ]; then
  echo "Error: no virtual env @ $VIRTUAL_ENV"
  ERROR=true
fi

if [ -z "$BACKUPUSER" ]; then
  echo "Error: Missing BACKUPUSER from $SCRIPT_DIR/.scriptenv"
  ERROR=true
fi

if [ ! -f "$SCRIPT_DIR/restore.conf" ]; then
  echo "Error: Missing $SCRIPT_DIR/restore.conf file"
  ERROR=true
fi

if [ $ERROR ]; then
  exit 1
fi

ENV_FILE="$NORDUNI_DIR/src/niweb/.env"
NOCLOOK_DIR="$NORDUNI_DIR/src/scripts"
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
cd $DATA_DIR
curl -s -u "$BACKUPUSER" -o "postgres.sql.gz" "$BACKUPURL/postgres.sql.gz"
curl -s -u "$BACKUPUSER" -o "ni_data.tar.gz" "$BACKUPURL/ni_data.tar.gz"
tar xf ni_data.tar.gz 


msg "Removing neo4j data"
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n:Node) OPTIONAL MATCH (n)-[r]-() DELETE n,r;"


msg "Drop DB"
dropdb $DB_NAME
createdb $DB_NAME


msg "Import SQL DB"
gunzip -c $DATA_DIR/postgres.sql.gz | psql --quiet -o /dev/null norduni


msg "Reset DB sequences"
psql --quiet -f "$NOCLOOK_DIR/sql/reset-sequences-noclook.sql" norduni


msg "Importing data from json"
. $VIRTUAL_ENV/bin/activate
cd $NOCLOOK_DIR
python noclook_consumer.py -C $SCRIPT_DIR/restore.conf -I

msg "Reset last modified"
psql --quiet -f "$NOCLOOK_DIR/sql/fix-last-modified.sql" norduni


msg "Cleanup nibackup"
rm -r $DATA_DIR/json

msg "Restore done."
