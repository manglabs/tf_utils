#!/usr/bin/env python

#################
#
# We developed our own process for student signups, using the fastest,
# most flexible CRM available: Google Docs Spreadsheets.
# It worked but has become unweildy. This script migrates our system
# to a proper system: Zoho CRM.
# 
# Here's our rollout plan
#
# 1) import all contacts w/o communication as leads
#   - email
#   - lname as email address
#   - signup date
#   - stage signed up
#   SOURCE: 
#     - Applicants tab WITH NO value for "Response to 1st email"
# 2) import all contacts with communication as contacts
#   - email
#   - fname blank 
#   - lname as email address
#   - signup date
#   SOURCE:
#     - Applicants tab WITH value for "Response to 1st email"
#     - Citi applicants
#     - Main site applicants
#     - Students & former students
# 3) for all #2, create a new "potential"
#   - (link via email of contact)
#   - close date ???
#   - funnel stage
#   - lead source
#   SOURCE:
#     - Same as #2
# 4) for contacts in manual sales process
#   - update stage
#   SOURCE:
#     - Newsletter processing
# 5) for contacts with name
#   - update name, phone, address, etc
#   SOURCE:
#   - All.
# 6) update lead source w/ KissMetrics data
# 6) move notes, emails, etc.
#
#
# Issues:
# - We have no unique identifier for students beyond email, which is unstable. But
#   - Zoho is our canonical data store.
#   - Want to use Zoho ID but it changes when a lead becomes a contact (or potential)
# - You must give Zoho THREE identifiers, including your plaintext password, for the API access. WTF?
#
#################


import os, pdb, csv
from datetime import datetime, timedelta
from optparse import OptionParser

# how elegant to put your own name in the library name...
from mfabrik.zoho.crm import CRM
from mfabrik.zoho.core import ZohoException
from beautiful_soupcon_tf_zoho import ThinkfulPerson


def load_tf_tab_file(fn, parse_func, *parse_func_args):
	print "Loading file '%s'" % fn
	tf_people = []
	is_header = True
	with open(fn) as csvfile:
		csvf = csv.reader(csvfile, delimiter=',', quotechar='"')
		for row in csvf:
			if is_header:
				is_header = False
				continue
			tf_people.append(parse_func(row, *parse_func_args))
	return tf_people

def load_tf_tabs(crm):
	tf_people = []

	prefix = "/Users/darrell/Downloads/CRM-Live"

	tf_people.append("Applicants!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Applicants.csv' % (prefix), 
			ThinkfulPerson.from_tf_applicants_tab))
	tf_people.append("Main Site Applicants!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Main Site Applicants.csv' % (prefix), 
			ThinkfulPerson.from_tf_citi_tab))
	tf_people.append("Citi Applicants!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Citi Applicants.csv' % (prefix), 
			ThinkfulPerson.from_tf_citi_tab))
	
	#
	# There's some logic to the order (see notes at the top)
	# mostly it's just logically cleaner to think in terms of 
	# getting all data in, then updating it.
	#
	tf_people.append("Students!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Students.csv' % (prefix), 
			ThinkfulPerson.from_tf_students_tab, 'Current student'))
	tf_people.append("Former Students!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Former Students.csv' % (prefix), 
			ThinkfulPerson.from_tf_students_tab, 'Former student'))
	tf_people.append("Newsletter Processing!")
	tf_people.extend(
		load_tf_tab_file('%s/Students - Newsletter Processing.csv' % (prefix), 
			ThinkfulPerson.from_tf_newsletter_processing_tab))

	for person in tf_people:
		if type(person) == str:
			# a hack to help the logs be clearer
			print "MIGRATING FROM NEW SOURCE FILE %s" % person
		else:
			print "Migrating to Zoho: %s" % (person)
			# pdb.set_trace()
			person.send2zoho(crm)

def main():
    def env(name, required=True):
        value = os.environ.get(name, None)
        if required and not value:
            raise Exception("Missing required env variable '%s'" % name)
        return value

    # note Zoho requires your password... Did these as env vars so at least 
    # they wouldn't be recorded in your .bash_history
    crm = CRM(username=env("ZOHO_USERNAME"), password=env("ZOHO_PASSWORD"), 
        authtoken=env("ZOHO_AUTHTOKEN"), scope="crmapi")
    crm.open()

    load_tf_tabs(crm)
    crm.close()

if __name__ == '__main__':
    main()

