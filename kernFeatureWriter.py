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

import os
import sys
import time
import itertools



def isGroup(itemName):
    '''
    Returns True if the first character of a kerning item is "@".

    >>> isGroup('@_A_LEFT')
    True
    >>> isGroup('@someGroupName')
    True
    >>> isGroup('a.ss01')
    False
    '''

    if itemName[0] == '@':
        return True
    else:
        return False



def checkPairForTag(tag, pair):
    '''
    Checks if a tag (e.g. _ARA, _EXC, _LAT) exists in one or 
    both sides of a kerning pair (e.g. arJeh @ALEF_2ND_ARA)

    >>> checkPairForTag('_ARA', ('a', 'c'))
    False
    >>> checkPairForTag('_HEB', ('@MMK_L_t', '@MMK_R_sups_round'))
    False
    >>> checkPairForTag('_LAT', ('@MMK_L_LAT_T_UC_LEFT', '@MMK_R_LAT_YSTROKE_UC_RIGHT'))
    True
    >>> checkPairForTag('_CYR', ('@MMK_L_CYR_VEBULG_LC_LEFT', '@MMK_R_CYR_ZE_LC_RIGHT'))
    True
    >>> checkPairForTag('_GRK', ('@MMK_L_DASH', '@MMK_R_GRK_XI_LC_RIGHT'))
    True
    '''

    if any([tag in item for item in pair]):
        return True
    else:
        return False


def isRTL(pair):

    '''
    >>> isRTL(('a', 'c'))
    False
    >>> isRTL(('@MMK_L_t', '@MMK_R_sups_round'))
    False
    >>> isRTL(('x', '@MMK_R_ARA_alef'))
    True
    >>> isRTL(('@MMK_L_ARA_T_UC_LEFT', '@MMK_R_LAT_YSTROKE_UC_RIGHT'))
    True
    >>> isRTL(('@MMK_L_CYR_VEBULG_LC_LEFT', '@MMK_R_HEB_ZE_LC_RIGHT'))
    True
    >>> isRTL(('@MMK_L_HEB_DASH', '@MMK_R_HEB_XI_LC_RIGHT'))
    True

    '''

    RTLkerningTagsList = [kArabicTag , kHebrewTag]
    for tag in RTLkerningTagsList:
        if any([tag in item for item in pair]):
            return True
    return False



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
                self.inRF = True
                self.appName = 'Robofont'
            except ImportError:
                pass

        if not any((self.inRF, self.inFL, self.inDC)):
            try:
                import flsys
                self.inFL = True
                self.appName = 'FontLab'
            except ImportError:
                pass

        if not any((self.inRF, self.inFL, self.inDC)):
            try:
                import defcon
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
        '''
        Returns a dictionary 
        {keyGlyph: FLClassName} 
        for a given list of group names.
        '''

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



class KernProcessor(object):
    def __init__(self, groups, kerning):
        self.groups = groups
        self.kerning = kerning

        # kerning dicts containing pair-value combinations
        self.glyph_glyph = {}
        self.glyph_glyph_exceptions = {}
        self.glyph_group = {}
        self.glyph_group_exceptions = {}
        self.group_glyph_exceptions = {}
        self.group_group = {}
        self.predefined_exceptions = {}
        
        self.RTLglyph_glyph = {}
        self.RTLglyph_glyph_exceptions = {}
        self.RTLglyph_group = {}
        self.RTLglyph_group_exceptions = {}
        self.RTLgroup_glyph_exceptions = {}
        self.RTLgroup_group = {}
        self.RTLpredefined_exceptions = {}
        
        self.grouped_left = self._getAllGroupedGlyphs(side='left')
        self.grouped_right = self._getAllGroupedGlyphs(side='right')
        
        self.pairs_unprocessed = 0
        self.pairs_processed = 0
        
        self._findExceptions()
        self._sanityCheck()


    def _sanityCheck(self):
        '''
        Checks if the number of kerning pairs input equals the number of kerning entries output.
        '''
        totalKernPairs = len(self.kerning)
        if totalKernPairs != self.pairs_processed + self.pairs_unprocessed:
            print 'Something went wrong...'
            print 'Kerning pairs provided: %s' % totalKernPairs
            print 'Kern entries generated: %s' % (self.pairs_processed + self.pairs_unprocessed)
            print 'Pairs not processed: %s' % (totalKernPairs - (self.pairs_processed + self.pairs_unprocessed))


    def _explode(self, leftGlyphList, rightGlyphList):
        '''
        Returns a list of tuples, containing all possible combinations of elements in both input lists.
        '''
        return list(itertools.product(leftGlyphList, rightGlyphList))


    def _getAllGroupedGlyphs(self, groupFilterList=None, side=None):
        '''
        Returns lists of glyphs used in groups on left or right side.
        This is used to calculate the subtable size for a given list of groups
        (groupFilterList) used within that subtable.
        '''
        grouped_left = []
        grouped_right = []

        if not groupFilterList:
            groupFilterList = self.groups.keys()

        for left, right in self.kerning.keys():
            if isGroup(left) and left in groupFilterList:
                grouped_left.extend(self.groups.get(left))
            if isGroup(right) and right in groupFilterList:
                grouped_right.extend(self.groups.get(right))

        if side == 'left':
            return sorted(set(grouped_left))
        elif side == 'right':
            return sorted(set(grouped_right))
        else:
            return sorted(set(grouped_left)), sorted(set(grouped_right))


    def _findExceptions(self):
        '''
        Process kerning to find which pairs are exceptions,
        and which are just normal pairs.
        '''

        for pair in self.kerning.keys()[::-1]:

            # Skip pairs in which the name of the left glyph contains the ignore tag.
            if kIgnorePairTag in pair[0]:
                self.pairs_unprocessed += 1
                continue
            
            # Looking for pre-defined exception pairs, and filtering them out.
            if checkPairForTag(kExceptionTag, pair):
                self.predefined_exceptions[pair] = self.kerning[pair]
                del self.kerning[pair]


        glyph_2_glyph = sorted([pair for pair in self.kerning.keys() if not isGroup(pair[0]) and not isGroup(pair[1])])
        glyph_2_group = sorted([pair for pair in self.kerning.keys() if not isGroup(pair[0]) and isGroup(pair[1])])
        group_2_group = sorted([pair for pair in self.kerning.keys() if isGroup(pair[0])])

        # print len(self.kerning.keys())
        # print sum([len(glyph_2_glyph), len(glyph_2_group), len(group_2_group)])
        
        # glyph to group pairs:
        # ---------------------

        for (glyph, group) in glyph_2_group:
            groupList = self.groups[group]
            isRTLpair = isRTL((glyph, group))
            if glyph in self.grouped_left:
                # it is a glyph_to_group exception!
                if isRTLpair:
                    self.RTLglyph_group_exceptions[glyph, group] = '<%s 0 %s 0>' % (self.kerning[glyph, group], self.kerning[glyph, group])
                else:
                    self.glyph_group_exceptions[glyph, group] = self.kerning[glyph, group]
                self.pairs_processed += 1

            else:
                for groupedGlyph in groupList:
                    pair = (glyph, groupedGlyph)
                    if pair in glyph_2_glyph:
                        # that pair is a glyph_to_glyph exception!
                        if isRTLpair:
                            self.RTLglyph_glyph_exceptions[pair] = '<%s 0 %s 0>' % (self.kerning[pair], self.kerning[pair])
                        else:
                            self.glyph_glyph_exceptions[pair] = self.kerning[pair]
                        self.pairs_processed += 1
                            
                else:
                    # skip the pair if the value is zero
                    if self.kerning[glyph, group] == 0:
                        self.pairs_unprocessed += 1
                        continue
                    
                    if isRTLpair:
                        self.RTLglyph_group[glyph, group] = '<%s 0 %s 0>' % (self.kerning[glyph, group], self.kerning[glyph, group])
                    else:
                        self.glyph_group[glyph, group] = self.kerning[glyph, group]
                    self.pairs_processed += 1
    
        # group to group pairs:
        # ---------------------

        explodedPairList = []
        RTLexplodedPairList = []

        for (leftGroup, rightGroup) in group_2_group:
            isRTLpair = isRTL((leftGroup, rightGroup))
            lgroup_glyphs = self.groups[leftGroup]
            
            try:
                rgroup_glyphs = self.groups[rightGroup]
            
            except KeyError: 
                # Because group-glyph pairs are included in the group-group 
                # bucket, the right-side element of the pair may not be a group.
                if rightGroup in self.grouped_right:
                    # it is a group_to_glyph exception!
                    if isRTLpair:
                        self.RTLgroup_glyph_exceptions[leftGroup, rightGroup] = '<%s 0 %s 0>' % (self.kerning[leftGroup, rightGroup], self.kerning[leftGroup, rightGroup])
                    else:
                        self.group_glyph_exceptions[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                    self.pairs_processed += 1
                    continue # it's an exception, so move on to the next pair
                
                else:
                    rgroup_glyphs = rightGroup

            
            # skip the pair if the value is zero
            if self.kerning[leftGroup, rightGroup] == 0:
                self.pairs_unprocessed += 1
                continue
            
            if isRTLpair:
                self.RTLgroup_group[leftGroup, rightGroup] = '<%s 0 %s 0>' % (self.kerning[leftGroup, rightGroup], self.kerning[leftGroup, rightGroup])
                RTLexplodedPairList.extend(self._explode(lgroup_glyphs, rgroup_glyphs))
            else:
                self.group_group[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                explodedPairList.extend(self._explode(lgroup_glyphs, rgroup_glyphs))
                # list of all possible pair combinations for the @class @class kerning pairs of the font.
            self.pairs_processed += 1

        self.exceptionPairs = set.intersection(set(explodedPairList), set(glyph_2_glyph))
        self.RTLexceptionPairs = set.intersection(set(RTLexplodedPairList), set(glyph_2_glyph))
        # Finds the intersection of the exploded pairs with the glyph_2_glyph pairs collected above.
        # Those must be exceptions, as they occur twice (once in class-kerning, once as a single pair).
        
        
        for pair in self.exceptionPairs:
            self.glyph_glyph_exceptions[pair] = self.kerning[pair]
            self.pairs_processed += 1

        for pair in self.RTLexceptionPairs:
            self.RTLglyph_glyph_exceptions[pair] = '<%s 0 %s 0>' %  (self.kerning[pair], self.kerning[pair])
            self.pairs_processed += 1
            

        # glyph to glyph pairs:
        # ---------------------
        # (No RTL possible, as of now. Since RTL pairs are now only identified 
        # by their group name, this must be changed one day (to a glyph note, for instance).)
        
        for (leftGlyph, rightGlyph) in glyph_2_glyph:
            pair = (leftGlyph, rightGlyph)
            if not pair in self.glyph_glyph_exceptions and not pair in self.RTLglyph_glyph_exceptions:
                self.glyph_glyph[pair] = self.kerning[pair]
                self.pairs_processed += 1



class run(object):

    def __init__(self, font, folderPath, minKern=kDefaultMinKern, writeTrimmed=kDefaultWriteTrimmed, writeSubtables=kDefaultWriteSubtables, fileName=kKernFeatureFileName):

        self.header = ['# Created: %s' % time.ctime()]
        self.fileName = fileName

        appTest = WhichApp()
        self.inFL = appTest.inFL

        self.f = font
        self.MM = False

        self.folder = folderPath
        self.minKern = minKern
        self.writeTrimmed = writeTrimmed
        self.writeSubtables = writeSubtables
        
        self.processedPairs = 0
        self.trimmedPairs = 0

        self.output = []
        
        self.subtbBreak = '\nsubtable;'
        self.lkupRTLopen = '\n\nlookup RTL_kerning {\nlookupflag RightToLeft IgnoreMarks;\n'
        self.lkupRTLclose = '\n\n} RTL_kerning;\n'
    

        if self.inFL: 
            self.header.append('# PS Name: %s' % self.f.font_name)

            flK = FLKerningData(self.f)
            self.MM = flK._isMMfont
            self.kerning = flK.kerning
            self.allGroups = flK.groups
            self.groups = {}

            for groupName in self.getUsedGroups(self.kerning):
                self.groups[groupName] = self.allGroups[groupName]

            self.groupOrder = [groupName for groupName in flK.groupOrder if groupName in self.groups.keys()] 

            if not self.MM:
              self.header.append('# MM Inst: %s' % self.f.menu_name)

        else:
            self.header.append('# PS Name: %s' % self.f.info.postscriptFontName)
            self.header.append('# MM Inst: %s' % self.f.info.styleMapFamilyName)

            self.kerning = self.f.kerning
            self.allGroups = self.f.groups
            self.groups = {}
            
            for groupName in self.getUsedGroups(self.kerning):
                self.groups[groupName] = self.allGroups[groupName]

            self.groupOrder = sorted(self.groups.keys())
            # self.groupOrder.sort(key=lambda x: (x.split('_')[1], len(x)))


        if not len(self.groups):
            print "\tWARNING: The font has no kerning classes! Trimming switched off."
            # If there are no kerning classes present, there is no way to distinguish between
            # low-value pairs that just result from interpolation; and exception pairs. 
            # Consequently, trimming is switched off here.
            self.minKern = 0
            
        # else:
        #     self.leftClasses, self.rightClasses = self.splitClasses(kLeftTag, kRightTag)


        self.header.append('# MinKern: +/- %s inclusive' % self.minKern)
        self.header.append('# exported from %s' % appTest.appName)

        if not len(self.kerning):
            print "\tERROR: The font has no kerning!"
            return

        self.makeOutput()
        self.writeDataToFile()



    def getUsedGroups(self, kernDict):
        '''
        Returns all groups which are actually used in kerning.
        '''
        groupList = []
        for left, right in kernDict.keys():
            if isGroup(left):
                groupList.append(left)
            if isGroup(right):
                groupList.append(right)
        return sorted(set(groupList))



    def dict2pos(self, pairValueDict, min=0, enum=False, RTL=False):
        '''
        Turns a dictionary to a list of kerning pairs. In a single master font, the function 
        can filter kerning pairs whose absolute value does not exceed a given threshold.
        '''
        data = []
        trimmed = 0

        for pair, value in pairValueDict.items():

            if RTL: 
                kernValue = int(value.split()[2])
                valueString = '<%s 0 %s 0>' % (kernValue, kernValue)
            else:
                kernValue = value
                valueString = value

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
    


    def makeOutput(self):
        'Building the output data.'

        kp = KernProcessor(self.groups, self.kerning)
        print dir(kp)
        print kp.pairs_processed
        print kp.pairs_unprocessed
        # kerning classes:
        # ----------------
        for groupName in self.groupOrder:
            glyphList = self.groups[groupName]
            self.output.append('%s = [%s];' % (groupName, ' '.join(glyphList)))


        # ------------------
        # LTR kerning pairs:
        # ------------------

        order = [
        # dictName                   # minKern       # comment                           # enum
        (kp.predefined_exceptions,   0,              '\n# pre-defined exceptions:',      True),
        (kp.glyph_glyph,             self.minKern,   '\n# glyph, glyph:',                False),
        (kp.glyph_glyph_exceptions,  0,              '\n# glyph, glyph exceptions:',     False),
        (kp.glyph_group_exceptions,  0,              '\n# glyph, group exceptions:',     True),
        (kp.group_glyph_exceptions,  0,              '\n# group, glyph exceptions:',     True),
        ]

        orderExtension = [ 
        # in case no subtables are desired
        (kp.glyph_group,             self.minKern,   '\n# glyph, group:',                False),
        (kp.group_group,             self.minKern,   '\n# group, group/glyph:',          False)
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
            glyph_to_class_subtables = MakeSubtables(kp.glyph_group, subtableTrigger='second').subtables
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
            class_to_class_subtables = MakeSubtables(kp.group_group).subtables
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
        # dictName                       # minKern       # comment                               # enum
        (kp.RTLpredefined_exceptions,    0,              '\n# RTL pre-defined exceptions:',      True),
        (kp.RTLglyph_glyph,              self.minKern,   '\n# RTL glyph, glyph:',                False),
        (kp.RTLglyph_glyph_exceptions,   0,              '\n# RTL glyph, glyph exceptions:',     False),
        (kp.RTLglyph_group_exceptions,   0,              '\n# RTL glyph, group exceptions:',     True),
        (kp.RTLgroup_glyph_exceptions,   0,              '\n# RTL group, glyph exceptions:',     True),
        ]

        RTLorderExtension = [ 
        # in case no subtables are desired
        (kp.RTLglyph_group,              self.minKern,   '\n# RTL glyph, group:',                False),
        (kp.RTLgroup_group,              self.minKern,   '\n# RTL group, group/glyph:',          False)
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
            RTL_glyph_class_subtables = MakeSubtables(self.RTLglyph_group, subtableTrigger='second', RTL=True).subtables
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
            RTL_class_class_subtables = MakeSubtables(self.RTLgroup_group, RTL=True).subtables
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





class MakeSubtables(run):
    def __init__(self, kernDict, subtableTrigger='first', RTL=False):
        self.kernDict  = kernDict
        self.RTL       = RTL        # Is the kerning RTL or not?
        self.subtableTrigger = subtableTrigger  # Which side of the pair is triggering the subtable decision? 
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
        
        self.subtableOrder = [
            kLatinTag, 
            kGreekTag, 
            kCyrillicTag, 
            kArmenianTag, 
            kArabicTag, 
            kHebrewTag, 
            kNumberTag, 
            kFractionTag, 
            'other',
        ]
        

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


if __name__ == '__main__':
    import defcon
    fPath = sys.argv[-1]
    fPath = fPath.rstrip('/')
    f = defcon.Font(fPath)
    # print dir(f)
    # print os.path.dirname(f.path)
    run(f, os.path.dirname(f.path))
    # x = KernProcessor(f.groups, f.kerning)
    # print dir(x)
    # print x
    # x.findExceptions()
