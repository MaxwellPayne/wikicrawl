import re

class ParseDepth():
	def __init__(self, tagName, htmlString, charIndex, depth=0):
		self.depth = depth
		self.tagName = tagName
		self.html = htmlString
		self.index = charIndex



class InnerHtmlParser():
	prefix_reg = re.compile(r'<\w+? |<\w+?>')
	postfix_reg = re.compile(r'/\w*>')

	# for efficiency: create hash of all valid tags

	def __init__(self, htmlString):
		self.html = htmlString

	@staticmethod
	def _cleanTag(tag):
		for ch in ['<', '>', '/', ' ']:
			tag = tag.replace(ch, '')
		return tag

	@staticmethod
	def isTag(text):
		# not true, can have fringe cases with '<' or '>' literal
		return re.search(r'<%s |<%s>|/%s>' % text, text)

	def depthAtIndex(self, strIndex):

		htmlSlice = self.html[:strIndex + 1]

		leftTags = self.__class__.prefix_reg.findall(htmlSlice)
		rightTags = self.__class__.postfix_reg.findall(htmlSlice)

		if not leftTags or not rightTags: raise ValueError('index not within html')

		innermostTag = leftTags[len(leftTags) - 1]

		print leftTags

		return ParseDepth( 
							self._cleanTag(innermostTag), 
							self.html,
							strIndex,
							depth=len(leftTags) - len(rightTags))

	def findall(text):
		# findall instances of text in self.html and keep them if they are innerHtml

		instances = re.findall(text, self.html)








"""
GARBAGE ATTEMPT TO WEED OUT NAVIGABLESTRINGS
BETWEEN OTHER PARENTHESE NAVIGABLESTRINGS

NOT SO! USE WITH < AND > TO DETECT WHETHER OR NOT
YOU ARE CURRENTLY WITHIN AN HTML TAG OF SOMESORT

<p>hi</p> 'hi' is within '<p>''
<p><a href="">hi</a></p> 'hi' is within '<a>'

track levels of nesting^ --<p> is level 0, <a> is level 1
track type of tag


start new level when you hit a <
jump out of that level when you hit />

lambda isLeftParen s: u'(' in s and u')' not in s
lambda isRightParen s: u')' in s and u')' not in s

found = []
leftParens, rightParens = 0, 0

for nav in map(unicode, navList):
	if isLeftParen(nav): leftParens += 1
	if isRightParen(nav): rightParens += 1

	if leftParens == rightParens:
		found.append(nav)
	elif leftParens > rightParens:
		continue
	else: # right greater than left
		raise ValueError('Unbalanced parens to the right')


	
	if withinParens:
		if u')' in nav: withinParens = True
	
	else: # outside of parens

		if u'(': # hit a right paren
			withinParens = True
			continue
		else:
	

"""