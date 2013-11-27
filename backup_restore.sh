#!/bin/sh

BACKUP=$FIXTURE_ROOT/postgres/tf_backup.dump
echo "Deleting existing backup"
dropdb --if-exists tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Creating empty db for tf_prod_backup"
x=`createdb -U thinkful -T template0 tf_prod_backup`
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Restoring to tf_prod_backup"
x=`psql -U thinkful --set ON_ERROR_STOP=on tf_prod_backup < $BACKUP`
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Congratulations! Your backup worked, friend!"

