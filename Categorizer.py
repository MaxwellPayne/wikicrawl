import random
import time
import threading
import re
import requests

from bs4 import BeautifulSoup
from Queue import Queue
from copy import deepcopy

from ProxyPool import ProxyPool

class LockedObject(object):
    def __init__(self, obj, copy=True):
        self.obj = deepcopy(obj) if copy else obj
        self.lock = threading.Lock()
        #self.obj = self._subclassObj(deepcopy(obj) if copy else obj)
    """def __getattr__(self, name):
        if name == 'obj':
            return deepcopy(self._obj)
        else:
            raise AttributeError("LockedObject can only access 'obj' property")
    def __setattr__(self, name, value):
            if name == 'obj':
                with self._lock:
                    self._obj = value"""



class RecursiveSearchThread(threading.Thread):

    #PROXY_POOL = ProxyPool(IPFiles)

    def __init__(self, SearchStruct, name=None, args=(), kwargs={}):
       super(ExponentialThread, self).__init__(group=None, target=None, name=name, args=args, kwargs=kwargs)
       """for prop, val in kwargs:
           if hasattr(self, prop):
               raise ValueError('self already has prop')
           else:
               setattr(self, prop, val)"""
               
        #self._kwargProps = tuple(p for p in kwargs.keys())
        self.SearchStruct = SearchStruct
        #self.childSeeds = tuple()

    @classmethod
    def goalAchieved(cls):
        raise NotImplementedError('err')

    def searchForChildren(self):
        """Must return list of SearchStruct objects"""
        raise NotImplementedError('do work')

    def run(self):
        # thread only worthwile if the category has not been reached
        if not self.goalAchieved():

            #for childData in self.childSeeds:
            for galaxyDog in self.searchForChildren():
                # VALIDATE galaxyDog keys == self._kwargProps
                #lilMushroom = self.__class__(kwargs={prop: getattr(self, prop) for prop in self._kwargProps})
                lilMushroom = self.__class__(self.SearchStruct)
                lilMushroom.setDaemon(True)
                lilMushroom.start()
                
            
    


#----------------------------------------------------------------------

def Categorizer(IPFiles, SearchStruct, page_name, seenStructs=(), name=None, args=(), kwargs={}):

    class Categorizer(RecursiveSearchThread):

        PROXY_POOL = ProxyPool(IPFiles)
        FOUND_CATEGORY = LockedObject(None)
        TOPLEVEL = ['History', 'Science']

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

        def __init__(self, SearchStruct, name=None, args=(), kwargs={}):
            data = {'seen': kwargs['seen'], 'page_name': kwargs['page_name']}
           super(Categorizer, self).__init__(name=name, args=args, kwargs=kwargs)
           #self.proxyIP = self.__class__.PROXY_POOL.get()
           #self.cat_dict = cat_dict
           #self.queue = q
           self.SearchStruct = SearchStruct
           self.page = None
           self.setPage()

        @classmethod
        def proxyIP(cls):
            return cls.PROXY_POOL.get()

        @classmethod
        def putBack(cls, ip):
            cls.PROXY_POOL.putBack(ip, cls.CRAWL_WAIT_TIME)

        @classmethod
        def categoryFromHref(cls, href):
            match = cls._category_reg.search(href)
            if match.groups(): return match.groups()[0]
            else: raise ValueError('%s href does not conform to category format' % href)

        @classmethod
        def goalAchieved(cls):
            with cls.FOUND_CATEGORY.lock:
                return bool(cls.FOUND_CATEGORY.obj)

        def searchForChildren(self):

            cat_div = self.page.find(id='mw-normal-catlinks')
            pageCatAnchors = cat_div.find_all('a', href=self._category_reg, recursive=True)
            print pageCats

            #PARENT CATS NEED TO BE SMART ABOUT TESTING TO SEE IF SEEN AND CHECKING FOR SUCCESS
            parentCats = tuple(self.categoryFromHref(link.href) for link in pageCatAnchors)
            
            return parentCats
            

        def setPage(self, page_name=None):
            """Find a page, set it as the page, and set self's cat div to the cat div"""
            proxyIP = self.proxyIP()
            if page_name: self.page_name = page_name

            page = requests.get(self._wikipedia_Root + self._category_extension + self.page_name, proxy={protocol: proxyIP for protocol in ('http', 'https', 'ftp')})
            self.page = BeautifulSoup(page.text)

            # discard the proxy IP for use by another thread
            self.putBack(proxyIP)

"""
        def run(self):
            #Main worker function of the Categorizer. Coordinates the many threads that will ascend the category tree to hit a top-level category.
            # thread only worthwile if the category has not been reached
            if not self.__class__.FOUND.isSet():


                parent_cats = self.categoryParents()
                
                for cat in parent_cats:
                    if cat in TOPLEVEL:
                        # found toplevel,set it and get out of town
                        self.__class__.FOUND.set()
                        with self.__class__.FOUND_CATEGORY.lock:
                            self.__class__.FOUND_CATEGORY.obj = cat
                            break
                    elif cat not in self.seen:
                        # spawn a child, somewhat recursively b/c of loop
                        child = Categorizer(cat, self.seen + (cat,))
                        child.setDaemon(True)
                        child.start()
                
            
                #with self.cat_dict.lock:
                #    print "%s finished sleeping" % self.page_name
                #    self.cat_dict.obj[self.page_name] = 'hi'

        """

    return Categorizer(SearchStruct, page_name, seen=seen, group=group, target=target, name=name, args=args, kwargs=kwargs)

def _main():

    """A simulation of what a user of this class might do"""
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

#_main()

