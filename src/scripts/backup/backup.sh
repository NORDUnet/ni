#!/usr/bin/env bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TODAY=$(date +"%Y-%m-%d")

if [ -z "$VIRTUALENV" ] || [ -z "$NORDUNIDIR" ] || [ -z "$BACKUPDIR" ] || [ -z "$BACKUPURL" ] || [ -z "$BACKUPUSER" ]; then
  echo "Please create file ${SCRIPT_DIR}/backup-env containing the following variables"
  echo "VIRTUALENV="
  echo "NORDUNIDIR="
  echo "BACKUPDIR="
  echo "BACKUPUSER="
  echo "BACKUPURL="

  exit 1
fi

set -e
# Souce env
. ${SCRIPT_DIR}/backup-env
# Activate virtual environment
. $VIRTUALENV

## Backup of SQL database
pg_dump norduni | gzip > $BACKUPDIR/postgres-$TODAY.sql.gz
# Backup Neo4j data
cd $NORDUNIDIR/src/scripts/
./noclook_producer.py -O $BACKUPDIR/json
cd $BACKUPDIR
tar cfz ni_data-$TODAY.tar.gz json/
rm -r json

# Push data
curl -s -X PUT -u "$BACKUPUSER" --data-binary "@postgres-$TODAY.sql.gz" "$BACKUPURL/"
curl -s -X PUT -u "$BACKUPUSER" --data-binary "@ni_data-$TODAY.tar.gz" "$BACKUPURL/"
# Make latest
curl -s -X COPY -u "$BACKUPUSER" -H "Destination: $BACKUPURL/postgres.sql.gz" "$BACKUPURL/postgres-$TODAY.sql.gz"
curl -s -X COPY -u "$BACKUPUSER" -H "Destination: $BACKUPURL/ni_data.tar.gz" "$BACKUPURL/ni_data-$TODAY.tar.gz"
