
#################
#
# A parser and migrator class for Thinkful interfacing w/ Zoho
# The parser is Thinkful specific, but the Zoho stuff is all generic.
#
# Requires the mfabrik.zoho lib
#
# The methods from_tf_* all take lists of Person data
# in the format that Thinkful used in its homegrown, GDocs spreadsheet
# CRMs. They normalize the data into a consistent view of a ThinkfulPerson,
# with fields left as None when their values aren't available.
#
# The methods from_zoho_* parse data from Zoho's API into a 
# consistent ThinkfulPerson object with fields left as None when their 
# values aren't available.
# 
# Note the unexpected use of "add_raw_..." and "update_..." methods. 
# See inline comments.
# 
#################

from datetime import datetime

class ThinkfulPerson(object):

    def _parse_name(self, name):
        if not name:
            return (None, None)
        first_name = name.split(" ")[0]
        if not first_name:
            first_name = None
        last_name = " ".join(name.split(" ")[1:])
        if not last_name:
            last_name = None
        return (first_name, last_name)
    def _parse_date(self, d):
        if not d or d == 'null':
            return None
        if d.count('-') == 2:
            (y,m,d) = map(int, d.split(' ')[0].split('-'))
        elif d.count('/') == 2:
            (m,d,y) = map(int, d.split(' ')[0].split('/'))
        else:
            raise Exception("Cannot parse date '%s'" % d)
        return datetime(year=y, month=m, day=d)
    def _calc_close_date(self, d):
        # Semi-randomly: 4 weeks is our current drip campaign length
        return dt + timedelta(weeks=4)
    def _dt2zoho(self, d):
        return "%s-%02d-%02d" % (d.year, d.month, d.day)
    def _rm_nones(self, d):
        d2 = {}
        for key, val in d.items():
            if val:
                d2[key] = val
        return d2
    def _parse_note(self, r, f, n):
        if r[n] is None or r[n].strip() == u"":
            return u""
        # Zoho doesn't handle unicode :(
        try:
            return u" - %s: %s\n" % (f, r[n].decode('utf-8').encode('ascii', 'ignore'))
        except UnicodeEncodeError:
            print "*** Unicode error parsing note for '%s' N %s" % (f, n)
            return " - %s: UnicodeEncodeError" % (f)

    @staticmethod
    def from_tf_applicants_tab(r):
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
    def from_tf_students_tab(r, funnel_stage):
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
    def from_tf_citi_tab(r):
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
    def from_tf_newsletter_processing_tab(r):
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
        tp.closing_date = tp._calc_close_date(datetime(year=2013, month=3, day=23))
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

    @staticmethod
    def from_tf_prototype_tfcom(r):
        # ['email']

        tp = ThinkfulPerson()
        tp.email = r[0]
        tp.first_name, tp.last_name = (None, None)
        tp.funnel_stage = 'Signed up'
        tp.last_modified = None
        tp.notes = None
        tp.phone = None
        tp.lead_source = "Other"
        tp.exact_lead_source = "prototype site thinkful.com - filtered"
        tp.signup_date = datetime(year=2012, month=10, day=1)
        tp.closing_date = tp._calc_close_date(tp.signup_date)
        tp.contact_type = "Student"
        tp.contact_owner = "dan@thinkful.com"
        tp.is_lead = True
        tp.is_potential = False

    @staticmethod
    def from_zoho_potential(r):
        #{u'Contact Name': u'Michael Simpson', u'CONTACTID': u'783072000000155159', 
        # u'Email': u'mgsimpson1@gmail.com', u'Phone': u'null'}
        def g(k):
            v = r[k]
            if not v or not v.strip() or v.strip() == 'null':
                return None
            return v

        tp = ThinkfulPerson()
        tp.zoho_contact_id = g('CONTACTID')
        tp.zoho_potential_id = g('POTENTIALID')
        tp.email = g('CONTACTID')# TODO

        # this is dumb. I should be able to query for it.
        tp.first_name, tp.last_name = tp._parse_name(g('Contact Name'))
        tp.signup_date = tp._parse_date(g('Signed up at'))
        tp.closing_date = tp._parse_date(g('Closing Date'))
        tp.lead_source = g('Lead Source')
        tp.exact_lead_source = g('Exact lead source')
        tp.funnel_stage = g('Stage')
        # tp.contact_type = "Student"
        # tp.phone = g('Phone')

        return tp

    @staticmethod
    def from_zoho_contact(r):
        # {u'Last Name': u'Miller', u'First Name': u'Mackenzie', 
        # u'CONTACTID': u'783072000000164897', u'Email': u'mmille22@friars.providence.edu'}
        def g(k):
            v = r[k]
            if not v or not v.strip() or v.strip() == 'null':
                return None
            return v.strip()

        tp = ThinkfulPerson()
        tp.zoho_contact_id = g('CONTACTID')
        tp.email = g('Email')
        tp.first_name = g('First Name')
        tp.last_name = g('Last Name')
        tp.contact_type = g('Contact Type')
        # tp.signup_date = tp._parse_date(g('Signed up at') or g('Created Time').split(' ')[0])
        tp.signup_date = tp._parse_date(g('Signed up at'))
        tp.funnel_stage = None
        tp.stripe_customer_id = g('Stripe Customer ID')
        return tp

    @staticmethod
    def from_zoho_lead(r):
        # {u'Last Name': u'sapp.development@gmail.com', u'First Name': u'null', 
        # u'Created Time': u'2013-03-21 23:34:58', u'Email': u'sapp.development@gmail.com', 
        # u'LEADID': u'783072000000110017'}
        def g(k):
            v = r[k]
            if not v or not v.strip() or v.strip() == 'null':
                return None
            return v.strip()
        tp = ThinkfulPerson()
        tp.first_name = g('First Name')
        tp.last_name = g('Last Name')
        tp.email = g('Email')
        tp.contact_type = "Student"
        tp.zoho_lead_id = g('LEADID')
        tp.email_opt_out = g('Email Opt Out') == 'true'
        tp.created_date = tp._parse_date(g('Created Time'))
        tp.signup_date = tp._parse_date(g('Signed up at'))
        tp.funnel_stage = g('Lead Status')
        return tp

    @staticmethod
    def from_cio(r):
        # sample = {u'attributes': {u'_delivered_email:11314547': 1366991323, 
        # u'_opened_email:10545898': 1366308241, u'id': u'ordinaryjoe80@gmail.com', 
        # u'_segment:9334:cache': 0, u'_last_emailed': 1367425173, 
        # u'_segment:8885': 1364312770, u'unsubscribed': True, 
        # u'_delivered_email:9495073': 1365003876, u'email': u'ordinaryjoe80@gmail.com', 
        # u'_segment:11802': 1367375408, u'funnel_stage': u'Expressed interest', 
        # u'_opened_email:8857892': 1364332246, u'_first_seen': 1364312770, 
        # u'_opened_email:9917495': 1365629371, u'_segment:9308': 1364875200, 
        # u'_opened_email:11314547': 1366991404, u'_delivered_email:10545898': 1366303665, 
        # u'contact_type': u'Student', u'created_at': 1364270400, u'_segment:12366': 1367932534, 
        # u'_delivered_email:8857892': 1364327346, u'_delivered_email:11635216': 1367425173, 
        # u'_opened_email:11635216': 1367426066, u'_opened_email:9495073': 1365005012, 
        # u'_delivered_email:9917495': 1365617210}, 
        # u'segments': {u'funnel_stage - On fence / Wants to think it over': None, 
        #   u'contact_type - Student': 1367375408, 
        #   u'Unsubscribed': 1367932534, 
        #   u'At least a week old': 1364875200, 
        #   u'Mentors': None, u'funnel_stage - Call confirmed': None, 
        #   u'funnel_stage - Expressed interest': 1364312770, 
        #   u'funnel_stage - Verbal close': None, 
        #   u'funnel_stage - Signed up': None, u'Missing funnel_stage': None, 
        #   u'Email bounce': None, u'Thinks': None, u'Missing contact_type': None}, 
        # u'id': u'ordinaryjoe80@gmail.com'}
        def g(k):
            v = r[k]
            if not v or not v.strip() or v.strip() == 'null':
                return None
            return v.strip()
        tp = ThinkfulPerson()
        tp.first_name = None
        tp.last_name = None
        tp.email = r['attributes']['email']
        tp.funnel_stage = r['attributes']['funnel_stage']
        tp.is_lead = tp.funnel_stage == "Signed up"
        tp.is_potential = not tp.is_lead
        tp.contact_type = r['attributes']['contact_type']
        tp.email_opt_out = r['attributes']['unsubscribed']
        return tp

    def add_as_raw_lead(self, crm):
        assert self.is_lead
        print "Adding lead: %s" % self
        lead = {
            "Email" : self.email,
            "Last Name" : self.email,
            "Lead Status" : "Signed up",
            "Lead Source" : self.lead_source,
            "Lead Owner" : self.contact_owner,
            "Signed up at" : self._dt2zoho(self.signup_date),
        }
        lead = self._rm_nones(lead)
        
        leads = crm.insert_leads([lead])
        self.lead_id = leads[0]['Id']
        return lead

    def add_as_raw_contact(self, crm):
        print "Adding contact: %s" % self
        contact = {
            "Email" : self.email,
            "Last Name" : self.email,
            "Signed up at" : self._dt2zoho(self.signup_date),
            "Contact Type" : self.contact_type,
            "Contact Owner" : self.contact_owner,
        }
        contact = self._rm_nones(contact)
        contacts = crm.insert_contacts([contact])
        self.potential_id = contacts[0]['Id']
        return contact

    def add_as_raw_potential(self, crm):
        assert self.is_potential
        print "Adding potential: %s" % self
        potential = {
            "Potential Name": self.email,
            "Stage": self.funnel_stage,
            "Contact Name": self.email,
            "Lead Source" : self.lead_source,
            "Exact lead source" : self.exact_lead_source,
            "Closing Date": self._dt2zoho(self.closing_date),
            "Signed up at" : self._dt2zoho(self.signup_date),
            "Potential Owner" : self.contact_owner,
        }
        potential = self._rm_nones(potential)
        return crm.insert_potentials([potential])

    def add_note(self, crm, entity_id):
        assert self.notes
        note = {
            "entityId" : entity_id,
            "Note Title" : self.note_title,
            "Note Content" : self.notes
        }
        note = self._rm_nones(note)
        return crm.insert_notes([note])

    def update_contact(self, crm):
        """Zoho has trouble matching leads / contacts. Splitting them
        into two updates helps when the matching datum (like last name) 
        is changed mid-update."""
        print "Updating contact: %s" % self

        contact = {}
        def e(key, val):
            if val:
                contact[key] = val
        e("Email", self.email)
        e("First Name", self.first_name)
        e("Last Name", self.last_name)
        e("Phone", self.phone)
        crm.insert_contacts([contact])

    def update_lead(self, crm):
        """Zoho has trouble matching leads / contacts. Splitting them
        into two updates helps when the matching datum (like last name) 
        is changed mid-update."""
        print "Updating lead: %s" % self

        lead = {}
        def e(key, val):
            if val:
                lead[key] = val
        e("Email", self.email)
        e("First Name", self.first_name)
        e("Last Name", self.last_name)
        e("Phone", self.phone)
        crm.insert_leads([lead])

    def send2zoho(self, crm):
        if self.is_lead:
            self.add_as_raw_lead(crm)
            if self.notes:
                self.add_note(crm, self.lead_id)
            self.update_lead(crm)
        elif self.is_potential:
            self.add_as_raw_contact(crm)
            self.add_as_raw_potential(crm)
            if self.notes:
                self.add_note(crm, self.potential_id)
            self.update_contact(crm)
        else:
            raise Exception("Unknown person type! Neither lead nor potential?")

    def __eq__(self, o):
        # print self.email, o.email, self.email == o.email
        return self.email == o.email
    def __hash__(self):
        return hash(self.email)

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'ignore')
    def __unicode__(self):
        return u"%s %s (%s) @ %s" % (self.first_name, self.last_name, \
            self.email, self.funnel_stage)
    __repr__ = __str__

class FunnelStage(object):
    """A single funnel stage for a single potential"""

    @staticmethod
    def from_zoho_potential(stages):
        fss = []
        for r in stages:
            fs = FunnelStage()
            fs.stage = r['Stage']
            fs.date = r['Last Modified Time'].split(' ')[0]# TODO
            fss.append(fs)
        return fss

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'ignore')
    def __unicode__(self):
        return u"%s on %s" % (self.stage, self.date)
    __repr__ = __str__


def _stitch_pages(f, *fargs, **fkwargs):
    """Zoho limits the number of records per request to 200. 
    We use this to combine all results behind the scenes into a 
    single result set.

    Note this can hose your API quota if you have a lot of entries.
    """
    records = []
    from_index=1
    to_index=200
    while True:
        print "Calling func %s for page index %s to %s" % (f.func_name, from_index, to_index)
        one_page = f(from_index=from_index, to_index=to_index, *fargs, **fkwargs)
        records.extend(one_page)
        if len(one_page) == 0 or len(one_page) < 200:
            break
        from_index = to_index
        to_index += 200
    return records

def get_zoho_contacts(crm):
    """Returns ALL contacts in the CRM. Note multiple API calls."""
    print "Getting all contacts..."
    tf_people = {}
    for c in _stitch_pages(crm.get_contacts):
        tfp = ThinkfulPerson.from_zoho_contact(c)
        tf_people[tfp.zoho_contact_id] = tfp
    return tf_people

