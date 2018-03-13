#!/usr/bin/python

import os
import time
import pprint
import itertools
import argparse

default_fileName = 'kern.fea'
# The default output filename

default_minKernValue = 3
# Default mimimum kerning value. This value is _inclusive_, which
# means that pairs that equal this absolute value will NOT be
# ignored/trimmed. Anything below that value will be trimmed.

default_subtableSize = 2 ** 14
# The maximum possible subtable size is 2 ** 16 = 65536.
# Since every other GPOS feature counts against that size,
# it needs to be quite a bit smaller.
# 2 ** 14 has been a good value for Source Serif.

option_writeTrimmed = False
# If 'False', trimmed pairs will not be processed and
# therefore not be written to the output file.

option_writeSubtables = False
# Write subtables -- yes or no?

option_dissolveSingleGroups = False
# If 'True', single-element groups are written as glyphs.


group_RTL = 'RTL_KERNING'

tags_left = ['_LEFT', '_1ST', '_L_']
tags_right = ['_RIGHT', '_2ND', '_R_']

tag_ara = '_ARA'
tag_heb = '_HEB'
tag_RTL = '_RTL'
tag_exception = 'EXC_'
tag_ignore = '.cxt'

__doc__ = '''
kernFeatureWriter.py 1.0 - Sept 2016

Rewrite of WriteFeaturesKernFDK.py, which will eventually be replaced by
this module. The main motivation for this were problems with kerning
subtable overflow.

Main improvements of this script compared to WriteFeaturesKernFDK.py:
-   can be called from the command line, with a UFO file as an argument
-   automatic subtable measuring
-   has the ability to dissolve single-glyph groups into glyph-pairs
    (this feature was written for subtable optimization)
-   can identify glyph-to-glyph RTL kerning (requirement: all RTL glyphs
    are part of a catch-all @RTL_KERNING group)

To do:
-   Write proper tests for individual functions.
    Some doctests were written, but not enough for all scenarios
-   Measure the `mark` feature, which also contributes to the size of the
    GPOS table (and therefore indirectly influences kerning overflow).
-   Test kerning integrity, to make sure referenced glyphs actually exist
    (and building binaries doesn't fail).

'''


class WhichApp(object):
    '''
    Testing the environment.
    When running from the command line,
    'Defcon' is the expected environment

    >>> a = WhichApp()
    >>> a.appName
    'Defcon'
    '''

    def __init__(self):
        self.inRF = False
        self.inFL = False
        self.inDC = False
        self.appName = 'noApp'

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

            FLclassName = cString.split(':')[0]  # FL class name, e.g. _L_LC_LEFT
            OTgroupName = '@%s' % FLclassName[1:]  # OT group name, e.g. @L_LC_LEFT
            markedGlyphList = cString.split(':')[1].split()
            cleanGlyphList = [gName.strip("'") for gName in markedGlyphList]  # strips out the keyglyph marker

            for gName in markedGlyphList:
                if gName[-1] == "'":  # finds keyglyph
                    keyGlyphName = gName.strip("'")
                    break
                else:
                    keyGlyphName = markedGlyphList[0]
                    print '\tWARNING: Kerning class %s has no explicit key glyph.\n\tUsing first glyph found (%s).' % (FLclassName, keyGlyphName)

            self.groupOrder.append(OTgroupName)
            self.groupToKeyglyph[OTgroupName] = keyGlyphName
            self.groups[OTgroupName] = cleanGlyphList

    def _splitFLGroups(self):
        '''
        Splits FontLab kerning classes into left and right sides; based on
        the class name. If classes do not have an explicit side-flag, they
        are assigned to both left and right sides.

        >>> fkd = FLKerningData(None)
        >>> fkd.groups = ['@PE_1ST_HEB', '@E_UC_LEFT_LAT', '@PERCENT', '@DALET_2ND_HEB', '@X_UC_LAT', '@PAREN_RIGHT_HEB', '@ROUND_UC_LEFT_LAT', '@T_LC_RIGHT_LAT']
        >>> fkd._splitFLGroups()
        >>> sorted(fkd.leftGroups)
        ['@E_UC_LEFT_LAT', '@PERCENT', '@PE_1ST_HEB', '@ROUND_UC_LEFT_LAT', '@X_UC_LAT']
        >>> sorted(fkd.rightGroups)
        ['@DALET_2ND_HEB', '@PAREN_RIGHT_HEB', '@PERCENT', '@T_LC_RIGHT_LAT', '@X_UC_LAT']
        '''

        leftTagsList = tags_left
        rightTagsList = tags_right

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
        '''
        Reads FontLab kerning and converts it into a UFO-style kerning dict.
        '''

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
    def __init__(
        self,
        groups=None, kerning=None,
        groupOrder=None, option_dissolve=False
    ):

        # kerning dicts containing pair-value combinations
        self.glyph_glyph = {}
        self.glyph_glyph_exceptions = {}
        self.glyph_group = {}
        self.glyph_group_exceptions = {}
        self.group_glyph_exceptions = {}
        self.group_group = {}
        self.predefined_exceptions = {}

        self.rtl_glyph_glyph = {}
        self.rtl_glyph_glyph_exceptions = {}
        self.rtl_glyph_group = {}
        self.rtl_glyph_group_exceptions = {}
        self.rtl_group_glyph_exceptions = {}
        self.rtl_group_group = {}
        self.rtl_predefined_exceptions = {}

        self.pairs_unprocessed = []
        self.pairs_processed = []

        if groups and option_dissolve:
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
            self.groupOrder = [groupName for groupName in groupOrder if groupName in usedGroups]
            self._sanityCheck(self.kerning)

    def _isGroup(self, itemName):
        '''
        Returns True if the first character of a kerning item is "@".

        >>> kp = KernProcessor()
        >>> kp._isGroup('@_A_LEFT')
        True
        >>> kp._isGroup('@someGroupName')
        True
        >>> kp._isGroup('a.ss01')
        False
        '''

        if itemName[0] == '@':
            return True
        else:
            return False

    def _isRTL(self, pair):
        '''
        Checks if a given pair is RTL, by looking for a RTL-specific group
        tag. Also using the hard-coded list of RTL glyphs.

        >>> kp = KernProcessor({},{},[])
        >>> kp._isRTL(('a', 'c'))
        False
        >>> kp._isRTL(('@MMK_L_t', '@MMK_R_sups_round'))
        False
        >>> kp._isRTL(('x', '@MMK_R_ARA_alef'))
        True
        >>> kp._isRTL(('@MMK_L_ARA_T_UC_LEFT', '@MMK_R_LAT_YSTROKE_UC_RIGHT'))
        True
        >>> kp._isRTL(('@MMK_L_CYR_VEBULG_LC_LEFT', '@MMK_R_HEB_ZE_LC_RIGHT'))
        True
        >>> kp._isRTL(('@MMK_L_HEB_DASH', '@MMK_R_HEB_XI_LC_RIGHT'))
        True
        '''

        RTLGlyphs = self.groups.get(group_RTL, [])
        RTLkerningTags = [tag_ara, tag_heb, tag_RTL]

        if set(self.groups.get(pair[0], [pair[0]]) + self.groups.get(pair[1], [pair[1]])) <= set(RTLGlyphs):
            return True

        for tag in RTLkerningTags:
            if any([tag in item for item in pair]):
                return True
        return False

    def _isRTLGroup(self, groupName):

        '''
        >>> kp = KernProcessor()
        >>> kp._isRTLGroup('a')
        False
        >>> kp._isRTLGroup('@MMK_L_t')
        False
        >>> kp._isRTLGroup('@MMK_L_ARA_T_UC_LEFT')
        True
        >>> kp._isRTLGroup('@MMK_L_HEB_DASH')
        True
        >>> kp._isRTLGroup('@MMK_L_whatever_RTL')
        True

        '''
        RTLkerningTags = [tag_ara, tag_heb, tag_RTL]

        for tag in RTLkerningTags:
            if any([tag in groupName]):
                return True
        return False

    def _getUsedGroups(self, kerning):
        '''
        Returns all groups which are actually used in kerning,
        by iterating through the kerning pairs.
        '''
        groupList = []
        for left, right in kerning.keys():
            if self._isGroup(left):
                groupList.append(left)
            if self._isGroup(right):
                groupList.append(right)
        return sorted(set(groupList))

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
            if self._isGroup(left) and left in groupFilterList:
                grouped_left.extend(self.groups.get(left))
            if self._isGroup(right) and right in groupFilterList:
                grouped_right.extend(self.groups.get(right))

        if side == 'left':
            return sorted(set(grouped_left))
        elif side == 'right':
            return sorted(set(grouped_right))
        else:
            return sorted(set(grouped_left)), sorted(set(grouped_right))

    def _dissolveSingleGroups(self, groups, kerning):
        '''
        Find any groups with a single-item glyph list,
        (which are not RTL groups) which can be dissolved
        into single, or group-to-glyph/glyph-to-group pairs.
        The intention is avoiding an overload of the group-group subtable.

        >>> groups = {'@ALEF_1ST_ARA': ['arAlef', 'arAlef.f', 'arAlef.wide', 'arAlef.fwide'], '@MMK_L_SIX_FITTED_NUM': ['six.fitted'], '@MMK_R_FOUR_FITTED_NUM': ['four.fitted'], '@MMK_L_LAT_BSMALL_LC_LEFT': ['Bsmall'], '@MMK_R_LAT_X_UC_RIGHT': ['X', 'Xdieresis', 'Xdotaccent'], '@MMK_L_PERIOD': ['period', 'ellipsis'], '@MMK_R_FOUR_SC_NUM_RIGHT': ['four.sc'], '@MMK_L_CYR_IUKRAN_LC_LEFT': ['i.ukran', 'yi'], '@MMK_R_CYR_HA_LC_RIGHT': ['ha', 'hadescender']}
        >>> kerning = {('@MMK_L_SIX_FITTED_NUM', '@MMK_R_FOUR_FITTED_NUM'): 10, ('@MMK_L_LAT_BSMALL_LC_LEFT', '@MMK_R_LAT_X_UC_RIGHT'): 20, ('@MMK_L_PERIOD', '@MMK_R_FOUR_SC_NUM_RIGHT'): 10, ('@MMK_L_CYR_IUKRAN_LC_LEFT', '@MMK_R_CYR_HA_LC_RIGHT'): 10}
        >>> kp = KernProcessor()
        >>> remaingGroups = kp._dissolveSingleGroups(groups, kerning)[0]
        >>> sorted(remaingGroups.items())
        [('@ALEF_1ST_ARA', ['arAlef', 'arAlef.f', 'arAlef.wide', 'arAlef.fwide']), ('@MMK_L_CYR_IUKRAN_LC_LEFT', ['i.ukran', 'yi']), ('@MMK_L_PERIOD', ['period', 'ellipsis']), ('@MMK_R_CYR_HA_LC_RIGHT', ['ha', 'hadescender']), ('@MMK_R_LAT_X_UC_RIGHT', ['X', 'Xdieresis', 'Xdotaccent'])]

        >>> remainingKerning = kp._dissolveSingleGroups(groups, kerning)[1]
        >>> sorted(remainingKerning.items())
        [(('@MMK_L_CYR_IUKRAN_LC_LEFT', '@MMK_R_CYR_HA_LC_RIGHT'), 10), (('@MMK_L_PERIOD', 'four.sc'), 10), (('Bsmall', '@MMK_R_LAT_X_UC_RIGHT'), 20), (('six.fitted', 'four.fitted'), 10)]

        '''
        singleGroups = dict([(groupName, glyphList) for groupName, glyphList in groups.items() if len(glyphList) == 1 and not self._isRTLGroup(groupName)])
        if singleGroups:
            dissolvedKerning = {}
            for (left, right), value in kerning.items():
                dissolvedLeft = singleGroups.get(left, [left])[0]
                dissolvedRight = singleGroups.get(right, [right])[0]
                dissolvedKerning[(dissolvedLeft, dissolvedRight)] = value

            remainingGroups = dict([(groupName, glyphList) for groupName, glyphList in groups.items() if groupName not in singleGroups])
            return remainingGroups, dissolvedKerning

        else:
            return groups, kerning

    def _sanityCheck(self, kerning):
        '''
        Checks if the number of kerning pairs input
        equals the number of kerning entries output.
        '''
        totalKernPairs = len(self.kerning.keys())
        processedPairs = len(self.pairs_processed)
        unprocessedPairs = len(self.pairs_unprocessed)
        if totalKernPairs != processedPairs + unprocessedPairs:
            print 'Something went wrong...'
            print 'Kerning pairs provided: %s' % totalKernPairs
            print 'Kern entries generated: %s' % (processedPairs + unprocessedPairs)
            print 'Pairs not processed: %s' % (totalKernPairs - (processedPairs + unprocessedPairs))

    def _explode(self, leftGlyphList, rightGlyphList):
        '''
        Returns a list of tuples, containing all possible combinations
        of elements in both input lists.

        >>> kp = KernProcessor()
        >>> input1 = ['a', 'b', 'c']
        >>> input2 = ['d', 'e', 'f']
        >>> explosion = kp._explode(input1, input2)
        >>> sorted(explosion)
        [('a', 'd'), ('a', 'e'), ('a', 'f'), ('b', 'd'), ('b', 'e'), ('b', 'f'), ('c', 'd'), ('c', 'e'), ('c', 'f')]
        '''

        return list(itertools.product(leftGlyphList, rightGlyphList))

    def _findExceptions(self):
        '''
        Process kerning to find which pairs are exceptions,
        and which are just normal pairs.
        '''

        for pair in self.kerning.keys()[::-1]:

            # Skip pairs in which the name of the
            # left glyph contains the ignore tag.
            if tag_ignore in pair[0]:
                del self.kerning[pair]
                continue

            # Looking for pre-defined exception pairs, and filtering them out.
            if any([tag_exception in item for item in pair]):
                self.predefined_exceptions[pair] = self.kerning[pair]
                del self.kerning[pair]

        glyph_2_glyph = sorted([pair for pair in self.kerning.keys() if not self._isGroup(pair[0]) and not self._isGroup(pair[1])])
        glyph_2_group = sorted([pair for pair in self.kerning.keys() if not self._isGroup(pair[0]) and self._isGroup(pair[1])])
        group_2_group = sorted([pair for pair in self.kerning.keys() if self._isGroup(pair[0])])

        # glyph to group pairs:
        # ---------------------
        for (glyph, group) in glyph_2_group:
            groupList = self.groups[group]
            isRTLpair = self._isRTL((glyph, group))
            if glyph in self.grouped_left:
                # it is a glyph_to_group exception!
                if isRTLpair:
                    self.rtl_glyph_group_exceptions[glyph, group] = self.kerning[glyph, group]
                else:
                    self.glyph_group_exceptions[glyph, group] = self.kerning[glyph, group]
                self.pairs_processed.append((glyph, group))

            else:
                for groupedGlyph in groupList:
                    pair = (glyph, groupedGlyph)
                    if pair in glyph_2_glyph:
                        # that pair is a glyph_to_glyph exception!
                        if isRTLpair:
                            self.rtl_glyph_glyph_exceptions[pair] = self.kerning[pair]
                        else:
                            self.glyph_glyph_exceptions[pair] = self.kerning[pair]
                        self.pairs_processed.append(pair)

                else:
                    # skip the pair if the value is zero
                    if self.kerning[glyph, group] == 0:
                        self.pairs_unprocessed.append((glyph, group))
                        continue

                    if isRTLpair:
                        self.rtl_glyph_group[glyph, group] = self.kerning[glyph, group]
                    else:
                        self.glyph_group[glyph, group] = self.kerning[glyph, group]
                    self.pairs_processed.append((glyph, group))

        # group to group/glyph pairs:
        # ---------------------------
        explodedPairList = []
        RTLexplodedPairList = []

        for (leftGroup, rightGroup) in group_2_group:
            isRTLpair = self._isRTL((leftGroup, rightGroup))
            lgroup_glyphs = self.groups[leftGroup]

            try:
                rgroup_glyphs = self.groups[rightGroup]

            except KeyError:
                # Because group-glyph pairs are included in the group-group
                # bucket, the right-side element of the pair may not be a group.
                if rightGroup in self.grouped_right:
                    # it is a group_to_glyph exception!
                    if isRTLpair:
                        self.rtl_group_glyph_exceptions[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                    else:
                        self.group_glyph_exceptions[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                    self.pairs_processed.append((leftGroup, rightGroup))
                    continue  # It is an exception, so move on to the next pair

                else:
                    rgroup_glyphs = rightGroup

            # skip the pair if the value is zero
            if self.kerning[leftGroup, rightGroup] == 0:
                self.pairs_unprocessed.append((leftGroup, rightGroup))
                continue

            if isRTLpair:
                self.rtl_group_group[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                RTLexplodedPairList.extend(self._explode(lgroup_glyphs, rgroup_glyphs))
            else:
                self.group_group[leftGroup, rightGroup] = self.kerning[leftGroup, rightGroup]
                explodedPairList.extend(self._explode(lgroup_glyphs, rgroup_glyphs))
                # list of all possible pair combinations for the @class @class kerning pairs of the font.
            self.pairs_processed.append((leftGroup, rightGroup))

        self.exceptionPairs = set(explodedPairList) & set(glyph_2_glyph)
        self.RTLexceptionPairs = set(RTLexplodedPairList) & set(glyph_2_glyph)
        # Finds the intersection of the exploded pairs with the glyph_2_glyph pairs collected above.
        # Those must be exceptions, as they occur twice (once in class-kerning, once as a single pair).

        for pair in self.exceptionPairs:
            self.glyph_glyph_exceptions[pair] = self.kerning[pair]
            self.pairs_processed.append(pair)

        for pair in self.RTLexceptionPairs:
            self.rtl_glyph_glyph_exceptions[pair] = self.kerning[pair]
            self.pairs_processed.append(pair)

        # glyph to glyph pairs:
        # ---------------------
        # RTL glyph-to-glyph pairs can only be identified if its glyphs are
        # in the @RTL_KERNING group.

        for pair in glyph_2_glyph:
            if pair not in self.glyph_glyph_exceptions and pair not in self.rtl_glyph_glyph_exceptions:
                if self._isRTL(pair):
                    self.rtl_glyph_glyph[pair] = self.kerning[pair]
                else:
                    self.glyph_glyph[pair] = self.kerning[pair]
                self.pairs_processed.append(pair)


class MakeMeasuredSubtables(object):

    def __init__(
        self, kernDict, kerning, groups,
        maxSubtableSize=default_subtableSize
    ):

        self.kernDict = kernDict
        self.subtables = []
        self.numberOfKernedGlyphs = self._getNumberOfKernedGlyphs(kerning, groups)

        coverageTableSize = 2 + (2 * self.numberOfKernedGlyphs)
        # maxSubtableSize = 2 ** 14

        print 'coverage table size:', coverageTableSize
        print '  max subtable size:', maxSubtableSize
        # If Extension is not used, coverage and class subtables are
        # pushed to very end of GPOS block.
        #
        # Order is: script list, lookup list, feature list, then
        # table that contains lookups.

        # GPOS table size
        # All GPOS lookups need to be considered
        # Look up size of all GPOS lookups

        measuredSubtables = []
        leftItems = sorted(set([left for left, right in self.kernDict.keys()]))

        groupedGlyphsLeft = set([])
        groupedGlyphsRight = set([])
        usedGroupsLeft = set([])
        usedGroupsRight = set([])

        subtable = []

        for item in leftItems:
            itemPair = [pair for pair in self.kernDict.keys() if pair[0] == item]

            for left, right in itemPair:
                groupedGlyphsLeft.update(groups.get(left, [left]))
                groupedGlyphsRight.update(groups.get(right, [right]))
                usedGroupsLeft.add(left)
                usedGroupsRight.add(right)

                leftClassSize = 6 + (2 * len(groupedGlyphsLeft))
                rightClassSize = 6 + (2 * len(groupedGlyphsRight))
                subtableMetadataSize = coverageTableSize + leftClassSize + rightClassSize
                subtableSize = 16 + len(usedGroupsLeft) * len(usedGroupsRight) * 2

            if subtableMetadataSize + subtableSize < maxSubtableSize:
                subtable.append(item)

            else:
                # print subtableMetadataSize + subtableSize
                measuredSubtables.append(subtable)

                subtable = []
                subtable.append(item)
                groupedGlyphsLeft = set([])
                groupedGlyphsRight = set([])
                usedGroupsLeft = set([])
                usedGroupsRight = set([])

        # Last subtable:
        if len(subtable):
            measuredSubtables.append(subtable)

        for leftItemList in measuredSubtables:
            stDict = {}
            for leftItem in leftItemList:
                for pair in [pair for pair in self.kernDict.keys() if pair[0] == leftItem]:
                    stDict[pair] = kerning.get(pair)
            self.subtables.append(stDict)

    def _getNumberOfKernedGlyphs(self, kerning, groups):
        leftList = []
        rightList = []
        for left, right in kerning.keys():
            leftList.extend(groups.get(left, [left]))
            rightList.extend(groups.get(right, [right]))

        # This previous approach counts every glyph only once,
        # which I think might be wrong:
        # Coverage table includes left side glyphs only.
        # Could measure only left side in order to get size of coverage table.
        allKernedGlyphs = set(leftList) | set(rightList)
        return len(allKernedGlyphs)
        # (Assume that a glyph must be counted twice when kerned
        # on both sides).
        # return len(set(leftList)) + len(set(rightList))

        # every time you get to 48 k add UseExtension keyword
        # mark is a gpos feature too.


class run(object):

    def __init__(
        self, font, folderPath,
        minKern=default_minKernValue,
        writeSubtables=option_writeSubtables,
        outputFileName=default_fileName,
        writeTrimmed=option_writeTrimmed,
        subtableSize=default_subtableSize,
        dissolveGroups=option_dissolveSingleGroups,
    ):
        self.header = ['# Created: %s' % time.ctime()]

        appTest = WhichApp()
        self.inFL = appTest.inFL

        self.f = font
        self.folder = folderPath

        self.minKern = minKern
        self.writeSubtables = writeSubtables
        self.subtableSize = subtableSize
        self.writeTrimmed = writeTrimmed
        self.dissolveGroups = dissolveGroups

        # This does not do anything really. Remove or fix
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
            if self.f.kerningGroupConversionRenameMaps:
                self.kerning, self.groups = self._remapGroupNames(self.f)
            else:
                self.kerning = self.f.kerning
                self.groups = self.f.groups
            self.groupOrder = sorted(self.groups.keys())

        if not self.kerning:
            print '\tERROR: The font has no kerning!'
            return

        self.header.append('# MinKern: +/- %s inclusive' % self.minKern)
        self.header.append('# exported from %s' % appTest.appName)

        outputData = self._makeOutputData()
        if outputData:
            self.writeDataToFile(outputData, outputFileName)

    def _remapGroupNames(self, font):
        '''
        In UFO3 the group names have public prefixes. Remove these by using the
        kerningGroupConversionRenameMaps dictionary.
        '''
        noPrefixToPrefixDict = font.kerningGroupConversionRenameMaps['side1']
        noPrefixToPrefixDict.update(font.kerningGroupConversionRenameMaps['side2'])
        prefixToNoPrefixDict = {v: k for k, v in noPrefixToPrefixDict.items()}

        remappedGroupsDict = {}
        for prefixedGroupName in font.groups.keys():
            if prefixedGroupName in prefixToNoPrefixDict:
                remappedGroupsDict[prefixToNoPrefixDict[prefixedGroupName]] = font.groups[prefixedGroupName]

        remappedKerningDict = {}
        for (first, second), value in font.kerning.items():
            if first in prefixToNoPrefixDict:
                first = prefixToNoPrefixDict[first]
            if second in prefixToNoPrefixDict:
                second = prefixToNoPrefixDict[second]
            remappedKerningDict[(first, second)] = value

        return remappedKerningDict, remappedGroupsDict

    def _dict2pos(self, pairValueDict, min=0, enum=False, RTL=False):
        '''
        Turns a dictionary to a list of kerning pairs. In a single master font,
        the function can filter kerning pairs whose absolute value does not
        exceed a given threshold.
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

            posLine = 'pos %s %s;' % (' '.join(pair), valueString)
            enumLine = 'enum %s' % posLine

            if self.MM:  # no filtering happening in MM.
                if enum:
                    data.append(enumLine)
                else:
                    data.append(posLine)

            else:
                if enum:
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

                subtableOutput.append(
                    self._dict2pos(table, self.minKern, RTL=RTL))
        print '%s subtables created' % self.subtablesCreated
        return subtableOutput

    def _makeOutputData(self):
        'Building the output data.'

        output = []
        kp = KernProcessor(
            self.groups,
            self.kerning,
            self.groupOrder,
            self.dissolveGroups
        )

        # ---------------
        # list of groups:
        # ---------------
        for groupName in kp.groupOrder:
            glyphList = kp.groups[groupName]
            output.append('%s = [%s];' % (groupName, ' '.join(glyphList)))

        # ------------------
        # LTR kerning pairs:
        # ------------------
        LTRorder = [
            # container_dict            # minKern     # comment                       # enum
            (kp.predefined_exceptions,  0,            '\n# pre-defined exceptions:',  True),
            (kp.glyph_glyph,            self.minKern, '\n# glyph, glyph:',            False),
            (kp.glyph_glyph_exceptions, 0,            '\n# glyph, glyph exceptions:', False),
            (kp.glyph_group_exceptions, 0,            '\n# glyph, group exceptions:', True),
            (kp.group_glyph_exceptions, 0,            '\n# group, glyph exceptions:', True),
        ]

        LTRorderExtension = [
            # in case no subtables are desired
            (kp.glyph_group,            self.minKern, '\n# glyph, group:',            False),
            (kp.group_group,            self.minKern, '\n# group, group/glyph:',      False),
        ]

        # ------------------
        # RTL kerning pairs:
        # ------------------
        RTLorder = [
            # container_dict                # minKern     # comment                           # enum
            (kp.rtl_predefined_exceptions,  0,            '\n# RTL pre-defined exceptions:',  True),
            (kp.rtl_glyph_glyph,            self.minKern, '\n# RTL glyph, glyph:',            False),
            (kp.rtl_glyph_glyph_exceptions, 0,            '\n# RTL glyph, glyph exceptions:', False),
            (kp.rtl_glyph_group_exceptions, 0,            '\n# RTL glyph, group exceptions:', True),
            (kp.rtl_group_glyph_exceptions, 0,            '\n# RTL group, glyph exceptions:', True),
        ]

        RTLorderExtension = [
            # in case no subtables are desired
            (kp.rtl_glyph_group,            self.minKern, '\n# RTL glyph, group:',            False),
            (kp.rtl_group_group,            self.minKern, '\n# RTL group, group/glyph:',      False)
        ]

        if not self.writeSubtables:
            LTRorder.extend(LTRorderExtension)
            RTLorder.extend(RTLorderExtension)

        for container_dict, minKern, comment, enum in LTRorder:
            if container_dict:
                output.append(comment)
                output.append(
                    self._dict2pos(container_dict, minKern, enum))
                self.processedPairs += len(container_dict)

        if self.writeSubtables:
            self.subtablesCreated = 0

            glyph_to_class_subtables = MakeMeasuredSubtables(
                kp.glyph_group, kp.kerning, kp.groups,
                self.subtableSize).subtables
            output.extend(self._buildSubtableOutput(
                glyph_to_class_subtables, '\n# glyph, group:'))

            class_to_class_subtables = MakeMeasuredSubtables(
                kp.group_group, kp.kerning, kp.groups,
                self.subtableSize).subtables
            output.extend(self._buildSubtableOutput(
                class_to_class_subtables, '\n# group, glyph and group, group:'))

        # Checking if RTL pairs exist
        rtlPairsExist = False
        for container_dict, minKern, comment, enum in RTLorderExtension + RTLorder:
            if container_dict.keys():
                rtlPairsExist = True
                break

        if rtlPairsExist:

            lookupRTLopen = '\n\nlookup RTL_kerning {\nlookupflag RightToLeft IgnoreMarks;\n'
            lookupRTLclose = '\n\n} RTL_kerning;\n'

            output.append(lookupRTLopen)

            for container_dict, minKern, comment, enum in RTLorder:
                if container_dict:
                    output.append(comment)
                    output.append(
                        self._dict2pos(container_dict, minKern, enum, RTL=True))
                    self.processedPairs += len(container_dict)

            if self.writeSubtables:
                self.RTLsubtablesCreated = 0

                rtl_glyph_class_subtables = MakeMeasuredSubtables(
                    kp.rtl_glyph_group, kp.kerning, kp.groups,
                    self.subtableSize).subtables
                output.extend(self._buildSubtableOutput(
                    rtl_glyph_class_subtables, '\n# RTL glyph, group:', RTL=True))

                rtl_class_class_subtables = MakeMeasuredSubtables(
                    kp.rtl_group_group, kp.kerning, kp.groups,
                    self.subtableSize).subtables
                output.extend(self._buildSubtableOutput(
                    rtl_class_class_subtables, '\n# RTL group, glyph and group, group:', RTL=True))

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
            if data:
                outfile.write('\n'.join(data))
                outfile.write('\n')

        if not self.inFL:
            print '\tOutput file written to %s' % outputPath


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'input_file',
        help='input font file')

    parser.add_argument(
        '-out', metavar='OUTPUT_NAME', action='store',
        default=default_fileName,
        help='change the output file name\n(default: %s)' % default_fileName)

    parser.add_argument(
        '-min',
        action='store', metavar='VALUE',
        default=default_minKernValue, type=int,
        help='minimum kerning value\n(default: %s)' % default_minKernValue)

    parser.add_argument(
        '-sub', '--subtables', action='store_true',
        help='write subtables\n(default: %s)' % option_writeSubtables)

    parser.add_argument(
        '-sts', metavar='VALUE', action='store',
        default=default_subtableSize, type=int,
        help='specify max subtable size\n(default: %s)' % default_subtableSize)

    parser.add_argument(
        '-trm', '--w_trimmed', action='store_true',
        help='write trimmed pairs to fea file (as comments)\n(default: %s)' % option_writeTrimmed)

    parser.add_argument(
        '-dis', '--dissolve', action='store_true',
        help='dissolve single-element groups to glyph names\n(default: %s)' % option_dissolveSingleGroups)

    parser.add_argument(
        '-t', '--test', action='store_true', help='test mode')

    parser.add_argument(
        '-x', action='store_true', help='test args')

    args = parser.parse_args()
    if args.test:
        pprint.pprint(args.__dict__)
        # import doctest
        # doctest.testmod()

    else:
        f_path = os.path.normpath(args.input_file)
        f_dir = os.path.dirname(f_path)
        import defcon
        if os.path.exists(f_path):

            f = defcon.Font(f_path)

            if not hasattr(f, 'kerningGroupConversionRenameMaps'):
                f.kerningGroupConversionRenameMaps = None

            run(f, f_dir,
                minKern=args.min,
                writeSubtables=args.subtables,
                outputFileName=args.out,
                writeTrimmed=args.w_trimmed,
                subtableSize=args.sts,
                dissolveGroups=args.dissolve,
                )
        else:
            print f_path, 'does not exist.'
