import requests
import time
import os
import socket
import Queue

from Queue import Queue
from threading import Thread, Lock, Event

testct=0

class ProxyIP(dict):
    http = 'http'
    https = 'https'
    ftp = 'ftp'

    def __init__(self, ip):
        super(ProxyIP, self).__init__()
        self[self.http] = ip
        self[self.https] = ip
        self[self.ftp] = ip


class ProxyPool(object):
    VERIFY_URL = 'http://icanhazip.com'
    INIT_WAIT_TIME = 3
    
    def __init__(self, IPFiles, pool_size=1000, test_buffer_size=20):
        self._files = IPFiles if isinstance(IPFiles, list) else [IPFiles]
        self._untested = Queue(maxsize=test_buffer_size)
        self._proxies = Queue(maxsize=pool_size)
        self._openFile = open(self._files.pop(0), 'r')
        #self._fileLock = Lock()
        self._locks = {'_openFile': Lock()}

        self._filesToEat = Event()
        self._filesToEat.set()
        self._timeToExit = Event()

        """Init refilling thread"""
        def testAndPut(ip):
            global testct
            testct += 1
            def callback():
                #print 'try refil %s' % ip
                if self.proxyIsValid(ip):
                    self._proxies.put(ip)
                    #self._untested.put(ip)
            return callback
        
        def masterRefillThread():
            print 'THE MASTER LIVES'
            while not self._timeToExit.isSet():
                if not self._proxies.full() and not self._openFile.closed:
                    try:
                        newIP = self._readIP()
                        #print 'newIP in master is %s' % newIP
                        filler = Thread(target=testAndPut(newIP))
                        filler.setDaemon(True)
                        filler.start()
                    except EOFError:
                        pass
                time.sleep(0.01)

        self._masterRefiller = Thread(target=masterRefillThread)
        self._masterRefiller.setDaemon(True)
        self._masterRefiller.start()

        #time.sleep(self.INIT_WAIT_TIME)

    def __del__(self):
        print '__del__'
        self._timeToExit.set()
        if self._openFile and not self.openFile.closed():
            self._openFile.close()

    def _put(self, ip):
        try:
            self._proxies.put(ip, block=False)
        except Queue.Full:
            pass

    def addFile(fname):
        self._files.append(fname)
        self._filesToEat.set()

    @staticmethod
    def isIPv4(ipStr):
        print 'isIPv4'
        try:
            byteArray = map(int, ipStr.split(':')[0].split('.'))
            byteTest = [byte for byte in byteArray if byte >= 0 and byte <= 255]
            return len(byteTest) == 4
        except:
            return False

    @classmethod
    def proxyIsValid(cls, ip):
        #print 'proxyIsValid'
        proxyDict = {protocol: 'http://' + ip for protocol in ('http', 'https', 'ftp')}
        try:
            r = requests.get(cls.VERIFY_URL, proxies=proxyDict)
            print ('is valid %s? %s' % (ip, r.text.rstrip() == ip.split(':')[0]))
            return r.text.rstrip() == ip.split(':')[0]
        except (requests.HTTPError, requests.ConnectionError, socket.error) as e:
            return False

    def _readIP(self):
        #print 'readIP'
        if self._filesToEat.isSet():
            self._locks['_openFile'].acquire()
            try:
                #print 'file closed? %s' % self._openFile.closed
                ip = self._openFile.readline().rstrip()
                if not ip: raise EOFError('')
                return ip
            except EOFError:
                self._openFile.close()
                if not self._files:
                    print "NO more files"
                    self._filesToEat.clear()
                    raise EOFError("All proxy files consumed")
                else:
                    self._openFile = open(self._files.pop(0), 'r')
                    return self._openFile.readline().rstrip()
            except Exception as e:
                print '_readIP was programmed poorly bc error %s' % e
                exit(1)
            finally:
                self._locks['_openFile'].release()
            

    def putBack(self, ip, delay=0):
        print 'putBack'
        def target():
            if self.isIPv4(ip):
                time.sleep(delay)
                self._proxies.put(ip)
            else: 
                raise ValueError("%s not a valid IPv4" % ip)

        thread = Thread(target=target)
        thread.setDaemon(True)
        thread.start()

    def get(self, block=True, timeout=None):
        print 'get'
        return self._proxies.get(block=block, timeout=timeout)

def _main():
    import random
    x = ProxyPool(os.path.join('proxylist', 'full_list', '_full_list.txt'))
    print x
    for i in range(1000):
        gotten =  x.get()
        print 'got %s' % gotten
        time.sleep(random.randint(1, 5))
        x.putBack(gotten)

    print testct
            
#_main()
