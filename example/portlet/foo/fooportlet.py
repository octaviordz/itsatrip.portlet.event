# -*- coding: utf-8 -*-
from zope import schema
from zope.formlib import form
from zope.interface import implements, Interface

from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from DateTime import DateTime
import parser
import tool
import time


# TODO: If you require i18n translation for any of your schema fields below,
# uncomment the following to import your package MessageFactory
from example.portlet.foo import FooPortletMessageFactory as _

# store the feeds here (which means in RAM)
FEED_DATA = {}  # url: is the key

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
        self._items_by_type = {}
        self._items = []
        self._title = ""
        self._siteurl = ""
        self._loaded = False    # is the feed loaded
        self._failed = False    # does it fail at the last update?
        self._last_update_time_in_minutes = 0 # when was the feed last updated?
        self._last_update_time = None            # time as DateTime or Nonw

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
                data = tool.read_data(url)
            except:
                self._loaded = True # we tried at least but have a failed load
                self._failed = True
                return False
            
            self._parser = parser.Parser()
            self._parser.parse(data)
            ##TODO: Title?
            self._title = u''
            self._siteurl = u'http://www.itsatrip.org/events/default.aspx'
            self._items = []
            lformat = self._siteurl + u'?eventid=%s'
            for item in self._parser.items:
                try:
                    link = lformat % item.id
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
                except AttributeError:
                    continue
                self._items.append(itemdict)
            self._loaded = True
            self._failed = False
            return True
        self._loaded = True
        self._failed = True # no url set means failed
        return False # no url set, although that actually should not really happen

    def items_by_type(self, event_types):
        if not self._parser or not event_types or len(event_types) <= 0:
            return []
        result = self._items_by_type.get(event_types, None)        
        if not result:
            result = []
            tags = event_types.split(';')
            tags = [t.strip() for t in tags if len(t.strip())>0]
            items = tool.search(self._parser, tags)
            lformat = self._siteurl + u'?eventid=%s'
            print 'items_by_type %s len:%s' % (event_types, len(items))
            for item in items:
                try:
                    link = lformat % item.id
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
                except AttributeError:
                    continue
                result.append(itemdict)
            self._items_by_type[event_types] = result
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



class IFooPortlet(IPortletDataProvider):
    """A portlet

    It inherits from IPortletDataProvider because for this portlet, the
    data that is being rendered and the portlet assignment itself are the
    same.
    """

    # TODO: Add any zope.schema fields here to capture portlet configuration
    # information. Alternatively, if there are no settings, leave this as an
    # empty interface - see also notes around the add form and edit form
    # below.

    portlet_title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Title of the portlet.'),
        required=False,
        default=u''
        )

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
    event_types = schema.TextLine(title=_(u'Event Types'),
                        description=_(u'Event types to display.'),
                        required=False,
                        default=u'')

class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """

    implements(IFooPortlet)

    portlet_title = u''
    url = u"http://www.itsatrip.org/api/xmlfeed.ashx"
    event_types = u''

    def __init__(self, portlet_title=u'', count=5,
            url=u'http://www.itsatrip.org/api/xmlfeed.ashx',
            timeout=100):
        self.portlet_title = portlet_title
        self.count = count
        self.url = url
        self.timeout = timeout
        
        
    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen.
        """
        return "Events from itsatrip"


class Renderer(base.DeferredRenderer):
    """Portlet renderer.

    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """
    
    render_full = ViewPageTemplateFile('fooportlet.pt')
    
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
        if self.data.event_types and len(self.data.event_types) > 0:
            items = self._getFeed().items_by_type(self.data.event_types)
            return items[:self.data.count]
        return self._getFeed().items[:self.data.count]

    @property
    def enabled(self):
        return self._getFeed().ok


class AddForm(base.AddForm):
    """Portlet add form.

    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """
    form_fields = form.Fields(IFooPortlet)

    def create(self, data):
        return Assignment(**data)


# NOTE: If this portlet does not have any configurable parameters, you
# can remove the EditForm class definition and delete the editview
# attribute from the <plone:portlet /> registration in configure.zcml


class EditForm(base.EditForm):
    """Portlet edit form.

    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """
    form_fields = form.Fields(IFooPortlet)
