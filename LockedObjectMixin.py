from threading import Lock

class LockedObjectMixin(object):

    def __init__(self):
        self.lock = Lock()

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.lock.release()




def _main():
    class Subcl(dict, LockedObjectMixin):
        
        def __init__(self):
            dict.__init__(self)
            LockedObjectMixin.__init__(self)


    x = Subcl()
    with x as unlocked:
        x['hi'] = 2

    with x as unlocked:
        x['bye'] = 4

    print x

if __name__ == '__main__':
    _main()
