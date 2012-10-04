# -*- coding: utf-8 -*-
import sys
import os
import time
import urllib2
import md5
import tempfile
import tool
import time
import HTMLParser
from xml.parsers import expat


class Event(object):
    def __init__(self):
        self.id = u''
        self.name = u''
        self.time = u''
        self.phone = u''
        self.website = u''
        self.description = u''
        self.city = u''
        self.address = u''
        self.addlPhones = u''
        self.venueName = u''
        self.admission = u''
        self._html_parser = _StripHTMLParser()
    
    @property
    def summary(self):
        desc = self._html_parser.strip(self.description, 140)
        return desc


class _StripHTMLParser(HTMLParser.HTMLParser):
    def __init__(self):
        self.clear()

    def clear(self):
        self.reset()
        self.close()
        self.lpos = None
        self.limit = 140
        self._count = 0
        self._buffer = u''
        self.starttags = []
        self.endtags = []

    def strip(self, html, limit):
        self.clear()
        self.limit = limit
        self.feed(html)
        #diff = self.limit - self._count
        #text = self._buffer[:diff] + (self._buffer[diff:] and u'...')
        return self._buffer

    def handle_starttag(self, tag, attrs):
        if self._count > self.limit:
            return
        self.starttags.append(tag)
        self._buffer = u''.join([self._buffer, '<'+tag+'>'])

    def handle_endtag(self, tag):
        if len(self.starttags) > 0 and self.starttags[-1:][0] == tag:
            self._buffer = u''.join([self._buffer, '</'+tag+'>'])
            self.starttags.pop()
        self.endtags.append(tag)

    def handle_data(self, data):
        if self._count > self.limit:
            return
        self._count += len(data)
        diff = self.limit - self._count
        if diff < 0:
            self.lpos = self.getpos()
            text = data[:diff]
            lindex = text.rfind(u' ')
            if lindex != -1:
                text = text[:lindex]
            self._buffer = u''.join([self._buffer, text, u'...'])
        else:
            self._buffer = u''.join([self._buffer, data])
        
    def handle_startendtag(self, tag, attr):
        if self._count > self.limit:
            return
        attrs = [a[0]+'="'+a[1]+'"' for a in attr]
        text = '<%s %s/>' %(tag, u' '.join(attrs))
        self._buffer = u''.join([self._buffer, text])


##http://effbot.org/librarybook/xml-parsers-expat.htm
##<name>Concert Screening: Queen-Hungarian Rhapsody</name>
##<eventTime>8pm</eventTime><admission>$13</admission>
##<phone>505-768-3522</phone>
##<website>http://www.cabq.gov/kimo</website>
##<shortDesc>Calling all Queen fans&hellip;Now&rsquo;s your chance to watch Queen&rsquo;s momentous concert movie, Hungarian Rhapsody: Queen Live In Budapest &rsquo;86 on the big screen for the first time. Remastered in high definition and 5.1 surround sound, this cinema event opens with a special 25 minute documentary feature following the legends of rock, Queen, from just after their show&ndash;stealing performance at Live Aid through the year leading up to the concert in Budapest. Staged for 80,000 ecstatic fans, the concert set includes favorite hits like Bohemian Rhapsody, Crazy Little Thing Called Love, I Want To Break Free and We Are The Champions. It&rsquo;s a fantastic opportunity to celebrate the magic of Queen at the KiMo. This Film is not rated and may be inappropriate for children.<br />
##Run time is 1 hour 55 minutes. Concessions will be available.</shortDesc>
##<city>Albuquerque</city>
##<address>423 Central NW</address>
##<addlPhones/>
##<venueName>KiMo Theatre</venueName>        
##interestName
class Parser:
    def __init__(self):
        self.events = {}
        self.items = []
        self.tags = {}
        self.current = None
        self.cnode = None
        self.isEventSection = False
        self.isTagSection = False
        self.buffer = u''
        self.p = expat.ParserCreate()
        self.p.buffer_text = True
        self.buffer_size = 256
        self.p.StartElementHandler = self.start_element
        self.p.EndElementHandler = self.end_element
        self.p.CharacterDataHandler = self.char_data
        
    def start_element(self, name, attr):
        self.cnode = name
        if name == u'Event':
            self.isEventSection = True
            self.current = Event()
        if name == u'EventInterestArea':
            self.isTagSection = True
        
    def end_element(self, name):
        self.cnode = None
        if name == u'Event':
            self.isEventSection = False
            self.current = None
        elif name == u'EventInterestArea':
            self.isTagSection = False
        elif name == u'interestName':
            tag = self.buffer.strip()            
            if not self.tags.has_key(tag):
                self.tags[tag] = [self.current]
            else:
                l = self.tags[tag]
                l.append(self.current)
        self._end_element_event(name)
        self.buffer = u''
    
    def _end_element_event(self, name):
        if self.isEventSection and self.current != None:
            if name == u'shortDesc':
                self.current.description = self.buffer.strip()
            elif hasattr(self.current, name):
                setattr(self.current, name, self.buffer.strip())

    def char_data(self, data):
        if self.cnode == None:
            return
        self.buffer = u''.join((self.buffer, data))
        if self.isTagSection:
            self._char_data_tag(data)
        elif self.isEventSection and self.current != None:            
            self._char_data_event(data)

    def _char_data_event(self, data):
        if self.cnode == u'eventID':
            self.current.id = data
            self.events[self.current.id] = self.current
            self.items.append(self.current)
        elif self.cnode == u'eventTime':            
            self.current.time = data

    def _char_data_tag(self, data):
        if self.cnode == u'eventID':
            self.current = self.events[data]

    def parse(self, data):
        self.p.Parse(data)


if __name__ == '__main__':
##    p = _StripHTMLParser()
##    result = p.strip(u"""<div>
##<img src="http://example.com/img.jpg"/>
##<h1>ORC</h1>
##<br />
##<span>0123456789</span><span>ABCDEFGHIJ</span></div>""", 10)
##    print result
##    sys.exit(0)

    data = tool.read_data('http://www.itsatrip.org/api/xmlfeed.ashx')
    p = Parser()
    p.parse(data)
    print u'Events count: %s' % len(p.events)
    #result = tool.search(p, [u'Art, History & Museums'])
    result = tool.free_events(p.items)
    print 'len(result):%s' % len(result)
    i = 0
    for item in result:
        id, name = item.id, item.name.encode('ascii', 'replace')
        print 'id:%s name:%s' % (id, name)
        desc = item.description.encode('ascii', 'replace')
        summary = item.summary.encode('ascii', 'replace')
        print 'description(%s):%s' % (len(desc), desc)
        print 'summary(%s):%s' % (len(summary), summary)
        i += 1
        if i > 0:
            break
##    for i in p.items:
##        name, description = (i.name.encode('ascii', 'replace'),
##            i.description.encode('ascii', 'replace'))
##        print 'id:%s n:%s d:%s t:%s' % (i.id, name, description, i.time)
##        break
