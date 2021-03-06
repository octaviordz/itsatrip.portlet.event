# -*- coding: utf-8 -*-
from zope import schema
from zope.formlib import form
from zope.interface import implements, Interface

from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary
from Acquisition import aq_base
from zope.app.form.browser.itemswidgets import OrderedMultiSelectWidget

from DateTime import DateTime
import parser
import tool
import time
import urllib2
import threading
import Queue

from itsatrip.portlet.event import EventPortletMessageFactory as _


# store the feeds here (which means in RAM)
FEED_DATA = {}  # url: is the key
_FEED_QUEUE = Queue.Queue()

def async_feed_update(itsatripfeed):
    rfeed = None
    if not _FEED_QUEUE.empty():
        rfeed = _FEED_QUEUE.get(False)
    if rfeed:
        fd = FEED_DATA.get(rfeed.url, None)
        if not fd and not FEED_DATA.get(rfeed.url, None):
            FEED_DATA[rfeed.url] = rfeed
        if rfeed.url == itsatripfeed.url:
            print 'Work for url previously done.%s'%itsatripfeed.url
            return
    def _work(feed):
        if not feed.ok:
            print 'async_feed_update...'
            feed.update()
            print 'async_feed_updated...'
            _FEED_QUEUE.put(feed, False)
    t = threading.Thread(target=_work, args=(itsatripfeed,))
    t.start()

#@zope.interface.implementer(IContextSourceBinder)
class _EventTypeVocabulary(object):
    implements(IContextSourceBinder)
    def __call__(self, context):
        """Available Event Types vocabulary"""
        event_types = []
        terms = []    
        if hasattr(context, u'url'):
            feed = FEED_DATA.get(context.url, None)
            if not feed:
                afeed = ItsatripFeed(context.url, context.timeout)
                async_feed_update(afeed)
            elif feed and feed.ok:
                print 'using event_types(tags) from feed'
                event_types = sorted(feed.tags)
        if not event_types:
            print 'using default event_types(tags)'
            event_types = (u'Art, History & Museums',
                    u'Cultural & Heritage',
                    u'Expositions & Conventions',
                    u'Family & Kids',
                    u'Festivals, Fairs & Parades',
                    u'Food & Wine',
                    u'Holiday & Seasonal',
                    u'Home & Garden',
                    u'Music & Concerts',
                    u'Nature & Outdoors',
                    u'Other',
                    u'Sports',
                    u'Theater, Dance, Film & Performing Arts',
                    u'Tours, Lectures & Presentations',
                    )
            event_types = sorted(event_types)
        #return SimpleVocabulary.fromValues(event_types)
        for et in event_types:
            svoc = SimpleVocabulary.createTerm(et, str(et), et)
            terms.append(svoc)
        return _FixSimpleVocabulary(terms)

EventTypeVocabulary = _EventTypeVocabulary()

class _FixSimpleVocabulary(SimpleVocabulary):
    def getTerm(self, value):
        result = None
        try:
            result = super(_FixSimpleVocabulary, self).getTerm(value)
        except Exception, ex:
            name = value+u'[x]'
            result = SimpleVocabulary.createTerm(name, str(name), name)
        return result
            

class IFeed(Interface):

    def __init__(url, timeout):
        """initialize the feed with the given url. will not automatically load it
           timeout defines the time between updates in minutes
        """

    def loaded():
        """return if this feed is in a loaded state"""

    def title():
        """return the title of the feed"""

    def items():
        """return the items of the feed"""

    def feed_link():
        """return the url of this feed in feed:// format"""

    def site_url():
        """return the URL of the site"""

    def last_update_time_in_minutes():
        """return the time this feed was last updated in minutes since epoch"""

    def last_update_time():
        """return the time the feed was last updated as DateTime object"""

    def needs_update():
        """return if this feed needs to be updated"""

    def update():
        """update this feed. will automatically check failure state etc.
           returns True or False whether it succeeded or not
        """

    def update_failed():
        """return if the last update failed or not"""

    def ok():
        """is this feed ok to display?"""


class ItsatripFeed(object):
    """an feed reader for http://www.itsatrip.org/api/xmlfeed.ashx structure"""
    implements(IFeed)

    # TODO: discuss whether we want an increasing update time here, probably not though
    FAILURE_DELAY = 10  # time in minutes after which we retry to load it after a failure

    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        self._parser = None
        self._items_view = {}
        self._items = []
        self._title = ""        
        self._siteurl = u'http://www.itsatrip.org/events/default.aspx'
        self._loaded = False    # is the feed loaded
        self._failed = False    # does it fail at the last update?
        self._last_update_time_in_minutes = 0 # when was the feed last updated?
        self._last_update_time = None            # time as DateTime or Nonw

    @property
    def tags(self):
        return self._parser.tags
    
    @property
    def last_update_time_in_minutes(self):
        """return the time the last update was done in minutes"""
        return self._last_update_time_in_minutes

    @property
    def last_update_time(self):
        """return the time the last update was done in minutes"""
        return self._last_update_time

    @property
    def update_failed(self):
        return self._failed

    @property
    def ok(self):
        return (not self._failed and self._loaded)

    @property
    def loaded(self):
        """return whether this feed is loaded or not"""
        return self._loaded

    @property
    def needs_update(self):
        """check if this feed needs updating"""
        now = time.time()/60
        return (self.last_update_time_in_minutes+self.timeout) < now

    def update(self):
        """update this feed"""
        now = time.time()/60    # time in minutes

        # check for failure and retry
        if self.update_failed:
            if (self.last_update_time_in_minutes+self.FAILURE_DELAY) < now:
                return self._retrieveFeed()
            else:
                return False

        # check for regular update
        if self.needs_update:
            return self._retrieveFeed()

        return self.ok

    def _retrieveFeed(self):
        """do the actual work and try to retrieve the feed"""
        url = self.url
        if url!='':
            self._last_update_time_in_minutes = time.time()/60
            self._last_update_time = DateTime()
            try:
                data = tool.read_data(url, force=True)
            except urllib2.URLError, ex:
                try:
                    data = tool.read_data(url)
                except:
                    # we tried at least but have a failed load
                    self._loaded = True 
                    self._failed = True
                    return False
            self._parser = parser.Parser()
            self._parser.parse(data)
            self._title = u'Events'
            self._items = self._model2view(self._parser.items)
            self._loaded = True
            self._failed = False
            return True
        self._loaded = True
        self._failed = True # no url set means failed
        return False # no url set, although that actually should not really happen

    def query_items(self, event_types, free_events):
        assert self._parser, 'Calling before parse'
        if not event_types and not free_events:
            return self._items
        elif free_events and not event_types:
            return self._model2view(tool.free_events(self._parser.items))
        stypes = u';'.join([et for et in event_types])
        vkey = u' '.join([stypes, str(free_events)])        
        print 'vkey %s' % vkey.encode('ascii', 'replace')
        result = self._items_view.get(vkey, None)
        if not result:
            items = tool.search(self._parser, event_types)
            if free_events:
                items = tool.free_events(items)
            result = self._model2view(items)
            self._items_view[vkey] = result
        return result
    
    def _fill_itemdict(self, item):
        link = self._siteurl + u'?eventid=%s' % item.id
        itemdict = {
            'title' : item.name,
            'url' : link,
            'summary' : item.summary,
            'venueName':item.venueName,
            'address' : item.address,
            'city' : item.city,
            'time' : item.time,
            'phone' : item.phone,
            'addlPhones' : item.addlPhones,
            'website' : item.website
        }
        if hasattr(item, "updated"):
            itemdict['updated']=DateTime(item.updated)
        return itemdict
    
    def _model2view(self, items):
        result = []
        for item in items:
            try:
                itemdict = self._fill_itemdict(item)
            except AttributeError:
                continue
            result.append(itemdict)
        return result

    @property
    def items(self):
        return self._items

    # convenience methods for displaying
    #

    @property
    def feed_link(self):
        """return rss url of feed for portlet"""
        return self.url.replace("http://","feed://")

    @property
    def title(self):
        """return title of feed for portlet"""
        return self._title

    @property
    def siteurl(self):
        """return the link to the site the RSS feed points to"""
        return self._siteurl
    

class IEventPortlet(IPortletDataProvider):
    """A portlet

    It inherits from IPortletDataProvider because for this portlet, the
    data that is being rendered and the portlet assignment itself are the
    same.
    """
    portlet_title = schema.TextLine(
            title=_(u'Title'),
            description=_(u'Title of the portlet.'),
            required=False,
            default=u'')
    count = schema.Int(title=_(u'Number of items to display'),
           description=_(u'How many items to list.'),
           required=True,
           default=5)
    url = schema.TextLine(title=_(u'Dataset url'),
            description=_(u'Link of the Dataset to display.'),
            required=True,
            default=u'http://www.itsatrip.org/api/xmlfeed.ashx')
    timeout = schema.Int(title=_(u'Feed reload timeout'),
            description=_(u'Time in minutes after which the feed should be reloaded.'),
            required=True,
            default=100)
    event_types_filter = schema.Set(title=u'Event Types',
            description=_(u'Only display the events of selected types.'),
            value_type=schema.Choice(vocabulary=
                    'itsatrip.portlet.event.EventTypeVocabulary'),
            required=False,)
    free_events = schema.Bool(title=_(u'Free events'),
            description=_(u'Display only free events.'),
            required=False,
            default=False)

class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """
    implements(IEventPortlet)
    portlet_title = u''    

    def __init__(self, portlet_title=u'', count=5,
            url=u'http://www.itsatrip.org/api/xmlfeed.ashx',
            timeout=100, free_events=False,
            event_types_filter=None):
        self.portlet_title = portlet_title
        self.count = count
        self.url = url
        self.timeout = timeout
        self.free_events = free_events
        self.event_types_filter = event_types_filter
        
    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen.
        """
        return "Events from itsatrip.org"


class Renderer(base.DeferredRenderer):
    """Portlet renderer.

    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """
    render_full = ViewPageTemplateFile('eventportlet.pt')
    
    @property
    def initializing(self):
        """should return True if deferred template should be displayed"""
        feed=self._getFeed()
        if not feed.loaded:
            return True
        if feed.needs_update:
            return True
        return False

    def deferred_update(self):
        """refresh data for serving via KSS"""
        feed = self._getFeed()
        feed.update()

    def update(self):
        """update data before rendering. We can not wait for KSS since users
        may not be using KSS."""
        self.deferred_update()

    def _getFeed(self):
        """return a feed object but do not update it"""
        feed = FEED_DATA.get(self.data.url,None)
        if feed is None:
            # create it
            print 'Creating FEED_DATA[%s]'%self.data.url
            feed = FEED_DATA[self.data.url] = ItsatripFeed(self.data.url,
                    self.data.timeout)
        return feed

    @property
    def url(self):
        """return url of feed for portlet"""
        return self._getFeed().url

    @property
    def siteurl(self):
        """return url of site for portlet"""
        return self._getFeed().siteurl

    @property
    def feedlink(self):
        """return rss url of feed for portlet"""
        return self.data.url.replace("http://","feed://")

    @property
    def title(self):
        """return title of feed for portlet"""
        return getattr(self.data, 'portlet_title', '') or self._getFeed().title

    @property
    def feedAvailable(self):
        """checks if the feed data is available"""
        return self._getFeed().ok

    @property    
    def items(self):
        items = []
        if self.data.event_types_filter:
            items = self._getFeed().query_items(self.data.event_types_filter,
                self.data.free_events)
        elif self.data.free_events:
            items = self._getFeed().query_items(None, self.data.free_events)
        else:
            items = self._getFeed().items
        return items[:self.data.count]

    @property
    def enabled(self):
        return self._getFeed().ok


class AddForm(base.AddForm):
    """Portlet add form.

    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """
    form_fields = form.Fields(IEventPortlet)
    #form_fields['event_types_filter'].custom_widget = MultiSelectWidget
    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):
    """Portlet edit form.

    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """
    form_fields = form.Fields(IEventPortlet)
    #form_fields['event_types_filter'].custom_widget = MultiSelectWidget

##https://mail.zope.org/pipermail/zope3-users/2009-April/008513.html
##http://pypi.python.org/pypi/collective.orderedmultiselectwidget
class _SecureOrderedMultiSelectWidget(OrderedMultiSelectWidget):
    """ This class fixes an acquisition bug in
        zope.app.form.browser.itemswidgets.py line 556.

        itemswidgets.py has since been moved to zope.formlib, which is zope.ap, 
        zope2 and Acquisition agnostic, so I don't see how this fix (which uses
        'aq_base') can be contributed there since Acquisition (and aq_base)
        isn't a dependency of zope.formlib.

        Description of the bug:
        -----------------------
        The 'get' method on the 'speakers' List fields is called, which tries
        to see if there is a 'speakers' attribute on the add or edit view.
        In the case of (for example) slc.seminarportal, we have a folder named 
        'speakers' which is then sometimes erroneously returned 
        (because of Acquisition) which then causes chaos.
    """

    def selected(self):        
        """Return a list of tuples (text, value) that are selected."""
        # Get form values
        values = self._getFormValue()        
        # Not all content objects must necessarily support the attributes
        # XXX: Line below contains the bugfix. (aq_base)
        if hasattr(aq_base(self.context.context), self.context.__name__):
            # merge in values from content 
            for value in self.context.get(self.context.context):
                if value not in values:
                    values.append(value)
        terms = [self.vocabulary.getTerm(value)
                 for value in values]
        return [{'text': self.textForValue(term), 'value': term.token}
                for term in terms]

def MultiSelectWidget(field, request):
    vocabulary = field.value_type.vocabulary
    widget = _SecureOrderedMultiSelectWidget(field, vocabulary, request)
    return widget
