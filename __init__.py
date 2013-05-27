
import os, json
from customerio import CustomerIO
from mfabrik.zoho.crm import CRM


class CustomerIOAwesome(CustomerIO):
    """Extend their API to include undocumented calls used by their webapp"""
    # TODO want to fork their lib, but it doesn't deploy to heroku for 
    # some reason, so punting.

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

def env(name, default=None, required=True):
    value = os.environ.get(name, default)
    if required and not value:
        raise Exception("Missing required environment var '%s'" % name)
    return value

def get_crm():
    """Connection to Zoho"""
    return CRM(username=env("ZOHO_USERNAME"), password=env("ZOHO_PASSWORD"), 
        authtoken=env("ZOHO_AUTHTOKEN"), scope="crmapi")

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
