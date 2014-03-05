import requests, bs4, re, random
import getopt, os, sys, collections, csv
from time import sleep


"""

To do:
Beware the 404 in WikiCrawl.navigate
WikiCrawl.nextWikiLink needs to deal with a page that has no good links
WikiCrawl.crawl needs to handle hash collisions/infinite loops of links
CSV Directory handling is shit
Handle NUM_TRIALS better

STRIP /WIKI/REAL_PAGE#ANCHOR_PART from urls

"""



def chunk(fPath, size=65536):
	"""Stream the contents of a file size at a time"""
	if size > 65536:
		raise ValueError('Too big a chunk size')

	with open(fPath, 'r') as f:

		while True:
			b = f.read(size)
			if not b: break
			else: yield b

def chooseRandLn(fPath):
	"""Choose to read a line at random from a text file"""

	numLines = sum([ch.count('\n') for ch in chunk(fPath)])
	# count newlines in the file

	#print "filelen should be %s" % numLines

	chosenLine = random.randint(0, numLines - 1)

	with open(fPath, 'r') as f:

		for _ in xrange(chosenLine):
			# consume a random number of lines
			f.readline()

		# return the chosen line
		return f.readline()

def randWikiStart(titleFilePath):
	"""Reads random line from titleFilePath, converts what it finds to valid
	wikipedia URL"""
	import urllib

	wikiWord = chooseRandLn(titleFilePath).rstrip('\n').replace(' ', '_')
	# choose random line, strip newline, replace spaces with underscore

	print 'wikiword %s' % wikiWord

	return unicode('http://wikipedia.org/wiki/') + urllib.quote(wikiWord.encode('UTF-8'))
	# return a unicode, url-safe url

def csvHeadersExist(pth, headerLs, delimiter=','):

	with open(pth, 'r') as f:
		return f.readline().rstrip().split(delimiter) == headerLs

class CrawlError(Exception):
	"""Wikipedia crawler has encountered a page that doesn't hold a valid link to any other Wikipedia page"""

	def __init__(self, message):

		Exception.__init__(self)
		self.message = message


class CrawlRecord(object):
	"""Records data about the crawl of a given wikipedia page"""

	def __init__(self, url, word, nth):
		self.urlExtension = url
		self.word = word
		self.nth = nth

	def __repr__(self):
		return 'CrawlRecord URL: %s, word %s, nth %s' % (self.urlExtension, self.word, self.nth)

	def listForCSV(self):
		"""Create list of properties the way they will be written to the CSV columns"""
		# hash value of self.word will produce unique primary key
		return [hash(self.urlExtension), self.word, self.url]


class WikiCrawl(object):

	_wikilink_reg = re.compile(r'(/wiki/[^:#]+)')
	# /wiki/something_without_a_colon, until a #anchor is seen
	# ASSUMPTION: ALL UNDESIRED WIKILINKS CONTAIN A COLON
	_CRAWL_WAIT_TIME = 1.5
	# I think robots.txt specifies a 1 second minimum

	
	def __init__(self, startURL):

		self.startURL = startURL
		self.currentURL = startURL

		self._visitedURLs = collections.OrderedDict()
		# Myabe OrderedDict so you can see previous and next
		# Key is /wiki/stuff, val is corresponding CrawlRecord
		self.currentPage = None
		self._nthSeen = 0
		# tracks how many pages crawler has crawled

		self._infRecord = None
		# temporary holding cell for the infinity record if there is one



	def navigate(self, navURL):
		"""Change the 'current page' and 'current URL' of self to page served by navURL"""

		page = requests.get(navURL)
		# BEWARE THE 404
		# make request
		self.currentURL = navURL

		self.currentPage = bs4.BeautifulSoup(page.text)
		# soupify request text

	def stripWikiURL(self, wikiURL):
		"""Given part or whole wikiURL, returns the /wiki/... portion.
		Raises exception if wikiURL does not match pattern"""

		#print 'stripping wiki url %s' % wikiURL

		#print 'findall %s' % str(WikiCrawl._wikilink_reg.findall(wikiURL, re.I))

		stripped = WikiCrawl._wikilink_reg.search(wikiURL)

		#print 'stripped search %s' % str(stripped)

		#print 'stripped %s' % str(stripped.groups())

		if stripped: return stripped.groups()[0]
		else: raise CrawlError("URL doesn't match /wiki/... pattern")

	def URLifyWikiExtension(self, urlExtension):
		"""Return urlExtension as a valid http://... wikipedia URL"""

		return unicode('http://wikipedia.org' + self.stripWikiURL(urlExtension))


	def wikiTitle(self, bs4Page):
		"""Given a bs4 wiki webpage, return the wiki title of the page"""

		header = bs4Page.find("h1", id="firstHeading")

		return header.string

	
	def nextWikiLink(self, page):
		"""Navigate to (wikipedia 'url'), parse page down to first 'wiki/some_page' <a> tag, 
		return the matched <a> element's link to the next wikipedia page"""

		# Should I alter parser to ignore 'Taxonomy (from ANCIENT GREEK...) start of article' situations?


		paragraphs = page.find("div", id="mw-content-text").findAll("p", recursive=False)

		# find first <p> within body
		# ASSUMPTION: FIRST <p> WILL COINTAIN WHAT I WANT

		for para in paragraphs:

			matched = para.find("a", recursive=False, href=WikiCrawl._wikilink_reg)

			if matched:
				break
		else:
			raise CrawlError("No valid wikilinks exist on current page")

		# find first <a> within paragraph whose href matched the reg pattern

		return matched.get("href")

	def crawl(self, numRuns):
		"""Crawl wikipedia numRuns times, store results as CrawlRecords in self._visitedURLs"""

		# NEED TO HANDLE NOMATCH EXCEPTION, INFINITE LOOP EXCEPTION, DEADEND EXCEPTION

		for _ in xrange(numRuns):
		# run numruns times

			self.navigate(self.currentURL)
			# navigate changes currentURL to result of navigating last currentURL

			currentURLStripped = self.stripWikiURL(self.currentURL)


			nextLink = self.nextWikiLink(self.currentPage)
			# grab the next link from the current page

			record = CrawlRecord(self.stripWikiURL(self.currentURL), 
									self.wikiTitle(self.currentPage),
									self._nthSeen)
			# create a record using the url just searched, title currently seen, and n



			try: 
				# if hashkey exists, we're in an infinite crawl loop
				self._visitedURLs[currentURLStripped]

				self._infRecord = record
				break
				# raise CrawlError('Key already visited, infinite loop')

			except KeyError:
				# url extension not visited yet, continue crawling


				self._visitedURLs[currentURLStripped] = record
				# insert this location into the hash

				self.currentURL = self.URLifyWikiExtension(nextLink)
				# set the next-current url to the result of this page

				self._nthSeen += 1
				# increment number of pages seen

				sleep(WikiCrawl._CRAWL_WAIT_TIME)
				# sleep to abide by robots.txt
			



	def _csvPath(self, fileName = None, directory = ''):

		if fileName: return fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: return self._visitedURLs[self.stripWikiURL(self.startURL)].word + '.csv'



	def verboseCSV(self, fileName = None, directory = '', delim = ','):
		"""Writes the path of all word seen on a traversal"""

		pth = self._csvPath(fileName, directory)
		
		visited = self._visitedURLs.values()

		row = [hash(visited[0])] + map(lambda record: record.word, self._visitedURLs.values())
		# Array starting with hashval of first word
		# followed by every single word seen

		if self._infRecord: row = row.append(self._infRecord)
		# append the inf record to words seen if it has been encountered

		with open(pth, 'a') as f:
			excelWriter = csv.writer(f, delimiter = delim)
			excelWriter.writeRow(row)


	def summaryCSV(self, fileName = None, directory = '', delim = ','):
		"""Writes startWord hash, startWord, last unique word, numSeen, and infWord if exists"""

		pth = self._csvPath(fileName, directory)

		headers = ['URL ID', 'Start Word', 'End Word', 'Number of Jumps', 'Loop Word']

		visited = self._visitedURLs.values()

		first, last = visited[0], visited[len(visited) - 1]
		# first word seen and last word seen
		infSeen = self._infRecord if self._infRecord else 'None'

		row = [hash(first), first, last, self._nthSeen, infSeen]

		with open(pth, 'a') as f:
			excelWriter = csv.writer(f, delimiter = delim)
			if os.path.getsize(pth) == 0:
				excelWriter.writeRow(headers)
			excelWriter.writeRow(row)


	def writeCSV(self, fileName=None, directory=''):
		import csv
		"""DEPRECATED"""

		assert False


		headers = ['URL ID', 'Word', 'URL']
		# csv column headers

		if fileName: name = fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: name = self._visitedURLs[self.stripWikiURL(self.startURL)].word + '.csv'

		# FIX FILENAME/DIRECTORY SHIT
		
		with open(name, 'wb+') as f:
			excelWriter = csv.writer(f, delimiter = '|')
			excelWriter.writerow(headers)


			# for k, v in sorted(self._visitedURLs.iteritems(), key=lambda kObj: kObj[1].nth):
				# iterator will look like ('wiki/something', <Crawl Record>), (... , ...)
				# sorts by nth attribute of the CrawlRecord

			for k, v in self._visitedURLs.iteritems():

				excelWriter.writerow(v.listForCSV())

			if self._infRecord:
				# if an infinite loop encountered, write it as last line
				excelWriter.writerow(self._infRecord.listForCSV())

		print 'Written %s' % name

		return self._visitedURLs
		# does this really need a return value?

	def flush(self):
		"""Return all properties to pre-crawl status"""
		self.currentURL = self.startURL
		self._visitedURLs = collections.OrderedDict()
		self.currentPage = None
		self._nthSeen = 0
		self._infRecord = None



def _run(argv):


	def usage():
		print "Usage: wikipedia jumper"
		print "\t-excel_path Excel File Path"
		print "\t--help"

	CSV_DIRECTORY, CSV_NAME = '', None
	INPUT_URL, NUM_TRIALS = None, 0
	# NUM_TRIALS is a magic number right now


	try:
		opts, args = getopt.getopt(argv, 'hn:', ['help', 'csv-directory=', 'csv-name='])
		# maybe add an output directory for experiment results
	except getopt.GetoptError:
		usage()
		exit(2)

	if len(args) == 1:
		INPUT_URL = args[0]

	elif len(args) > 1:
		print "Unrecognized command line argument"
		usage()
		exit(2)

	optDict = dict(opts)

	if '-n' not in optDict.keys():
		print 'no -n arg'
		usage()
		exit(2)
	else:
		NUM_TRIALS = int(optDict['-n'])
		# handle invalid argument (bad number)

	

	if '-h' in optDict.keys() or '--help' in optDict.keys():
		usage()
		exit(0)

	if '--csv-directory' in optDict.keys():
		CSV_DIRECTORY = optDict['--csv-directory']
	if '--csv-name' in optDict.keys():
		CSV_NAME = optDict['--csv-name']


	# do I really need to mkdir?
	try:
		os.mkdir('Trials_Results')
	except:
		# directory already exists
		OSError

	if INPUT_URL: crawler = WikiCrawl(INPUT_URL)
	else: crawler = WikiCrawl(randWikiStart('enwiki-latest-all-titles-in-ns0'))

	crawler.crawl(NUM_TRIALS)

	os.chdir('Trials_Results')

	crawler.writeCSV(fileName = CSV_NAME, directory=CSV_DIRECTORY)





_run(sys.argv[1:])

