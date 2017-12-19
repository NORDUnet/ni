#!/usr/bin/env bash
# 2017-10-06
# markus@nordu.net

usage="Usage: $0 [-h] -r <repository_path> [directories to add]"

while getopts ":r:a:" options; do
  case $options in
    r) REPO=$OPTARG;;
    h) echo $usage;;
    \?) echo $usage
        exit 1;;
    *) echo $usage
       exit 1;;
  esac
done

shift "$((OPTIND - 1))"


if [ -z $REPO ] || [ ! -d $REPO ]; then
        echo "Error: no repo @ $REPO, use -r <repo>"
        exit 1
fi

if [ "$#" -lt 1 ]; then
    echo "Error: you need to specify at least one directory to add"
    exit 1
fi

(
flock -x 201

cd $REPO

git pull --quiet origin master
for var in "$@"; do
  git add "$var"
done

# Only try to commit if anything was staged.
if ! git diff --cached --quiet ; then
  git commit --quiet -m "$(date)"
  git push --quiet origin master
fi
) 201>/tmp/ni-producer-git.lock
