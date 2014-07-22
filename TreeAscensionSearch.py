import cPickle

from Queue import Queue

import Categorizer

from LockedObjectMixin import LockedObjectMixin

def LockedDictFactory(pickleTo=None, unpickleFrom=None):

    class LockedDict(dict, LockedObjectMixin):

        def __init__(self, pickleTo=None):
            dict.__init__(self)
            LockedObjectMixin.__init__(self)
            self.pickleTo = pickleTo if pickleTo else None

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

        def serialize(self, pickleTo=None):
            pth = pickleTo or self.pickleTo
            if not pth: raise cPickle.PickleError("Object never given a picklePath")
            with open(pth, 'wb') as f:
                cPickle.dump(self, f)


    if unpickleFrom:
        with open(unpickleFrom, 'rb') as f:
            obj = cPickle.load(f)
        return obj
    else:
        return LockedDict(pickleTo=pickleTo)




class TreeAscensionSearch(object):

    def __init__(self):
        self._searchQueue = Queue()



def _main():
    pth = 'pickled-category-cache'

    d = LockedDictFactory(pickleTo=pth)


    

    with d as unlocked:
        unlocked['hi'] = 2

    d.serialize()

    d2 = LockedDictFactory(unpickleFrom=pth)
    print d2

if __name__ == '__main__':
    _main()
