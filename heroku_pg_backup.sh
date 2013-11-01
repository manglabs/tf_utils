#!/bin/sh

# to run this script you must have access privileges for Thinkful's production
# Heroku account.  

echo "Deleting existing backup"
dropdb --if-exists tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Intitializing tf_prod_backup db"
createdb -U postgres tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Retrieving most recent pg_backup from Heroku."
curl -o ${TEMP_BACKUP_PATH} `heroku pgbackups:url --app tf-pysplash-prod`
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Restoring backup to tf_prod_backup"
pg_restore --no-owner --no-acl ${TEMP_BACKUP_PATH} -d tf_prod_backup
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi
rm ${TEMP_BACKUP_PATH}

echo "Sanitizing backup data. Please hold."
psql_output=`psql -U postgres tf_prod_backup << EOF
UPDATE users SET password='';
UPDATE users SET salt='';
UPDATE users SET tf_login= tf_login || '_';
UPDATE contacts SET email = email || '_';
UPDATE contacts SET tf_login = tf_login || '_' WHERE tf_login IS NOT NULL;
EOF`
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Dumping sanitized database so you can share it with others"
dump_path=$1
pg_dump --no-owner tf_prod_backup > $dump_path"tf_backup.dump" 
if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi

echo "Congratulations! Your backup worked!"
