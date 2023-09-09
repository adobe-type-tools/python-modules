#!/usr/bin/env python3

'''
Current draft for modernized mark feature writer module.
This work is incomplete (i.e. support for Indic mark features still
needs to be added).
'''

import sys
import argparse
from defcon import Font
from pathlib import Path


class Defaults(object):
    """
    default values
    These can be overridden via argparse.
    """

    def __init__(self):

        # self.input_file
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

    def asdict(self):
        return self.__dict__


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


def trim_anchor_name(anchor_name):
    suffixes = ['UC', 'LC', 'SC']
    for suffix in suffixes:
        if anchor_name.endswith(suffix):
            trimmed_name = anchor_name.replace(suffix, '')
            return trimmed_name
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

        ufo_path = Path(args.input_file)
        ufo_dir = ufo_path.parent
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

        f = Font(ufo_path)
        self.glyph_order = f.lib['public.glyphOrder']

        combining_anchor_dict = {}
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
            a.name for g in combining_marks for a in g.anchors if
            a.name.startswith('_')])
        if self.trim_tags:
            combining_anchor_names = [
                trim_anchor_name(a_name) for a_name in combining_anchor_names]

        mkmk_anchor_dict = {}
        mkmk_marks = [g for g in combining_marks if not all(
            [anchor.name.startswith('_') for anchor in g.anchors])]

        base_glyph_anchor_dict = {}
        base_glyphs = [
            g for g in f if
            g.anchors and
            g not in combining_marks and
            g.width != 0 and
            not all([anchor.name.startswith('_') for anchor in g.anchors])
        ]

        for g in combining_marks:
            for anchor in g.anchors:
                if self.trim_tags:
                    anchor_name = trim_anchor_name(anchor.name)
                else:
                    anchor_name = anchor.name

                position = round_coordinate((anchor.x, anchor.y))
                am = combining_anchor_dict.setdefault(
                    anchor_name, AnchorMate(anchor))
                am.pos_name_dict.setdefault(position, []).append(g.name)

        for g in base_glyphs:
            for anchor in g.anchors:
                if self.trim_tags:
                    anchor_name = trim_anchor_name(anchor.name)
                else:
                    anchor_name = anchor.name

                position = round_coordinate((anchor.x, anchor.y))

                # only consider anchors that have an attachment equivalent
                # in the combining mark glyphs
                attaching_anchor_name = '_' + anchor_name
                if attaching_anchor_name in combining_anchor_names:
                    am = base_glyph_anchor_dict.setdefault(
                        anchor_name, AnchorMate(anchor))
                    am.pos_name_dict.setdefault(position, []).append(g.name)

        for g in mkmk_marks:
            for anchor in g.anchors:
                if self.trim_tags:
                    anchor_name = trim_anchor_name(anchor.name)
                else:
                    anchor_name = anchor.name

                position = round_coordinate((anchor.x, anchor.y))
                am = mkmk_anchor_dict.setdefault(
                    anchor_name, AnchorMate(anchor))
                am.pos_name_dict.setdefault(position, []).append(g.name)

        # mark classes
        mark_class_list = []
        for anchor_name, a_mate in sorted(combining_anchor_dict.items()):
            if anchor_name.startswith('_'):
                # write the class if a corresponding base anchor exists.
                if base_glyph_anchor_dict.get(anchor_name[1:]):
                    mc = self.make_mark_class(anchor_name, a_mate)
                    mark_class_list.append(mc)
                # if not, do not write it and complain.
                else:
                    print(
                        f'anchor {anchor_name} does not have a corresponding '
                        'base anchor.')

        mark_class_content = self.make_mark_classes_content(mark_class_list)

        # mark feature
        mark_feature_content = []
        for anchor_name, a_mate in sorted(base_glyph_anchor_dict.items()):
            mark_lookup = self.make_mark_lookup(anchor_name, a_mate)
            mark_feature_content.append(mark_lookup)
            mark_feature_content.append('\n')

        # mkmk feature
        mkmk_feature_content = []
        for anchor_name, a_mate in sorted(mkmk_anchor_dict.items()):
            if not anchor_name.startswith('_'):
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

        # write the mark feature
        consolidated_content.extend(mark_feature_content)

        if self.write_mkmk:
            # write mkmk only if requested, in the adjacent mkmk.fea file
            write_output(ufo_dir, self.mkmk_file, mkmk_feature_content)

        write_output(ufo_dir, self.mark_file, consolidated_content)

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
        The make_mark_class method returns a tuple of three lists per
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

    def make_mark_lookup(self, anchor_name, a_mate):

        lookup_name = f'MARK_BASE_{anchor_name}'
        open_lookup = f'lookup {lookup_name} {{'
        close_lookup = f'}} {lookup_name};'

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

    def make_mkmk_lookup(self, anchor_name, a_mate):
        lookup_name = f'MKMK_MARK_{anchor_name}'
        open_lookup = (
            f'lookup {lookup_name} {{\n'
            f'\tlookupflag MarkAttachmentType @MC_{anchor_name};\n')
        close_lookup = f'}} {lookup_name};'

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

# constants from contextual mark feature writer, to be included in future
# iterations
# kPREMarkFileName = "mark-pre.fea"
# kPOSTMarkFileName = "mark-post.fea"
# kLigaturesClassName = "LIGATURES_WITH_%d_COMPONENTS"  # The '%d' part is required
# kCasingTagsList = ['LC', 'UC', 'SC', 'AC']  # All the tags must have the same number of characters, and that number must be equal to kCasingTagSize
# kCasingTagSize = 2
# kRTLtagsList = ['_AR', '_HE']  # Arabic, Hebrew
# kIgnoreAnchorTag = "CXT"
# kLigatureComponentOrderTags = ['1ST', '2ND', '3RD', '4TH']  # Add more as necessary to a maximum of 9 (nine)

# kIndianAboveMarks = "abvm"
# kIndianBelowMarks = "blwm"
