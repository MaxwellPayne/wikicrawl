import random
import time
import threading
import re
import requests

from bs4 import BeautifulSoup
from Queue import Queue

class LockedObject(object):

    def __init__(self, obj):
        self.obj = obj
        self.lock = threading.Lock()


class Categorizer(threading.Thread):
    _wikipedia_Root = 'http://wikipedia.org'
    #_wikilink_reg = re.compile(r'(/wiki/[^:]+?$)')
    #_href_wikilink_reg = re.compile(r'\"(/wiki/[^:]+?)\"')
    # /wiki/something_without_a_colon, until a #anchor is seen
    # ASSUMPTION: ALL UNDESIRED WIKILINKS CONTAIN A COLON
    # ASSUMPTION: ALL CITATIONS ex. superscript^[1],
    # do not have /wiki/ in their <a href>'s
    _CRAWL_WAIT_TIME = 1.1
    # I think robots.txt specifies a 1 second minimum
    _category_extension = '/wiki/Category:'
    _category_reg = re.compile('^' + _category_extension + '(.+?)$')

    def __init__(self, page_name, cat_dict, q, group=None, target=None, name=None, args=(), kwargs={}):
       super(Categorizer, self).__init__(group=group, target=target, name=name, args=args, kwargs=kwargs)
       self.page_name = page_name
       self.cat_dict = cat_dict
       self.queue = q
       self.page, self.page_cats = None, None
       self.setPage()

    def setPage(self, page_name=None):
        if page_name: self.page_name = page_name
        page = requests.get(self._wikipedia_Root + self._category_extension + self.page_name)
        self.page = BeautifulSoup(page.text)

        cat_div = self.page.find(id='mw-normal-catlinks')
        #print cat_div

        self.page_cats = cat_div.find_all('a', href=self._category_reg, recursive=True)
        #print self.page_cats
        
        

    def categoryParent(self):
        pass

    def breadthFirstSearch(self):
        seen_cats = {}

        
        
        with self.cat_dict.lock:
            print "%s finished sleeping" % self.page_name
            self.cat_dict.obj[self.page_name] = 'hi'
        
    def run(self):
        pg = self.queue.get()
        for i in range(10):
            requests.get(self._wikipedia_Root)
            print '%s got request number %s' % (pg, i)
        

        self.breadthFirstSearch()
        self.queue.task_done()

def _main():


    ldict = LockedObject(dict())
    q = Queue()

    for pg in ("Academia", "Society", "Research"):
        q.put(pg)

        t = Categorizer(pg, ldict, q)
        t.setDaemon(True)
        t.start()
    q.join()

    print "done now"
    print ldict.obj
    return 0

_main()

