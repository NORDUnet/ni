#!/bin/sh

MANAGE_PY=/app/niweb/manage.py
case "$*" in
  dev)
    export SECRET_KEY=$(python -c "import random; print(''.join([random.SystemRandom().choice('abcdefghijlkmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(50)]))")
    export DEBUG_MODE=True
    export DJANGO_SETTINGS_MODULE=niweb.settings.dev

    # check if the dbs are up
    for i in $(seq 1 60)
    do
      if nc -z postgres 5432 && nc -z neo4j 7687; then
        break
      fi
      sleep 1
    done

    yes no | python $MANAGE_PY migrate
    exec python $MANAGE_PY runserver 0.0.0.0:8000
    ;;
  shell)
    export DJANGO_SETTINGS_MODULE=niweb.settings.dev
    /bin/sh
    ;;
  neo4j-password)
    PASSWORD=${2:-docker}
    curl -H "Content-Type: application/json" -X POST -d "{\"password\":\"$PASSWORD\"}" -u neo4j:neo4j http://neo4j:7474/user/neo4j/password
    ;;
  manage*)
    shift
    echo "python $MANAGE_PY $@"
    python $MANAGE_PY "$@"
    ;;
  consume-restore)
    if [ ! -f /app/scripts/restore.conf ]; then
      cat <<EOM > /app/scripts/restore.conf
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
    fi
    cd /app/scripts
    python noclook_consumer.py -C restore.conf -I
    ;;
  consume)
    if [ ! -f /app/scripts/consume.conf ]; then
      cat > /app/scripts/consume.conf
    fi
    cd /app/scripts
    python noclook_consumer.py -C consume.conf -I
    ;;
esac
