#!/usr/bin/env bash

######################
#
# Simple script to dump specific redis data to our env repo.
# Commits the results to repo but doesn't push them.
#
######################

BACKUP="$FIXTURE_ROOT/redis"
HOST="http://dada:iheartthinkful@www.thinkful.com"


function dump {
    key=$1
    from="$HOST/tim/api/$key"
    to="$BACKUP/tim_$key"
    echo "Dumping '$key' to '$to'"
    curl -v "$from" > "$to" 2>/dev/null
    if [ `echo $?` -ne 0 ]; then echo "Could not dump '$key'. Aborting."; exit 1; fi
}

dump "customers"
dump "leads"
dump "status"

# this is weird, but want to automate backup process completely
echo "Committing changes to environment repo"
cd "$ENV_REPO_PATH"
git add "$BACKUP"
git commit -m "new dump of production redis data as of `date`"
cd -
