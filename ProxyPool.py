import requests
import time


from Queue import Queue

class ProxyProtocol:
    http = 'http'
    https = 'https'
    ftp = 'ftp'

class ProxyPool(object):
    VERIFY_URL = 'http://icanhazip.com'
    
    def __init__(self, IPFiles, pool_size=None, test_buffer_size=20):
        self.files = IPFiles if isinstance(IPFiles, list) else [IPFiles]
        self.untested = Queue(maxsize=buffer_size)
        self.proxies = Queue(maxsize=pool_size)

    @staticmethod
    def isIPv4(ipStr):
        try:
            byteArray = map(int, ipStr.split('.'))
            byteTest = [byte for byte in byteArray if byte >= 0 and byte <= 255]
            return len(byteTest) == 4
        except:
            return False

    @classmethod
    def proxyIsValid(cls, ip):
        proxyDict = {protocol: ip for protocol in ('http', 'https', 'ftp')}
        try:
            r = requests.get(cls.VERIFY_URL, proxies=proxyDict)
            print r.text
            return True
        except requests.HTTPError:
            return False

    def putBack(self, ip, delay=0):
        if self.isIPv4(ip):
            time.sleep(delay)
            self.proxies.put(ip)
        else: 
            raise ValueError("%s not a valid IPv4" % ip)

        

            
        
