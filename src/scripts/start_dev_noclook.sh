#!/bin/bash
set -e
export JAVA_HOME=/usr/lib/jvm/java-6-openjdk/jre/
LOGFILE=/home/lundberg/norduni/logs/noclook.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=1
# user/group to run as
USER=lundberg
GROUP=lundberg
cd /home/lundberg/norduni/src/niweb
source env/bin/activate
test -d $LOGDIR || mkdir -p $LOGDIR
exec env/bin/gunicorn_django -w $NUM_WORKERS \
	 --user=$USER --group=$GROUP --log-level=debug \
	  --log-file=$LOGFILE 2>>$LOGFILE
