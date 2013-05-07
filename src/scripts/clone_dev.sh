set -e
export JAVA_HOME=/usr/lib/jvm/java-6-openjdk-i386
sudo echo "Fire and forget..."
/usr/local/sbin/ni-pull.sh -r /home/lundberg/nistore/ 
# Purge both databases
. /home/lundberg/norduni/src/niweb/env/bin/activate
cd /home/lundberg/norduni/src/scripts/
./noclook_consumer.py -C restore_dev.conf -P
# Drop all helper tables
sudo -u postgres psql -c "DROP database norduni2" postgres
# Restore a clone of the SQL database
sudo -u postgres psql -f /home/lundberg/nistore/producers/noclook/sql/postgres.sql postgres
# Restore the nodes from the backup
./noclook_consumer.py -C restore_dev.conf -I
chown -R lundberg:lundberg /home/lundberg/norduni/dependencies/neo4jdb
