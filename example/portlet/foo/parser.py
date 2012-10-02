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
            self.current = Event()
        if name == u'EventInterestArea':
            self.isTagSection = True
        
    def end_element(self, name):
        self.cnode = None
        if name == u'Event':
            self.current = None
        elif name == u'EventInterestArea':
            self.isTagSection = False
        elif name == u'interestName':
            ##TODO:are coma separated?
            ##str.split(data)
            ##Theater, Dance, Film & Performing Arts
            tag = self.buffer.strip()            
            if not self.tags.has_key(tag):
                self.tags[tag] = [self.current]
            else:
                l = self.tags[tag]
                l.append(self.current)
        self.buffer = ''

    def char_data(self, data):
        if self.cnode == None:
            return
        if self.isTagSection:
            self.buffer = u''.join((self.buffer, data))
            self._char_data_tag(data)
            return
        ## if is not a interest area check if there is a current event
        ## if there is one we are still reading the events
        if self.current != None:            
            self._char_data_event(data)
            
    def _char_data_event(self, data):
        if self.cnode == u'eventID':
            self.current.id = data
            self.events[self.current.id] = self.current
            self.items.append(self.current)
        elif self.cnode == u'eventTime':
            ce = self.events[self.current.id]
            ce.time = data
        elif hasattr(self.current, self.cnode):
            setattr(self.current, self.cnode, data)
                
    def _char_data_tag(self, data):
        if self.cnode == u'eventID':
            self.current = self.events[data]
        if self.cnode == u'interestName':
            pass
            
    def parse(self, data):
        st = time.time()
        self.p.Parse(data)
        et = time.time()
        print et - st



if __name__ == '__main__':
    data = tool.read_data()
    p = Parser()
    p.parse(data)
    print 'Events cout: %s' % len(p.events)
    ##e = p.events[u'9665']
    ##print u'Event %s %s' % (e.time, '.')
