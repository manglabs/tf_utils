from google_spreadsheet.api import SpreadsheetAPI
from register.views import match_email_to_contact, collect_error
from splash.views import CONTACT_OWNER
from tf_utils import crm_connection, env

"""
def update_spreadsheet(row, un, pw, src, key):
	api = SpreadsheetAPI(un, pw, src)
	sheet = api.get_worksheet(key, 'od6')
	row['sumissiontime'] = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
	sheet.insert_row(row)
"""

PYTHON_SPREADSHEET_KEY = '0Ao-rA1kr2miTdExMdzRpbV9fenR2WXphZjFsbkZ1VUE'

def add_python_potential_to_contact(contact, crm):
	date = '07-09-2013'  # day before next class
	potential = {
		"Potential Name": applicant.email,
		"Stage": 'Signed up',
		"Contact Name": applicant.email,
		"Lead Source": leads[0],
		"Exact lead source": leads[1],
		"Signed up at": date,
		"RelCntId": contact['CONTACTID'],
		"Potential Owner": CONTACT_OWNER,
		"Closing Date": date,
		"Discount code": "PYT500"
	}

	potential = crm.insert_potentials([potential])[0]
	note = {
		'entityId': potential['Id'],
		'Note Title': 'Lead source',
		'Note Content': "Signed up for the Python class beta directly through us."
	}
	crm.insert_notes([note])

def process_python_students():
	errors = []
	api = SpreadsheetAPI(env('GOOGLE_APPS_USERNAME'), env('GOOGLE_APPS_PASSWORD'), 'thinkful.com')
	sheet = api.get_worksheet(PYTHON_SPREADSHEET_KEY, 'od6')
	emails = map(lambda row: row['email'], sheet.get_rows())
	with crm_connection() as crm:
		for email in emails:
			with collect_error(errors):
				contact = match_email_to_contact(row['email'], crm)
				add_python_potential_to_contact(contact, email)
	print '<%s>' % '<\n>'.join(errors)

if __name__ == '__main__':
	process_python_students()