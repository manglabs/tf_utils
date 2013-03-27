#!/usr/bin/env python

#####################
#
# Migrate leads / potentials from Zoho crm into Customer.io
#
#
# TODO Require name be filled in in CRM so we can personalize email.
#####################

import os, pdb
from datetime import datetime
from optparse import OptionParser

from mfabrik.zoho.crm import CRM
from beautiful_soupcon_tf_zoho import (ThinkfulPerson, 
    get_zoho_contacts, _stitch_pages)
from customerio import CustomerIO

def get_all_potential_contacts(crm, all_contacts):
    tf_people = []
    if True:
        fh = open('leads2contact.csv', 'r')
        leads2contacts = {}
        for line in fh.readlines():
            email,contactid,potentialid = line.split(',')
            leads2contacts[potentialid.strip()] = (email, contactid)
        fh.close()
        for potential in crm.get_potentials():
            (email, contactid) = leads2contacts[potential['POTENTIALID']]
            tfp = all_contacts[contactid]
            tfp.funnel_stage = potential['Stage']
            tf_people.append(tfp)
    else:
        serial = open('leads2contact.csv', 'w')
        serial.write('email,contactid,potentialid\n')
        pdb.set_trace()# beware api quotas
        for potential in crm.get_potentials():
            for contact in crm.get_contacts_for_potential(potential['POTENTIALID']):
                ptfp = ThinkfulPerson.from_zoho_potential(contact)
                serial.write('%s,%s,%s\n' % (ptfp.email, ptfp.zoho_contact_id, potential['POTENTIALID']))
                serial.flush()
                tfp = all_contacts[ptfp.zoho_contact_id]
                print "Mapping", ptfp, "to", tfp
                tfp.funnel_stage = potential['Stage']
                tf_people.append(tfp)
        serial.close()
    return tf_people

def _dt2unix(string_date):
    (y,m,d) = map(int, string_date.split('-'))
    dt = datetime(year=y, month=m, day=d)
    return dt.strftime('%s')

def send_potentials_to_customerio(crm, cio):
    all_contacts = get_zoho_contacts(crm)
    contacts = get_all_potential_contacts(crm, all_contacts)
    for c in contacts:
        print "Sending potential %s to customer.io" % c
        # cio.identify(id=c.zoho_contact_id, email=c.email, 
        #     funnel_stage=c.funnel_stage, created_at=_dt2unix(c.signup_date))
        cio.identify(id=c.email, email=c.email, 
            funnel_stage=c.funnel_stage, created_at=_dt2unix(c.signup_date))

def send_leads_to_customerio(crm, cio):
    for lead in _stitch_pages(crm.get_leads):
        tfp = ThinkfulPerson.from_zoho_lead(lead)
        print "Sending lead %s to customer.io" % tfp
        cio.identify(id=tfp.email, email=tfp.email, 
            funnel_stage=tfp.funnel_stage, created_at=_dt2unix(tfp.signup_date))


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

def main():
    parser = OptionParser("%prog --rpt_bad_data | --send_potentials_to_cio | --send_leads_to_cio")
    parser.add_option("--rpt_bad_data", action="store_true"
        , help="Report bad data in CRM (this is read-only)")
    parser.add_option("--send_potentials_to_cio", action="store_true"
        , help="Send all 'potentials' from Zoho to customer.io")
    parser.add_option("--send_leads_to_cio", action="store_true"
        , help="Send all 'leads' from Zoho to customer.io")
    (options, args) = parser.parse_args()

    def env(name, required=True):
        value = os.environ.get(name, None)
        if required and not value:
            raise Exception("Missing required environment var '%s'" % name)
        return value

    (options, args) = parser.parse_args()
    # note Zoho requires your password... Did these as env vars so at least 
    # they wouldn't be recorded in your .bash_history
    crm = CRM(username=env("ZOHO_USERNAME"), password=env("ZOHO_PASSWORD"), 
        authtoken=env("ZOHO_AUTHTOKEN"), scope="crmapi")
    crm.open()

    if options.send_potentials_to_cio or options.send_leads_to_cio:
        cio = CustomerIO(env("CIO_SITE_ID"), env("CIO_API_KEY"))

    if options.rpt_bad_data:
        all_leads_also_contacts(crm)
    if options.send_potentials_to_cio:
        send_potentials_to_customerio(crm, cio)
    if options.send_leads_to_cio:
        send_leads_to_customerio(crm, cio)

if __name__ == '__main__':
    main()

