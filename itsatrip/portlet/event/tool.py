# -*- coding: utf-8 -*-
import os
import time
import urllib2
import md5
import tempfile
import time


def read_data(url=None, force=False):
    data = None
    assert url != None, "url not given"
    hash = md5.new(url)
    tmpf = tempfile.gettempdir()
    tmpf = os.path.join(tmpf, 'itsatrip_data')
    if not os.path.exists(tmpf):
        os.makedirs(tmpf)
    tmpf = os.path.join(tmpf, hash.hexdigest())
    if not force and os.path.exists(tmpf):
        file = open(tmpf, 'rt')
        data = file.read()
        file.close()
    else:
        try:
            file = urllib2.urlopen(url)
            data = file.read()
            try:
                try:
                    sfile = open(tmpf, 'wt')
                    sfile.write(data)
                    sfile.close()            
                finally:
                    if sfile: sfile.close()
            except:
                pass
        finally:
            if file: file.close()
    return data


def search(parser, tags):
    tageventdic = parser.tagevent
    items = parser.items
    result = []
    for tag in tags:
        if tageventdic.has_key(tag):
            result += ([i for i in items if i in tageventdic[tag]])
    return result


def free_events(items):
    """Filter items by free admission"""
    result = ([i for i in items if i.admission.lower() == 'free'])
    return result

