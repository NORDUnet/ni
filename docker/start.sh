#!/bin/sh

set -e
set -x

. /var/opt/norduni_environment/bin/activate

# These could be set from Puppet if multiple instances are deployed
base_dir=${base_dir-"/var/opt/norduni"}
name=${name-"noclook"}
# These *can* be set from Puppet, but are less expected to...
project_dir=${project_dir-"${base_dir}/norduni/src/niweb"}
log_dir=${log_dir-'/var/log/norduni'}
state_dir=${state_dir-"${base_dir}/run"}
workers=${workers-1}
worker_class=${worker_class-sync}
worker_threads=${worker_threads-1}
worker_timeout=${worker_timeout-30}
gunicorn_args="--bind 0.0.0.0:8080 -w ${workers} -k ${worker_class} --threads ${worker_threads} -t ${worker_timeout} niweb.wsgi"

chown ni: "${log_dir}" "${state_dir}"

# set PYTHONPATH if it is not already set using Docker environment
export PYTHONPATH=${PYTHONPATH-${project_dir}}

dev_args=""
if [ -f "/var/opt/source/norduni/README" ]; then
    # developer mode, restart on code changes
    dev_args="--reload"
fi

# nice to have in docker run output, to check what
# version of something is actually running.
/var/opt/norduni_environment/bin/pip freeze

start-stop-daemon --start -c ni:ni --exec \
     /var/opt/norduni_environment/bin/gunicorn \
     --pidfile "${state_dir}/${name}.pid" \
     --user=ni --group=ni -- $gunicorn_args $dev_args
