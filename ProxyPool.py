import requests
import time


from Queue import Queue
from threading import Thread

class ProxyProtocol:
    http = 'http'
    https = 'https'
    ftp = 'ftp'

class ProxyPool(object):
    VERIFY_URL = 'http://icanhazip.com'
    INIT_WAIT_TIME = 3
    
    def __init__(self, IPFiles, pool_size=None, test_buffer_size=20):
        self.files = IPFiles if isinstance(IPFiles, list) else [IPFiles]
        self._untested = Queue(maxsize=test_buffer_size)
        self._proxies = Queue(maxsize=pool_size)
        self.openFile = open(self.files.pop(0), 'r')

        """Init refilling thread"""
        def testAndPut(ip):
            def callback():
                print 'try refil %s' % ip
                if proxyIsValid(ip):
                    self.untested.put(ip)
                return callback
        
        def masterRefillThread():
            print 'THE MASTER LIVES'
            while True:
                if not self._untested.full():
                    newIP = self._readIP()
                    
                    filler = Thread(target=testAndPut(newIP))
                    filler.setDaemon(True)
                    filler.start()
                time.sleep(0.01)

        masterRefiller = Thread(target=masterRefillThread)
        masterRefiller.setDaemon(True)
        masterRefiller.start()

        #time.sleep(self.INIT_WAIT_TIME)

    def __del__(self):
        print '__del__'
        if self.openFile and not self.openFile.closed():
            self.openFile.close()

    @staticmethod
    def isIPv4(ipStr):
        print 'isIPv4'
        try:
            byteArray = map(int, ipStr.split('.'))
            byteTest = [byte for byte in byteArray if byte >= 0 and byte <= 255]
            return len(byteTest) == 4
        except:
            return False

    @classmethod
    def proxyIsValid(cls, ip):
        print 'proxyIsValid'
        proxyDict = {protocol: ip for protocol in ('http', 'https', 'ftp')}
        try:
            r = requests.get(cls.VERIFY_URL, proxies=proxyDict)
            print r.text
            return True
        except requests.HTTPError:
            return False

    def _readIP(self):
        print 'readIP'
        try:
            return self.openFile.readline().rstrip()
        except EOFError:
            self.openFile.close()
            if not self.files:
                raise EOFError("No more IP Files")
            self.openFile = open(self.files.pop(0), 'r')
            return openFile.readline().rstrip()

    def putBack(self, ip, delay=0):
        print 'putBack'
        if self.isIPv4(ip):
            time.sleep(delay)
            self.proxies.put(ip)
        else: 
            raise ValueError("%s not a valid IPv4" % ip)

    def get(self, block=True, timeout=None):
        print 'get'
        return self._proxies.get(block=block, timeout=timeout)


            
        
