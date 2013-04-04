import os
from defcon import Font as defconFont


__license__ =  """
Copyright (c) 2013 Adobe Systems Incorporated. All rights reserved.
 
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.
"""

__copyright__ = __license__

class ClassKerningToUFO(object):
	'''
	Module to write FontLab class-kerning to UFO.
	
	Needs to be called with a FL font object (fl.font), and a prefixOption.
	The prefixOption is used for renaming kerning classes to various UFO-styles.
	
	If the prefixOption is None, class names will be prefixed with to @L_ and @R_ to 
	keep track of their side (in case they need to be converted the opposite way and 
	re-imported to FL).
	
	The prefixOptions are:
	'MM': convert class names to MetricsMachine-readable group names
	'UFO3': convert to UFO3-style class names
	
	usage (one of the three):

	kernExport.ClassKerningToUFO(fl.font)
	kernExport.ClassKerningToUFO(fl.font, prefixOption = 'MM')
	kernExport.ClassKerningToUFO(fl.font, prefixOption = 'UFO3')
		
	'''
	
	def __init__(self, font, prefixOption = None):
		
		self.f = font
		self.destFont = self.getUFO()
		
		self.leftKeyGlyphs     = {}
		self.rightKeyGlyphs    = {}
		self.groups            = {}
		self.kerning           = {}

		self.leftPrefix      = '@L_'
		self.rightPrefix     = '@R_'
		self.MMleftPrefix    = '@MMK_L_'
		self.MMrightPrefix   = '@MMK_R_'
		self.UFO3leftPrefix  = 'public.kern1.'
		self.UFO3rightPrefix = 'public.kern2.'

		if prefixOption == 'MM':
			self.leftPrefix = self.MMleftPrefix
			self.rightPrefix = self.MMrightPrefix

		if prefixOption == 'UFO3':
			self.leftPrefix = self.UFO3leftPrefix
			self.rightPrefix = self.UFO3rightPrefix

		self.run()


	def goodbye(self):
		print 'Unhappy End.'


	def getUFO(self):
		UFOfound = False
		assumedUFO = self.f.file_name.replace('.vfb', '.ufo')
		
		if os.path.exists(assumedUFO):
			print 'UFO found at %s.' % assumedUFO
			foundFont = defconFont(assumedUFO)
			UFOfound = True
			
		else:
			try:
				from robofab.interface.all.dialogs import GetFile
			except ImportError:
				print 'No Robofab installed, this script ends here; also the World!!!'
				self.goodbye()

			userPick = GetFile('Select corresponding UFO file:')
			if not userPick:
				print 'No UFO picked.'
				self.goodbye()

			else:
				if os.path.splitext(userPick)[1].lower() == '.ufo':
					foundFont = defconFont(userPick)
					UFOfound = True
					
		if UFOfound: 
			return foundFont


	def getClass(self, glyphName, side):
		'Replaces a glyph name by its class name, in case it is a key glyph for that side.'
	
		if side == 'left':
			if glyphName in self.leftKeyGlyphs:
				return self.leftKeyGlyphs[glyphName]
			else:
				return glyphName
	
		if side == 'right':
			if glyphName in self.rightKeyGlyphs:
				return self.rightKeyGlyphs[glyphName]
			else:
				return glyphName
	
	
	def readFontKerning(self):
		print 'analyzing kerning ...'
		glyphs = self.f.glyphs
		for gIdx in range(len(glyphs)):
			gName = str(glyphs[gIdx].name)
			gKerning = glyphs[gIdx].kerning
			for gKern in gKerning:
				gNameRightglyph = str(glyphs[gKern.key].name)
				kernValue = int(gKern.value)
				
				pair = self.getClass(gName,'left'), self.getClass(gNameRightglyph,'right')
				self.kerning[pair] = kernValue


	def analyzeKernClasses(self):
		print 'analyzing classes ...'
		classes = {}
		for ci in range(len(self.f.classes)):
			className = self.f.classes[ci]
			if className[0] == '_':
				
				if (self.f.GetClassLeft(ci), self.f.GetClassRight(ci)) == (1,0):
					classes[className] = "LEFT"
				elif (self.f.GetClassLeft(ci), self.f.GetClassRight(ci)) == (0,1):
					classes[className] = "RIGHT"
				elif (self.f.GetClassLeft(ci), self.f.GetClassRight(ci)) == (1,1):
					classes[className] = "BOTH"
				else:
					classes[className] = "NONE"
				
		for c in classes:
			repFound = False
			sep = ":"
			className = c.split(sep)[0]	# FL class name, e.g. _L_LC_LEFT
			# OTgroupName = '@%s' % className[1:] # OT group name, e.g. @L_LC_LEFT
			leftName = '%s%s' % (self.leftPrefix, className[1:])
			rightName = '%s%s' % (self.rightPrefix, className[1:])
			glyphList = c.split(sep)[1].split()
			cleanGlyphList = [i.strip("'") for i in glyphList] # strips out the keyglyph marker

			for g in glyphList:
				if g[-1] == "'":  # finds keyglyph
					rep = g.strip("'")  
					repFound = True
					break
				else:
					rep = glyphList[0]
			if repFound == False: 
				print "\tWARNING: Kerning class %s has no explicit key glyph.\n\tAssuming it is the first glyph found (%s).\n" % (className, glyphList[0])

			if classes[c] == 'LEFT':
				self.leftKeyGlyphs[rep] = leftName
				self.groups[leftName] = cleanGlyphList 
			elif classes[c] == 'RIGHT':
				self.rightKeyGlyphs[rep] = rightName
				self.groups[rightName] = cleanGlyphList 
			elif classes[c] == 'BOTH':
				self.leftKeyGlyphs[rep] = leftName
				self.groups[leftName] = cleanGlyphList 
				self.rightKeyGlyphs[rep] = rightName
				self.groups[rightName] = cleanGlyphList 
			else:
				print "\tWARNING: Kerning class %s is not assigned to any side (No checkbox active). Skipping.\n" % className

	def run(self):
		
		glyphset = [g.name for g in self.f.glyphs]
		
		if not set(glyphset) <= set(self.destFont.keys()):
			# test if glyphs in font are a subset of the UFO; in case a wrong UFO is picked.
			print 'Glyphs in VFB and UFO do not match.'
			self.goodbye()
		
		else:
		
			self.analyzeKernClasses()
			self.readFontKerning()
			
			self.destFont.groups.clear()
			self.destFont.kerning.clear()

			self.destFont.groups.update(self.groups)
			self.destFont.kerning.update(self.kerning)
				
			self.destFont.save()

			print 'done'
	
	
__doc__ = ClassKerningToUFO.__doc__

