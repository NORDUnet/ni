et -e
pushd `dirname $0` > /dev/null
SCRIPT_DIR="$(pwd)"
popd > /dev/null
VIRTUAL_ENV="/var/norduni/env"
MANAGE_PY="/var/norduni/src/niweb"
NOCLOOK_DIR="/var/norduni/src/scripts"
NISTORE_DIR="/var/nistore"
NEO4J_DIR="/var/opt/neo4j-community"
DB_NAME="norduni"
SQL_DUMP="/var/nistore/producers/noclook/sql"
DJANGO_DB_USER="ni"

function now (){
  date +"%Y-%m-%d %H:%M:%S"
}

function msg(){
  echo "> $1 - $(now)"
}


    msg "Removing neo4j data"
    . $VIRTUAL_ENV/bin/activate
    cd $NOCLOOK_DIR
    python noclook_consumer.py -C $SCRIPT_DIR/ndn.conf -P

    msg "Adding indexes to neo4j"
    curl -D - -H "Content-Type: application/json" --data '{"name" : "node_auto_index","config" : {"type" : "fulltext","
provider" : "lucene"}}' -X POST http://localhost:7474/db/data/index/node/
    curl -D - -H "Content-Type: application/json" --data '{"name" : "relationship_auto_index","config" : {"type" : "fulltext","provider" : "lucene"}}' -X POST http://localhost:7474/db/data/index/relationship/


    msg "Drop DB"
    dropdb $DB_NAME
    createdb $DB_NAME


    msg "Import SQL DB"
    psql -f $SQL_DUMP/postgres.sql norduni


    msg "Reset DB sequences"
    psql -f "$NOCLOOK_DIR/sql/reset-sequences-noclook.sql" norduni


    msg "Importing data from json"
    . $VIRTUAL_ENV/bin/activate
    cd $NOCLOOK_DIR
    python noclook_consumer.py -C $SCRIPT_DIR/restore.conf -I


    msg "Updating data from nistore"
    . $VIRTUAL_ENV/bin/activate
    cd $NOCLOOK_DIR
    python noclook_consumer.py -C $SCRIPT_DIR/ndn.conf -I


    msg "Restore and upgrade done."

