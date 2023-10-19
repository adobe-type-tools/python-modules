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

    # write a basic mark feature
    python markFeatureWriter.py font.ufo

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
from defcon import Font
from pathlib import Path

# ligature anchors end with 1ST, 2ND, 3RD, etc.
ORDINALS = ['1ST', '2ND', '3RD'] + [f'{i}TH' for i in range(4, 10)]


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


def get_args(args=None):

    defaults = Defaults()
    parser = argparse.ArgumentParser(
        description=(
            'Mark Feature Writer'
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'input_file',
        help='input UFO file')

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


def round_coordinate(coordinate):
    rounded_coordinate = tuple(int(round(v)) for v in coordinate)
    return rounded_coordinate


class AnchorMate(object):
    '''
    AnchorMate lifts anchors from one or more glyphs and
    sorts them in a dictionary {a_position: gName}
    '''

    def __init__(self, anchor):
        self.pos_name_dict = {}


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
            ufo_path = Path(args.input_file)
            self.run(ufo_path)

    def run(self, ufo_path):
        f = Font(ufo_path)
        ufo_dir = ufo_path.parent
        self.glyph_order = f.lib['public.glyphOrder']

        combining_marks_group = f.groups.get(self.mkgrp_name, [])
        if not combining_marks_group:
            sys.exit(
                f'No group named "{self.mkgrp_name}" found. '
                'Please add it to your UFO file '
                '(and combining marks to it).'
            )

        combining_marks = [f[g_name] for g_name in combining_marks_group]
        # find out which attachment anchors exist in combining marks
        combining_anchor_names = set([
            process_anchor_name(a.name, self.trim_tags) for
            g in combining_marks for a in g.anchors if is_attaching(a.name)])

        mkmk_marks = [g for g in combining_marks if not all(
            [is_attaching(anchor.name) for anchor in g.anchors])]

        base_glyphs = [
            g for g in f if
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
            write_output(ufo_dir, self.mkclass_file, mark_class_content)
        else:
            # otherwise they go on top of the mark.fea file
            consolidated_content.extend(mark_class_content)

        # add mark feature content
        consolidated_content.extend(mark_feature_content)

        if self.write_mkmk:
            # write mkmk only if requested, in the adjacent mkmk.fea file
            write_output(ufo_dir, self.mkmk_file, mkmk_feature_content)

        if self.indic_format:
            # write abvm/blwm in adjacent files.
            write_output(ufo_dir, self.abvm_file, abvm_feature_content)
            write_output(ufo_dir, self.blwm_file, blwm_feature_content)

        # write the mark feature
        write_output(ufo_dir, self.mark_file, consolidated_content)

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
                    position = round_coordinate((anchor.x, anchor.y))
                    index_pos_dict[anchor_index] = position
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
                position = round_coordinate((anchor.x, anchor.y))
                am = anchor_dict.setdefault(anchor_name, AnchorMate(anchor))
                am.pos_name_dict.setdefault(position, []).append(g.name)

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
        glyph_list.sort(key=lambda x: self.glyph_order.index(x))
        return glyph_list

    def make_mark_class(self, anchor_name, a_mate):
        pos_gname = sorted(a_mate.pos_name_dict.items())
        mgroup_definitions = []
        mgroup_attachments = []
        single_attachments = []

        for position, g_names in pos_gname:
            pos_x, pos_y = position
            if len(g_names) > 1:
                sorted_g_names = self.sort_gnames(g_names)
                # represent negative numbers with “n”, because minus is
                # reserved for ranges:
                str_x = str(pos_x).replace('-', 'n')
                str_y = str(pos_y).replace('-', 'n')
                group_name = f'@mGC{anchor_name}_{str_x}_{str_y}'
                group_glyphs = ' '.join(sorted_g_names)
                mgroup_definitions.append(
                    f'{group_name} = [ {group_glyphs} ];')
                mgroup_attachments.append(
                    f'markClass {group_name} <anchor {pos_x} {pos_y}> '
                    f'@MC{anchor_name};')

            else:
                g_name = g_names[0]
                single_attachments.append(
                    f'markClass {g_name} <anchor {pos_x} {pos_y}> '
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

        pos_to_gname.sort(key=lambda x: self.glyph_order.index(x[1][0]))
        # data looks like this:
        # [((235, 506), ['tonos']), ((269, 506), ['dieresistonos'])]

        mgroup_definitions = []
        mgroup_attachments = []
        single_attachments = []

        for position, g_names in pos_to_gname:
            pos_x, pos_y = position
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
                    f'\tpos base {group_name} <anchor {pos_x} {pos_y}> '
                    f'mark @MC_{anchor_name};')

            else:
                g_name = g_names[0]
                single_attachments.append(
                    # pos base AE <anchor 559 683> mark @MC_above;
                    f'\tpos base {g_name} <anchor {pos_x} {pos_y}> '
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
                pos_x, pos_y = position
                if a_index == 0:
                    liga_attachment += (
                        f' <anchor {pos_x} {pos_y}> '
                        f'mark @MC_{anchor_name}')
                else:
                    liga_attachment += (
                        f' ligComponent <anchor {pos_x} {pos_y}> '
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

        pos_to_gname.sort(key=lambda x: self.glyph_order.index(x[1][0]))
        mkmk_attachments = []

        for position, g_names in pos_to_gname:
            pos_x, pos_y = position
            sorted_g_names = self.sort_gnames(g_names)
            for g_name in sorted_g_names:
                mkmk_attachments.append(
                    # pos mark acmb <anchor 0 763> mark @MC_above;
                    f'\tpos mark {g_name} <anchor {pos_x} {pos_y}> '
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
