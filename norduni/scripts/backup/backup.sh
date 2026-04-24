#!/usr/bin/env bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TODAY=$(date +"%Y-%m-%d")

# Souce env
. ${SCRIPT_DIR}/backup-env

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
# Activate virtual environment
. $VIRTUALENV

# Make backup directory if missing
[ -d $BACKUPDIR ] || mkdir -p $BACKUPDIR

## Backup of SQL database
pg_dump norduni | gzip > $BACKUPDIR/postgres-$TODAY.sql.gz
# Backup Neo4j data
[ -d $BACKUPDIR/json ] && rm -r $BACKUPDIR/json
mkdir $BACKUPDIR/json
cd $NORDUNIDIR/src/scripts/
./noclook_producer.py -O $BACKUPDIR/json
cd $BACKUPDIR
tar cfz ni_data-$TODAY.tar.gz json/
rm -r json

if [ -z "$DISABLE_UPLOAD" ]; then
  # Push data
  curl -sS -u "$BACKUPUSER" -T "$BACKUPDIR/postgres-$TODAY.sql.gz" "$BACKUPURL/"
  curl -sS -u "$BACKUPUSER" -T "$BACKUPDIR/ni_data-$TODAY.tar.gz" "$BACKUPURL/"
  # Make latest
  set +e
  curl -sS -X DELETE -u "$BACKUPUSER" "$BACKUPURL/ni_data.tar.gz"
  curl -sS -X DELETE -u "$BACKUPUSER" "$BACKUPURL/postgres.sql.gz"
  set -e
  curl -sS -X COPY -u "$BACKUPUSER" -H "Destination: $BACKUPURL/postgres.sql.gz" "$BACKUPURL/postgres-$TODAY.sql.gz"
  curl -sS -X COPY -u "$BACKUPUSER" -H "Destination: $BACKUPURL/ni_data.tar.gz" "$BACKUPURL/ni_data-$TODAY.tar.gz"
fi

# Cleanup
find $BACKUPDIR -mtime +8 -exec rm {} \;
