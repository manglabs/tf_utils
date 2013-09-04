
import os, json, pdb
from customerio import CustomerIO
from mfabrik.zoho.crm import CRM


class CustomerIOAwesome(CustomerIO):
    """Extend their API to include undocumented calls used by their webapp"""
    # TODO want to fork their lib, but it doesn't deploy to heroku for 
    # some reason, so punting.

    def _stitch_pages(self, f, *fargs, **fkwargs):
        """CustomerIO limits the number of records per request to 100. 
        We use this to combine all results behind the scenes into a 
        single result set.
        """
        records = {'customers':[]}
        page=1
        per_page=10
        while True:
            print "Calling func %s for page %s per_page %s" % (f.func_name, page, per_page)
            one_page = f(*fargs, page=page, per_page=per_page, **fkwargs)
            records['customers'].extend(one_page['customers'])
            if len(one_page) == 0 or len(one_page['customers']) < per_page:
                break
            page += 1
        return records

    def get_segment(self, segment_ids, page=1, per_page=100):
        # TODO hack the mapping of segment name -> ID
        # https://manage.customer.io/api/v1/customers?page=1&per=10&segments=[[12366]]
        self._orig_host = self.host
        self.host = "manage.customer.io"
        query_string = "%(url_prefix)s/customers?page=%(page)s&per=%(per_page)s&segments=[%(segment_ids)s]" % (
            dict(url_prefix=self.url_prefix, page=page, per_page=per_page, segment_ids=segment_ids))
        response = self.send_request("GET", query_string, {})
        self.host = self._orig_host
        return json.loads(response)

    def get_customer(self, customer_id):
        # https://manage.customer.io/api/v1/customers/0.63214180967@thinkful.com
        self._orig_host = self.host
        self.host = "manage.customer.io"
        query_string = "%s/customers/%s" % (self.url_prefix, customer_id)
        response = self.send_request("GET", query_string, {})
        self.host = self._orig_host
        return json.loads(response)

    def get_customers(self, page=1, per_page=100):
        # https://manage.customer.io/api/v1/customers?page=2&per=10
        self._orig_host = self.host
        self.host = "manage.customer.io"
        query_string = "%(url_prefix)s/customers?page=%(page)s&%(per_page)s" % (
            dict(url_prefix=self.url_prefix, page=page, per_page=per_page))
        response = self.send_request("GET", query_string, {})
        self.host = self._orig_host
        return json.loads(response)

    def get_sent_emails(self, customer_id, page=1, per_page=100):
        # https://manage.customer.io/api/v1/sent_emails?customer_id=wildfeuer05%40gmail.com&page=1&per=10
        self._orig_host = self.host
        self.host = "manage.customer.io"
        query_string = "%(url_prefix)s/sent_emails?customer_id=%(customer_id)s&page=%(page)s&per=%(per_page)s" % (
            dict(url_prefix=self.url_prefix, customer_id=customer_id, page=page, per_page=per_page))
        response = self.send_request("GET", query_string, {})
        self.host = self._orig_host
        return json.loads(response)


def env(name, default=None, required=True):
    value = os.environ.get(name, default)
    if required and not value:
        raise Exception("Missing required environment var '%s'" % name)
    return value

def get_crm():
    """Connection to Zoho"""
    return CRM(username=env("ZOHO_USERNAME"), password=env("ZOHO_PASSWORD"), 
        authtoken=env("ZOHO_AUTHTOKEN"), scope="crmapi")

class crm_connection():
    """
    Usage:
    with crm_connection as crm():
        do_things()
    """
    def __enter__(self):
        self.crm = get_crm()
        self.crm.open()
        return self.crm

    def __exit__(self, type, value, traceback):
        self.crm.close()

def get_cio():
    """Connection to customer.io"""
    return CustomerIOAwesome(env("CIO_SITE_ID"), env("CIO_API_KEY"))

def get_stripe():
    """Setup connection to stripe. 
    It's annoying there's no object... that it's just the lib
    """
    import stripe
    stripe.api_key = env('STRIPE_SECRET_KEY')
    return stripe


def get_all_customers():
    customers = []
    cio = get_cio()
    # customers = cio._stitch_pages(cio.get_customers)
    base_dir = '/Users/darrell/projects/thinkful/src/environment/fixtures/cio'
    fn = '%s/cio.customers.20130901.json' % base_dir
    fh = open(fn)
    raw = fh.readlines()
    fh.close()
    customers = json.loads(raw[0])
    print "loaded %s customers from '%s'" % (len(customers['customers']), fn)
    
    for customer in customers['customers']:
        id = customer['id']
        id = id.replace(' ', '%20')
        fn = '%s/sent_emails/%s' % (base_dir, id)
        if os.path.exists(fn):
            print "Not resaving '%s'" % fn
        else:
            print "Saving sent emails to %s" % fn
            raw = cio.get_sent_emails(id)
            fh = open(fn, 'w')
            fh.write(json.dumps(raw))
            fh.close()

        # pdb.set_trace()

