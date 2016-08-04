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
chown ni: /var/log/norduni
chmod 770 /var/log/norduni

cd /var/opt/norduni
git clone https://git.nordu.net/norduni.git
cd norduni
git checkout bolt

/var/opt/norduni_environment/bin/pip install -r requirements/prod.txt

/var/opt/norduni_environment/bin/pip freeze
