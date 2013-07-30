#!/usr/bin/env python

#####################
#
# Migrate leads / potentials from Zoho crm into Customer.io
#
#
# TODO Require name be filled in in CRM so we can personalize email.
# TODO "signed up at" should be a date / time so we don't lose granularity we had at lead sign up time.
# TODO create way for any contact to be allowed to receive newsletter (investors, long term hires, who else?)
# TODO there's no "resubscribe:" anyone who resubscribes will be auto-unsubscribed when mismatched_unsubscribed() is run
#      The only way to do this is to have Zoho be the canonical data source: replace the unsubscribe URL w/ an API call to Zoho.
#
#####################

import os, pickle, pdb
from datetime import datetime
from optparse import OptionParser

from mfabrik.zoho.crm import CRM
from beautiful_soupcon_tf_zoho import (ThinkfulPerson, 
    get_zoho_contacts, _stitch_pages)
from tf_utils import get_cio, get_crm
from queue import conn
from tf_utils.fixtures import fixtureable

def get_all_potential_contacts(crm, all_contacts):
    tf_people = []
    if crm.use_api_allowance:
        serial = open('potential2contact.csv', 'w')
        serial.write('email,contactid,potentialid\n')
        for potential in _stitch_pages(crm.get_potentials):
            for contact in crm.get_contacts_for_potential(potential['POTENTIALID']):
                ptfp = ThinkfulPerson.from_zoho_potential_contact(contact)
                serial.write('%s,%s,%s\n' % (ptfp.email, ptfp.zoho_contact_id, potential['POTENTIALID']))
                serial.flush()
                tfp = all_contacts[ptfp.zoho_contact_id]
                # print "Mapping", ptfp, "to", tfp
                tfp.funnel_stage = potential['Stage']
                tfp.signup_date_from_potential = tfp._parse_date(potential['Signed up at'])
                tf_people.append(tfp)
        serial.close()
    else:
        fh = open('potential2contact.csv', 'r')
        potential2contact = {}
        for line in fh.readlines():
            email,contactid,potentialid = line.split(',')
            potential2contact[potentialid.strip()] = (email, contactid)
        fh.close()
        for potential in _stitch_pages(crm.get_potentials):
            try:
                (email, contactid) = potential2contact[potential['POTENTIALID']]
            except KeyError:
                print "PotentialID '%(pid)s' has no associated contact! Skipping. Check url https://crm.zoho.com/crm/ShowEntityInfo.do?module=Potentials&id=%(pid)s&isload=true" % (dict(pid=potential['POTENTIALID']))
                continue
            tfp = all_contacts[contactid]
            tfp.funnel_stage = potential['Stage']
            tfp.signup_date_from_potential = tfp._parse_date(potential['Signed up at'])
            tf_people.append(tfp)
    return tf_people

def _dt2unix(string_date):
    (y,m,d) = map(int, string_date.split('-'))
    dt = datetime(year=y, month=m, day=d)
    return dt.strftime('%s')

def _get_cio_customer(cio, customer_id):
    try:
        return cio.get_customer(customer_id)
    except Exception, e:
        return None

def send_contact_to_customerio(cio, contact, extra_cio_args=None):
    def valid_name(d, k):
        return d[k] and not '@' in d[k] and not 'null' in d[k]

    email = contact['Email'].strip()

    cio_args = dict(id=email, email=email, 
        contact_type=contact['Contact Type'])

    tfp = ThinkfulPerson()
    if valid_name(contact, 'Signed up at'):
        created_at = int((tfp._parse_date(contact['Signed up at']) - datetime.utcfromtimestamp(0)).total_seconds())
        cio_args['created_at'] = created_at
    if valid_name(contact, 'First Name'):
        cio_args['first_name'] = contact['First Name']
    if valid_name(contact, 'Last Name'):
        cio_args['last_name'] = contact['Last Name']
    
    if not extra_cio_args == None:
        # override above w/ what was sent in
        cio_args.update(extra_cio_args)

    cio.identify(**cio_args)

def send_potential_to_customerio(cio, pot, contact):
    def valid_name(d, k):
        return d[k] and not '@' in d[k] and not 'null' in d[k]

    extra_cio_args = dict()
    cio_customer = _get_cio_customer(cio, contact['Email'])
    if cio_customer and cio_customer['customer']['attributes'].has_key('created_at'):
        print "Updating potential %s in customer.io" % pot['POTENTIALID']
        extra_cio_args['created_at'] = cio_customer['customer']['attributes']['created_at']
    else:
        print "No created date for potential %s. Sending as blank" % pot
    
    if valid_name(pot, 'Course'):
        extra_cio_args['course'] = pot['Course']

    send_contact_to_customerio(cio, contact, extra_cio_args=extra_cio_args)

def send_potentials_to_customerio(cio):
    pots_by_contact = {}
    for pot in _get_from_cache('tim_potentials'):
        pots_by_contact[pot.zoho_contact_id] = pot
    contacts = _get_from_cache('tim_contacts')
    for c in contacts:
        if not pots_by_contact.has_key(c['CONTACTID']):
            continue
        pot = pots_by_contact[c['CONTACTID']]
        try:
            send_potential_to_customerio(cio, pot, c)
        except Exception, e:
            print "Could not send %s to customer.io! %s" % (c, e)
            # pdb.set_trace()

def send_leads_to_customerio(crm, cio):
    for lead in _stitch_pages(crm.get_leads):
        tfp = ThinkfulPerson.from_zoho_lead(lead)
        if tfp.funnel_stage == 'Signed up':
            # print "Sending lead %s to customer.io with funnel stage '%s'" % (tfp, tfp.funnel_stage)
            cio.identify(id=tfp.email, email=tfp.email, 
                created_at=tfp.signup_date.strftime('%s'),
                funnel_stage=tfp.funnel_stage, 
                contact_type=tfp.contact_type)
        else:
            print "Not sending non-funnel lead %s to customer.io" % (tfp)

def _inc_or_1(d, k, v):
    if d.has_key(k):
        d[k].append(v)
    else:
        d[k] = [v]

def all_leads_also_contacts(crm):
    """Show all contacts or leads with overlapping email addresses"""

    leads = {}
    print "Getting all leads..."
    for lead in _stitch_pages(crm.get_leads):
        leads[lead['LEADID']] = lead['Email']
    
    contacts = get_zoho_contacts(crm)

    dup_emails = {}
    for contact in contacts.values():
        _inc_or_1(dup_emails, contact.email, contact.zoho_contact_id)
    for lead_id, email in leads.items():
        _inc_or_1(dup_emails, email, lead_id)

    if len(dup_emails):
        print "Found %s leads that are also contacts:" % len(dup_emails)
        print "Format: {email} : [zoho_id, ...]"
        for email, items in dup_emails.items():
            if len(items) > 1:
                print email, ":", items
    else:
        print "No leads found that are also contacts!"

def mismatched_signup_date_potentials_contacts(crm):
    all_contacts = get_zoho_contacts(crm)
    contacts = get_all_potential_contacts(crm, all_contacts)
    for c in contacts:
        if not c.signup_date_from_potential and not c.signup_date:
            print "No known signup_date for %s" % (c)
        elif c.signup_date_from_potential == c.signup_date:
            print "Signup date is all good for %s" % c
        elif c.signup_date_from_potential and not c.signup_date:
            print "Updating missing signup_date for %s to %s" % (c, c.signup_date_from_potential)
            contact = {
                "Id": c.zoho_contact_id,
                "Signed up at": c._dt2zoho(c.signup_date_from_potential),
            }
            contacts = crm.update_contacts([contact])
        elif not c.signup_date_from_potential and c.signup_date:
            print "Contact has signup date %s, Potential is missing for: %s" % (c.signup_date, c)
        else:
            print "Mismatched signup date %s! %s vs %s" \
                % (c, c.signup_date_from_potential, c.signup_date)

def missing_signup_date_leads(crm):
    print "Getting all leads..."
    for lead in _stitch_pages(crm.get_leads):
        tfp = ThinkfulPerson.from_zoho_lead(lead)
        if tfp.signup_date:
            print "Signup date is all good for lead %s (set to %s, created %s)" \
                % (tfp, tfp.signup_date, tfp.created_date)
        elif tfp.funnel_stage:
            print "Correcting missing signup date for lead %s (should be created date %s)" % (tfp, tfp.created_date)
            # pdb.set_trace()
            lead = {
                "Id" : tfp.zoho_lead_id,
                "Signed up at": tfp._dt2zoho(tfp.created_date),
            }
            crm.update_leads([lead])
        else:
            print "Lead doesn't / shouldn't have signup date %s" % (tfp)

def _get_zoho_set(crm, search_condition):
    print "Getting all leads & contacts from zoho matching search condition '%s'..." % search_condition
    unsubscribed = set()
    for lead in _stitch_pages(crm.search_leads, search_condition):
        unsubscribed.add(ThinkfulPerson.from_zoho_lead(lead))
    for contact in _stitch_pages(crm.search_contacts, search_condition):
        unsubscribed.add(ThinkfulPerson.from_zoho_contact(contact))
    print "Found %s unsubscribed leads & contacts." % len(unsubscribed)
    return unsubscribed

def _get_cio_segment(cio, segment_id):
    print "Getting all customers from CustomerIO segment %s..." % segment_id
    unsubscribed = set()
    segment_json = cio._stitch_pages(cio.get_segment, [segment_id])

    for customer in segment_json['customers']:
        # print customer
        if not customer['attributes'].has_key('email'):
            print "***ERROR***: Customer ID %s has no email. Skipping." % customer['attributes']['id']
            continue
        tfp = ThinkfulPerson.from_cio(customer)
        unsubscribed.add(tfp)
    return unsubscribed

def _get_from_cache(cache_key):
    pickled = fixtureable('redis', conn.get)(cache_key)
    cached = pickle.loads(pickled)
    return cached

def _get_cached_person(cache_key, person_key, person_value):
    for row in _get_from_cache(cache_key):
        if row.has_key(person_key) and row[person_key] == person_value:
            return row
    return None

def _update_zoho_unsubscriber(crm, tfp):
    tfp_as_lead = _get_cached_person('tim_leads', 'Email', tfp.email)
    if tfp_as_lead:
        update_f, key = crm.update_leads, tfp_as_lead['LEADID']
    else:
        tfp_as_contact = _get_cached_person('tim_contacts', 'Email', tfp.email)
        if tfp_as_contact:
            update_f, key = crm.update_contacts, tfp_as_contact['CONTACTID']
        else:
            raise Exception("***ERROR*** Cannot find %s in cache." % tfp)

    if not key or key.strip() == "":
        raise Exception("***ERROR*** Invaid key for %s" % tfp)

    update_f([{
        "Id" : key,
        "Email Opt Out": "true",
    }])
    return True

def mismatched_unsubscribed(crm, cio):
    unsub_zoho = _get_zoho_set(crm, "(Email Opt Out|=|true)")
    # unsub_zoho = set()# avoid hitting api quota
    print "Currently %s unsubscribed contacts in Zoho" % len(unsub_zoho)
    # This is the segment containing all "Customers" who've unsubscribed
    # https://manage.customer.io/segments/12366/edit
    unsub_cio = _get_cio_segment(cio, 12366)
    print "Currently %s unsubscribed customers in CIO." % len(unsub_cio)

    # pdb.set_trace()

    # Unsubscribed in Zoho not synced to CIO
    print "Found %s email(s) in Zoho not in CIO." % len(unsub_zoho - unsub_cio)
    for tfp in unsub_zoho - unsub_cio:
        print "  In Zoho not in CIO:", tfp
        cio.identify(id=tfp.email, unsubscribed=True)

    # Unsubscribed in CIO not synced to Zoho
    print "Found %s email(s) in CustomerIO not in Zoho." % len(unsub_cio - unsub_zoho)
    for tfp in unsub_cio - unsub_zoho:
        print "  In CIO not in Zoho:",  tfp
        try:
            _update_zoho_unsubscriber(crm, tfp)
        except Exception, e:
            print e

def clean_out_test_emails_from_cio(cio):
    """remove our own emails from marketing so we don't receive all the 
    drip marketing and mess up the analytics.
    """
    test_emails = _get_cio_segment(cio, 16259)
    funnel_stage = "N/A: Was test."
    for tfp in test_emails:
        if (tfp.funnel_stage in ['Signed up', funnel_stage]) \
            and ('+' in tfp.email or '-' in tfp.email):
            contact_type = funnel_stage
            print "Setting %s in customer.io to funnel_stage & contact_type '%s'" % (tfp, funnel_stage)
            cio.identify(id=tfp.email,
                funnel_stage=funnel_stage,
                contact_type=contact_type)
        else:
            print "Not changing lead %s in customer.io" % (tfp)

def main():
    parser = OptionParser("%prog --rpt_bad_data | --update_cio | --mismatched_unsubscribed")
    parser.add_option("--rpt_bad_data", action="store_true"
        , help="Report bad data in CRM (this is read-only)")
    parser.add_option("--mismatched_unsubscribed", action="store_true")
    parser.add_option("--clean_out_test_emails_from_cio", action="store_true")
    parser.add_option("--update_cio", action="store_true"
        , help="Send all 'potentials' and 'leads' from Zoho to customer.io")
    parser.add_option("--use_api_allowance", action="store_true"
        , help="use valuable API allowances instead of cached copy. Beware api limits in Zoho!")
    (options, args) = parser.parse_args()
    
    # note Zoho requires your password... Did these as env vars so at least 
    # they wouldn't be recorded in your .bash_history
    crm = get_crm()
    crm.open()
    crm.use_api_allowance = options.use_api_allowance

    cio = get_cio()

    if options.rpt_bad_data:
        # all_leads_also_contacts(crm)
        # mismatched_signup_date_potentials_contacts(crm)
        # missing_signup_date_leads(crm)
        pass
    if options.clean_out_test_emails_from_cio:
        clean_out_test_emails_from_cio(cio)
    if options.mismatched_unsubscribed:
        mismatched_unsubscribed(crm, cio)
    if options.update_cio:
        send_potentials_to_customerio(cio)
        # we no longer use leads for potential students, so commented this out.
        # send_leads_to_customerio(crm, cio)

if __name__ == '__main__':
    main()

