# -*- coding: utf-8 -*-

from zope.interface import implements

from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base

# TODO: If you define any fields for the portlet configuration schema below
# do not forget to uncomment the following import
from zope import schema
from zope.formlib import form

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

# TODO: If you require i18n translation for any of your schema fields below,
# uncomment the following to import your package MessageFactory
from example.portlet.foo import FooPortletMessageFactory as _


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
    url = schema.TextLine(title=_(u'URL of feed'),
                        description=_(u'Link of the feed to display.'),
                        required=True,
                        default=u'http://www.itsatrip.org/api/xmlfeed.ashx')

    timeout = schema.Int(title=_(u'Feed reload timeout'),
                        description=_(u'Time in minutes after which the feed should be reloaded.'),
                        required=True,
                        default=100)

class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """

    implements(IFooPortlet)

    portlet_title = u''
    url=u"http://www.itsatrip.org/api/xmlfeed.ashx"

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
            feed = FEED_DATA[self.data.url] = RSSFeed(self.data.url,self.data.timeout)
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
