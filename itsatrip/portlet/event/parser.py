# -*- coding: utf-8 -*-
import os
import time
import urllib2
import md5
import tempfile
import tool
import time
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
    
    @property
    def summary(self):
        #TODO:cut to 240 chars
        desc = self.description
        return desc

        
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
            #print 'elmnt name:%s buffer:%s id:%s'%(name, self.buffer.strip(),
            #        self.current.id)
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
        st = time.time()
        self.p.Parse(data)
        et = time.time()
        print et - st



if __name__ == '__main__':
    data = tool.read_data()
    p = Parser()
    p.parse(data)
    print u'Events cout: %s' % len(p.events)
    result = tool.search(p, u'Art, History & Museums')
    for i in result:
        id, name = i.id, i.name.encode('ascii', 'replace')
        print 'id:%s name:%s' % (id, name)
        break
    for i in p.items:
        name, description = (i.name.encode('ascii', 'replace'),
            i.description.encode('ascii', 'replace'))
        print 'id:%s n:%s d:%s t:%s' % (i.id, name, description, i.time)
        break
