#!/usr/bin/env python3

'''
Kern Feature Writer for the FDK font production workflow.

Optional functionality of this tool includes:
-   subtable measuring and automatic insertion of subtable breaks
-   dissolving of single-element groups into glyph pairs
    (helping with subtable optimization)
-   identify glyph-to-glyph RTL kerning
    (requirement: all RTL glyphs are part of a RTL-specific kerning group,
    or are members of the catch-all @RTL_KERNING group)

'''

import argparse
import itertools
import os
import time


group_rtl = 'RTL_KERNING'

tags_left = ['_LEFT', '_1ST', '_L_']
tags_right = ['_RIGHT', '_2ND', '_R_']

tag_ara = '_ARA'
tag_heb = '_HEB'
tag_rtl = '_RTL'
tag_exception = 'EXC_'
tag_ignore = '.cxt'


class Defaults(object):
    """
    default values
    These can later be overridden by argparse.
    """

    def __init__(self):

        # The default output filename
        self.output_name = 'kern.fea'

        # Default mimimum kerning value. This value is _inclusive_, which
        # means that pairs that equal this absolute value will NOT be
        # ignored/trimmed. Anything in range of +/- value will be trimmed.
        self.min_value = 3

        # The maximum possible subtable size is 2 ** 16 = 65536.
        # Since every other GPOS feature counts against that size, the
        # subtable size chosen needs to be quite a bit smaller.
        # 2 ** 14 has been a good value for Source Serif
        # (but failed for master_2, where 2 ** 13 was used)
        self.subtable_size = 2 ** 13

        # If 'False', trimmed pairs will not be processed and therefore
        # not be written to the output file.
        self.write_trimmed_pairs = False

        # Write subtables -- yes or no?
        self.write_subtables = False

        # Write time stamp in .fea file header?
        self.write_timestamp = False

        # Write single-element groups as glyphs?
        # (This has no influence on the output kerning data, but helps with
        # balancing subtables, and potentially makes the number of kerning
        # pairs involving groups a bit smaller).
        self.dissolve_single = False


class WhichApp(object):
    '''
    Test the environment.
    When running from the command line,
    'Defcon' is the expected environment
    '''

    def __init__(self):
        self.inRF = False
        self.inDC = False
        self.appName = 'noApp'

        if not any((self.inRF, self.inDC)):
            try:
                import mojo.roboFont
                self.inRF = True
                self.appName = 'Robofont'
            except ImportError:
                pass

        if not any((self.inRF, self.inDC)):
            try:
                import defcon
                self.inDC = True
                self.appName = 'Defcon'
            except ImportError:
                pass


class KernProcessor(object):
    def __init__(
        self,
        groups=None, kerning=None,
        option_dissolve=False
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

        if kerning:
            sanitized_kerning = self.sanitize_kerning(groups, kerning)
            used_groups = self._get_used_groups(groups, sanitized_kerning)
            self.reference_groups = self._get_reference_groups(groups)

            if used_groups and option_dissolve:
                dissolved_groups, dissolved_kerning = self._dissolve_single_groups(
                    used_groups, sanitized_kerning)
                self.groups = self._remap_groups(dissolved_groups)
                self.kerning = self._remap_kerning(dissolved_kerning)

            else:
                self.groups = self._remap_groups(used_groups)
                self.kerning = self._remap_kerning(sanitized_kerning)

            self.grouped_left = self._get_grouped_glyphs(left=True)
            self.grouped_right = self._get_grouped_glyphs(left=False)
            self.rtl_glyphs = self._get_rtl_glyphs(self.groups)

            self._find_exceptions()

            if self.kerning and len(self.kerning.keys()):
                self.group_order = sorted(
                    [gr_name for gr_name in self.groups])
                self._sanityCheck()

    def sanitize_kerning(self, groups, kerning):
        '''
        Check kerning dict for pairs referencing items that do not exist
        in the groups dict.

        This solution is not ideal since there is another chance for producing
        an invalid kerning pair -- by referencing a glyph name which is not in
        the font. The font object is not present in this class, so a comparison
        would be difficult to achieve. This check is better than nothing for
        the moment, since crashing downstream is avoided.
        '''
        all_pairs = [pair for pair in kerning.keys()]
        all_kerned_items = set([item for pair in all_pairs for item in pair])
        all_kerned_groups = [
            item for item in all_kerned_items if self._is_group(item)]

        bad_groups = set(all_kerned_groups) - set(groups.keys())
        sanitized_kerning = {
            pair: value for
            pair, value in kerning.items() if
            not set(pair).intersection(bad_groups)}

        bad_kerning = sorted([
            pair for pair in kerning.keys() if
            pair not in sanitized_kerning.keys()])

        for pair in bad_kerning:
            print(
                'pair {} {} references non-existent group'.format(*pair))

        return sanitized_kerning

    def _remap_name(self, item_name):
        '''
        Remap a single item from public.kern style to @MMK style (if it is
        a group). Otherwise, just pass it through.
        '''
        if 'public.kern1.' in item_name:
            stripped_name = item_name.replace('public.kern1.', '')
            if stripped_name.startswith('@MMK_L_'):
                # UFO2 files contain the @ in the XML, Defcon reads it as
                # 'public.kernX.@MMK'
                return stripped_name
            else:
                # UFO3 files just contain the public.kern notation
                return item_name.replace('public.kern1.', '@MMK_L_')

        elif 'public.kern2.' in item_name:
            stripped_name = item_name.replace('public.kern2.', '')
            if stripped_name.startswith('@MMK_R_'):
                return stripped_name
            else:
                return item_name.replace('public.kern2.', '@MMK_R_')
        else:
            return item_name

    def _remap_groups(self, groups):
        '''
        Remap groups dictionary to not contain public.kern prefixes.
        '''
        return {self._remap_name(gn): gl for gn, gl in groups.items()}

    def _remap_kerning(self, kerning):
        '''
        Remap kerning dictionary to not contain public.kern prefixes.
        '''
        remapped_kerning = {}
        for (left, right), value in kerning.items():
            remapped_pair = (self._remap_name(left), self._remap_name(right))
            remapped_kerning[remapped_pair] = value

        return remapped_kerning

    def _is_group(self, itemName):
        '''
        Check if an item name implies a group.
        '''

        if itemName[0] == '@':
            return True
        if itemName.split('.')[0] == 'public':
            return True
        return False

    def _is_kerning_group(self, groupName):
        '''
        Check if a group name implies a kerning group.
        '''

        if groupName.startswith('@MMK_'):
            return True
        if groupName.startswith('public.kern'):
            return True
        return False

    def _is_rtl(self, pair):
        '''
        Check if a given pair is RTL, by looking for a RTL-specific group
        tag, or membership in an RTL group
        '''

        rtl_group = self.reference_groups.get(group_rtl, [])
        all_rtl_glyphs = set(rtl_group) | set(self.rtl_glyphs)
        rtl_tags = [tag_ara, tag_heb, tag_rtl]

        if set(pair) & set(all_rtl_glyphs):
            # Any item in the pair is an RTL glyph.
            return True

        for tag in rtl_tags:
            # Group tags indicate presence of RTL item.
            # This will work for any pair including a RTL group.
            if any([tag in item for item in pair]):
                return True
        return False

    def _is_rtl_group(self, groupName):
        '''
        Check if a given group is a RTL group
        '''
        rtl_tags = [tag_ara, tag_heb, tag_rtl]

        if any([tag in groupName for tag in rtl_tags]):
            return True
        return False

    def _get_used_groups(self, groups, kerning):
        '''
        Return all groups which are actually used in kerning,
        by iterating through the kerning pairs.
        '''
        used_group_names = []
        for left, right in kerning.keys():
            if self._is_group(left):
                used_group_names.append(left)
            if self._is_group(right):
                used_group_names.append(right)
        used_groups = {
            g_name: groups.get(g_name) for g_name in used_group_names
        }
        return used_groups

    def _get_reference_groups(self, groups):
        reference_group_names = [
            gn for gn in groups if not self._is_kerning_group(gn)]
        reference_groups = {
            gn: groups.get(gn) for gn in reference_group_names}
        return reference_groups

    def _get_rtl_glyphs(self, groups):
        rtl_groups = [
            group for group in groups.keys() if any([
                tag_ara in group,
                tag_heb in group,
                tag_rtl in group,
            ])]
        rtl_glyphs = list(itertools.chain.from_iterable(
            groups.get(rtl_group) for rtl_group in rtl_groups))
        return rtl_glyphs

    def _get_grouped_glyphs(self, left=False):
        '''
        Return lists of glyphs used in groups on left or right side.
        This is used to calculate the subtable size for a given list
        of groups (groupFilterList) used within that subtable.
        '''
        grouped_left = []
        grouped_right = []

        group_names = list(self.groups.keys())

        for left, right in self.kerning.keys():
            if self._is_group(left) and left in group_names:
                grouped_left.extend(self.groups.get(left))
            if self._is_group(right) and right in group_names:
                grouped_right.extend(self.groups.get(right))

        if left is True:
            return sorted(set(grouped_left))
        else:
            return sorted(set(grouped_right))

    def _dissolve_single_groups(self, groups, kerning):
        '''
        Find any (non-RTL) group with a single-item glyph list.
        This group can be dissolved into a single glyph to create more
        glyph-to-glyph pairs. The intention is shifting the load from the
        group-to-group subtable.

        The actual effect of this depends on the group setup.
        '''
        single_groups = dict(
            [(group_name, glyphs) for group_name, glyphs in groups.items() if(
                len(glyphs) == 1 and not self._is_rtl_group(group_name))])
        if single_groups:
            dissolved_kerning = {}
            for (left, right), value in kerning.items():
                dissolvedLeft = single_groups.get(left, [left])[0]
                dissolvedRight = single_groups.get(right, [right])[0]
                dissolved_kerning[(dissolvedLeft, dissolvedRight)] = value

            remaining_groups = dict(
                [(gr_name, glyphs) for gr_name, glyphs in groups.items() if(
                    gr_name not in single_groups)]
            )
            return remaining_groups, dissolved_kerning

        else:
            return groups, kerning

    def _sanityCheck(self):
        '''
        Check if the number of kerning pairs input
        equals the number of kerning entries output.
        '''
        num_pairs_total = len(self.kerning.keys())
        num_pairs_processed = len(self.pairs_processed)
        num_pairs_unprocessed = len(self.pairs_unprocessed)

        if num_pairs_total != num_pairs_processed + num_pairs_unprocessed:
            print('Something went wrong...')
            print('Kerning pairs provided: %s' % num_pairs_total)
            print('Kern entries generated: %s' % (
                num_pairs_processed + num_pairs_unprocessed))
            print('Pairs not processed: %s' % (
                num_pairs_total - (num_pairs_processed + num_pairs_unprocessed)))

    def _explode(self, leftGlyphList, rightGlyphList):
        '''
        Return a list of tuples, containing all possible combinations
        of elements in both input lists.
        '''

        return list(itertools.product(leftGlyphList, rightGlyphList))

    def _find_exceptions(self):
        '''
        Process kerning to find which pairs are exceptions,
        and which are just normal pairs.
        '''

        for pair in list(self.kerning.keys())[::-1]:

            # Skip pairs in which the name of the
            # left glyph contains the ignore tag.
            if tag_ignore in pair[0]:
                del self.kerning[pair]
                continue

            # Looking for pre-defined exception pairs, and filtering them out.
            if any([tag_exception in item for item in pair]):
                self.predefined_exceptions[pair] = self.kerning[pair]
                del self.kerning[pair]

        glyph_2_glyph = sorted(
            [pair for pair in self.kerning.keys() if(
                not self._is_group(pair[0]) and
                not self._is_group(pair[1]))]
        )
        glyph_2_group = sorted(
            [pair for pair in self.kerning.keys() if(
                not self._is_group(pair[0]) and
                self._is_group(pair[1]))]
        )
        group_2_item = sorted(
            [pair for pair in self.kerning.keys() if(
                self._is_group(pair[0]))]
        )

        # glyph to group pairs:
        # ---------------------
        for (glyph, group) in glyph_2_group:
            pair = glyph, group
            value = self.kerning[pair]
            is_rtl_pair = self._is_rtl(pair)
            if glyph in self.grouped_left:
                # it is a glyph_to_group exception!
                if is_rtl_pair:
                    self.rtl_glyph_group_exceptions[pair] = value
                else:
                    self.glyph_group_exceptions[pair] = value
                self.pairs_processed.append(pair)

            else:
                for grouped_glyph in self.groups[group]:
                    gr_pair = (glyph, grouped_glyph)
                    if gr_pair in glyph_2_glyph:
                        gr_value = self.kerning[gr_pair]
                        # that pair is a glyph_to_glyph exception!
                        if is_rtl_pair:
                            self.rtl_glyph_glyph_exceptions[gr_pair] = gr_value
                        else:
                            self.glyph_glyph_exceptions[gr_pair] = gr_value

                # skip the pair if the value is zero
                if value == 0:
                    self.pairs_unprocessed.append(pair)
                    continue

                if is_rtl_pair:
                    self.rtl_glyph_group[pair] = value
                else:
                    self.glyph_group[pair] = value
                self.pairs_processed.append(pair)

        # group to group/glyph pairs:
        # ---------------------------
        exploded_pair_list = []
        exploded_pair_list_rtl = []

        for (group_l, item_r) in group_2_item:
            # the right item of the pair may be a group or a glyph
            pair = (group_l, item_r)
            value = self.kerning[pair]
            is_rtl_pair = self._is_rtl(pair)
            l_group_glyphs = self.groups[group_l]

            if self._is_group(item_r):
                r_group_glyphs = self.groups[item_r]
            else:
                # not a group, therefore a glyph
                if item_r in self.grouped_right:
                    # it is a group_to_glyph exception!
                    if is_rtl_pair:
                        self.rtl_group_glyph_exceptions[pair] = value
                    else:
                        self.group_glyph_exceptions[pair] = value
                    self.pairs_processed.append(pair)
                    continue  # It is an exception, so move on to the next pair

                else:
                    r_group_glyphs = [item_r]

            # skip the pair if the value is zero
            if value == 0:
                self.pairs_unprocessed.append(pair)
                continue

            if is_rtl_pair:
                self.rtl_group_group[pair] = value
                exploded_pair_list_rtl.extend(
                    self._explode(l_group_glyphs, r_group_glyphs))
            else:
                self.group_group[pair] = value
                exploded_pair_list.extend(
                    self._explode(l_group_glyphs, r_group_glyphs))
                # list of all possible pair combinations for the
                # @class @class kerning pairs of the font.
            self.pairs_processed.append(pair)

        # Find the intersection of the exploded pairs with the glyph_2_glyph
        # pairs collected above. Those must be exceptions, as they occur twice
        # (once in class-kerning, once as a single pair).
        self.exception_pairs = set(exploded_pair_list) & set(glyph_2_glyph)
        self.exception_pairs_rtl = set(exploded_pair_list_rtl) & set(glyph_2_glyph)

        for pair in self.exception_pairs:
            self.glyph_glyph_exceptions[pair] = self.kerning[pair]

        for pair in self.exception_pairs_rtl:
            self.rtl_glyph_glyph_exceptions[pair] = self.kerning[pair]

        # finally, collect normal glyph to glyph pairs:
        # ---------------------------------------------
        # NB: RTL glyph-to-glyph pairs can only be identified if its
        # glyphs are in the @RTL_KERNING group.

        for glyph_1, glyph_2 in glyph_2_glyph:
            pair = glyph_1, glyph_2
            value = self.kerning[pair]
            is_rtl_pair = self._is_rtl(pair)
            if any(
                [glyph_1 in self.grouped_left, glyph_2 in self.grouped_right]
            ):
                # it is an exception!
                # exceptions expressed as glyph-to-glyph pairs -- these cannot
                # be filtered and need to be added to the kern feature
                # ---------------------------------------------
                if is_rtl_pair:
                    self.rtl_glyph_glyph_exceptions[pair] = value
                else:
                    self.glyph_glyph_exceptions[pair] = value
                self.pairs_processed.append(pair)
            else:
                if (
                    pair not in self.glyph_glyph_exceptions and
                    pair not in self.rtl_glyph_glyph_exceptions
                ):
                    if self._is_rtl(pair):
                        self.rtl_glyph_glyph[pair] = self.kerning[pair]
                    else:
                        self.glyph_glyph[pair] = self.kerning[pair]
                    self.pairs_processed.append(pair)


class MakeMeasuredSubtables(object):

    def __init__(self, kernDict, kerning, groups, maxSubtableSize):

        self.kernDict = kernDict
        self.subtables = []
        self.numberOfKernedGlyphs = self._getNumberOfKernedGlyphs(
            kerning, groups)

        coverageTableSize = 2 + (2 * self.numberOfKernedGlyphs)
        # maxSubtableSize = 2 ** 14

        print('coverage table size:', coverageTableSize)
        print('  max subtable size:', maxSubtableSize)
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
            itemPair = [
                pair for pair in self.kernDict.keys() if pair[0] == item]

            for left, right in itemPair:
                groupedGlyphsLeft.update(groups.get(left, [left]))
                groupedGlyphsRight.update(groups.get(right, [right]))
                usedGroupsLeft.add(left)
                usedGroupsRight.add(right)

                leftClassSize = 6 + (2 * len(groupedGlyphsLeft))
                rightClassSize = 6 + (2 * len(groupedGlyphsRight))
                subtableMetadataSize = (
                    coverageTableSize + leftClassSize + rightClassSize)
                subtable_size = (
                    16 + len(usedGroupsLeft) * len(usedGroupsRight) * 2)

            if subtableMetadataSize + subtable_size < maxSubtableSize:
                subtable.append(item)

            else:
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
                for pair in [
                    pair for pair in self.kernDict.keys() if
                    pair[0] == leftItem
                ]:
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

    def __init__(self, font, args=None):

        if not args:
            args = Defaults()

        self.f = font
        self.minKern = args.min_value
        self.write_subtables = args.write_subtables
        self.subtable_size = args.subtable_size
        self.write_trimmed_pairs = args.write_trimmed_pairs
        self.dissolve_single = args.dissolve_single
        self.trimmedPairs = 0

        if self.f:
            self.kerning = self.f.kerning
            self.groups = self.f.groups
            self.group_order = sorted(self.groups.keys())

            if not self.kerning:
                print('ERROR: The font has no kerning!')
                return

            output_data = self._makeOutputData(args)
            if output_data:
                self.header = self.make_header(args)
                output_dir = os.path.abspath(os.path.dirname(self.f.path))
                output_path = os.path.join(output_dir, args.output_name)
                self.writeDataToFile(output_data, output_path)

    def make_header(self, args):
        app = WhichApp()
        try:
            ps_name = self.f.info.postscriptFontName
        except Exception:
            ps_name = None

        header = []
        if args.write_timestamp:
            header.append('# Created: %s' % time.ctime())
        header.append('# PS Name: %s' % ps_name)
        header.append('# MinKern: +/- %s inclusive' % args.min_value)
        header.append('# exported from %s' % app.appName)
        return header

    def _dict2pos(self, pairValueDict, minimum=0, enum=False, RTL=False):
        '''
        Turn a dictionary to a list of kerning pairs. Kerning pairs whose
        absolute value does not exceed a given threshold can be filtered.
        '''

        data = []
        trimmed = 0
        for pair, value in pairValueDict.items():

            if RTL:
                value_str = '<{0} 0 {0} 0>'.format(value)
            else:
                value_str = str(value)

            posLine = 'pos %s %s;' % (' '.join(pair), value_str)

            if enum:
                data.append('enum ' + posLine)
            else:
                if abs(value) < minimum:
                    if self.write_trimmed_pairs:
                        data.append('# ' + posLine)
                        trimmed += 1
                    else:
                        continue
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
        print('%s subtables created' % self.subtablesCreated)
        return subtableOutput

    def _makeOutputData(self, args):
        # Build the output data.

        output = []
        kp = KernProcessor(
            self.groups,
            self.kerning,
            self.dissolve_single
        )

        # ---------------
        # list of groups:
        # ---------------
        for groupName in kp.group_order:
            glyphList = kp.groups[groupName]
            if not glyphList:
                print('WARNING: Kerning group %s has no glyphs.' % groupName)
                continue
            output.append('%s = [%s];' % (groupName, ' '.join(glyphList)))

        # ------------------
        # LTR kerning pairs:
        # ------------------
        LTRorder = [
            # container_dict, minKern, comment, enum
            (kp.predefined_exceptions, 0,
                '\n# pre-defined exceptions:', True),
            (kp.glyph_glyph, self.minKern,
                '\n# glyph, glyph:', False),
            (kp.glyph_glyph_exceptions, 0,
                '\n# glyph, glyph exceptions:', False),
            (kp.glyph_group_exceptions, 0,
                '\n# glyph, group exceptions:', True),
            (kp.group_glyph_exceptions, 0,
                '\n# group, glyph exceptions:', True),
        ]

        LTRorderExtension = [
            # in case no subtables are desired
            (kp.glyph_group, self.minKern, '\n# glyph, group:', False),
            (kp.group_group, self.minKern, '\n# group, group/glyph:', False),
        ]

        # ------------------
        # RTL kerning pairs:
        # ------------------
        RTLorder = [
            # container_dict, minKern, comment, enum
            (kp.rtl_predefined_exceptions, 0,
                '\n# RTL pre-defined exceptions:', True),
            (kp.rtl_glyph_glyph, self.minKern,
                '\n# RTL glyph, glyph:', False),
            (kp.rtl_glyph_glyph_exceptions, 0,
                '\n# RTL glyph, glyph exceptions:', False),
            (kp.rtl_glyph_group_exceptions, 0,
                '\n# RTL glyph, group exceptions:', True),
            (kp.rtl_group_glyph_exceptions, 0,
                '\n# RTL group, glyph exceptions:', True),
        ]

        RTLorderExtension = [
            # in case no subtables are desired
            (kp.rtl_glyph_group, self.minKern,
                '\n# RTL glyph, group:', False),
            (kp.rtl_group_group, self.minKern,
                '\n# RTL group, group/glyph:', False)
        ]

        if not self.write_subtables:
            LTRorder.extend(LTRorderExtension)
            RTLorder.extend(RTLorderExtension)

        for container_dict, minKern, comment, enum in LTRorder:
            if container_dict:
                output.append(comment)
                output.append(
                    self._dict2pos(container_dict, minKern, enum))

        if self.write_subtables:
            self.subtablesCreated = 0

            glyph_to_class_subtables = MakeMeasuredSubtables(
                kp.glyph_group, kp.kerning, kp.groups,
                self.subtable_size).subtables
            output.extend(self._buildSubtableOutput(
                glyph_to_class_subtables, '\n# glyph, group:'))

            class_to_class_subtables = MakeMeasuredSubtables(
                kp.group_group, kp.kerning, kp.groups,
                self.subtable_size).subtables
            output.extend(self._buildSubtableOutput(
                class_to_class_subtables,
                '\n# group, glyph and group, group:')
            )

        # Check if RTL pairs exist
        rtlPairsExist = False
        for container_dict, _, _, _ in RTLorderExtension + RTLorder:
            if container_dict.keys():
                rtlPairsExist = True
                break

        if rtlPairsExist:

            lookupRTLopen = (
                '\n\nlookup RTL_kerning {\n'
                'lookupflag RightToLeft IgnoreMarks;\n')
            lookupRTLclose = '\n\n} RTL_kerning;\n'

            output.append(lookupRTLopen)

            for container_dict, minKern, comment, enum in RTLorder:
                if container_dict:
                    output.append(comment)
                    output.append(
                        self._dict2pos(
                            container_dict, minKern, enum, RTL=True))

            if self.write_subtables:
                self.RTLsubtablesCreated = 0

                rtl_glyph_class_subtables = MakeMeasuredSubtables(
                    kp.rtl_glyph_group, kp.kerning, kp.groups,
                    self.subtable_size).subtables
                output.extend(self._buildSubtableOutput(
                    rtl_glyph_class_subtables,
                    '\n# RTL glyph, group:', RTL=True))

                rtl_class_class_subtables = MakeMeasuredSubtables(
                    kp.rtl_group_group, kp.kerning, kp.groups,
                    self.subtable_size).subtables
                output.extend(self._buildSubtableOutput(
                    rtl_class_class_subtables,
                    '\n# RTL group, glyph and group, group:', RTL=True))

            output.append(lookupRTLclose)

        return output

    def writeDataToFile(self, data, output_path):

        print('Saving %s file...' % os.path.basename(output_path))

        if self.trimmedPairs > 0:
            print('Trimmed pairs: %s' % self.trimmedPairs)

        with open(output_path, 'w') as blob:
            blob.write('\n'.join(self.header))
            blob.write('\n\n')
            if data:
                blob.write('\n'.join(data))
                blob.write('\n')

        print('Output file written to %s' % output_path)


def get_args(args=None):

    defaults = Defaults()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'input_file',
        help='input font file')

    parser.add_argument(
        '-o', '--output_name',
        action='store',
        default=defaults.output_name,
        help='change the output file name')

    parser.add_argument(
        '-m', '--min_value',
        action='store',
        default=defaults.min_value,
        metavar='INT',
        type=int,
        help='minimum kerning value')

    parser.add_argument(
        '-s', '--write_subtables',
        action='store_true',
        default=defaults.write_subtables,
        help='write subtables')

    parser.add_argument(
        '--subtable_size',
        action='store',
        default=defaults.subtable_size,
        metavar='INT',
        type=int,
        help='specify max subtable size')

    parser.add_argument(
        '-t', '--write_trimmed_pairs',
        action='store_true',
        default=defaults.write_trimmed_pairs,
        help='write trimmed pairs to output file (as comments)')

    parser.add_argument(
        '--write_timestamp',
        action='store_true',
        default=defaults.write_timestamp,
        help='write time stamp in header of output file')

    parser.add_argument(
        '--dissolve_single',
        action='store_true',
        default=defaults.dissolve_single,
        help='dissolve single-element groups to glyph names')

    return parser.parse_args(args)


def main(test_args=None):
    args = get_args(test_args)
    f_path = os.path.normpath(args.input_file)
    import defcon
    if os.path.exists(f_path):

        f = defcon.Font(f_path)
        run(f, args)

    else:
        print(f_path, 'does not exist.')


if __name__ == '__main__':
    main()
