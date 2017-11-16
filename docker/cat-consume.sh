#!/bin/sh

usage="Usage: $0 [-h] [-n <nmap_path>] [-j <juniper_path>] [-x <nagios_path>] [-c <cfengine_path>] [-b <noclook_backup_path>] [-d <base_dir>] [-a <data_age>]"

DATA_AGE=30
while getopts ":n:j:x:c:b:d:a:" opt; do
  case $opt in
    d) BASE_DIR="$OPTARG";;
    j) JUNIPER=${OPTARG:-juniper_conf/json/};;
    n) NMAP=${OPTARG:-nmap_services_py/json/};;
    x) NAGIOS=${OPTARG:-nagiosxi_api/json/};;
    c) CFENGINE=${OPTARG:-cfengine_report/json/};;
    b) BACKUP=${OPTARG:-noclook/json/};;
    a) DATA_AGE=${OPTARG:-30};;
    *) echo $usage
       exit 1;;
  esac
done

function path() {
  if [ -n "$1" ]; then
    echo "$BASE_DIR$1"
  fi
}

cat <<EOM
[data_age]
juniper_conf = $DATA_AGE

[delete_data]
juniper_conf = false

[data]
juniper_conf = $(path $JUNIPER)
nmap_services_py = $(path $NMAP)
alcatel_isis =
nagios_checkmk = $(path $NAGIOS)
cfengine_report = $(path $CFENGINE)
noclook = $(path $BACKUP)
EOM
