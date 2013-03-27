
###################
#
# A bash client for the customer.io API. 
# Why bash? Because pain is good!
#
# But seriously... I've since migrated this to Python 
# (see our GitHub account)
#
# Note this includes a parser for Thinkful's internal CRM which 
# was a gdocs spreadsheet.
#
# TODO Stop this: Customer.io user ids are the row in applicants tab in gdoc
# 
###################


function date2u {
    # $1 must be mm/d/yyyy
    date="$1"
    echo `date -j -f "%m/%d/%Y %T" "$date 00:00:00" "+%s"`
}

# remove a user from customer.io by their (TF) user id
function cio_rm {
    id="$1"
    echo "Removing $id"
    curl -i https://track.customer.io/api/v1/customers/$id \
        -X DELETE \
        -u $SITE_ID:$API_KEY 2>&1 1>/dev/null
    if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi
}

# add a user to customer.io
function cio_add {
    id="$1"
    email="$2"
    created_at=`date2u $3`

    echo "Adding id:$id '$email' ca:$created_at"
    curl -i https://track.customer.io/api/v1/customers/$id \
        -X PUT \
        -d created_at=$created_at \
        -d funnel_stage="Signed up" \
        -u $SITE_ID:$API_KEY \
        -d email=$email 2>&1 1>/dev/null
    if [ `echo $?` -ne 0 ]; then echo "Last cmd failed! Aborting."; exit 100; fi
    #   -d name=Bob
    #   -d plan=premium
}

# this is a Thinkful-specific parser
function tab_applicants {
    #
    # cut out header, create vars of each CSV cell and 
    # add to customer.io as new/updated user
    #
    FILE_APPLICANTS = $1
    tail -n +2 "$FILE_APPLICANTS" | while read row; do
        read id email signup_date <<<$(IFS=","; echo $row)
        cio_add $id $email $signup_date
        # cio_rm $id
    done
}

tab_applicants "/Users/darrell/Downloads/Students - Sheet13.csv"
