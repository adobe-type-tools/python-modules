#!/usr/bin/env python3

'''
This tool interprets glyphs and anchor points within a UFO to write a
`makeotf`-compatible GPOS mark feature file.

The input UFO file needs to have base glyphs and zero-width combining
marks. Base- and mark glyphs attach via anchor pairs (e.g. `above` and
`_above`, or `top`, and `_top`).
Combining marks must be members of a `COMBINING_MARKS` reference group.

#### Default functionality:

-   writing a `mark.fea` file, which contains mark classes/groups, and
    per-anchor mark-to-base positioning lookups (GPOS lookup type 4)
-   writing mark-to-ligature positioning lookups (GPOS lookup type 5).
    This requires anchor names to be suffixed with an ordinal (`1ST`, `2ND`,
    `3RD`, etc). For example – if a mark with an `_above` anchor is to be
    attached to a ligature, the ligature’s anchor names would be `above1ST`,
    `above2ND`, etc – depending on the amount of ligature elements.

#### Optional functionality:

-   writing `mkmk.fea`, for mark-to-mark positioning (GPOS lookup type 6)
-   writing `abvm.fea`/`blwm.fea` files, as used in Indic scripts (anchor pairs
    are `abvm`, `_abvm`, and `blwm`, `_blwm`, respectively)
-   writing mark classes into a separate file (in case classes need to be
    shared across multiple lookup types)
-   trimming casing tags (`UC`, `LC`, or `SC`)

    Trimming tags is a somewhat specific feature, but it is quite essential:
    In a UFO, anchors can be used to build composite glyphs – for example
    `aacute`, and `Aacute`. Since those glyphs would often receive a
    differently-shaped accent, the anchor pairs (on bases `a`/`A` and
    marks `acutecmb`/`acutecmb.cap`) would be `aboveLC`/`_aboveLC`, and
    `aboveUC/_aboveUC`, respectively.

    When writing the mark feature, we care more about which group of combining
    marks triggers a certain behavior, so removing those casing tags allows
    grouping all `_above` marks together, hence attaching to a base glyph –
    no matter if it is upper- or lowercase. The aesthetic substitution of the
    mark (e.g. smaller mark on the uppercase letter) can happen later, in the
    `ccmp` feature.

#### Usage:
```zsh

    # write a basic mark feature for a static font
    python markFeatureWriter.py font.ufo

    # write a basic mark feature for a variable font
    python markFeatureWriter.py font.designspace

    # write mark and mkmk feature files
    python markFeatureWriter.py -m font.ufo

    # trim casing tags
    python markFeatureWriter.py -t font.ufo

    # further usage information
    python markFeatureWriter.py -h

```
'''

import argparse
import sys
from abc import abstractmethod
from pathlib import Path
from collections import defaultdict, namedtuple
from graphlib import TopologicalSorter, CycleError
from math import inf

from defcon import Font
from fontTools.designspaceLib import (
    DesignSpaceDocument,
    DesignSpaceDocumentError,
)

# ligature anchors end with 1ST, 2ND, 3RD, etc.
ORDINALS = ['1ST', '2ND', '3RD'] + [f'{i}TH' for i in range(4, 10)]
SHORTINSTNAMEKEY = 'com.adobe.shortInstanceName'
NONEPOS = (-inf, -inf)

class Defaults(object):
    """
    default values
    These can be overridden via argparse.
    """

    def __init__(self):

        self.input_file = None

        self.trim_tags = False
        self.write_classes = False
        self.write_mkmk = False
        self.indic_format = False

        self.mark_file = 'mark.fea'
        self.mkmk_file = 'mkmk.fea'
        self.mkclass_file = 'markclasses.fea'
        self.abvm_file = 'abvm.fea'
        self.blwm_file = 'blwm.fea'
        self.mkgrp_name = 'COMBINING_MARKS'


def check_input_file(parser, file_name):
    file_path = Path(file_name)
    if file_path.suffix.lower() == '.ufo':
        if not file_path.exists():
            parser.error(f'{file_name} does not exist')
        elif not file_path.is_dir():
            parser.error(f'{file_name} is not a directory')
    elif file_path.suffix.lower() == '.designspace':
        if not file_path.exists():
            parser.error(f'{file_name} does not exist')
        elif not file_path.is_file():
            parser.error(f'{file_name} is not a file')
    else:
        parser.error(f'Unrecognized input file type')
    return file_name


def get_args(args=None):

    defaults = Defaults()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        'input_file',
        type=lambda f: check_input_file(parser, f),
        help='input UFO or designspace file')

    parser.add_argument(
        '-t', '--trim_tags',
        action='store_true',
        default=defaults.trim_tags,
        help='trim casing tags from anchor names?')

    parser.add_argument(
        '-c', '--write_classes',
        action='store_true',
        default=defaults.write_classes,
        help='write mark classes to extra file?')

    parser.add_argument(
        '-m', '--write_mkmk',
        action='store_true',
        default=defaults.write_mkmk,
        help='write mark-to-mark feature file?')

    parser.add_argument(
        '-i', '--indic_format',
        action='store_true',
        default=defaults.indic_format,
        help='write Indic mark format?')

    parser.add_argument(
        '--mark_file',
        action='store',
        metavar='NAME',
        default=defaults.mark_file,
        help='name for mark feature file')

    parser.add_argument(
        '--mkmk_file',
        action='store',
        metavar='NAME',
        default=defaults.mkmk_file,
        help='name for mkmk feature file')

    parser.add_argument(
        '--mkclass_file',
        action='store',
        metavar='NAME',
        default=defaults.mkclass_file,
        help='name for mark classes file')

    parser.add_argument(
        '--abvm_file',
        action='store',
        metavar='NAME',
        default=defaults.abvm_file,
        help='name for above mark feature file')

    parser.add_argument(
        '--blwm_file',
        action='store',
        metavar='NAME',
        default=defaults.blwm_file,
        help='name for below mark feature file')

    parser.add_argument(
        '--mkgrp_name',
        action='store',
        metavar='NAME',
        default=defaults.mkgrp_name,
        help='name for group containing all mark glyphs')

    return parser.parse_args(args)


def write_output(directory, file, line_list):
    with open(directory / file, 'w') as of:
        of.write('\n'.join(line_list))
    print(f'writing {file}')


def is_attaching(anchor_name):
    '''
    check if the anchor name in question is attaching or not
    '''
    return anchor_name.startswith('_')


def split_liga_anchor_name(anchor_name):
    '''
    if the anchor name ends with 1ST, 2ND, etc.; get the implied index,
    and the name without the suffix
    '''
    if anchor_name.endswith(tuple(ORDINALS)):
        trimmed_name = anchor_name[:-3]
        index = ORDINALS.index(anchor_name[-3:])
        return index, trimmed_name


def process_anchor_name(anchor_name, trim=False):
    if trim and anchor_name.endswith(('UC', 'LC', 'SC')):
        return anchor_name[:-2]
    return anchor_name


class AnchorMate(object):
    '''
    AnchorMate lifts anchors from one or more glyphs and
    sorts them in a dictionary {a_position: gName}
    '''

    def __init__(self, anchor):
        self.pos_name_dict = {}


AnchorInfo = namedtuple('AnchorInfo', 'name, position')


class GlyphAnchorInfo(object):
    '''
    The GlyphAnchorInfo object is just an attribute-based data structure
    for communicating anchor parameters, somewhat based on the defcon
    structure. It uses three attributes: "name", which is the the name of
    the glyph, "width", which is the advance width, and "anchors", which
    is a list of AnchorInfo named tuples.
    '''

    def __init__(self, name, width, anchor_list):
        self.name = name
        self.width = width
        self.anchors = anchor_list


class MarkAdapter(object):
    '''
    Interface between underlying data source and MarkFeatureWriter
    '''

    @abstractmethod
    def anchor_glyphs(self):
        '''
        Returns a dict of GlyphAnchorInfo objects, one per named glyph
        '''
        pass

    @abstractmethod
    def glyph_order(self):
        '''
        Returns a dictionary of all the glyphs in the source font where
        the key is the name and the value is the order of the glyph in
        the font.
        '''
        pass

    @abstractmethod
    def groups(self):
        '''
        Returns a dict of all groups in the sources, with the name as a
        key and a list of glyphs in the group as the value
        '''
        pass

    @abstractmethod
    def path(self):
        '''
        Returns path to the top of the source as a Path() object
        '''
        pass

    @abstractmethod
    def unique_name(self, prefix, position):
        '''
        Returns a name starting with prefix that is unique relative to
        the position parameter. (Can assume it will be called once per
        unique position, so it does not need to track names already
        returned.)
        '''
        pass

    @abstractmethod
    def anchor_position_string(self, position):
        '''
        Returns the position as a string that can be used in an anchor
        directive in a feature file.
        '''
        pass

class UFOMarkAdapter(MarkAdapter):
    '''
    Adapter for a single UFO
    '''

    def __init__(self, path):
        self.f = Font(path)
        if not self.f:
            sys.exit(f'Problem opening UFO file {path}')

    def anchor_glyphs(self):
        d = {}
        for g in self.f:
            anchor_list = [AnchorInfo(a.name, (round(a.x), round(a.y)))
                           for a in g.anchors]
            d[g.name] = GlyphAnchorInfo(g.name, g.width, anchor_list)
        return d

    def glyph_order(self):
        return {gn: i for (i, gn)
                in enumerate(self.f.lib['public.glyphOrder'])}

    def groups(self):
        return self.f.groups

    def path(self):
        return Path(self.f.path)

    def unique_name(self, prefix, position):
        # represent negative numbers with “n”, because minus is
        # reserved for ranges:
        str_x = str(position[0]).replace('-', 'n')
        str_y = str(position[1]).replace('-', 'n')
        return f'{prefix}_{str_x}_{str_y}'

    def anchor_position_string(self, position):
        return str(position[0]) + ' ' + str(position[1])


class DesignspaceMarkAdapter(MarkAdapter):
    '''
    Adapter for a UFO-based variable font with a designspace file
    '''

    def __init__(self, dsDoc):
        try:
            self.fonts = dsDoc.loadSourceFonts(Font)
        except DesignSpaceDocumentError as err:
            sys.exit(err)

        for i, f in enumerate(self.fonts):
            f.sourceIndex = i

        defaultSource = dsDoc.findDefault()
        if defaultSource is not None:
            defaultIndex = dsDoc.sources.index(defaultSource)
            default_font = self.fonts.pop(defaultIndex)
            self.fonts.insert(0, default_font)
        else:
            sys.exit('Error: did not find source for default instance')

        # Add name map
        self.shortNames = [None]
        for f in self.fonts[1:]:
            if SHORTINSTNAMEKEY in f.lib:
                self.shortNames.append(f.lib[SHORTINSTNAMEKEY])
            else:
                self.shortNames.append(self.make_short_name(dsDoc,
                                                            f.sourceIndex))

        self.base_names = {}
        self.dsDoc = dsDoc

    # Must match function in kernFeatureWriter, which writes locations.fea
    def make_short_name(self, dsDoc, sourceIndex):
        source = dsDoc.sources[sourceIndex]
        location = source.location
        anames = []
        for an in dsDoc.getAxisOrder():
            avstr = "%c%g" % (an[0], location[an])
            avstr = avstr.replace('.', 'p')
            avstr = avstr.replace('-', 'n')
            anames.append(avstr)
        return '_'.join(anames)

    def anchor_glyphs(self):
        d = {}
        f = self.fonts[0]
        for g in f:
            position_map = {}
            for a in g.anchors:
                # Put the default instance position first so that the
                # position sorting groups those together
                position_map[a.name] = [(round(a.x), round(a.y))]
            anchorNameSet = set(position_map.keys())
            ni = 0
            for i, source in enumerate(self.fonts):
                if i == 0:
                    continue
                # If the glyph is absent put NONEPOS as the position
                if g.name not in source:
                    for plist in position_map.values():
                        postions.append(NONEPOS)
                    continue
                foundNameSet = set()
                for sga in source[g.name].anchors:
                    if sga.name not in anchorNameSet:
                        sys.exit(f'Error: glyph {g.name} has anchor {a.name} '
                                f'in source of instance {self.shortNames[i]} '
                                'but not in source of default instance')
                    else:
                        plist = position_map[sga.name]
                        plist.append((round(sga.x), round(sga.y)))
                        foundNameSet.add(sga.name)
                missingNames = anchorNameSet - foundNameSet
                if missingNames:
                    mnamestr = ', '.join(missingNames)
                    sys.exit(f'Error: glyph {g.name} has anchors {mnamestr} '
                             'in source of default instance but not '
                             f'source of instance {self.shortNames[i]}')
            anchor_list = [AnchorInfo(a.name, tuple(position_map[a.name]))
                           for a in g.anchors]
            d[g.name] = GlyphAnchorInfo(g.name, g.width, anchor_list)
        return d

    def glyph_order(self):
        # Use the glyph ordering in the source for the default instance
        # as that should (always?) have all the glyphs
        f = self.fonts[0]
        return {gn: i for (i, gn)
                in enumerate(f.lib['public.glyphOrder'])}

    def groups(self):
        if hasattr(self, '_groups'):
            return self._groups
        # Calculate partial orderings for groups across all fonts
        group_orderings = defaultdict(lambda: defaultdict(set))
        for i, f in enumerate(self.fonts):
            for g, gl in f.groups.items():
                ordering = group_orderings[g]
                for j, gn in enumerate(gl):
                    ordering[gn] |= set(gl[j+1:])

        # Use the partial orderings to calculate a total ordering,
        # or failing that use the order in which the glyphs were
        # encountered
        self._groups = {}
        for g, ordering in group_orderings.items():
            try:
                ts = TopologicalSorter(ordering)
                l = list(ts.static_order())
            except CycleError as err:
                print(f'glyphs in group {g} have different orderings across '
                      'different sources, ordering cannot be preserved')
                l = ordering.keys()
            self._groups[g] = l

        return self._groups

    def path(self):
        return Path(self.dsDoc.path)

    def unique_name(self, prefix, position):
        # represent negative numbers with “n”, because minus is
        # reserved for ranges:
        str_x = str(position[0][0]).replace('-', 'n')
        str_y = str(position[0][1]).replace('-', 'n')
        # We choose names based on the position in the default instance
        # but other position values could be different. A position is
        # a tuple of two-tuples, one for each source, and are always the
        # same length so they can be sorted and compared for identity.
        # So all we need to do here is be careful not to hand out the
        # same name for two different positions. Because unique_name
        # will only be called with a prefix,position pair once, all we
        # need to do is track how many we've handed out so far and add
        # a unique suffix
        base_name = f'{prefix}_{str_x}_{str_y}'
        if base_name not in self.base_names:
            self.base_names[base_name] = 0
            return base_name
        else:
            rev = self.base_names[base_name] + 1
            self.base_names[base_name] = rev
            return base_name + '_' + str(rev)


    def anchor_position_string(self, position):
        assert len(position) == len(self.fonts)
        def_pos = position[0]
        def_str = str(def_pos[0]) + ' ' + str(def_pos[1])
        if all(p == NONEPOS or p == def_pos for p in position[1:]):
            return def_str

        pos_strs = ['<' + def_str + '>']
        for i, p in enumerate(position):
            if i == 0 or p == NONEPOS:
                continue
            pos_strs.append('@' + self.shortNames[i] + ':<' +
                            str(p[0]) + ' ' + str(p[1]) + '>')
        return '(' + ' '.join(pos_strs) + ')'


class MarkFeatureWriter(object):
    def __init__(self, args=None):

        if not args:
            args = Defaults()

        self.mark_file = args.mark_file
        self.mkmk_file = args.mkmk_file
        self.mkclass_file = args.mkclass_file
        self.abvm_file = args.abvm_file
        self.blwm_file = args.blwm_file
        self.mkgrp_name = args.mkgrp_name
        self.trim_tags = args.trim_tags
        self.indic_format = args.indic_format
        self.write_mkmk = args.write_mkmk
        self.write_classes = args.write_classes

        if args.input_file:
            input_path = Path(args.input_file)
            if input_path.is_file():
                dsDoc = DesignSpaceDocument.fromfile(input_path)
                adapter = DesignspaceMarkAdapter(dsDoc)
            else:
                adapter = UFOMarkAdapter(Path(args.input_file))
            self.run(adapter)

    def run(self, adapter):
        self.adapter = adapter
        self.glyphs = adapter.anchor_glyphs()
        self.glyph_order = adapter.glyph_order()
        self.groups = adapter.groups()
        output_dir = adapter.path().parent

        if self.mkgrp_name not in self.groups:
            sys.exit(
                f'No group named "{self.mkgrp_name}" found. '
                'Please add it to your UFO file '
                '(and combining marks to it).'
            )

        combining_marks_group = self.groups[self.mkgrp_name]

        combining_marks = [self.glyphs[g_name]
                           for g_name in combining_marks_group]
        # find out which attachment anchors exist in combining marks
        combining_anchor_names = set((
            process_anchor_name(a.name, self.trim_tags) for
            g in combining_marks for a in g.anchors if is_attaching(a.name)))

        mkmk_marks = [g for g in combining_marks if not all(
            [is_attaching(anchor.name) for anchor in g.anchors])]

        base_glyphs = [
            g for g in self.glyphs.values() if
            g.anchors and
            g not in combining_marks and
            g.width != 0 and
            not all([is_attaching(anchor.name) for anchor in g.anchors])
        ]

        ligature_base_glyphs = [g for g in base_glyphs if any(
            [anchor.name.endswith(tuple(ORDINALS)) for anchor in g.anchors])
        ]

        combining_anchor_dict = self.make_anchor_dict(combining_marks)
        base_glyph_anchor_dict = self.make_anchor_dict(
            base_glyphs, combining_anchor_names)
        mkmk_anchor_dict = self.make_anchor_dict(mkmk_marks)
        liga_anchor_dict = self.make_liga_anchor_dict(
            ligature_base_glyphs, combining_anchor_names)

        # mark classes
        mark_class_list = []
        for anchor_name, a_mate in sorted(combining_anchor_dict.items()):
            if is_attaching(anchor_name):
                # write the class if a corresponding base anchor exists.
                if any([
                    anchor_name[1:] in base_glyph_anchor_dict,
                    anchor_name[1:] in liga_anchor_dict]
                ):
                    mc = self.make_mark_class(anchor_name, a_mate)
                    mark_class_list.append(mc)
                # if not, do not write it and complain.
                else:
                    print(
                        f'anchor {anchor_name} does not have a corresponding '
                        'base anchor.')

        mark_class_content = self.make_mark_classes_content(mark_class_list)

        # abvm blwm features
        if self.indic_format:
            abvm_feature_content = []
            blwm_feature_content = []

            for anchor_name, a_mate in sorted(base_glyph_anchor_dict.items()):
                if anchor_name.startswith('abvm'):
                    mark_lookup = self.make_mark_lookup(anchor_name, a_mate)
                    abvm_feature_content.append(mark_lookup)
                    abvm_feature_content.append('\n')
                    del base_glyph_anchor_dict[anchor_name]

                if anchor_name.startswith('blwm'):
                    mark_lookup = self.make_mark_lookup(anchor_name, a_mate)
                    blwm_feature_content.append(mark_lookup)
                    blwm_feature_content.append('\n')
                    del base_glyph_anchor_dict[anchor_name]

        # mark feature
        mark_feature_content = []
        for anchor_name, a_mate in sorted(base_glyph_anchor_dict.items()):
            mark_lookup = self.make_mark_lookup(anchor_name, a_mate)
            mark_feature_content.append(mark_lookup)
            mark_feature_content.append('\n')

        # ligature lookups
        for anchor_name, gname_index_dict in sorted(liga_anchor_dict.items()):
            if anchor_name in combining_anchor_dict:
                liga_lookup = self.make_liga_lookup(
                    anchor_name, gname_index_dict)
                mark_feature_content.append(liga_lookup)
                mark_feature_content.append('\n')
            else:
                print(
                    f'ligature anchor {anchor_name} does not have '
                    'a corresponding mark anchor.')

        # mkmk feature
        mkmk_feature_content = []
        for anchor_name, a_mate in sorted(mkmk_anchor_dict.items()):
            if not is_attaching(anchor_name):
                mkmk_lookup = self.make_mkmk_lookup(anchor_name, a_mate)
                mkmk_feature_content.append(mkmk_lookup)
                mkmk_feature_content.append('\n')

        # assemble content
        consolidated_content = []
        if self.write_classes:
            # write the classes into an external file if so requested
            write_output(output_dir, self.mkclass_file, mark_class_content)
        else:
            # otherwise they go on top of the mark.fea file
            consolidated_content.extend(mark_class_content)

        # add mark feature content
        consolidated_content.extend(mark_feature_content)

        if self.write_mkmk:
            # write mkmk only if requested, in the adjacent mkmk.fea file
            write_output(output_dir, self.mkmk_file, mkmk_feature_content)

        if self.indic_format:
            # write abvm/blwm in adjacent files.
            write_output(output_dir, self.abvm_file, abvm_feature_content)
            write_output(output_dir, self.blwm_file, blwm_feature_content)

        # write the mark feature
        write_output(output_dir, self.mark_file, consolidated_content)

    def make_liga_anchor_dict(self, glyph_list, attachment_list=None):
        '''
        create a nested dict mapping idealized anchor names to attachment
        points within a ligature (and their index, indicated by 1ST, 2ND, etc):
        'aboveAR': {
            'arSeenAlefMaksura': {
                0: (890, 390),
                1: (150, 260)},
            'arTahYehBarree.s': {
                0: (320, 820),
                1: (110, 250)},
            }
        '''

        anchor_dict = {}
        for g in glyph_list:
            for anchor in g.anchors:
                if anchor.name.endswith(tuple(ORDINALS)):
                    anchor_index, trimmed_anchor_name = split_liga_anchor_name(
                        anchor.name)
                    anchor_name = process_anchor_name(
                        trimmed_anchor_name, self.trim_tags)
                    ap = anchor_dict.setdefault(anchor_name, {})
                    index_pos_dict = ap.setdefault(g.name, {})
                    index_pos_dict[anchor_index] = anchor.position
        return anchor_dict

    def make_anchor_dict(self, glyph_list, attachment_list=None):
        '''
        create a dict mapping anchor names to attachment points, which may
        be shared by various glyphs -- for example:

        'aboveLC': {
            (275, 495): ['oslash', 'o'],
            (251, 495): ['a']},
        'belowLC': {
            (250, -20): ['a'],
            (275, -20): ['o']}

        '''
        anchor_dict = {}
        for g in glyph_list:
            for anchor in g.anchors:
                anchor_name = process_anchor_name(anchor.name, self.trim_tags)
                am = anchor_dict.setdefault(anchor_name, AnchorMate(anchor))
                am.pos_name_dict.setdefault(anchor.position, []).append(g.name)

        if attachment_list:
            # remove anchors that do not have an attachment equivalent
            for anchor_name in list(anchor_dict.keys()):
                attaching_anchor_name = '_' + anchor_name
                if attaching_anchor_name not in attachment_list:
                    del anchor_dict[anchor_name]

        return anchor_dict

    def sort_gnames(self, glyph_list):
        '''
        Sort list of glyph names based on the glyph order
        '''
        glyph_list.sort(key=lambda x: self.glyph_order[x])
        return glyph_list

    def make_mark_class(self, anchor_name, a_mate):
        pos_gname = sorted(a_mate.pos_name_dict.items())
        mgroup_definitions = []
        mgroup_attachments = []
        single_attachments = []

        for position, g_names in pos_gname:
            position_string = self.adapter.anchor_position_string(position)
            if len(g_names) > 1:
                sorted_g_names = self.sort_gnames(g_names)
                group_name = self.adapter.unique_name(f'@mGC{anchor_name}',
                                                      position)
                group_glyphs = ' '.join(sorted_g_names)
                mgroup_definitions.append(
                    f'{group_name} = [ {group_glyphs} ];')
                mgroup_attachments.append(
                    f'markClass {group_name} <anchor {position_string}> '
                    f'@MC{anchor_name};')

            else:
                g_name = g_names[0]
                single_attachments.append(
                    f'markClass {g_name} <anchor {position_string}> '
                    f'@MC{anchor_name};')

        return mgroup_definitions, mgroup_attachments, single_attachments

    def make_mark_classes_content(self, mark_class_list):
        '''
        The make_mark_class method returns a three-list tuple per
        anchor. Here, those lists are organized in chunks:

        - first mark group definitions, like
            @mGC_above_0_495 = [ gravecmb acutecmb circumflexcmb ];
            @mGC_above_0_690 = [ gravecmb.cap acutecmb.cap circumflexcmb.cap ];

        - then, markClass attachments relating to those groups:
            markClass @mGC_above_0_495 <anchor 0 495> @MC_above;
            markClass @mGC_above_0_690 <anchor 0 690> @MC_above;

        - finally, markClass attachments relating to single glyphs:
            markClass cedillacmb <anchor 0 0> @MC_base;
            markClass horncmb <anchor 0 475> @MC_horn;

        '''
        group_definitions = []
        group_attachments = []
        single_attachments = []

        for group_def, group_attachment, single_attachment in mark_class_list:
            if group_def:
                group_definitions.extend(group_def)
            if group_attachment:
                group_attachments.extend(group_attachment)
            if single_attachment:
                single_attachments.extend(single_attachment)

        output = []
        for content in [group_definitions, group_attachments, single_attachments]:
            if content:
                output.extend(sorted(content) + [''])
        return output

    def make_lookup_wrappers(self, anchor_name, lookup_prefix, mkmk=False):
        '''
        make the fences the lookup is surrounded by - something like
        lookup MARK_BASE_above {
        } MARK_BASE_above;
        '''
        rtl = anchor_name.endswith(('AR', 'HE', 'RTL'))

        lookup_flag = ['lookupflag']
        if rtl:
            lookup_flag.append('RightToLeft')

        if mkmk:
            lookup_flag.append(f'MarkAttachmentType @MC_{anchor_name}')

        if not any([mkmk, rtl]):
            lookup_flag = None

        lookup_name = f'{lookup_prefix}{anchor_name}'
        open_lookup = f'lookup {lookup_name} {{'
        if lookup_flag:
            open_lookup += '\n\t' + ' '.join(lookup_flag) + ';\n'
        close_lookup = f'}} {lookup_name};'

        return open_lookup, close_lookup

    def make_mark_lookup(self, anchor_name, a_mate):

        open_lookup, close_lookup = self.make_lookup_wrappers(
            anchor_name, 'MARK_BASE_')
        pos_to_gname = []
        for position, g_list in a_mate.pos_name_dict.items():
            pos_to_gname.append((position, self.sort_gnames(g_list)))

        pos_to_gname.sort(key=lambda x: self.glyph_order[x[1][0]])
        # data looks like this:
        # [((235, 506), ['tonos']), ((269, 506), ['dieresistonos'])]

        mgroup_definitions = []
        mgroup_attachments = []
        single_attachments = []

        for position, g_names in pos_to_gname:
            position_string = self.adapter.anchor_position_string(position)
            if len(g_names) > 1:
                sorted_g_names = self.sort_gnames(g_names)
                # GNUFL introduces the colon as part of the glyph name,
                # e.g. thai:kokai, which breaks group names.
                safe_group_name = sorted_g_names[0].replace(':', '_')
                group_name = f'@bGC_{safe_group_name}_{anchor_name}'

                group_glyphs = ' '.join(sorted_g_names)
                mgroup_definitions.append(
                    f'\t{group_name} = [ {group_glyphs} ];')
                mgroup_attachments.append(
                    f'\tpos base {group_name} <anchor {position_string}> '
                    f'mark @MC_{anchor_name};')

            else:
                g_name = g_names[0]
                single_attachments.append(
                    # pos base AE <anchor 559 683> mark @MC_above;
                    f'\tpos base {g_name} <anchor {position_string}> '
                    f'mark @MC_{anchor_name};')

        output = [open_lookup]

        if mgroup_definitions:
            output.append('\n'.join(mgroup_definitions))
            output.append('\n'.join(mgroup_attachments))
        if single_attachments:
            output.append('\n'.join(single_attachments))

        output.append(close_lookup)

        return '\n'.join(output)

    def make_liga_lookup(self, anchor_name, gname_index_dict):
        open_lookup, close_lookup = self.make_lookup_wrappers(
            anchor_name, 'MARK_LIGATURE_')

        sorted_g_names = self.sort_gnames(list(gname_index_dict.keys()))
        liga_attachments = []
        for g_name in sorted_g_names:
            liga_attachment = f'\tpos ligature {g_name}'
            for a_index, position in sorted(gname_index_dict[g_name].items()):
                position_string = self.adapter.anchor_position_string(position)
                if a_index == 0:
                    liga_attachment += (
                        f' <anchor {position_string}> '
                        f'mark @MC_{anchor_name}')
                else:
                    liga_attachment += (
                        f' ligComponent <anchor {position_string}> '
                        f'mark @MC_{anchor_name}')
            liga_attachment += ';'
            liga_attachments.append(liga_attachment)

        output = [open_lookup]
        output.append('\n'.join(liga_attachments))
        output.append(close_lookup)

        return '\n'.join(output)

    def make_mkmk_lookup(self, anchor_name, a_mate):

        open_lookup, close_lookup = self.make_lookup_wrappers(
            anchor_name, 'MKMK_MARK_', mkmk=True)

        pos_to_gname = []
        for position, g_list in a_mate.pos_name_dict.items():
            pos_to_gname.append((position, self.sort_gnames(g_list)))

        pos_to_gname.sort(key=lambda x: self.glyph_order[x[1][0]])
        mkmk_attachments = []

        for position, g_names in pos_to_gname:
            position_string = self.adapter.anchor_position_string(position)
            sorted_g_names = self.sort_gnames(g_names)
            for g_name in sorted_g_names:
                mkmk_attachments.append(
                    # pos mark acmb <anchor 0 763> mark @MC_above;
                    f'\tpos mark {g_name} <anchor {position_string}> '
                    f'mark @MC_{anchor_name};')

        output = [open_lookup]
        output.append('\n'.join(mkmk_attachments))
        output.append(close_lookup)

        return '\n'.join(output)


def main(test_args=None):
    args = get_args(test_args)
    MarkFeatureWriter(args)


if __name__ == '__main__':
    main()


# constants from contextual mark feature writer, to be included in future iterations
# kPREMarkFileName = "mark-pre.fea"
# kPOSTMarkFileName = "mark-post.fea"
# kCasingTagsList = ['LC', 'UC', 'SC', 'AC']
# kIgnoreAnchorTag = "CXT"
