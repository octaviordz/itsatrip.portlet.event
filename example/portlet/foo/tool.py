import os
import time
import urllib2
import md5
import tempfile


def read_data(url=None, force=False):
    data = None
    if url == None:
        url = 'http://www.itsatrip.org/api/xmlfeed.ashx'
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
        file = urllib2.urlopen(url)
        data = file.read()
        sfile = open(tmpf, 'wt')
        sfile.write(data)
        sfile.close()
        file.close()
    return data


def search(parser, tag):
    tags = parser.tags
    result = None
    if tags.has_key(tag):
        result = tags[tag]
    return result
