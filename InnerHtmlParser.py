import re


class CommonEqualityMixin(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


self_closing_pattern = r'<\w+?[^/>]*?/>'

noattrib_left_pattern = r'<\w+?>'
attrib_left_pattern = r'<\w+? [^>]+?\">'

#open_left_pattern = r'<\w+? '
#closed_left_pattern = r'<\w+?>'
#endof_left_pattern = r'\">'
right_pattern = r'/\w*?>'
# general form for word_right and blank_right
# DOES NOT TELL WHICH

word_right_pattern = r'/\w+?>'
blank_right_pattern = r'/>'




class TagType(CommonEqualityMixin):
	"""
	ClosedLeft = 1
	OpenLeft = 2
	EndOfLeft = 3
	WordRight = 4
	BlankRight = 5
	"""

	SelfClosing = 0
	NoAttribLeft = 1
	AttribLeft = 2
	WordRight = 3
	BlankRight = 4

	def __init__(self, tagStr):
		self.tagType = self.classifyTag(tagStr)
		self.tagName = self.cleanTag(tagStr)

	def __repr__(self):
		return '<TagType: tagName=%s, tagType=%s>' % (self.tagName, self.tagType)

	@classmethod
	def cleanTag(cls, rawTag):
		tag_class = cls.classifyTag(rawTag)



		if tag_class == cls.NoAttribLeft:
			return rawTag.replace('<', '').replace('>', '')

		elif tag_class in [cls.AttribLeft, cls.SelfClosing]:
			return re.findall(r'<\w+? ', rawTag)[0].rstrip().replace('<', '')

		elif tag_class == cls.WordRight:
			return rawTag.replace('/', '').replace('>', '')

		elif tag_class == cls.BlankRight:
			return ''

		else: raise ValueError('bad class')



	@classmethod
	def classifyTag(cls, tagString):
		"""
		if re.match(endof_left_pattern, tagString):
			return cls.EndOfLeft
		elif re.match(open_left_pattern, tagString):
			return cls.OpenLeft
		elif re.match(closed_left_pattern, tagString):
			return cls.ClosedLeft
		"""
		if re.match(self_closing_pattern, tagString):
			return cls.SelfClosing

		elif re.match(noattrib_left_pattern, tagString):
			return cls.NoAttribLeft

		elif re.match(attrib_left_pattern, tagString):
			return cls.AttribLeft

		elif re.match(word_right_pattern, tagString):
			return cls.WordRight

		elif re.match(blank_right_pattern, tagString):
			return cls.BlankRight

		else: raise ValueError('tag does not match any regex')



class ParseDepth():
	def __init__(self, rawTag, htmlString, charIndex, leftTags, rightTags, depth=0):
		self.depth = depth
		self.tag = TagType(rawTag)
		self.html = htmlString
		self.index = charIndex
		self.leftTags = self.classifyTagList(leftTags)
		self.rightTags = self.classifyTagList(rightTags)



	@staticmethod
	def classifyTagList(tagLs):
		return map(TagType, tagLs)


	def isInnerHtml(self):
		print self.leftTags
		print self.rightTags

		return ( 
			typeof(self.rightTags[0]) == TagType.BlankRight
			and self.leftTags[-1].tagName == self.rightTags[0].tagName
			)







class InnerHtmlParser():

	#prefix_reg = re.compile(closed_left_pattern + r'|' + open_left_pattern)
	#postfix_reg = re.compile(right_pattern)

	"""
	tag_reg = re.compile(endof_left_pattern + '|' + 
						closed_left_pattern + '|' + 
						open_left_pattern + '|' + 
						right_pattern)
	# ORDER MATTERS HERE
	"""

	tag_reg = re.compile(self_closing_pattern + '|' +
						 noattrib_left_pattern + '|' +
						 attrib_left_pattern + '|' +
						 right_pattern)

	def __init__(self, htmlString):
		self.html = htmlString



	@staticmethod
	def isTag(text):
		# not true, can have fringe cases with '<' or '>' literal
		return re.search(r'<%s |<%s>|/%s>' % text, text)

	def depthAtIndex(self, strIndex):

		leftTags = self.__class__.tag_reg.findall(self.html[:strIndex + 1])
		rightTags = self.__class__.tag_reg.findall(self.html[strIndex:])

		if not leftTags or not rightTags: raise ValueError('index not within html')

		innermostTag = leftTags[-1]

		return ParseDepth( 
							innermostTag, 
							self.html,
							strIndex,
							leftTags,
							rightTags,
							depth=len(leftTags) - len(rightTags),)

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