
"""
A simple client for Google Calendar's API.

Crucially, this DOES NOT use OAuth, which is frankly way 
simpler to manage, and not necessary for our use since we 
only want to write to our own calendars.
"""


import dateutil, pytz
import atom
import gdata.calendar.data
import gdata.calendar.client
import gdata.acl.data

from datetime import datetime
from tf_utils import env


class SimpleGCal(object):
    """
    Adopted from https://code.google.com/p/gdata-python-client/downloads/list
    as led by https://developers.google.com/google-apps/calendar/v2/developers_guide_python

    Magically, this impl doeesn't require OAuth!
    """

    def __init__(self, email, password):
        self.cal_client = gdata.calendar.client.CalendarClient(source='tf-utils-simple-gcal.1.0')
        self.cal_client.ClientLogin(email, password, self.cal_client.source)

    def _dt2gdt(self, date):
        return date.isoformat('T')
    def _s2dt(self, d):
        dt = dateutil.parser.parse(d)
        if len(d) == 10:
            # only a date; make time zone aware, which it doesn't do for us.
            dt = pytz.UTC.localize(dt)
        return dt

    def get_all_calendars(self):
        feed = self.cal_client.GetAllCalendarsFeed()
        return (feed.title.text, feed.entry)
    
    def get_events(self, start_date, end_date, max_results=100):
        # datetimes *must* be in UTC
        query = gdata.calendar.client.CalendarEventQuery(max_results=max_results,
            start_min=self._dt2gdt(start_date), start_max=self._dt2gdt(end_date))
        feed = self.cal_client.GetCalendarEventFeed(q=query)
        return feed.entry

    def is_available(self, start_date, end_date, all_day_events_are_busy):
        # queries google. Simpler for single availability window.
        events = self.get_events(start_date, end_date)
        if len(events) == 0:
            # no events of any kind: we're available!
            return True
        if all_day_events_are_busy and len(events) > 0:
            # either all day or timed events mean we're not available
            return False

        for event in events:
            for when in event.when:
                if len(when.start) > 10:
                    # timed event in our window! We're busy.
                    return False
        return True

    def is_available_local(self, events, start_date, end_date, all_day_events_are_busy):
        # doesn't query google; better when dealing 
        # with lots of availability windows.
        for event in events:
            for when in event.when:
                if not all_day_events_are_busy and len(when.start) == 10:
                    # this is an all day event, but we ignore those.
                    continue
                if self._s2dt(when.end) <= start_date:
                    # event ended before this one starts
                    continue
                if self._s2dt(when.start) >= end_date:
                    # event starts after this one ends
                    continue
                return False
        return True

    def add_single_event(self, start_date, end_date, title, content=None, 
            allow_dup=True, all_day_events_are_busy=False, invitees=[]):
        if not allow_dup and not self.is_available(start_date, end_date, all_day_events_are_busy):
            return False

        event = gdata.calendar.data.CalendarEventEntry()
        event.send_event_notifications = gdata.calendar.data.SendEventNotificationsProperty(value='true')
        event.title = atom.data.Title(text=title)
        if content:
            event.content = atom.data.Content(text=content)
        event.when.append(gdata.data.When(
            start=self._dt2gdt(start_date), end=self._dt2gdt(end_date)))

        for email in invitees:
            event.who.append(gdata.data.Who(email=email, value=email))

        new_event = self.cal_client.InsertEvent(event)
        return new_event

    def add_reminder(self, event, method, minutes):
        for when in event.when:
            when.reminder.append(gdata.data.Reminder(method=method, minutes=str(minutes)))
        return self.cal_client.Update(event)

    def invite(self, event, emails):
        # Note because event is already created these invitees won't receive 
        # email notifications that they've been invited. But they WILL receive
        # future emails: updates, reminders, cancellations, etc as per the event's 
        # original settings
        for email in emails:
            event.who.append(gdata.data.Who(email=email, value=email))
        return self.cal_client.Update(event)

    def delete_single_event(self, start_date, end_date, title):
        """Note this is not done by ID for convenience to the caller. 
        But we don't allow ambiguity AFAIK."""
        events = self.get_events(start_date, end_date)
        to_delete = []
        for event in events:
            if event.title.text == title:
                to_delete.append(event)

        if not len(to_delete) == 1:
            raise Exception("Ambiguity in what event to delete. Found %s" % len(to_delete))

        # delete it!
        self.cal_client.Delete(to_delete[0].GetEditLink().href, force=True)


def main():
    gc = SimpleGCal(env('GOOGLE_SCHEDULE_CALL_USERNAME'), 
        env('GOOGLE_SCHEDULE_CALL_PASSWORD'))

    def demo_get_all_cals():
        name, cals = gc.get_all_calendars()
        print "Calendars in account '%s'" % name
        for cal in cals:
            print "\t", cal.title.text

    def demo_get_events():
        start_date = datetime(2013,9,23,9)
        end_date = datetime(2013,9,24)
        events = gc.get_events(start_date, end_date)
        print "Events from %s - %s" % (start_date, end_date)
        for i, an_event in zip(xrange(len(events)), events):
            print '\t%s. %s' % (i+1, an_event.title.text,)
            for a_when in an_event.when:
                print '\t\tStart time: %s' % (a_when.start,)
                print '\t\tEnd time:   %s' % (a_when.end,)

    demo_get_all_cals()
    print ""
    demo_get_events()

if __name__ == '__main__':
    main()
