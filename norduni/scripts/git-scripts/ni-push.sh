#!/bin/bash
#
# 2010-10-25
# jbn@nordu.net
#
# Generic cron-script that commits local nerds-data and pushes it to central g$

GIT="/usr/bin/git"

usage="Usage: $0 [-h] [-r repostitory location]"

while getopts ":r:" options; do
  case $options in
    r ) REPO=$OPTARG;;
    h ) echo $usage;;
    \?) echo $usage
         exit 1;;
    * ) echo $usage
         exit 1;;
  esac
done

if [ -z $REPO ] || [ ! -d $REPO ]; then
        echo "Error: no repo @ $REPO, use -r <repo>"
        exit 1
fi
cd $REPO
$GIT add -A
$GIT commit -a -m "$(date)"
$GIT push --quiet origin master

