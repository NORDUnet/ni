#!/bin/sh

MANAGE_PY=/app/niweb/manage.py
case "$*" in
  dev)
    export SECRET_KEY=$(python -c "import random; print(''.join([random.SystemRandom().choice('abcdefghijlkmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(50)]))")
    export DEBUG_MODE=True
    export DJANGO_SETTINGS_MODULE=niweb.settings.dev
    yes no | python $MANAGE_PY migrate
    python $MANAGE_PY runserver 0.0.0.0:8000
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
  consume)
    if [ ! -f /app/consume.conf ]; then
      cat > /app/consume.conf
    fi
    cd /app/scripts
    python noclook_consumer.py -C /app/consume.conf -I
    ;;
esac
