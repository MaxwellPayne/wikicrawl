#!/usr/bin/env python

import requests, bs4, re, random, itertools
import getopt, os, sys, collections, csv
from time import sleep
from itertools import count


"""

To do:
Beware the 404 in WikiCrawl.navigate
Crawler needs to deal with a page that has no good links
CSV Directory handling is shit
Handle NUM_TRIALS better

:/ Handle disambiguation case

:) WikiCrawl.crawl needs to handle hash collisions/infinite loops of links
:) STRIP /WIKI/REAL_PAGE#ANCHOR_PART from urls

"""

"""Main self.URLify-ing should come from linkFinderFunc"""





def csvHeadersExist(pth, headerLs, delimiter=','):
	"""Checks to see if a csv file has headers in its first row"""

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
		self.urlExtension = unicode(url)
		self.word = word
		self.nth = nth

	def __repr__(self):
		return 'CrawlRecord URL: %s, word %s, nth %s' % (self.urlExtension, self.word, self.nth)

	def listForCSV(self):
		"""Create list of properties the way they will be written to the CSV columns"""
		# hash value of self.word will produce unique primary key
		return [hash(self.urlExtension), self.word, self.urlExtension]


class WikiCrawl(object):

	_wikipedia_Root = 'http://wikipedia.org'

	_wikilink_reg = re.compile(r'(/wiki/[^:]+?$)')
	_href_wikilink_reg = re.compile(r'\"(/wiki/[^:]+?)\"')

	# /wiki/something_without_a_colon, until a #anchor is seen
	# ASSUMPTION: ALL UNDESIRED WIKILINKS CONTAIN A COLON
	# ASSUMPTION: ALL CITATIONS ex. superscript^[1],
				# do not have /wiki/ in their <a href>'s
	_CRAWL_WAIT_TIME = 1.5
	# I think robots.txt specifies a 1 second minimum

	
	def __init__(self, startURL = ''):

		if startURL:
		# initialize with starting URL if present
			startQuoted = self.URLify(startURL)
		else:
		# choose a random wiki page
			startQuoted = self.URLify(self.wiki_randomURL())

		previewFirstPage = requests.get(startQuoted)
		previewFirstPage = bs4.BeautifulSoup(previewFirstPage.text)
		# the starting url must be normalized by visiting the site
		self.startURL = self.URLify(previewFirstPage)

		self.currentURL = startURL

		self._visitedURLs = collections.OrderedDict()
		# Myabe OrderedDict so you can see previous and next
		# Key is /wiki/stuff, val is corresponding CrawlRecord
		self.currentPage = None
		self._nthSeen = 0
		# tracks how many pages crawler has crawled

		self._infRecord = None
		# temporary holding cell for the infinity record if there is one


	@classmethod
	def wiki_randomURL(cls):
		"""Returns a unicode url of a random wikipedia page"""
		random_extension = '/wiki/Special:Random'

		randPage = requests.get(cls._wikipedia_Root + random_extension)

		return randPage.url


	def navigate(self, navURL):
		"""Change the 'current page' and 'current URL' of self to page served by navURL"""

		page = requests.get(navURL)
		# BEWARE THE 404
		# make request


		self.currentPage = bs4.BeautifulSoup(page.text)
		# soupify request text

		self.currentURL = self.URLify(self.currentPage)
		# grab new url from the page. self.URLify will use the article title
		# as the new /wiki/{Article_Title} url
		# --This helps with redirection issues



	@staticmethod
	def is_disambiguation(bs4Page):
		"""Is this page a disambiguation?"""

		return bool(bs4Page.find('table', id = 'disambigbox'))

	@classmethod
	def linkFinderFunc(cls, bs4Page):
		"""Higher order abstraction function for seeking link on a given page.
		Returns a func that will succesfully parse page links, regardless
		of whether or not that page is a disambiguation"""

		"""MIGHT WANT TO SIMPLY EXECUTE RETURN FUNC RATHER THAN ACTUALLY
		RETURNING B/C 'BS4PAGE' IS USUALLY USED IN THE CALL TO THE RETURNED FUNC"""

		if cls.is_disambiguation(bs4Page):
			# assuming that no disambiguations will happen when you start at :Random
			# assumption is not yet proven

			def disambigFunc(page):
				raise CrawlError('Hit a disambiguation at %s' % bs4Page.url)

			return disambigFunc

		else:

			def regularPageFunc(page):
				"""Navigate to (wikipedia 'url'), parse page down to first 'wiki/some_page' <a> tag, 
				return the matched <a> element's link to the next wikipedia page"""





				contentParagraphs = page.find("div", id="mw-content-text").findAll("p", recursive=False)


				firstParagraph, restParagraphs = contentParagraphs[0], contentParagraphs[1:]


				linkInFirst = cls.firstParagraphLink(firstParagraph)

				if linkInFirst: return cls.URLify(linkInFirst)


				# find valid wikilinks in all paragraphs but the first
				for para in restParagraphs:

					matched = para.find("a", recursive=False, href=WikiCrawl._wikilink_reg)
					# match only /wiki/... hrefs

					if matched:
						break
				else:
					raise CrawlError("No valid wikilinks exist on current page")

				# find first <a> within paragraph whose href matched the reg pattern

				return self.URLify(matched.get("href"))

			return regularPageFunc



	@classmethod
	def firstParagraphLink(cls, bs4FirstParagraph):

		sanitizedParagraph = bs4FirstParagraph
		"""WARNING: this destructively alters bs4FirstParagraph.
		Can't figure out a way to copy the paragraph"""


		"""
		from copy import deepcopy

		sanitizedParagraph = bs4.BeautifulSoup(unicode(bs4FirstParagraph.text))

		deepcopy(bs4FirstParagraph)

		print 'sanitized paragraph is first paragrapg? %s' % (sanitizedParagraph is bs4FirstParagraph,)
		print sanitizedParagraph.findAll('sup', {'class':'reference'})
		"""

		for cite in sanitizedParagraph.findAll('sup', {'class':'reference'}):
			cite.extract()


		def linkOutsideParens(paragraphHtml):

			ILLEGAL_FIRSTSENTENCE_REG = lambda link: re.compile( 
														r""" \( [^)] +?                    # left paren, anything but right paren
												 		href=\" """ + link + r""" \" # href(equals)"/wiki/topic"
												 		[^)] *?  </a>[^)] *?  \)""",        # ... </a> ... first left paren seen
														re.X)                               # verbose regex
			# illegal formation for a hyperlink in the first sentence of a wikipage

				

			potentialy_valid_wikilinks = cls._href_wikilink_reg.finditer(paragraphHtml)

			for linkMatch in potentialy_valid_wikilinks:
				linkText = linkMatch.groups()[0]

				if not ILLEGAL_FIRSTSENTENCE_REG(linkText).search(paragraphHtml):
					# if this link doesn't match the illegal pattern, return link
					return cls.URLify(linkText)




		def indexOfFirstSentence(bs4Paragraph):
			#period_reg = re.compile(r'(\.)', re.U)
			end_of_sentence_reg = re.compile(r'\.(?: [A-Z]|\[\d+\] )', re.U)
			# ^find a period then either
				# -- space after period followed by capital letter
				# -- [number] immediately after period, follwed by space
				# ---- ex. 'data[1] ' where [1] is a citation

			all_navstrings = tuple(bs4Paragraph.strings)

			all_navstrings_str = u''.join(all_navstrings)


			for navstring, index_in_navstrings in zip(all_navstrings, count()):
				# attempt to find a period in every navstring

				#print 'navstring %s groups %s' % (navstring, matches)

				#if period_reg.search(navstring):
				if u'.' in navstring:
					# if period found in this navstring

					if (index_in_navstrings == len(all_navstrings) - 1
						# if last navstring in paragraph, assumed to be end-of-sentence
						or end_of_sentence_reg.search(all_navstrings_str)):
						# if a period at end-of-sentence, success

						# if period found, return its navstring's index in parent
						return bs4Paragraph.index(all_navstrings[index_in_navstrings])
			else:

				print 'FIRST SENTENCE CANNOT BE SPLIT\n'

				return None


		sentenceSplitIndex = indexOfFirstSentence(sanitizedParagraph)
		# index of element in firstParagraph's tag contents

		# attempt to cut the first paragraph with a period
		# if possible, this will exclude the parenthese check for
		# sentences other than the first

		if sentenceSplitIndex:
			"""If sentence can be split, split it into a firstSentence
			string and a restOf array of bs4 elements. First look for valid
			links within the firstSentence. If that fails, look for valid links
			within the restOf. If both fail, return None because there ar NO
			valid links within the first paragraph"""

			
			firstSentenceHtml = u''.join(map(unicode, sanitizedParagraph.contents[:sentenceSplitIndex + 1]))
			# string representation of all html up to and including first sentence
			restOf_firstParagraph = sanitizedParagraph.contents[sentenceSplitIndex:]
			# list of tags that follow the first sentence inner html

			firstSentence_link = linkOutsideParens(firstSentenceHtml)

			if firstSentence_link:
				# if valid link within first sentence, return it
				return firstSentence_link
				
			else:
				# look at rest of paragraph for valid links
				for elem in restOf_firstParagraph:
					# search through restOf_firstParagraph for <a> links
					# return link if link is /wiki/...
					if elem.name == 'a' and cls._wikilink_reg.match(elem['href']):
						return elem['href']

				else:
					# looked through both first sentence and rest, failed to find
					return None

		else:
			"""Sentence cannot be split. Must apply the paren exclusion
			search to the ENTIRE paragraph. This is undesireable b/c it
			may exclude valid parentheses later on in the text"""


			return linkOutsideParens(unicode(sanitizedParagraph))

			




	@classmethod
	def URLify(cls, urlSource):
		"""OVERLOADED:
			bs4.page: find Title on wikipage, append it to _wikipedia_Root
			string: strip out /wiki/... from urlSource & produce full wikilink
		"""
		import urllib

		def stripWikiUrl(wikiURL):
			"""Given part or whole wikiURL, returns the /wiki/... portion.
			Raises exception if wikiURL does not match pattern"""


			URL_ANCHOR_HASH_REG = re.compile(r'#.*$', re.DOTALL)
			# match the \urlstuff#(anchor_location) portion of a url

			stripped = URL_ANCHOR_HASH_REG.sub('', cls._wikilink_reg.search(wikiURL).groups()[0])
			# find the /wiki/rest#anchor_location portion of a url, then strip
			# off the #anchor_location

			if stripped: return urllib.quote(stripped)
			else: raise CrawlError("URL doesn't match /wiki/... pattern")


		if isinstance(urlSource, bs4.BeautifulSoup):
			# if given page, find page title, urlify it, and create full wikilink
			return unicode(cls._wikipedia_Root +
							'/wiki/' +
							urllib.quote(cls.wikiTitle(urlSource)))

		elif isinstance(urlSource, basestring):
			print "URLification of %s to %s" % (urlSource, unicode(cls._wikipedia_Root + stripWikiUrl(urlSource)))
			return unicode(cls._wikipedia_Root + stripWikiUrl(urlSource))

		else:
			raise TypeError('Must pass bs4.BeautifulSoup or str')


	@staticmethod
	def wikiTitle(bs4Page):
	#def wikiTitle(self, bs4Page):
		"""Given a bs4 wiki webpage, return the wiki title of the page"""

		header = bs4Page.find("h1", id="firstHeading")

		return header.string

	
	def nextWikiLink(self, page):
		"""DEPRECATED. CONTENTS REASSIGNED TO regularPageFunc OF linkFinderFunc"""
		pass

	def crawl(self, numRuns):
		"""Crawl wikipedia numRuns times, store results as CrawlRecords in self._visitedURLs"""

		# NEED TO HANDLE NOMATCH EXCEPTION, INFINITE LOOP EXCEPTION, DEADEND EXCEPTION

		def advanceCrawler():

			self.navigate(self.currentURL)
			# navigate changes currentURL to result of navigating last currentURL
			# REDIRECTION: navigate will take in any url, but will account
			# for urls that may yield redirection

			self._nthSeen += 1
			# increment number of pages seen

			currentURLStripped = self.currentURL

			print 'just visited self.currentUrl %s\n' % (self.currentURL,)



			nextLink = self.linkFinderFunc(self.currentPage)(self.currentPage)
			# grab the next link from the current page

			record = CrawlRecord(self.URLify(self.currentURL), 
									self.wikiTitle(self.currentPage),
									self._nthSeen)
			# create a record using the url just searched, title currently seen, and n



			try: 
				# if hashkey exists, we're in an infinite crawl loop
				self._visitedURLs[currentURLStripped]

				self._infRecord = record
				
				raise CrawlError('Key already visited, infinite loop')

			except KeyError:
				# url extension not visited yet, continue crawling


				self._visitedURLs[currentURLStripped] = record
				# insert this location into the hash

				self.currentURL = nextLink #self.URLify(nextLink)
				# set the next-current url to the result of this page

				print 'AdvanceCrawler: nextLink %s' % nextLink

				sleep(WikiCrawl._CRAWL_WAIT_TIME)
				# sleep to abide by robots.txt


		for _ in xrange(numRuns):
		# run numruns - 1 times

			try:
				# crawler might hit infinite loop
				advanceCrawler()

			except CrawlError:
				# infinite record hit, crawling complete
				pass



	def _csvPath(self, fileName = None, directory = ''):

		if fileName: return fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: return self._visitedURLs[self.URLify(self.startURL)].word + '.csv'



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

		#assert False


		headers = ['URL ID', 'Word', 'URL']
		# csv column headers



		if fileName: name = fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: name = self._visitedURLs[self.startURL].word + '.csv'

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
	else: crawler = WikiCrawl()

	#else: crawler = WikiCrawl(randWikiStart('enwiki-latest-all-titles-in-ns0'))
	"""DEPRECATED b/c no longer using the wiki text file, instead using /wiki/Special:Random"""

	crawler.crawl(NUM_TRIALS)

	os.chdir('Trials_Results')

	crawler.writeCSV(fileName = CSV_NAME, directory=CSV_DIRECTORY)





_run(sys.argv[1:])

"""

def tagsUntilNavCondition(bs4TagLs, stopTagName, stopCondition, inclusive = True):
	from itertools import count
	#Capture all tags in bs4TagLs until you hit a tag of type stopTagName
	#whose navigable string meets stopCondition
	tags = []
	for tag, i in bs4TagLs, count():
		if i == 100:
			print tag.string
		if tag.name == stopTagName and stopCondition(tag.string):
			tags.append(tag) if inclusive and tag not in tags else None
			break
		else:
			tags.append(tag) if tag not in tags else None
	return tags
"""







