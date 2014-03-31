#!/usr/bin/env python

import requests, bs4, re, random, itertools, unicodecsv
import getopt, os, sys, collections, csv, codecs

from time import sleep
from itertools import count
#from unicode_csv import UnicodeWriter

class Ns():
	pass

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


"""
Exclusions:
	- Fully italic links
	- Fully bold links
	- Anything in the first sentence that falls between parentheses
	- Anything in a table

Inclusions:
	- Unordered Lists
	- Ordered Lists


"""






def csvHeadersExist(pth, headerLs, delimiter=','):
	"""Checks to see if a csv file has headers in its first row"""

	with open(pth, 'r') as f:
		return f.readline().rstrip().split(delimiter) == headerLs

class CrawlError(Exception):
	"""Wikipedia crawler has encountered a page that doesn't hold a valid link to any other Wikipedia page"""

	def __init__(self, message):

		Exception.__init__(self)
		self.message = message

class DisambiguationError(CrawlError):

	def __init__(self, message):
		CrawlError.__init__(self, message)

class DeadEndError(CrawlError):

	def __init__(self, message):
		CrawlError.__init__(self, message)


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
		#return WikiCrawl._mapEncode([hash(self.urlExtension), self.word, self.urlExtension])
		return map(unicode, [hash(self.urlExtension), self.word, self.urlExtension])


class WikiCrawl(object):

	_wikipedia_Root = 'http://wikipedia.org'

	_wikilink_reg = re.compile(r'(/wiki/[^:]+?$)')
	_href_wikilink_reg = re.compile(r'\"(/wiki/[^:]+?)\"')

	# /wiki/something_without_a_colon, until a #anchor is seen
	# ASSUMPTION: ALL UNDESIRED WIKILINKS CONTAIN A COLON
	# ASSUMPTION: ALL CITATIONS ex. superscript^[1],
				# do not have /wiki/ in their <a href>'s
	_CRAWL_WAIT_TIME = 1.1
	# I think robots.txt specifies a 1 second minimum

	
	def __init__(self, startURL = ''):

		self._initialize(startURL)


	def _initialize(self, startURL = ''):
		"""Basically __init__ method, but can be reused
		if the crawler has to be restarted"""

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

		self.currentURL = self.startURL

		self._visitedURLs = collections.OrderedDict()
		# Myabe OrderedDict so you can see previous and next
		# Key is /wiki/stuff, val is corresponding CrawlRecord
		self.currentPage = None
		self._nthSeen = 0
		# tracks how many pages crawler has crawled

		self._infRecord = None
		# temporary holding cell for the infinity record if there is one
		self._stepsToInfRecord = None


	@classmethod
	def manualEntry(cls):
		"""Manually enter a url"""

		print '\a' * 2
		# alert user of a problem

		INPUT_MESSAGE = 'Manually enter the link to the next page: '
		return cls.URLify(raw_input(INPUT_MESSAGE))

	@classmethod
	def wiki_randomURL(cls):
		"""Returns a unicode url of a random wikipedia page"""
		random_extension = '/wiki/Special:Random'

		randPage = requests.get(cls._wikipedia_Root + random_extension)

		return randPage.url

	@classmethod
	def WhitelsitedFailures(cls, title):

		COMMUNITY = 'Community'
		# inline text list: '1) blah blah and 2) blah'
		# causes unbalanced parens

		# COMMON_FAILURES is a dict of all common failure titles
		# and their first link solution
		COMMON_FAILURES = {COMMUNITY: 'Level_of_analysis#Meso-level',}

		if title in COMMON_FAILURES:
			print 'found title %s in dict: %s' % (title, COMMON_FAILURES[title])
			return cls.URLify('/wiki/' + COMMON_FAILURES[title])
		else:
			return None


	def navigate(self):
		"""Change the 'current page' and 'current URL' of self to page served by self.currentURL"""

		def sanitizePage(soup, boldLinks=False, italLinks=False):
			"""Remove unwanted elements from the bs4"""

			from sets import Set

			DIRTY_ELEMENT_NAMES = ('p', 'li', 'sup', 'i', 'b', 'span')

			content_text = soup.find('div', id='mw-content-text')

			

			try:
				nav_tables = content_text.findAll('table')
				for t in nav_tables:
					#print t
					t.extract()
			except AttributeError:
				#print 'didnt find navtable'
				# didn't find any bad tables
				pass


			IPA_CLASS_BLACKLIST = ('IPA', 'IPA nopopups')
			# delete all spans associated with class 'IPA'
			IPA_spans = content_text.findAll(lambda e: (e.name == 'span'
											 and 'class' in e.attrs
											 and (bool(Set(e['class']) & Set(IPA_CLASS_BLACKLIST)))),
											 recursive = True)

			for span in IPA_spans:
				span.extract()


			dirty_elements = content_text.findAll(lambda elem: elem.name in DIRTY_ELEMENT_NAMES)

			for elem in dirty_elements:


				if elem.name == 'p':


					if elem.find('span', {'style' : 'font-size: small;'}):
						# top right corner small text paragraphs; aren't
						# real meat of the article
						elem.extract()

					

					if (len(tuple(elem.children)) == 1 
						and elem.find(lambda e: e.name in ('b', 'i'), recursive=False)):
						# <p><i>So and so redirects here</i></p>
						# <p><b>BOLD LINK</b></p>
						elem.extract()

					if not tuple(elem.strings):
						# paragraph has no navstrings inside of it
						# ex. <p><br></p>
						elem.extract()



				if not italLinks and elem.name == 'i':
					# remove <i> tags
					elem.extract()

				if not boldLinks and elem.name == 'b':
					# delete <b> tags and their children
					# don't want <b><a>...BOLD LINK</a></b>
					elem.extract()
				

					

				try:
					if elem.name == 'sup' and elem['class'] == 'reference':
						# extract [1],[2],[\d+] citations
						elem.extract()
				except KeyError:
					# elem['class'] doesn't necessarily exist
					pass



		page = requests.get(self.currentURL)
		# BEWARE THE 404
		# make request


		self.currentPage = bs4.BeautifulSoup(page.text)
		# soupify request text

		self.currentURL = self.URLify(self.currentPage)
		# update the current url so it is normalized by using page title

		sanitizePage(self.currentPage)

		#self.currentURL = self.URLify(self.currentPage)
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
				raise DisambiguationError('Hit a disambiguation')

			return disambigFunc

		else:

			def regularPageFunc(page):
				"""Navigate to (wikipedia 'url'), parse page down to first 'wiki/some_page' <a> tag, 
				return the matched <a> element's link to the next wikipedia page"""



				ELEMENT_STRAINER = lambda elem: elem.name in ('p', 'ol', 'ul')
				# look for these types of elements
				NULL_PARAGRAPH = bs4.BeautifulSoup('<p></p>')
				# used as a dummy value if the page is empty

				contents = page.find("div", id="mw-content-text").findAll(ELEMENT_STRAINER, recursive=False)


				firstParagraph = contents[0] if contents != [] else NULL_PARAGRAPH
				restContents = contents[1:]


				linkInFirst = cls.firstParagraphLink(firstParagraph)

				if linkInFirst: return linkInFirst


				# find valid wikilinks in all paragraphs but the first
				for elem in restContents:

					matched = elem.find('a', 
										recursive=True if elem.name in ('ol', 'ul') else False, 
										href=WikiCrawl._wikilink_reg)
					# match only /wiki/... hrefs, recursively for <ol>

					if matched:
						break
				else:
					raise DeadEndError("No valid wikilinks exist on current page")

				# find first <a> within paragraph whose href matched the reg pattern

				#return self.URLify(matched.get("href"))
				return cls.URLify(matched.get('href'))

			return regularPageFunc



	@classmethod
	def firstParagraphLink(cls, bs4FirstParagraph):



		"""
		from copy import deepcopy

		bs4FirstParagraph = bs4.BeautifulSoup(unicode(bs4FirstParagraph.text))

		deepcopy(bs4FirstParagraph)

		print 'sanitized paragraph is first paragrapg? %s' % (bs4FirstParagraph is bs4FirstParagraph,)
		print bs4FirstParagraph.findAll('sup', {'class':'reference'})
		"""




		def linkOutsideParens(paragraphHtml):
			"""DEPRECATED"""

			assert False



			ILLEGAL_FIRSTSENTENCE_REG = lambda link: re.compile( 
														r""" \( [^)] +?                    # left paren, anything but right paren
												 		href=\" """ + link + r""" \" # href(equals)"/wiki/topic"
												 		.*?  </a>.*  \)""",        # ... </a> ... first left paren seen
														re.X | re.DOTALL)                  # verbose regex, dotall
			# illegal formation for a hyperlink in the first sentence of a wikipage

				

			potentialy_valid_wikilinks = cls._href_wikilink_reg.finditer(paragraphHtml)

			for linkMatch in potentialy_valid_wikilinks:
				linkText = linkMatch.groups()[0]
				print linkText


				if not ILLEGAL_FIRSTSENTENCE_REG(linkText).search(paragraphHtml):
					# if this link doesn't match the illegal pattern, return link
					return cls.URLify(linkText)


		def cutWithinParens(elemLs):

			"""Find a left paren, put every element you see in the delete deletable_cache
			until you find a right paren. When you do, extract all elements and
			restart search for another left"""

			LEFT_PAREN_REG = re.compile(r'[^)]* \( [^)]*', re.VERBOSE)
			# ( with no )
			RIGHT_PAREN_REG = re.compile(r'[^(]* \) [^(]*', re.VERBOSE)
			# ) with no (

			closure = Ns()
			closure.left_seen, closure.right_seen = 0, 0

			def incrParens(s):

				for char in s:
					if char == '(': closure.left_seen += 1
					elif char == ')': closure.right_seen += 1


			deletable_cache = []

			def emptyCache():
				"""Eradicate every element in the deletable_cache"""

				for e in reversed(deletable_cache):
					#print 'time to delete %s' % e
					# clear cache

					
					try:
						#print 'deletable cache before %s' % deletable_cache
						deletable_cache.remove(e)
						#print 'deletable_cache after %s' % deletable_cache
						elemLs.remove(e)

					except ValueError:
						# element already deleted by parent tag's deletion
						#print 'had trouble removing %s' % e
						pass

					e.extract()



			elemLs_clone = tuple(elem for elem in elemLs)
			# will be destructively mutating elemLs during iteration
			# so want to keep a clone purely for iteration purposes

			for elem in elemLs_clone:

				#print '\nexamining %s, cache is %s, LR(%i, %i)\n' % (elem, deletable_cache, closure.left_seen, closure.right_seen)

				if closure.left_seen > closure.right_seen:
					# left paren prevails, add elements to cache
					deletable_cache.append(elem)

				elif closure.left_seen == closure.right_seen:

					#print 'deleting %s of len %s\n' % (deletable_cache, len(deletable_cache))
					# right paren just equaled

					emptyCache()


				else:
					# right parens outweigh left parens,
					# this imbalance shouldn't happen on wikipedia
					raise CrawlError('This page has unbalanced Parens')


				if isinstance(elem, bs4.NavigableString):
					# if working with navstring, recalculate parens
					incrParens(elem)

			else:
				# empty the cache at the end of the function

				if closure.left_seen == closure.right_seen:
					emptyCache()




		def indexOfFirstSentence(bs4Paragraph):

			period_reg = re.compile(r'(?<!\.[A-Za-z])(?:^\.|\.$|\.(?: [A-Z]|\[\d+\] ))(?![A-Za-z]\.)', re.U)
			                           # watch out for  # meat of the sentence finder   # watch out for
			                           # U.(S.)                                         # (U.)S.

			# ^find a period then either
				# beginning of navstring
				# end of navstring

				# -- space after period followed by capital letter
				# -- [number] immediately after period, follwed by space
				# ---- ex. 'data[1] ' where [1] is a citation

			Chester_A_Arthur_reg = re.compile(r'[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+', re.U)
			# prevent names (Chester A(.) Arthur) from being matched

			Blacklisted_Period_reg = re.compile('(?:Mr|Mrs|Ms|Sr|Jr|Dr|lat|sing)\.', re.U | re.I)



			all_navstrings = tuple(bs4Paragraph.strings)

			all_navstrings_str = u''.join(all_navstrings)



			for navstring, index_in_navstrings in zip(all_navstrings, count()):
				# attempt to find a period in every navstring

				#print 'navstring %s groups %s' % (navstring, matches)

				"""

				IMPROVED THE period_reg so this isn't necessary

				if u'.' in navstring:
					# THIS IS DIFFICULT B/C NAVSTRING MAY NOT EXACTLY MATCH
					# period_reg BUT ITS SURROUNDING CONTEXT WILL

					if (index_in_navstrings == len(all_navstrings) - 1
						# if last navstring in paragraph, assumed to be end-of-sentence
						or period_reg.search(all_navstrings_str)):
						# if a period at end-of-sentence, success
				"""

				if (period_reg.search(navstring) 
					and not Chester_A_Arthur_reg.search(navstring)
					and not Blacklisted_Period_reg.search(navstring)):

						print 'within ' + str(all_navstrings)
						print 'lies %s' % all_navstrings[index_in_navstrings]
						print 'at %i' % index_in_navstrings

						# if period found, return its navstring's index in parent
						return bs4Paragraph.index(all_navstrings[index_in_navstrings])
			else:

				print 'FIRST SENTENCE:\n %s\n CANNOT BE SPLIT\n' % ''.join(map(str, bs4Paragraph))

				return None


		sentenceSplitIndex = indexOfFirstSentence(bs4FirstParagraph)
		# index of element in firstParagraph's tag contents

		# attempt to cut the first paragraph with a period
		# if possible, this will exclude the parenthese check for
		# sentences other than the first

		if sentenceSplitIndex:
			"""If sentence can be split, split it into a firstSentence
			string and a restOf array of bs4 elements. Sanitize the firstSentenceElements
			by stripping out anything between parens, then rejoin the
			firstSentenceElements with the restOf_firstParagraph"""

			firstSentenceElements = bs4FirstParagraph.contents[:sentenceSplitIndex + 1]
			# all the tags up to and including the end-of-first-sentence inner html

			restOf_firstParagraph = bs4FirstParagraph.contents[sentenceSplitIndex:]
			# list of tags that follow the first sentence inner html

			cutWithinParens(firstSentenceElements)
			# cleanse the firstSentenceElements so all <a>'s inside parens are deleted

			searchableElements = firstSentenceElements + restOf_firstParagraph
			# join the sanitized firstSentenceElements with the
			# untouched restOf_firstParagraph





		else:
			"""Sentence cannot be split. Must apply the paren exclusion
			cleansing to the ENTIRE paragraph. This is undesireable b/c it
			may exclude valid parentheses outside of the first sentence"""


			searchableElements = [elem for elem in bs4FirstParagraph.contents]
			# all content elements are treated equally, regardless
			# of first sentence's status b/c it cannot be determined

			cutWithinParens(searchableElements)
			# apply paren exclusion to entire first paragraph


		for elem in searchableElements:
			# search through paragraph elements for valid wikilinks

			if elem.name == 'a' and cls._wikilink_reg.match(elem['href']):
				return cls.URLify(elem['href'])

		else:
			# looked through both first sentence and rest, failed to find
			return None

			




	@classmethod
	def URLify(cls, urlSource):
		"""OVERLOADED:
			bs4.page: find Title on wikipage, append it to _wikipedia_Root
			string: strip out /wiki/... from urlSource & produce full wikilink
		"""
		import urllib

		WIKI_QUOTE = lambda url: urllib.quote(url.encode('utf-8'), safe='%:/')
		# avoids recursive or arbitrary quoting

		def stripWikiUrl(wikiURL):
			"""Given part or whole wikiURL, returns the /wiki/... portion.
			Raises exception if wikiURL does not match pattern"""


			URL_ANCHOR_HASH_REG = re.compile(r'#.*$', re.DOTALL)
			# match the \urlstuff#(anchor_location) portion of a url

			stripped = URL_ANCHOR_HASH_REG.sub('', cls._wikilink_reg.search(wikiURL).groups()[0])
			# find the /wiki/rest#anchor_location portion of a url, then strip
			# off the #anchor_location

			if stripped: return WIKI_QUOTE(stripped)
			else: raise CrawlError("URL doesn't match /wiki/... pattern")


		if isinstance(urlSource, bs4.BeautifulSoup):
			# if given page, find page title, urlify it, and create full wikilink
			return unicode(cls._wikipedia_Root +
							'/wiki/' +
							WIKI_QUOTE(cls.wikiTitle(urlSource)))

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

		return header.text

	
	def nextWikiLink(self, page):
		"""DEPRECATED. CONTENTS REASSIGNED TO regularPageFunc OF linkFinderFunc"""
		pass

	def crawl(self, numRuns):
		"""Crawl wikipedia numRuns times, store results as CrawlRecords in self._visitedURLs"""

		# NEED TO HANDLE NOMATCH EXCEPTION, INFINITE LOOP EXCEPTION, DEADEND EXCEPTION

		def advanceCrawler():

			try:

				self.navigate()
				# navigate changes currentURL to result of navigating last currentURL
				# REDIRECTION: navigate will take in any url, but will account
				# for urls that may yield redirection

				self._nthSeen += 1
				# increment number of pages seen

				print 'just visited self.currentUrl %s\n' % (self.currentURL,)



				nextLink = self.linkFinderFunc(self.currentPage)(self.currentPage)
				# grab the next link from the current page

			except CrawlError as e:

				if isinstance(e, DisambiguationError) or isinstance(e, DeadEndError):
					# Disambiguation Errors cause the crawl to halt and
					# must be handled at a higher level
					raise e

				else:
					# Other Crawl Errors can be migigated by manual entry
					print 'Error crawling %s: %s' % (self.currentURL, e.message)

					whitelisted = self.WhitelsitedFailures(
														self.wikiTitle(self.currentPage))

					nextLink = whitelisted if whitelisted else self.manualEntry()
					# if the failure is whitelisted use its solution, else manual entry


			record = CrawlRecord(self.currentURL, 
									self.wikiTitle(self.currentPage),
									self._nthSeen)
				# create a record using the url just searched, title currently seen, and n


			try: 
				# if hashkey exists, we're in an infinite crawl loop
				self._visitedURLs[self.currentURL]

				self._infRecord = record
				self._stepsToInfRecord = self._visitedURLs[self.currentURL].nth
				
				raise CrawlError('Key already visited, infinite loop')

			except KeyError:
				# url extension not visited yet, continue crawling


				self._visitedURLs[self.currentURL] = record
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

			except CrawlError as e:

				if isinstance(e, DisambiguationError):
					print '\a'
					print e.message
					self.restart(numRuns)


				elif isinstance(e, DeadEndError):
					raise e

				else:
					# infinite record hit, crawling complete
					break

	@staticmethod
	def _mapEncode(ls, encoding='utf-8'):
		return [unicode(s).encode(encoding) for s in ls]

	def _csvPath(self, fileName = None, directory = ''):

		if fileName: return fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: return self._visitedURLs[self.URLify(self.startURL)].word + '.csv'



	def verboseCSV(self, fileName = None, directory = '', delim = ','):
		"""Writes the path of all word seen on a traversal"""

		pth = self._csvPath(fileName, directory)
		
		visited = self._visitedURLs.values()

		row = self._mapEncode(
			[hash(visited[0])] + 
			map(lambda record: record.word, self._visitedURLs.values()))
		# Array starting with hashval of first word
		# followed by every single word seen

		if self._infRecord: row = row.append(self._infRecord)
		# append the inf record to words seen if it has been encountered

		with codecs.open(pth, 'a', encoding='utf-8') as f:
			excelWriter = csv.writer(f, delimiter = delim)
			excelWriter.writeRow(row)


	def summaryCSV(self, fileName = None, directory = '', delim = ','):
		"""Writes startWord hash, startWord, last unique word, numSeen, and infWord if exists"""
		

		pth = self._csvPath(fileName, directory)

		headers = self._mapEncode(['URL ID', 'Start Word', 'End Word', 'Number of Jumps', 'Loop Word'])

		visited = self._visitedURLs.values()

		first, last = visited[0], visited[len(visited) - 1]
		# first word seen and last word seen
		infSeen = self._infRecord if self._infRecord else 'None'

		row = self._mapEncode([hash(first), first, last, self._nthSeen, infSeen])

		with codecs.open(pth, 'a', encoding='utf-8') as f:
			excelWriter = UnicodeWriter(f, delimiter = delim)
			if os.path.getsize(pth) == 0:
				excelWriter.writeRow(headers)
			excelWriter.writeRow(row)


	def writeCSV(self, fileName=None, directory=''):
		import csv
		"""DEPRECATED"""

		#assert False


		headers = map(unicode, ['URL ID', 'Word', 'URL'])
		# csv column headers



		if fileName: name = fileName.replace('.csv', '') + '.csv'
		# if name passed, use it; else name output first word seen by default
		else: name = self._visitedURLs[self.startURL].word + '.csv'

		# FIX FILENAME/DIRECTORY SHIT
		
		with open(name, 'wb+') as f:
			#excelWriter = UnicodeWriter(f, delimiter = '|', encoding = 'utf-8')
			excelWriter = unicodecsv.writer(f, delimiter = '|', encoding='utf-8')
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
		print name

		return self._visitedURLs
		# does this really need a return value?

	def restart(self, numRuns,  startURL = ''):
		"""Return all properties to pre-crawl status"""

		self._initialize(startURL)
		self.crawl(numRuns)




def _run(argv):
	import traceback


	def usage():
		print "Usage: wikipedia jumper"
		print "\t-excel_path Excel File Path"
		print "\t--help"

	CSV_DIRECTORY, CSV_NAME = '', None
	INPUT_URL, NUM_TRIALS = None, 0
	# NUM_TRIALS is a magic number right now


	try:
		opts, args = getopt.getopt(argv, 'hn:', ['help', 'debug', 'csv-directory=', 'csv-name='])
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

	if '--debug' in optDict.keys(): DEBUG = True
	else: DEBUG = False


	# do I really need to mkdir?
	try:

		out_dir = 'Trials_Results' if DEBUG else 'Real_Deal_Trials'

		os.mkdir(out_dir)
	except:
		# directory already exists
		OSError

	try:

		if INPUT_URL: crawler = WikiCrawl(INPUT_URL)
		else: crawler = WikiCrawl()

		#else: crawler = WikiCrawl(randWikiStart('enwiki-latest-all-titles-in-ns0'))
		"""DEPRECATED b/c no longer using the wiki text file, instead using /wiki/Special:Random"""

		crawler.crawl(NUM_TRIALS)

		os.chdir(out_dir)

		crawler.writeCSV(fileName = CSV_NAME, directory=CSV_DIRECTORY)

	except Exception as e:
		# any program-terminating exception
		# alert user
		traceback.print_exc()

		print 'Fatal error: %s' % e.message

		if type(e) != KeyboardInterrupt and not DEBUG:

			print '\a' * 5

		exit(1)





			




	





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







