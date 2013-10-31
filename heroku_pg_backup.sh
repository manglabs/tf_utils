#!/bin/sh

echo "Deleting existing backup"
dropdb --if-exists tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Intitializing tf_prod_backup db"
createdb tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Retrieving most recent pg_backup from Heroku."
curl -o ${TEMP_BACKUP_PATH} `heroku pgbackups:url --app tf-pysplash-prod`
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Restoring backup to tf_prod_backup"
pg_restore ${TEMP_BACKUP_PATH} -d tf_prod_backup --no-owner
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Sanitizing backup data. Please hold."
psql tf_prod_backup << EOF
ALTER TABLE users DROP COLUMN password;
ALTER TABLE users DROP COLUMN salt;
UPDATE users SET tf_login='_' || tf_login;
UPDATE contacts SET email = '_' || tf_login;
EOF
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

