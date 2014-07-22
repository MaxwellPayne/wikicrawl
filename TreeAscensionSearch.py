import cPickle

from Queue import Queue
from threading import Lock

import Categorizer

from LockedObjectMixin import LockedObjectMixin


class LockedDict(dict, LockedObjectMixin):

    def __init__(self):
        dict.__init__(self)
        LockedObjectMixin.__init__(self)

    """Subclass of dict that prevents existing keys from being overwritten, unless expcility done via the overwrite() method"""
    def set(self, key, value):
        if key in self:
            raise KeyError("Key %s already mapped to %s, cannot alter existing relationship by setting directly" % (key, value))
        dict.__setitem__(self, key, value)

    def __setitem__(self, key, value):
        self.set(key, value)

    def overwrite(self, key, value):
        if key not in self:
            raise KeyError("Cannot overwrite %s because it is not currently a key" % key)
        dict.__setitem__(self, key, value)





class TreeAscensionSearch(object):

    def __init__(self, unpickleDictFrom=None, pickleDictTo=None):
        if unpickleDictFrom:
            with open(unpickleDictFrom, 'rb') as f:
                self.cache = cPickle.load(f)
                self.cache.lock = Lock()
        else:
            self.cache = LockedDict()
        self.pickleDictTo = pickleDictTo
        self._searchQueue = Queue()

        

    def __del__(self):
        if self.pickleDictTo:
            cache, lock = self.cache, self.cache.lock
            self.cache.lock = None
            with open(self.pickleDictTo, 'wb') as f:
                cPickle.dump(self.cache, f)
            self.cache.lock = lock


def _main():
    pth = 'pickled-category-cache'

    t = TreeAscensionSearch(pickleDictTo=pth)

    with t.cache as c:
        t.cache['hi'] = 1

    del t

    t2 = TreeAscensionSearch(unpickleDictFrom=pth)

    with t2.cache as c:
        print c

if __name__ == '__main__':
    _main()
