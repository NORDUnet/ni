#!/bin/sh

set -e
set -x

. /opt/eduid/bin/activate

# These could be set from Puppet if multiple instances are deployed
base_dir=${base_dir-"/var/opt/norduni"}
# These *can* be set from Puppet, but are less expected to...
cfg_dir=${cfg_dir-"${base_dir}/etc"}
log_dir=${log_dir-'/var/log/norduni'}
state_dir=${state_dir-"${base_dir}/run"}
cfg=${cfg-"${cfg_dir}/.env"}

chown ni: "${log_dir}" "${state_dir}"

# || true to not fail on read-only cfg_dir
chgrp ni "${cfg}" || true
chmod 640 "${cfg}" || true

dev_args=""
if [ -f "/var/opt/norduni/src/norduni/README" ]; then
    # developer mode, restart on code changes
    dev_args=""
fi

# nice to have in docker run output, to check what
# version of something is actually running.
/opt/eduid/bin/pip freeze

