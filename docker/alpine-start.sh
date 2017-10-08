#!/bin/sh

case "$*" in
  dev)
    export SECRET_KEY=$(python -c "import random; print(''.join([random.SystemRandom().choice('abcdefghijlkmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(50)]))")
    export DEBUG_MODE=True
    yes no | python manage.py migrate
    python /app/niweb/manage.py runserver 0.0.0.0:8000
    ;;
  shell)
    /bin/sh
    ;;
esac
