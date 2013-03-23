
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
# - "Thinkful ID" (for the sake of Customer.io) is email address or Zoho id. Sad but true.
# - "prototype tf.com filtered" in "Resurrection" are so far ignored. 
#   Don't know to create them as leads or contacts/potentials
#
#################


import os, pdb, csv
from datetime import datetime, timedelta

from mfabrik.zoho.crm import CRM
from mfabrik.zoho.core import ZohoException



def log(m):
	print m

class ThinkfulPerson(object):

	def _parse_name(self, name):
		first_name = name.split(" ")[0]
		if not first_name:
			first_name = None
		last_name = " ".join(name.split(" ")[1:])
		if not last_name:
			last_name = None
		return (first_name, last_name)
	def _parse_date(self, d):
		if not d:
			return None
		(m,d,y) = map(int, d.split('/'))
		return "%s-%02d-%02d" % (y,m,d)
	def _calc_close_date(self, d):
		(y,m,d) = map(int, d.split('-'))
		dt = datetime(year=y, month=m, day=d)
		close_dt = dt + timedelta(weeks=4)
		return close_dt.strftime("%Y-%m-%d")
	def _rm_nones(self, d):
		d2 = {}
		for key, val in d.items():
			if val:
				d2[key] = val
		return d2

	def _parse_note(self, r, f, n):
		if r[n] is None or r[n].strip() == u"":
			return u""
		return u" - %s: %s\n" % (f, r[n].decode('utf-8').encode('ascii', 'ignore'))

	@staticmethod
	def from_applicants_tab(r):
		assert type(r) == list, "Expecting a list. Got %s" % type(r)
		assert len(r) == 14, "Array unexpected length: %s" % len(r)
		#['Name', 'Email Address', 'Signup Date', 'Owner', 'Response 1st Email?', 
		# 'Response 2nd Email? (+7 days)', 'Response 3rd Email? (+14 days)', 
		# 'Price Quoted', 'Price Reaction', 'Status', 'How Found TF?', 
		# 'Lead source', 'Goals', 'Notes']

		tp = ThinkfulPerson()
		tp.email = r[1]
		tp.first_name, tp.last_name = tp._parse_name(r[0])
		tp.signup_date = tp._parse_date(r[2])
		tp.closing_date = tp._calc_close_date(tp.signup_date)
		tp.lead_source = None if r[11].strip() is "" else r[11]
		tp.exact_lead_source = r[10]
		tp.close_date = tp._parse_date(r[2])
		tp.phone = None
		tp.contact_type = "Student"
		tp.contact_owner = None if r[3].strip() is "" else "%s@thinkful.com" % (r[3].lower())

		if r[4] == None or r[4].strip() == "":
			tp.funnel_stage = "Signed up"
			tp.is_lead = True
			tp.is_potential = False
		else:
			tp.funnel_stage = "Expressed interest"
			tp.is_lead = False
			tp.is_potential = True

		tp.notes = ""
		tp.notes += tp._parse_note(r, "Price quoted", 7)
		tp.notes += tp._parse_note(r, "Price reaction", 8)
		tp.notes += tp._parse_note(r, "Status", 9)
		tp.notes += tp._parse_note(r, "Goals", 12)
		tp.notes += tp._parse_note(r, "Other notes", 13)
		if tp.notes:
			tp.note_title = u"All notes from GDoc"
		return tp

	@staticmethod
	def from_students_tab(r, funnel_stage):
		#['Name', 'How they found us', 'Lead source', 'Seeking job?', "What's in their syllabus", 
		# 'Email signup date', 'Close date', 'Price', 'Coach Intro?', 'Billed?', 
		# 'Paid?', 'Start Date', 'Address', 'Email', 'Content, Accounts', 
		# 'Outcome', 'End Date', 'Phone number']

		# Name,How they found us,Lead source,Seeking job?,What's in their syllabus,
		# Email signup date,Close date,Price,Coach Intro?,Billed?,Paid?,Start Date,
		# Address,Email,"Content, Accounts",Outcome,End Date,Phone number


		tp = ThinkfulPerson()
		tp.email = r[13]
		tp.first_name, tp.last_name = tp._parse_name(r[0])
		tp.closing_date = tp._parse_date(r[11])# class start date is deal close date
		tp.funnel_stage = funnel_stage
		tp.lead_source = r[2]
		tp.exact_lead_source = None if r[1].strip() is "" else r[1]
		tp.signup_date = None# this data wasn't maintained here & is elsewhere
		tp.phone = r[17]
		tp.contact_type = "Student"
		tp.contact_owner = None
		tp.is_lead = False
		tp.is_potential = True

		tp.notes = ""
		tp.notes += tp._parse_note(r, "Class end date", 16)
		tp.notes += tp._parse_note(r, "Seeking job?", 3)
		tp.notes += tp._parse_note(r, "Price paid", 7)
		tp.notes += tp._parse_note(r, "Billed", 9)
		tp.notes += tp._parse_note(r, "Paid", 10)
		tp.notes += tp._parse_note(r, "Mailing address", 12)
		tp.notes += tp._parse_note(r, "Outcome", 15)
		tp.notes += tp._parse_note(r, "Content/Accounts", 14)
		tp.notes += tp._parse_note(r, "What's in their syllabus", 4)
		if tp.notes:
			tp.note_title = "All notes from GDoc"
		return tp

	@staticmethod
	def from_citi_tab(r):
		#['Name', 'Email', 'January Followup', 'Current Status', 'Phone', 'City', 
		# 'Linkedin', 'Followup', 'Signup date', "What you're hoping to get out 
		# of it. Ability to commit time. Current position.", 'Decision Sent', 
		# 'How found Thinkful', 'Price Point', '']

		tp = ThinkfulPerson()
		tp.email = r[1]
		tp.first_name, tp.last_name = tp._parse_name(r[0])
		tp.funnel_stage = "Verbal close" if r[2].lower() == 'yes' else "Closed Lost"
		tp.signup_date = tp._parse_date(r[8])
		tp.closing_date = tp._calc_close_date(tp.signup_date)
		tp.phone = r[4]
		tp.contact_type = "Student"
		tp.contact_owner = "dan@thinkful.com"
		tp.lead_source = None if r[11].strip() is not "" else "Press coverage"
		tp.exact_lead_source = r[11] if r[11].strip() is not "" else "Citi Promo (TechCrunch / Hacker News)"
		tp.is_lead = False
		tp.is_potential = True

		tp.notes = ""
		tp.notes += tp._parse_note(r, "City", 5)
		tp.notes += tp._parse_note(r, "LinkedIn", 6)
		tp.notes += tp._parse_note(r, "Last status", 3)
		tp.notes += tp._parse_note(r, "Goals", 9)
		tp.notes += tp._parse_note(r, "Price point", 12)
		if tp.notes:
			tp.note_title = "All notes from GDoc"
		return tp

	@staticmethod
	def from_newsletter_processing_tab(r):
		# ['Name', 'Email Address', 'Funnel Stage?', 
		# 'Date of Most Recent Email?', 'Date of Most Recent Response?', 
		# 'Notes']

		tp = ThinkfulPerson()
		tp.email = r[1]
		tp.first_name, tp.last_name = tp._parse_name(r[0])
		tp.funnel_stage = r[2]
		tp.last_modified = r[3]
		tp.notes = r[5]
		tp.phone = None
		tp.lead_source = None
		tp.signup_date = None
		tp.closing_date = tp._calc_close_date('2013-03-23')
		tp.exact_lead_source = None
		tp.contact_type = "Student"
		tp.contact_owner = "nora@thinkful.com"
		tp.is_lead = False
		tp.is_potential = True

		tp.notes = ""
		tp.notes += tp._parse_note(r, "Other", 5)
		tp.notes += tp._parse_note(r, "Date of Most Recent Email?", 3)
		tp.notes += tp._parse_note(r, "Date of Most Recent Response?", 4)
		if tp.notes:
			tp.note_title = "All notes from GDoc"

		return tp

	def add_as_raw_lead(self):
		assert self.is_lead
		log("Adding lead: %s" % self)
		lead = {
			"Email" : self.email,
			"Last Name" : self.email,
			"Lead Status" : "Signed up",
			"Lead Source" : self.lead_source,
			"Signed up at" : self.signup_date,
		}
		lead = self._rm_nones(lead)
		
		leads = crm.insert_leads([lead])
		self.lead_id = leads[0]['Id']
		return lead

	def add_as_raw_contact(self):
		log("Adding contact: %s" % self)
		contact = {
			"Email" : self.email,
			"Last Name" : self.email,
			"Signed up at" : self.signup_date,
			"Contact Type" : self.contact_type,
			"Contact Owner" : self.contact_owner,
		}
		contact = self._rm_nones(contact)
		contacts = crm.insert_contacts([contact])
		self.potential_id = contacts[0]['Id']
		return contact

	def add_as_raw_potential(self):
		assert self.is_potential
		log("Adding potential: %s" % self)
		potential = {
			"Closing Date": self.closing_date,
			"Potential Name": self.email,
			"Stage": self.funnel_stage,
			"Contact Name": self.email,
			"Lead Source" : self.lead_source,
			"Exact lead source" : self.exact_lead_source,
			"Signed up at" : self.signup_date,
			"Potential Owner" : self.contact_owner,
		}
		potential = self._rm_nones(potential)
		return crm.insert_potentials([potential])

	def add_note(self, entity_id):
		assert self.notes
		note = {
			"entityId" : entity_id,
			"Note Title" : self.note_title,
			"Note Content" : self.notes
		}
		note = self._rm_nones(note)
		return crm.insert_notes([note])

	def update_contact(self):
		log("Updating contact: %s" % self)

		contact = {}
		def e(key, val):
			if val:
				contact[key] = val
		e("Email", self.email)
		e("First Name", self.first_name)
		e("Last Name", self.last_name)
		e("Phone", self.phone)
		crm.insert_contacts([contact])

	def update_lead(self):
		log("Updating lead: %s" % self)

		lead = {}
		def e(key, val):
			if val:
				lead[key] = val
		e("Email", self.email)
		e("First Name", self.first_name)
		e("Last Name", self.last_name)
		e("Phone", self.phone)
		crm.insert_leads([lead])

	def send2zoho(self):
		if self.is_lead:
			self.add_as_raw_lead()
			if self.notes:
				self.add_note(self.lead_id)
			self.update_lead()
		elif self.is_potential:
			self.add_as_raw_contact()
			self.add_as_raw_potential()
			if self.notes:
				self.add_note(self.potential_id)
			self.update_contact()
		else:
			raise Exception("Unknown person type! Neither lead nor potential?")

	def __str__(self):
		return "%s %s (%s)" % (self.first_name, self.last_name, self.email)


def setup():
	# Initialize Zoho CRM API connection
	# You need valid Zoho credentials and API key for this.
	# You get necessary data from Zoho > Setup > Admin > Developer key
	username = os.environ.get("ZOHO_USERNAME", None)
	password = os.environ.get("ZOHO_PASSWORD", None)
	authtoken = os.environ.get("ZOHO_AUTHTOKEN", None)
	crm = CRM(username=username, password=password, authtoken=authtoken, scope="crmapi")
	# Open connection can be used to make as many as possible API calls
	# This will raise ZohoException if credentials are incorrect.
	# Also IOError or URLError will be raised if you the connection to Zoho servers
	# does not work.
	crm.open()
	return crm

def load_tab_file(fn, parse_func, *parse_func_args):
	log("Loading file '%s'" % fn)
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

def load_tabs():
	tf_people = []

	prefix = "/Users/darrell/Downloads/CRM-Live"

	tf_people.append("Applicants!")
	tf_people.extend(
		load_tab_file('%s/Students - Applicants.csv' % (prefix), 
			ThinkfulPerson.from_applicants_tab))
	tf_people.append("Main Site Applicants!")
	tf_people.extend(
		load_tab_file('%s/Students - Main Site Applicants.csv' % (prefix), 
			ThinkfulPerson.from_citi_tab))
	tf_people.append("Citi Applicants!")
	tf_people.extend(
		load_tab_file('%s/Students - Citi Applicants.csv' % (prefix), 
			ThinkfulPerson.from_citi_tab))
	
	#
	# There's some logic to the order (see notes at the top)
	# mostly it's just logically cleaner to think in terms of 
	# getting all data in, then updating it.
	#
	tf_people.append("Students!")
	tf_people.extend(
		load_tab_file('%s/Students - Students.csv' % (prefix), 
			ThinkfulPerson.from_students_tab, 'Current student'))
	tf_people.append("Former Students!")
	tf_people.extend(
		load_tab_file('%s/Students - Former Students.csv' % (prefix), 
			ThinkfulPerson.from_students_tab, 'Former student'))
	tf_people.append("Newsletter Processing!")
	tf_people.extend(
		load_tab_file('%s/Students - Newsletter Processing.csv' % (prefix), 
			ThinkfulPerson.from_newsletter_processing_tab))

	# pdb.set_trace()
	for person in tf_people:
		if type(person) == str:
			log("MIGRATING FROM NEW SOURCE FILE %s" % person)
		else:
			log("Migrating to Zoho: %s" % (person))
			# pdb.set_trace()
			person.send2zoho()

def main():
	global crm
	crm = setup()
	load_tabs()
	crm.close()

if __name__ == '__main__':
	main()
