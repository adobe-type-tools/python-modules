
kDefaultFileName = "kern.fea"

kDefaultMinKern = 3
# Inclusive; this means that pairs which equal this absolute value will
# NOT be ignored/trimmed. Anything in the below that value will be trimmed.

kDefaultWriteTrimmed = False
# If 'False', trimmed pairs will not be processed and therefore
# not be written to the output file.

kDefaultWriteSubtables = True

# dissolveSingleGroups = False
dissolveSingleGroups = True

kLeftTag = ['_LEFT','_1ST', '_L_']
kRightTag = ['_RIGHT','_2ND', '_R_']

kLatinTag = '_LAT'
kGreekTag = '_GRK'
kCyrillicTag = '_CYR'
kArmenianTag = '_AM'

kArabicTag = '_ARA'
kHebrewTag = '_HEB'
kRTLTag = '_RTL'

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

    RTLkerningTagsList = [kArabicTag , kHebrewTag, kRTLTag]

    for tag in RTLkerningTagsList:
        if any([tag in item for item in pair]):
            return True
    return False


def isRTLGroup(groupName):

    '''
    >>> isRTLGroup('a')
    False
    >>> isRTLGroup('@MMK_L_t')
    False
    >>> isRTLGroup('@MMK_L_ARA_T_UC_LEFT')
    True
    >>> isRTLGroup('@MMK_L_HEB_DASH')
    True
    >>> isRTLGroup('@MMK_L_whatever_RTL')
    True

    '''

    RTLkerningTagsList = [kArabicTag , kHebrewTag, kRTLTag]

    for tag in RTLkerningTagsList:
        if any([tag in groupName]):
            return True
    return False



class WhichApp(object):
    '''
    Testing the environment.
    When running from the command line, 'Defcon' is the expected environment
    >>> a = WhichApp()
    >>> a.appName
    'Defcon'
    '''

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

    def __init__(self, font=None):
        self.f = font

        if font:
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


    def _readFLGroups(self):
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
        Splits FontLab kerning classes into left and right sides; based on
        the class name. Both sides are assigned to classes without an explicit
        side-flag.'

        >>> fkd = FLKerningData(None)
        >>> fkd.groups = ['@PE_1ST_HEB', '@E_UC_LEFT_LAT', '@PERCENT', '@DALET_2ND_HEB', '@X_UC_LAT', '@PAREN_RIGHT_HEB', '@ROUND_UC_LEFT_LAT', '@T_LC_RIGHT_LAT']
        >>> fkd._splitFLGroups()
        >>> sorted(fkd.leftGroups)
        ['@E_UC_LEFT_LAT', '@PERCENT', '@PE_1ST_HEB', '@ROUND_UC_LEFT_LAT', '@X_UC_LAT']
        >>> sorted(fkd.rightGroups)
        ['@DALET_2ND_HEB', '@PAREN_RIGHT_HEB', '@PERCENT', '@T_LC_RIGHT_LAT', '@X_UC_LAT']
        '''

        leftTagsList = kLeftTag
        rightTagsList = kRightTag

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
                    kernValue = '<%s>' % ' '.join(map(str, flKerningPair.values))
                    # flKerningPair.values is an array holding kern values for each master
                else:
                    kernValue = int(flKerningPair.value)

                pair = self.leftKeyGlyphs.get(gNameLeft, gNameLeft), self.rightKeyGlyphs.get(gNameRight, gNameRight)
                self.kerning[pair] = kernValue



class KernProcessor(object):
    def __init__(self, groups=None, kerning=None, groupOrder=None):

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

        self.pairs_unprocessed = 0
        self.pairs_processed = 0

        if groups and dissolveSingleGroups:
            self.groups, self.kerning = self._dissolveSingleGroups(groups, kerning)

        else:
            self.groups = groups
            self.kerning = kerning

        if groups:
            self.grouped_left = self._getAllGroupedGlyphs(side='left')
            self.grouped_right = self._getAllGroupedGlyphs(side='right')
            self._findExceptions()

        if self.kerning and len(self.kerning.keys()):
            usedGroups = self._getUsedGroups(self.kerning)
            self.groupOrder = [ groupName for groupName in groupOrder if groupName in usedGroups ]
            self._sanityCheck(self.kerning)


    def _getUsedGroups(self, kerning):
        '''
        Returns all groups which are actually used in kerning.
        '''
        groupList = []
        for left, right in kerning.keys():
            if isGroup(left):
                groupList.append(left)
            if isGroup(right):
                groupList.append(right)
        return sorted(set(groupList))


    def _dissolveSingleGroups(self, groups, kerning):
        '''
        Finds any groups with a single-item glyph list, which are not RTL groups.
        '''
        singleGroups = dict([(groupName, glyphList) for groupName, glyphList in groups.items() if len(glyphList) == 1 and not isRTLGroup(groupName)])
        dissolvedKerning = {}
        for (left, right), value in kerning.items():
            dissolvedLeft = singleGroups.get(left, [left])[0]
            dissolvedRight = singleGroups.get(right, [right])[0]
            dissolvedKerning[(dissolvedLeft, dissolvedRight)] = value

        remainingGroups = dict([(groupName, glyphList) for groupName, glyphList in groups.items() if not groupName in singleGroups])
        return remainingGroups, dissolvedKerning


    def _sanityCheck(self, kerning):
        '''
        Checks if the number of kerning pairs input equals the number of kerning entries output.
        '''
        totalKernPairs = len(kerning.keys())
        if totalKernPairs != self.pairs_processed + self.pairs_unprocessed:
            print 'Something went wrong...'
            print 'Kerning pairs provided: %s' % totalKernPairs
            print 'Kern entries generated: %s' % (self.pairs_processed + self.pairs_unprocessed)
            print 'Pairs not processed: %s' % (totalKernPairs - (self.pairs_processed + self.pairs_unprocessed))


    def _explode(self, leftGlyphList, rightGlyphList):
        '''
        Returns a list of tuples, containing all possible combinations
        of elements in both input lists.

        >>> kp = KernProcessor(None, None, None)
        >>> input1 = ['a', 'b', 'c']
        >>> input2 = ['d', 'e', 'f']
        >>> explosion = kp._explode(input1, input2)
        >>> sorted(explosion)
        [('a', 'd'), ('a', 'e'), ('a', 'f'), ('b', 'd'), ('b', 'e'), ('b', 'f'), ('c', 'd'), ('c', 'e'), ('c', 'f')]
        '''

        return list(itertools.product(leftGlyphList, rightGlyphList))


    def _getAllGroupedGlyphs(self, groupFilterList=None, side=None):
        '''
        Returns lists of glyphs used in groups on left or right side.
        This is used to calculate the subtable size for a given list
        of groups (groupFilterList) used within that subtable.
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
                del self.kerning[pair]
                continue

            # Looking for pre-defined exception pairs, and filtering them out.
            if checkPairForTag(kExceptionTag, pair):
                self.predefined_exceptions[pair] = self.kerning[pair]
                del self.kerning[pair]


        glyph_2_glyph = sorted([pair for pair in self.kerning.keys() if not isGroup(pair[0]) and not isGroup(pair[1])])
        glyph_2_group = sorted([pair for pair in self.kerning.keys() if not isGroup(pair[0]) and isGroup(pair[1])])
        group_2_group = sorted([pair for pair in self.kerning.keys() if isGroup(pair[0])])


        # glyph to group pairs:
        # ---------------------
        for (glyph, group) in glyph_2_group:
            groupList = self.groups[group]
            isRTLpair = isRTL((glyph, group))
            if glyph in self.grouped_left:
                # it is a glyph_to_group exception!
                if isRTLpair:
                    self.RTLglyph_group_exceptions[glyph, group] = self.kerning[glyph, group]
                else:
                    self.glyph_group_exceptions[glyph, group] = self.kerning[glyph, group]
                self.pairs_processed += 1

            else:
                for groupedGlyph in groupList:
                    pair = (glyph, groupedGlyph)
                    if pair in glyph_2_glyph:
                        # that pair is a glyph_to_glyph exception!
                        if isRTLpair:
                            self.RTLglyph_glyph_exceptions[pair] = self.kerning[pair]
                        else:
                            self.glyph_glyph_exceptions[pair] = self.kerning[pair]
                        self.pairs_processed += 1

                else:
                    # skip the pair if the value is zero
                    if self.kerning[glyph, group] == 0:
                        self.pairs_unprocessed += 1
                        continue

                    if isRTLpair:
                        self.RTLglyph_group[glyph, group] = self.kerning[glyph, group]
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
                        self.RTLgroup_glyph_exceptions[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
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
                self.RTLgroup_group[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
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
            self.RTLglyph_glyph_exceptions[pair] = self.kerning[pair]
            self.pairs_processed += 1


        # glyph to glyph pairs:
        # ---------------------
        # No RTL possible here, as of now, since RTL pairs are now only identified
        # by a tag in their group name. This should be changed one day (to a glyph
        # note, for instance).
        for pair in glyph_2_glyph:
            if not pair in self.glyph_glyph_exceptions and not pair in self.RTLglyph_glyph_exceptions:
                self.glyph_glyph[pair] = self.kerning[pair]
                self.pairs_processed += 1



class run(object):

    def __init__(self, font, folderPath, minKern=kDefaultMinKern, writeTrimmed=kDefaultWriteTrimmed, writeSubtables=kDefaultWriteSubtables, outputFileName=kDefaultFileName):

        self.header = ['# Created: %s' % time.ctime()]

        appTest = WhichApp()
        self.inFL = appTest.inFL

        self.f = font
        self.folder = folderPath

        self.minKern = minKern
        self.writeTrimmed = writeTrimmed
        self.writeSubtables = writeSubtables

        self.processedPairs = 0
        self.trimmedPairs = 0


        if self.inFL:
            self.header.append('# PS Name: %s' % self.f.font_name)

            flK = FLKerningData(self.f)
            self.MM = flK._isMMfont()
            self.kerning = flK.kerning
            self.groups = flK.groups
            self.groupOrder = flK.groupOrder

            if self.MM:
                outputFileName = 'mm' + outputFileName
            else:
                self.header.append('# MM Inst: %s' % self.f.menu_name)

        else:
            self.header.append('# PS Name: %s' % self.f.info.postscriptFontName)

            self.MM = False
            self.kerning = self.f.kerning
            self.groups = self.f.groups
            self.groupOrder = sorted(self.groups.keys())


        if not len(self.kerning):
            print "\tERROR: The font has no kerning!"
            return

        self.header.append('# MinKern: +/- %s inclusive' % self.minKern)
        self.header.append('# exported from %s' % appTest.appName)

        outputData = self._makeOutputData()
        self.writeDataToFile(outputData, outputFileName)


    def dict2pos(self, pairValueDict, min=0, enum=False, RTL=False):
        '''
        Turns a dictionary to a list of kerning pairs. In a single master font,
        the function can filter kerning pairs whose absolute value does not
        exceed a given threshold.

        # >>>kD_RTL_MM = {
        # >>>    ('@VAV_1ST_HEB', '@TSADI_HEB'): '<22 15 26 19>',
        # >>>    ('@TSADI_HEB', '@TET_2ND_HEB'): '<4 -17 0 -17>',
        # >>>    ('@QUOTEBASE', '@SHIN_2ND_HEB'): '<-38 -69 0 -50>',
        # >>>    ('@QUOTEBASE', '@KAF_2ND_HEB'): '<-22 0 -9 0>',
        # >>>}

        # >>>kD_MM = {
        # >>>    ('@PERIODCENTERED_CAP', 'V'): '<-10 0>',
        # >>>    ('@QUOTELEFT_LEFT', '@COMMA'): '<-30 -60>',
        # >>>    ('@QUESTIONDOWN_LEFT', '@T_UC_RIGHT_LAT'): '<0 -40>',
        # >>>    ('@PERIOD', 'zeta'): '<-19 -30>',
        # >>>}

        # >>>kD = {
        # >>>    ('@QUOTERIGHT', '@YA_LC_RIGHT_CYR'): -49,
        # >>>    ('@QUOTE', '@T_UC_RIGHT_LAT'): 30,
        # >>>    ('@QUOTERIGHT', '@UPSILON_ACC1_LC_RIGHT_GRK'): 292,
        # >>>    ('@PARENLEFT', '@J_LC_RIGHT_LAT'): -11,

        # >>>kD_RTL = {
        # >>>    ('@QUOTERIGHT', '@YA_LC_RIGHT_CYR'): -49,
        # >>>    ('@QUOTE', '@T_UC_RIGHT_LAT'): 30,
        # >>>    ('@QUOTERIGHT', '@UPSILON_ACC1_LC_RIGHT_GRK'): 292,
        # >>>    ('@PARENLEFT', '@J_LC_RIGHT_LAT'): -11,
        # >>>}


        '''

        data = []
        trimmed = 0
        for pair, value in pairValueDict.items():

            if RTL:
                if self.MM:
                    # kern value is stored in an array (represented as a string),
                    # for instance: '<10 20 30 40>'

                    values = value[1:-1].split()
                    values = ['<{0} 0 {0} 0>'.format(kernValue) for kernValue in values]
                    valueString = '<%s>' % ' '.join(values)
                    # creates an (experimental, but consequent) string like this:
                    # <<10 0 10 0> <20 0 20 0> <30 0 30 0> <40 0 40 0>>

                else:
                    kernValue = value
                    valueString = '<{0} 0 {0} 0>'.format(kernValue)

            else:
                kernValue = value
                valueString = value

            posLine =  'pos %s %s;' % (' '.join(pair), valueString)
            enumLine = 'enum %s' % posLine

            if self.MM: # no filtering happening in MM.
                data.append(posLine)
            elif enum:
                data.append(enumLine)
            else:
                if abs(kernValue) < min:
                    if self.writeTrimmed:
                        data.append('# %s' % posLine)
                    trimmed += 1
                else:
                    data.append(posLine)

        self.trimmedPairs += trimmed
        data.sort()

        return '\n'.join(data)


    def _buildSubtableOutput(self, subtableList, comment, RTL=False):
        subtableOutput = []
        subtableBreak = '\nsubtable;'

        if sum([len(subtable.keys()) for subtable in subtableList]) > 0:
            subtableOutput.append(comment)

        for table in subtableList:
            if len(table):
                self.processedPairs += len(table)

                if RTL:
                    self.RTLsubtablesCreated += 1
                    if self.RTLsubtablesCreated > 1:
                        subtableOutput.append(subtableBreak)

                else:
                    self.subtablesCreated += 1
                    if self.subtablesCreated > 1:
                        subtableOutput.append(subtableBreak)

                subtableOutput.append(self.dict2pos(table, self.minKern, RTL=RTL))

        return subtableOutput


    def _makeOutputData(self):
        'Building the output data.'

        output = []
        kp = KernProcessor(self.groups, self.kerning, self.groupOrder)

        # ----------------
        # kerning groups:
        # ----------------

        for groupName in kp.groupOrder:
            glyphList = kp.groups[groupName]
            output.append('%s = [%s];' % (groupName, ' '.join(glyphList)))


        # ------------------
        # LTR kerning pairs:
        # ------------------

        LTRorder = [
            # dictName                   # minKern       # comment                           # enum
            (kp.predefined_exceptions,   0,              '\n# pre-defined exceptions:',      True),
            (kp.glyph_glyph,             self.minKern,   '\n# glyph, glyph:',                False),
            (kp.glyph_glyph_exceptions,  0,              '\n# glyph, glyph exceptions:',     False),
            (kp.glyph_group_exceptions,  0,              '\n# glyph, group exceptions:',     True),
            (kp.group_glyph_exceptions,  0,              '\n# group, glyph exceptions:',     True),
        ]

        LTRorderExtension = [
            # in case no subtables are desired
            (kp.glyph_group,             self.minKern,   '\n# glyph, group:',                False),
            (kp.group_group,             self.minKern,   '\n# group, group/glyph:',          False),
        ]

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
            LTRorder.extend(LTRorderExtension)
            RTLorder.extend(RTLorderExtension)


        for dictName, minKern, comment, enum in LTRorder:
            if len(dictName):
                self.processedPairs += len(dictName)
                output.append(comment)
                output.append(self.dict2pos(dictName, minKern, enum))


        if self.writeSubtables:
            self.subtablesCreated = 0

            glyph_to_class_subtables = MakeSubtables(kp.glyph_group, subtableTrigger='second').subtables
            output.extend(self._buildSubtableOutput(glyph_to_class_subtables, '\n# glyph, group:'))

            class_to_class_subtables = MakeSubtables(kp.group_group).subtables
            output.extend(self._buildSubtableOutput(class_to_class_subtables, '\n# group, glyph and group, group:'))


        # Checking if RTL pairs exist
        RTLpairsExist = False
        for dictName, minKern, comment, enum in RTLorderExtension + RTLorder:
            if len(dictName.keys()):
                RTLpairsExist = True
                break

        if RTLpairsExist:

            lookupRTLopen = '\n\nlookup RTL_kerning {\nlookupflag RightToLeft IgnoreMarks;\n'
            lookupRTLclose = '\n\n} RTL_kerning;\n'

            output.append(lookupRTLopen)

            for dictName, minKern, comment, enum in RTLorder:
                if len(dictName):
                    self.processedPairs += len(dictName)
                    output.append(comment)
                    output.append(self.dict2pos(dictName, minKern, enum, RTL=True))


            if self.writeSubtables:
                self.RTLsubtablesCreated = 0

                RTL_glyph_class_subtables = MakeSubtables(kp.RTLglyph_group, subtableTrigger='second', RTL=True).subtables
                output.extend(self._buildSubtableOutput(RTL_glyph_class_subtables, '\n# RTL glyph, group:', RTL=True))

                RTL_class_class_subtables = MakeSubtables(kp.RTLgroup_group, RTL=True).subtables
                output.extend(self._buildSubtableOutput(RTL_class_class_subtables, '\n# RTL group, glyph and group, group:', RTL=True))


            output.append(lookupRTLclose)

        return output



    def writeDataToFile(self, data, fileName):

        print '\tSaving %s file...' % fileName

        if self.trimmedPairs > 0:
            print '\tTrimmed pairs: %s' % self.trimmedPairs

        outputPath = os.path.join(self.folder, fileName)

        with open(outputPath, 'w') as outfile:
            outfile.write('\n'.join(self.header))
            outfile.write('\n\n')
            if len(data):
                outfile.write('\n'.join(data))
                outfile.write('\n')

        if not self.inFL:
            print '\tOutput file written to %s' % outputPath



class NewSubtables(object):
    """docstring for NewSubtables"""
    def __init__(self, kerning,):
        # super(NewSubtables, self).__init__()
        self.kerning = kerning



class MakeSubtables(object):
    def __init__(self, kernDict, subtableTrigger='first', RTL=False):
        self.kernDict  = kernDict
        self.RTL       = RTL        # Is the kerning RTL or not?

        # 'subtableTrigger' defines which side of the pair triggers the subtable break decision.
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
        if subtableTrigger == 'first':
            # Creates 'traditional' subtables, for class-to-class, and class-to-glyph kerning.
            for pair in self.kernDict.keys()[::-1]:
                first, second, tagDict = self.identifyPair(pair)

                for tag in tagDict:
                    if self.checkGroupForTag(tag, first):
                        tagDict[tag][pair] = kernDict[pair]
                        del self.kernDict[pair]

            for pair in self.kernDict:
                self.otherPairs_dict[pair] = self.kernDict[pair]


        if subtableTrigger == 'second':
            # Create dictionary of all glyphs on the left side, and the language
            # tags of classes those glyphs are kerned against (e.g. _LAT, _GRK)
            kernPartnerLanguageTags = {}
            for pair in self.kernDict:
                first, second, tagDict = self.identifyPair(pair)

                if not first in kernPartnerLanguageTags:
                    kernPartnerLanguageTags[first] = set([])
                kernPartnerLanguageTags[first].add(self.returnGroupTag(pair[1]))

            for pair in self.kernDict.keys()[::-1]:
                first, second, tagDict = self.identifyPair(pair)

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
                        # of the subtable list LTRorder is necessary.
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


    def identifyPair(self, pair):
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
    arguments = sys.argv

    if '-t' in arguments:
        import doctest
        doctest.testmod()

    else:
        import defcon
        fPath = arguments[-1]
        fPath = fPath.rstrip('/')
        f = defcon.Font(fPath)
        # print KernProcessor()
        run(f, os.path.dirname(f.path))
