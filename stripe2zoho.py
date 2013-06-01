

"""
Sync data between Stripe & Zoho
"""


import pdb, pickle
from tf_utils import get_crm, get_stripe

from beautiful_soupcon_tf_zoho import ThinkfulPerson, _stitch_pages
from optparse import OptionParser

def stitch_pages_stripe(f, *args, **kwargs):
    records = dict(data=[], object=list, url=None, count=None)
    offset = 0
    while True:
        print "Calling stripe func %s %s for offset %s" \
            % (f.im_self, f.func_name, offset)
        one_page = f(*args, count=100, offset=offset, **kwargs)
        records['data'].extend(one_page['data'])
        if not records['count']:
            records['count'] = one_page['count']
        if not records['url']:
            records['url'] = one_page['url']
        if len(records['data']) >= records['count']:
            break
        offset += 100
    return records

def send_stripe_ids_to_zoho_contacts(zoho, stripe):
    """
    all stripe customers are contacts in Zoho
    all zoho CC on file & students are in stripe
    Zoho contacts have stripe IDs
    """
    # TODO this should be in javascript

    print "Getting Customers from Stripe..."
    customers = []
    for customer in stitch_pages_stripe(stripe.Customer.all)['data']:
        customers.append(customer)

    print "Getting contacts from Zoho..."
    contacts = {}
    contacts_by_stripe_id = {}
    if zoho.use_api_allowance:
        for contact in _stitch_pages(zoho.search_contacts, "(Contact Type|=|Student)"):
            tfp = ThinkfulPerson.from_zoho_contact(contact)
            contacts[tfp.email.lower()] = tfp
            if tfp.stripe_customer_id:
                contacts_by_stripe_id[tfp.stripe_customer_id] = tfp
        contacts_fh = open('contacts.pickle', 'w')
        pickle.dump(contacts, contacts_fh)
        contacts_fh.close()
    else:
        contacts_fh = open('contacts.pickle', 'r')
        contacts = pickle.load(contacts_fh)
        contacts_fh.close()

    for customer in customers:
        if not contacts.has_key(customer.email.lower()):
            if contacts_by_stripe_id.has_key(customer.id):
                print "For %s: Mapped to Stripe customer ID '%s' even though in Stripe the email address is '%s'. Assuming this is on purpose." \
                    % (contacts_by_stripe_id[customer.id], customer.id, customer.email)
            else:
                print "ERROR: Email %s in Stripe not in Zoho! Stripe Customer ID is '%s'" \
                    % (customer.email.lower(), customer.id)
            continue

        contact = contacts[customer.email.lower()]
        if contact.stripe_customer_id == None:
            print "For %s: Adding Stripe Customer ID '%s'" \
                % (contact, customer.id)
            # this could be done in bulk, but easier to debug / check /
            # report / error handle when done individually.
            zoho.update_contacts([{
                "Id" : contact.zoho_contact_id,
                "Stripe Customer ID": customer.id,
            }])
        elif contact.stripe_customer_id == customer.id:
            print "For %s: Stripe Customer ID is correctly set to '%s'" \
                % (contact, customer.id)
        else:
            print "ERROR For %s: Mismatch! Zoho has Stripe Customer ID '%s', Stripe says '%s'" \
                % (contact, contact.stripe_customer_id, customer.id)


def main():
    parser = OptionParser("%prog")
    parser.add_option("--use_api_allowance", action="store_true")
    (options, args) = parser.parse_args()
    
    crm = get_crm()
    crm.open()
    crm.use_api_allowance = options.use_api_allowance

    stripe = get_stripe()
    send_stripe_ids_to_zoho_contacts(crm, stripe)


if __name__ == '__main__':
    main()
