# Module used by InstanceGenerator and KernFeatureGenerator

###################################################
### THE VALUES BELOW CAN BE EDITED AS NEEDED ######
###################################################

kKernFeatureFileName = "kern.fea"

kDefaultMinKern = 3 
# Inclusive; this means that pairs which equal this absolute value will 
# NOT be ignored/trimmed. Anything in the below that value will be trimmed.

kDefaultWriteTrimmed = False  
# If 'False', trimmed pairs will not be processed and therefore 
# not be written to the output file.

kDefaultWriteSubtables = True

kLeftTag = ['_LEFT','_1ST', '_L_']
kRightTag = ['_RIGHT','_2ND', '_R_']

kLatinTag = '_LAT'
kGreekTag = '_GRK'
kCyrillicTag = '_CYR'
kArmenianTag = '_AM'
kArabicTag = '_ARA'
kHebrewTag = '_HEB'

kNumberTag = '_NUM'
kFractionTag = '_FRAC'
kExceptionTag = 'EXC_'

kIgnorePairTag = '.cxt'
	
###################################################

__copyright__ = __license__ =  """
Copyright (c) 2006-2014 Adobe Systems Incorporated. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. 
"""

__doc__ = """
WriteKernFeaturesFDK.py v4 - Oct 2015

"""

import os, time, itertools


class WhichApp(object):
	'Testing the environment'
	
	def __init__(self):
		self.inRF = False
		self.inFL = False
		self.inDC = False
		self.appName = "noApp"
		
		if not any((self.inRF, self.inFL, self.inDC)):
			try:
				import mojo.roboFont
				# print 'in Robofont'
				self.inRF = True
				self.appName = 'Robofont'
			except ImportError:
				pass

		if not any((self.inRF, self.inFL, self.inDC)):
			try:
				import flsys
				# print 'In FontLab, dork!'
				self.inFL = True
				self.appName = 'FontLab'
			except ImportError:
				pass

		if not any((self.inRF, self.inFL, self.inDC)):
			try:
				import defcon
				# print 'defcon'
				self.inDC = True
				self.appName = 'Defcon'
			except ImportError:
				pass



class FLKerningData(object):

	def __init__(self, font):
		self.f = font

		self._readFLGroups()
		self._splitFLGroups()

		self.leftKeyGlyphs = self._filterKeyGlyphs(self.leftGroups)
		self.rightKeyGlyphs = self._filterKeyGlyphs(self.rightGroups)

		self._readFLKerning()



	def _isMMfont(self):
		'Checks if the FontLab font is a Multiple Master font.'
		if self.f[0].layers_number > 1:
			return True
		else:
			return False



	def _readFLGroups(self, *args):
		self.groupToKeyglyph = {}
		self.groups = {}
		self.groupOrder = []
		
		flClassStrings = [cString for cString in self.f.classes if cString[0] == '_']
		
		for cString in flClassStrings:

			FLclassName     = cString.split(":")[0]      # FL class name, e.g. _L_LC_LEFT
			OTgroupName     = '@%s' % FLclassName[1:]    # OT group name, e.g. @L_LC_LEFT
			markedGlyphList = cString.split(":")[1].split()
			cleanGlyphList  = [gName.strip("'") for gName in markedGlyphList] # strips out the keyglyph marker

			for gName in markedGlyphList:
				if gName[-1] == "'":  # finds keyglyph
					keyGlyphName = gName.strip("'")  
					break
				else:
					keyGlyphName = markedGlyphList[0]
					print "\tWARNING: Kerning class %s has no explicit key glyph.\n\tUsing first glyph found (%s)." % (cString, keyGlyphName)


			self.groupOrder.append(OTgroupName)
			self.groupToKeyglyph[OTgroupName] = keyGlyphName
			self.groups[OTgroupName] = cleanGlyphList 




	def _splitFLGroups(self):
		'''
		Splits FontLab kerning classes into left and right sides; based on the 
		class name. Both sides are assigned to classes without an explicit side-flag.'
		'''

		leftTagsList = ['_LEFT','_1ST', '_L_']
		rightTagsList = ['_RIGHT','_2ND', '_R_']

		self.leftGroups = []
		self.rightGroups = []

		for groupName in self.groups:
			if any([tag in groupName for tag in leftTagsList]):
				self.leftGroups.append(groupName)
			elif any([tag in groupName for tag in rightTagsList]):
				self.rightGroups.append(groupName)
			else:
				self.leftGroups.append(groupName)
				self.rightGroups.append(groupName)



	def _filterKeyGlyphs(self, groupList):
		'Returns a dictionary {keyGlyph: FLClassName} for a given list of classNames.'

		filteredKeyGlyphs = {}

		for groupName in groupList:
			keyGlyphName = self.groupToKeyglyph[groupName]
			filteredKeyGlyphs[keyGlyphName] = groupName

		return filteredKeyGlyphs



	def _readFLKerning(self):
		'Reads FontLab kerning and converts it into a UFO-style kerning dict.'

		self.kerning = {}
		glyphs = self.f.glyphs

		for gIndexLeft, glyphLeft in enumerate(glyphs):
			gNameLeft = glyphLeft.name
			flKerningArray = glyphs[gIndexLeft].kerning
			
			for flKerningPair in flKerningArray:
				gIndexRight = flKerningPair.key
				gNameRight = glyphs[gIndexRight].name

				if self._isMMfont():
					kernValue = '<%s>' % ' '.join( map( str, flKerningPair.values ) )  
					# gl.kerning[p].values is an array holding kern values for each master
				else:
					kernValue = int(flKerningPair.value)
				
				pair = self.leftKeyGlyphs.get(gNameLeft, gNameLeft), self.rightKeyGlyphs.get(gNameRight, gNameRight)
				self.kerning[pair] = kernValue





class KernDataClass(object):

	def __init__(self, font, folderPath, minKern=kDefaultMinKern, writeTrimmed=kDefaultWriteTrimmed, writeSubtables=kDefaultWriteSubtables, fileName=kKernFeatureFileName):
		self.header = ['# Created: %s' % time.ctime()]
		self.fileName = fileName

		appTest = WhichApp()
		self.inRF = appTest.inRF
		self.inFL = appTest.inFL
		self.inDC = appTest.inDC
		self.appName = appTest.appName

		self.f = font
		self.MM = False

		self.folder = folderPath
		self.minKern = minKern
		self.writeTrimmed = writeTrimmed
		self.writeSubtables = writeSubtables

		self.kerning = {}
		self.groups = {}

		self.totalKernPairs = 0
		self.trimmedPairs = 0
		self.processedPairs = 0
		self.notProcessed = 0
		
		# kerning lists for pairs only
		self.group_group = []
		self.glyph_glyph = []
		self.glyph_group = []

		# kerning subtables containing pair-value combinations
		self.glyph_glyph_dict = {}
		self.glyph_glyph_exceptions_dict = {}
		self.glyph_group_dict = {}
		self.glyph_group_exceptions_dict = {}
		self.group_glyph_exceptions_dict = {}
		self.group_group_dict = {}		
		self.predefined_exceptions_dict = {}
		
		self.RTLglyph_glyph_dict = {}
		self.RTLglyph_glyph_exceptions_dict = {}
		self.RTLglyph_group_dict = {}
		self.RTLglyph_group_exceptions_dict = {}
		self.RTLgroup_glyph_exceptions_dict = {}
		self.RTLgroup_group_dict = {}		
		self.RTLpredefined_exceptions_dict = {}
		
		self.grouped_right = []
		self.grouped_left = []
		self.output = []
		
		self.subtbBreak = '\nsubtable;'
		self.lkupRTLopen = '\n\nlookup RTL_kerning {\nlookupflag RightToLeft IgnoreMarks;\n'
		self.lkupRTLclose = '\n\n} RTL_kerning;\n'
	

		if self.inFL: 
			self.header.append('# PS Name: %s' % self.f.font_name)
			# self.isMMfont(self.f) # sets self.MM to True or False
			flK = FLKerningData(self.f)
			self.MM = flK._isMMfont
			self.groups = flK.groups
			self.groupOrder = flK.groupOrder
			self.kerning = flK.kerning

			self.analyzeGroups()

			# if not self.MM:
			# 	self.header.append('# MM Inst: %s' % self.f.menu_name)

		else:
			self.header.append('# PS Name: %s' % self.f.info.postscriptFontName)
			self.header.append('# MM Inst: %s' % self.f.info.styleMapFamilyName)

			groupsUsedInKerning = self.findGroupsUsedInKerning()
			self.groups.update(groupsUsedInKerning)
			self.groupOrder = sorted(self.groups.keys())
			# self.groupOrder.sort(key=lambda x: (x.split('_')[1], len(x)))

			self.analyzeGroups()
			self.kerning = self.f.kerning


		self.header.append('# MinKern: +/- %s inclusive' % self.minKern)
		self.header.append('# exported from %s' % self.appName)


		self.totalKernPairs = len(self.kerning)
		if not len(self.kerning):
			print "\tERROR: The font has no kerning!"
			return

		
		self.processKerningPairs()
		self.findExceptions()
		self.makeOutput()
		self.sanityCheck()
		self.writeDataToFile()


	def findGroupsUsedInKerning(self):
		'''
		Finds all groups used in kerning, and filters all other groups.
		(e.g. MetricsMachine reference groups). 
		This also means that any zero-length group is thrown out since
		it will likely not be used in a kerning pair.
		'''
		kerningGroupDict = {}
		for (first, second), value in self.f.kerning.items():
			if self.isGroup(first):
				kerningGroupDict.setdefault(first, self.f.groups[first])
			if self.isGroup(second):
				kerningGroupDict.setdefault(second, self.f.groups[second])
		return kerningGroupDict


	def isGroup(self, name):
		'Checks for the first character of a group name. Returns True if it is "@" (OT KerningClass).'
		if name[0] == '@':
			return True
		else:
			return False


	def explode(self, leftClass, rightClass):
		'Returns a list of tuples, containing all possible combinations of elements in both input lists.'
		return list(itertools.product(leftClass, rightClass))


	def checkGroupForTag(self, tag, groupName):
		'Checks if a tag (e.g. _CYR, _EXC, _LAT) exists in a group name (e.g. @A_LC_LEFT_LAT)'
		if tag in groupName:
			return True
		else:
			return False


	def returnGroupTag(self, groupName):
		'Returns group tag (e.g. _CYR, _EXC, _LAT) for a given group name (e.g. @A_LC_LEFT_LAT)'
		tags = [kLatinTag, kGreekTag, kCyrillicTag, kArmenianTag, kArabicTag, kHebrewTag, kNumberTag, kFractionTag, kExceptionTag]
		foundTag = None
		
		for tag in tags:
			if self.checkGroupForTag(tag, groupName):
				foundTag = tag
				break
		return foundTag
				

	def checkPairForTag(self, tag, pair):
		'Checks if a tag (e.g. _ARA, _EXC, _LAT) exists in one of both sides of a kerning pair (e.g. arJeh @ALEF_2ND_ARA)'
		left = pair[0]
		right = pair[1]

		if tag in left:
			return True
		elif tag in right:
			return True
		else:
			return False

			
	def checkForRTL(self, pair):
		'Checks if a given kerning pair is RTL. (Must involve a class on at least one side.)'
		RTLkerningTagsList = [kArabicTag , kHebrewTag]
		isRTLpair = False
		for tag in RTLkerningTagsList:
			if self.checkPairForTag(tag, pair):
				isRTLpair = True
				break
		return isRTLpair



	def dict2pos(self, dictionary, min=0, enum=False, RTL=False):
		'''
		Turns a dictionary to a list of kerning pairs. In a single master font, the function 
		can filter kerning pairs whose absolute value does not exceed a given threshold.
		'''
		data = []

		trimmed = 0

		for pair in dictionary:

			if RTL: 
				kernValue = int(dictionary[pair].split()[2])
				valueString = '<%s 0 %s 0>' % (kernValue, kernValue)
			else: 
				kernValue = dictionary[pair]
				valueString = kernValue

			string =  'pos %s %s;' % (' '.join(pair), valueString) 
			enumstring = 'enum %s' % string

			if self.MM: # no filtering happening in MM.
				data.append(string)

			elif enum:
				data.append(enumstring)
				
			else:
				if abs(kernValue) < min:
					if self.writeTrimmed:
						data.append('# %s' % string)
					trimmed += 1
					
				else:
					data.append(string)

		self.trimmedPairs += trimmed
		data.sort()

		return '\n'.join(data)
	
	

	def analyzeGroups(self):
		'Uses self.groups for analysis and splitting.'
		if not len(self.groups):
			print "\tWARNING: The font has no kerning classes! Trimming switched off."
			# If there are no kerning classes present, there is no way to distinguish between
			# low-value pairs that just result from interpolation; and exception pairs. 
			# Consequently, trimming is switched off here.
			self.minKern = 0
			
		else:
			self.leftClasses, self.rightClasses = self.splitClasses(kLeftTag, kRightTag)

			# Lists of all glyphs that belong to kerning classes.
			for i in self.leftClasses:
				self.grouped_left.extend(self.groups[i])
			for i in self.rightClasses:
				self.grouped_right.extend(self.groups[i])
			


	def splitClasses(self, leftTagsList, rightTagsList):
		'Splits kerning classes into left and right sides; and assigns both sides classes without explicit side-flag.'

		ll = []
		rl = []

		for cl in self.groups:
			if any([tag in cl for tag in leftTagsList]):
				ll.append(cl)
			elif any([tag in cl for tag in rightTagsList]):
				rl.append(cl)
			else:
				ll.append(cl)
				rl.append(cl)
	
		return ll, rl


	def processKerningPairs(self):
		'Sorting the kerning into various buckets.'
		
		print '\tProcessing kerning pairs...'
		
		for (left, right), value in sorted(self.kerning.items()[::-1]):
			pair = (left, right)

			# Skip pairs in which the name of the left glyph contains the ignore tag.
			if kIgnorePairTag in left:
				self.notProcessed += 1
				continue
			
			# Looking for pre-defined exception pairs, and filtering them out.
			if self.checkPairForTag(kExceptionTag, pair):
				self.predefined_exceptions_dict[pair] = self.kerning[pair]
				del self.kerning[pair]
			
			else:
				# Filtering the kerning by type.
				if self.isGroup(left):
					self.group_group.append((left, right))

				else:
					if self.isGroup(right):
						self.glyph_group.append((left, right))
					else:
						self.glyph_glyph.append((left, right))

		
		# Quick sanity check
		if len(self.glyph_group) + len(self.glyph_glyph) + len(self.group_group) != len(self.kerning)-self.notProcessed: 
			print 'Something went wrong: kerning lists do not match the amount of kerning pairs present in the font.'
				
				

	def findExceptions(self):
		'Process lists (glyph_group, group_group etc.) created above to find out which pairs are exceptions, and which are just normal pairs'
		
		# glyph to group pairs:
		# ---------------------

		for (g, gr) in self.glyph_group:
			isRTLpair = self.checkForRTL((g, gr))
			group = self.groups[gr]
			if g in self.grouped_left:
				# it is a glyph_to_group exception!
				if isRTLpair:
					self.RTLglyph_group_exceptions_dict[g, gr] = '<%s 0 %s 0>' % (self.kerning[g, gr], self.kerning[g, gr])
				else:
					self.glyph_group_exceptions_dict[g, gr] = self.kerning[g, gr]
			else:
				for i in group:
					pair = (g, i)
					if pair in self.glyph_glyph:
						# that pair is a glyph_to_glyph exception!
						if isRTLpair:
							self.RTLglyph_glyph_exceptions_dict[pair] = '<%s 0 %s 0>' % (self.kerning[pair], self.kerning[pair])
						else:
							self.glyph_glyph_exceptions_dict[pair] = self.kerning[pair]
							
				else:
					# skip the pair if the value is zero
					if self.kerning[g, gr] == 0:
						self.notProcessed += 1
						continue
					
					if isRTLpair:
						self.RTLglyph_group_dict[g, gr] = '<%s 0 %s 0>' % (self.kerning[g, gr], self.kerning[g, gr])
					else:
						self.glyph_group_dict[g, gr] = self.kerning[g, gr]
	

		# group to group pairs:
		# ---------------------

		explodedPairList = []
		RTLexplodedPairList = []
		for (lgr, rgr) in self.group_group:
			isRTLpair = self.checkForRTL((lgr, rgr))
			lgroup = self.groups[lgr]
			
			try:
				rgroup = self.groups[rgr]
			
			except KeyError: # Because group-glyph pairs are included in the group-group bucket, the right-side element of the pair may not be a group
				if rgr in self.grouped_right:
					# it is a group_to_glyph exception!
					if isRTLpair:
						self.RTLgroup_glyph_exceptions_dict[lgr, rgr] = '<%s 0 %s 0>' % (self.kerning[lgr, rgr], self.kerning[lgr, rgr])
					else:
						self.group_glyph_exceptions_dict[lgr, rgr] = self.kerning[lgr, rgr]
					continue # it's an exception, so move on to the next pair
				
				else:
					rgroup = rgr
			
			# skip the pair if the value is zero
			if self.kerning[lgr, rgr] == 0:
				self.notProcessed += 1
				continue
			
			if isRTLpair:
				self.RTLgroup_group_dict[lgr, rgr] = '<%s 0 %s 0>' % (self.kerning[lgr, rgr], self.kerning[lgr, rgr])
				RTLexplodedPairList.extend(self.explode(lgroup, rgroup))
			else:
				self.group_group_dict[lgr, rgr] = self.kerning[lgr, rgr]
				explodedPairList.extend(self.explode(lgroup, rgroup))
				# list of all possible pair combinations for the @class @class kerning pairs of the font.


		exceptionPairs = set.intersection(set(explodedPairList), set(self.glyph_glyph))
		RTLexceptionPairs = set.intersection(set(RTLexplodedPairList), set(self.glyph_glyph))
		# Finds the intersection of the exploded pairs with the glyph_glyph pairs collected above.
		# Those must be exceptions, as they occur twice (once in class-kerning, once as a single pair).
		
		
		for pair in exceptionPairs:
			self.glyph_glyph_exceptions_dict[pair] = self.kerning[pair]

		for pair in RTLexceptionPairs:
			self.RTLglyph_glyph_exceptions_dict[pair] = '<%s 0 %s 0>' %  (self.kerning[pair], self.kerning[pair])
			


		# glyph to glyph pairs (No RTL possible, as of now. RTL pairs are now only identified by their group name, this must be changed one day (to a glyph note, for instance).)
		# ---------------------
		
		for (lg, rg) in self.glyph_glyph:
			pair = (lg, rg)
			if not pair in self.glyph_glyph_exceptions_dict and not pair in self.RTLglyph_glyph_exceptions_dict:
				self.glyph_glyph_dict[pair] = self.kerning[pair]



	def makeOutput(self):
		'Building the output data.'

		# kerning classes:
		# ----------------

		for kernClass in self.groupOrder:
			glyphList = self.groups[kernClass]
			glyphString = ' '.join(glyphList)
			
			if kernClass[0] == '@':
				self.output.append( '%s = [%s];' % (kernClass, glyphString) )


		# ------------------
		# LTR kerning pairs:
		# ------------------

		order = [
		# dictName							# minKern		# comment							# enum
		(self.predefined_exceptions_dict,	0,				'\n# pre-defined exceptions:',		True),
		(self.glyph_glyph_dict,				self.minKern,	'\n# glyph, glyph:',				False),
		(self.glyph_glyph_exceptions_dict,	0,				'\n# glyph, glyph exceptions:',		False),
		(self.glyph_group_exceptions_dict,	0,				'\n# glyph, group exceptions:',		True),
		(self.group_glyph_exceptions_dict,	0,				'\n# group, glyph exceptions:',		True),
		]

		orderExtension = [ 
		# in case no subtables are desired
		(self.glyph_group_dict,				self.minKern,	'\n# glyph, group:',				False),
		(self.group_group_dict,				self.minKern,	'\n# group, group/glyph:',			False)
		]
		

		if not self.writeSubtables:
			order.extend(orderExtension)
			

		for dictName, minKern, comment, enum in order:
			if len(dictName):
				self.processedPairs += len(dictName)
				self.output.append(comment)
				self.output.append(self.dict2pos(dictName, minKern, enum))


		if self.writeSubtables:
			subtablesCreated = 0
			# Keeping track of the number of subtables created;
			# There is no necessity to add a "subtable;" statement before the first subtable.

			# glyph-class subtables
			# ---------------------
			glyph_to_class_subtables = MakeSubtables(self.glyph_group_dict, subtableTrigger='second').subtables
			self.output.append( '\n# glyph, group:' )

			for table in glyph_to_class_subtables:
				if len(table):
					self.processedPairs += len(table)
					subtablesCreated += 1
				
					if subtablesCreated > 1:
						self.output.append( self.subtbBreak )

					self.output.append( self.dict2pos(table, self.minKern) )


			# class-class subtables
			# ---------------------
			class_to_class_subtables = MakeSubtables(self.group_group_dict).subtables
			self.output.append( '\n# group, glyph and group, group:' )

			for table in class_to_class_subtables:
				if len(table):
					self.processedPairs += len(table)
					subtablesCreated += 1
				
					if subtablesCreated > 1:
						self.output.append( self.subtbBreak )

					self.output.append( self.dict2pos(table, self.minKern) )


		# ------------------
		# RTL kerning pairs:
		# ------------------

		RTLorder = [
		# dictName								# minKern		# comment								# enum
		(self.RTLpredefined_exceptions_dict,	0,				'\n# RTL pre-defined exceptions:',		True),
		(self.RTLglyph_glyph_dict,				self.minKern,	'\n# RTL glyph, glyph:',				False),
		(self.RTLglyph_glyph_exceptions_dict,	0,				'\n# RTL glyph, glyph exceptions:',		False),
		(self.RTLglyph_group_exceptions_dict,	0,				'\n# RTL glyph, group exceptions:',		True),
		(self.RTLgroup_glyph_exceptions_dict,	0,				'\n# RTL group, glyph exceptions:',		True),
		]

		RTLorderExtension = [ 
		# in case no subtables are desired
		(self.RTLglyph_group_dict,				self.minKern,	'\n# RTL glyph, group:',				False),
		(self.RTLgroup_group_dict,				self.minKern,	'\n# RTL group, group/glyph:',			False)
		]


		if not self.writeSubtables:
			RTLorder.extend(RTLorderExtension)
		
		# checking if RTL pairs exist
		RTLpairsExist = False
		allRTL = RTLorderExtension + RTLorder
		for dictName, minKern, comment, enum in allRTL:
			if len(dictName):
				RTLpairsExist = True
				break
		
		if RTLpairsExist:
			self.output.append(self.lkupRTLopen)
		
			for dictName, minKern, comment, enum in RTLorder:
				if len(dictName):
					self.processedPairs += len(dictName)
					self.output.append(comment)
					self.output.append( self.dict2pos(dictName, minKern, enum, RTL=True) )
		

		if RTLpairsExist and self.writeSubtables:
			RTLsubtablesCreated = 0

			# RTL glyph-class subtables
			# -------------------------
			RTL_glyph_class_subtables = MakeSubtables(self.RTLglyph_group_dict, subtableTrigger='second', RTL=True).subtables
			self.output.append( '\n# RTL glyph, group:' )

			for table in RTL_glyph_class_subtables:
				if len(table):
					self.processedPairs += len(table)
					RTLsubtablesCreated += 1
				
					if RTLsubtablesCreated > 1:
						self.output.append( self.subtbBreak )
		
					self.output.append( self.dict2pos(table, self.minKern, RTL=True) )


			# RTL class-class subtables
			# -------------------------
			RTL_class_class_subtables = MakeSubtables(self.RTLgroup_group_dict, RTL=True).subtables
			self.output.append( '\n# RTL group, glyph and group, group:' )

			for table in RTL_class_class_subtables:
				if len(table):
					self.processedPairs += len(table)
					RTLsubtablesCreated += 1
				
					if RTLsubtablesCreated > 1:
						# This would happen when both Arabic and Hebrew glyphs are present in one font.
						self.output.append( self.subtbBreak )
					
					self.output.append( self.dict2pos(table, self.minKern, RTL=True) )
					
					
		if RTLpairsExist:
			self.output.append(self.lkupRTLclose)
			

	def sanityCheck(self):
		'Checks if the number of kerning pairs input equals the number of kerning entries output.'
		
		if self.totalKernPairs != self.processedPairs + self.notProcessed: # len(self.allKernPairs) + self.notProcessed - self.numBreaks + self.trimmedPairs:
			print 'Something went wrong...'
			print 'Kerning pairs provided: %s' % self.totalKernPairs
			print 'Kern entries generated: %s' % (self.processedPairs + self.notProcessed)
			print 'Pairs not processed: %s' % (self.totalKernPairs - (self.processedPairs+self.notProcessed))


	def writeDataToFile(self):

		if self.MM:
			kKernFeatureFile = 'mm' + self.fileName
		else:
			kKernFeatureFile = self.fileName

		print '\tSaving %s file...' % kKernFeatureFile
		if self.trimmedPairs > 0:
			print '\tTrimmed pairs: %s' % self.trimmedPairs
		
		filePath = os.path.join(self.folder, kKernFeatureFile)

		outfile = open(filePath, 'w')
		outfile.write('\n'.join(self.header))
		outfile.write('\n\n')
		if len(self.output):
			outfile.write('\n'.join(self.output))
			outfile.write('\n')
		outfile.close()
		if not self.inFL: print '\tOutput file written to %s' % filePath



class MakeSubtables(KernDataClass):
	def __init__(self, kernDict, subtableTrigger='first', RTL=False):
		self.kernDict  = kernDict
		self.RTL       = RTL		# Is the kerning RTL or not?
		self.subtableTrigger = subtableTrigger	# Which side of the pair is triggering the subtable decision? 
									# "first" would be the left side for LTR, right for RTL.
									# "second" would be the right side for LTR, left for RTL.
		
		self.otherPairs_dict = {}
		# Container for any pairs that cannot be assigned to a specific language tag.

		self.LTRtagDict = {
			kLatinTag: {},
			kGreekTag: {},
			kCyrillicTag: {},
			kArmenianTag: {},
			kArabicTag: {},
			kHebrewTag: {},
			kNumberTag: {},
			kFractionTag: {},
			'other': self.otherPairs_dict
		}

		self.RTLtagDict = {
			kArabicTag: {},
			kHebrewTag: {},
			'other': self.otherPairs_dict
		}
		
		self.subtableOrder = [kLatinTag, kGreekTag, kCyrillicTag, kArmenianTag, kArabicTag, kHebrewTag, kNumberTag, kFractionTag, 'other']
		# The order in which subtables are written
		

		'Split class-to-class kerning into subtables.'
		if self.subtableTrigger == 'first':
			# Creates 'traditional' subtables, for class-to-class, and class-to-glyph kerning.
			for pair in self.kernDict.keys()[::-1]: 
				first, second, tagDict = self.analyzePair(pair)
				
				for tag in tagDict:
					if self.checkGroupForTag(tag, first):
						tagDict[tag][pair] = kernDict[pair]
						del self.kernDict[pair]

			for pair in self.kernDict:
				self.otherPairs_dict[pair] = self.kernDict[pair]
			

		if self.subtableTrigger == 'second':

			# Create dictionary of all glyphs on the left side, and the language 
			# tags of classes those glyphs are kerned against (e.g. _LAT, _GRK)
			kernPartnerLanguageTags = {}
			for pair in self.kernDict:
				first, second, tagDict = self.analyzePair(pair)

				if not first in kernPartnerLanguageTags:
					kernPartnerLanguageTags[first] = set([])
				kernPartnerLanguageTags[first].add(self.returnGroupTag(pair[1]))

			for pair in self.kernDict.keys()[::-1]:
				first, second, tagDict = self.analyzePair(pair)
				
				for tag in tagDict:
					if self.checkGroupForTag(tag, second) and len(kernPartnerLanguageTags[first]) == 1:
						# Using the previously created kernPartnerLanguageTags
						# If any glyph is kerned against more than one language system, 
						# it has to go to the 'otherPairs_dict' subtable.
						tagDict[tag][pair] = self.kernDict[pair]
						del self.kernDict[pair]
						
			'This splits the glyph-to-class part into subtables of 1000 left-side items.'
			if len(self.kernDict) < 1000:
				self.otherPairs_dict.update(self.kernDict)

			else:
				# find all the first elements in a kerning pair, since the subtable 
				# split can only happen between chunks of left elements
				firstItems = sorted(set([first for first, second in self.kernDict.keys()]))

				# lambda function to split a list into sublists
				splitList = lambda A, n=100 : [A[i:i+n] for i in range(0, len(A), n)]
				subTableList = splitList(firstItems)

				for chunk in subTableList:
					subtableIndex = subTableList.index(chunk)
					pairlist = sorted([(left, right) for (left, right) in self.kernDict.keys() if left in chunk])

					if subtableIndex == 0:
						# for the first item in the list, no modification 
						# of the subtable list order is necessary.
						for pair in pairlist:
							self.otherPairs_dict[pair] = self.kernDict[pair]
							del self.kernDict[pair]

					else:
						subtableName = 'other_%s' % subtableIndex
						self.LTRtagDict[subtableName] = {}
						self.subtableOrder.append(subtableName)

						for pair in pairlist:
							self.LTRtagDict[subtableName][pair] = self.kernDict[pair]
							del self.kernDict[pair]


		if RTL:
			self.subtables = [self.RTLtagDict[i] for i in self.subtableOrder if i in self.RTLtagDict]
		else:
			self.subtables = [self.LTRtagDict[i] for i in self.subtableOrder]

				
		
	def analyzePair(self, pair):
		if self.RTL:
			first   = pair[0]
			second  = pair[1]
			tagDict = self.RTLtagDict
				
		else:
			first   = pair[0]
			second  = pair[1]
			tagDict = self.LTRtagDict

		return first, second, tagDict
