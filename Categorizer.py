import random
import time
import threading
import re
import requests
import datetime

from bs4 import BeautifulSoup
from Queue import Queue
from copy import deepcopy

from ProxyPool import ProxyPool
from LockedObjectMixin import LockedObjectMixin


class LockedObject(object):
    def __init__(self, obj, copy=True):
        self.obj = deepcopy(obj) if copy else obj
        self.lock = threading.Lock()
        #self.obj = self._subclassObj(deepcopy(obj) if copy else obj)




class RecursiveSearchThread(threading.Thread):

    #PROXY_POOL = ProxyPool(IPFiles)

    def __init__(self, SearchStruct, seenStructs=set(), name=None, args=(), kwargs={}):
        super(RecursiveSearchThread, self).__init__(group=None, target=None, name=name, args=args, kwargs=kwargs)
        
        self.SearchStruct = SearchStruct
        self.seenStructs = set(seenStructs)

    @classmethod
    def goalAchieved(cls):
        raise NotImplementedError('err')

    @classmethod
    def wait(cls, timeout=0.0):
        start = datetime.datetime.now()
        while not (cls.goalAchieved() or (datetime.datetime.now() - start > datetime.timedelta(seconds=timeout) if timeout else False)):
            time.sleep(0.01)

    def searchForChildren(self):
        """Must return set of SearchStruct objects"""
        raise NotImplementedError('do work')

    def run(self):
        # thread only worthwile if the category has not been reached
        children = set(self.searchForChildren())
        if not self.goalAchieved():
            
            seen = children | self.seenStructs
            for galaxyDog in seen:
                lilMushroom = self.__class__(self.SearchStruct, seen=seen)
                lilMushroom.setDaemon(True)
                lilMushroom.start()
                
            
    


#----------------------------------------------------------------------

def CategorizerFactory(IPFiles, name=None, proxyPool=None, args=(), kwargs={}):

    class Categorizer(RecursiveSearchThread):

        PROXY_POOL = proxyPool if proxyPool else ProxyPool(IPFiles)
        FOUND_CATEGORY = LockedObject(None)
        TOPLEVEL = ['History', 'Science']
        _wikipedia_Root = 'http://wikipedia.org'
        _CRAWL_WAIT_TIME = 1.1
        _REQUEST_TIMEOUT = 4.0
        # I think robots.txt specifies a 1 second minimum
        _category_extension = '/wiki/Category:'
        _category_reg = re.compile('^' + _category_extension + '(.+?)$')

        def __init__(self, page_name, timeout=0.0, name=None, args=(), kwargs={}):
           super(Categorizer, self).__init__(str, name=name, args=args, kwargs=kwargs)
           self.timeout = timeout
           self.page, self.page_name = None, None
           self.setPage(page_name)
           print 'CATEGORIZER INSTANTIATION'

        @classmethod
        def proxyIP(cls):
            return cls.PROXY_POOL.get()

        @classmethod
        def putBack(cls, ip):
            cls.PROXY_POOL.putBack(ip, cls._CRAWL_WAIT_TIME)

        @classmethod
        def categoryFromHref(cls, href):
            print 'HREF %s' % href
            match = cls._category_reg.search(href)
            if match.groups(): return match.groups()[0]
            else: raise ValueError('%s href does not conform to category format' % href)

        @classmethod
        def goalAchieved(cls):
            with cls.FOUND_CATEGORY.lock:
                return bool(cls.FOUND_CATEGORY.obj)

        def category(self):
            if not self.goalAchieved():
                self.start()
                self.wait(self.timeout);

            lockedFound = self.__class__.FOUND_CATEGORY
            with lockedFound.lock:
                if lockedFound.obj: 
                    return lockedFound.obj
            
            raise Exception('category timed out')

        def searchForChildren(self):

            cat_div = self.page.find(id='mw-normal-catlinks')
            pageCatAnchors = cat_div.find_all('a', href=self._category_reg, recursive=True)
            print pageCatAnchors

            parentCats = tuple(self.categoryFromHref(link['href']) for link in pageCatAnchors)

            cls = self.__class__
            for cat in parentCats:
                if cat in cls.TOPLEVEL:
                    with cls.FOUND_CATEGORY.lock:
                        cls.FOUND_CATEGORY.obj = cat
                    break
            
            return parentCats
            

        def setPage(self, page_name=None):
            """Find a page, set it as the page, and set self's cat div to the cat div"""
            if page_name: self.page_name = page_name
            
            for attempt in xrange(100):
                try:
                    proxyIP = self.proxyIP()

                    page = requests.get(self._wikipedia_Root + self._category_extension + self.page_name, proxies={protocol: 'http://' + proxyIP for protocol in ('http', 'https', 'ftp')}, timeout=self.__class__._REQUEST_TIMEOUT)
                    print 'PAGE %s' % page
                    self.page = BeautifulSoup(page.text)
                    # discard the proxy IP for use by another thread
                    self.putBack(proxyIP)
                    break

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    # shitty proxyIP
                    pass
                
    return Categorizer



def _main():

    """A simulation of what a user of this class might do"""
    ldict = LockedObject(dict())
    q = Queue()

    Categorizer = CategorizerFactory('proxylist/full_list/_full_list.txt')

    print Categorizer

    c = Categorizer('Philosophy_of_history')
    #r = RecursiveSearchThread(str)
    #print str(c.page)[:200]
    print 'category is: %s' % str(c.category())
    """
    for pg in ("Academia", "Society", "Research"):
        q.put(pg)

        t = Categorizer(pg, ldict, q)
        t.setDaemon(True)
        t.start()
    q.join()"""

    print "done now"
    print ldict.obj
    print c.category()
    return 0

if __name__ == '__main__':
    _main()
