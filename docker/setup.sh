#!/bin/bash
#
# Install all requirements
#

set -e
set -x

virtualenv /var/opt/norduni_environment

addgroup --system ni
adduser --system --shell /bin/false ni

mkdir -p /var/log/norduni
chown -R ni:root /var/log/norduni

mkdir -p /var/opt/norduni
chown -R ni:ni /var/opt/norduni

mkdir -p /var/opt/norduni/run
chown -R ni:ni /var/opt/norduni/run

mkdir -p /var/opt/norduni/staticfiles
chown -R ni:ni /var/opt/norduni/staticfiles

mkdir -p /var/opt/norduni/media
chown -R ni:ni /var/opt/norduni/media

mkdir -p /var/opt/source

cd /var/opt/norduni/norduni/

/var/opt/norduni_environment/bin/pip install -r requirements/prod.txt
/var/opt/norduni_environment/bin/pip install -r requirements/dev.txt
/var/opt/norduni_environment/bin/pip install -r requirements/testing.txt

/var/opt/norduni_environment/bin/pip freeze
