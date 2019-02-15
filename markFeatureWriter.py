#!/usr/bin/env python3

'''
First draft of a modernized mark feature writer module.
This work is incomplete (i.e. argparse needs to be hooked up).
The anchor_name_no_underscore process is odd and was added to patch a bug.
'''

from __future__ import print_function
import os
import sys
import math
# import argparse
from defcon import Font

TRIM_TAGS = True


class AnchorMate(object):
    """
    AnchorMate lifts anchors from one or more glyphs and
    sorts them in a dictionary {a_position: gName}
    """

    def __init__(self, anchor):
        # self.name = anchor.name
        self.pos_name_dict = {}


def write_output(directory, file_name, data):
    f_path = os.path.join(directory, file_name)
    with open(f_path, 'w') as of:
        of.write(data)
    print('writing {}'.format(file_name))


def italic_x_offset(y_dist, angle):
    if angle:
        angle = math.radians(angle)
        x_offset = math.tan(-angle) * y_dist
        return int(round(x_offset))
    return 0


def sort_gnames(glyph_list):
    glyph_list.sort(key=lambda x: GLYPH_ORDER.index(x))
    return glyph_list


def trim_anchor_name(anchor_name):
    suffixes = ['UC', 'LC', 'SC']
    for suffix in suffixes:
        if anchor_name.endswith(suffix):
            trimmed_name = anchor_name.replace(suffix, '')
            return trimmed_name
    return anchor_name


def make_one_mark_class(anchor_name, a_mate):
    pos_gname = sorted(a_mate.pos_name_dict.items())
    mgroup_definitions = []
    mgroup_attachments = []
    single_attachments = []

    for position, g_names in pos_gname:
        pos_x, pos_y = position
        if len(g_names) > 1:
            sorted_g_names = sort_gnames(g_names)
            group_name = '@mgC{}_{}_{}'.format(
                anchor_name,
                str(pos_x).replace('-', 'n'),
                str(pos_y).replace('-', 'n'))
            group_list = ' '.join(sorted_g_names)
            mgroup_definitions.append('{} = [ {} ];'.format(
                group_name, group_list))
            mgroup_attachments.append(
                'markClass {} <anchor {} {}> @MC{};'.format(
                    group_name, pos_x, pos_y, anchor_name))

        else:
            g_name = g_names[0]
            single_attachments.append(
                'markClass {} <anchor {} {}> @MC{};'.format(
                    g_name, pos_x, pos_y, anchor_name))

    return mgroup_definitions, mgroup_attachments, single_attachments


def make_mark_class_output(list_of_lists):
    '''
    The make_one_mark_class method returns a tuple of three lists per anchor,
    which may have data or not. Here those lists are assembled into a neatly,
    organized text string ready for writing in a file.
    '''
    top = []
    mid = []
    bot = []
    for sublist in list_of_lists:
        group_def, group_att, single_att = sublist
        if group_def:
            top.extend(group_def)
        if group_att:
            mid.extend(group_att)
        if single_att:
            bot.extend(single_att)

    output = []
    output.extend(top)
    output.extend([''])
    output.extend(mid)
    output.extend([''])
    output.extend(bot)
    output.extend([''])
    return '\n'.join(output)


def make_mark_feature_lookup(anchor_name, a_mate):

    lookup_name = 'MARK_BASE_{}'.format(anchor_name)
    open_lookup = 'lookup {} {{'.format(lookup_name)
    close_lookup = '}} {};'.format(lookup_name)

    pos_to_gname = []
    for position, g_list in a_mate.pos_name_dict.items():
        pos_to_gname.append((position, sort_gnames(g_list)))

    pos_to_gname.sort(key=lambda x: GLYPH_ORDER.index(x[1][0]))

    mgroup_definitions = []
    mgroup_attachments = []
    single_attachments = []

    anchor_name_no_underscore = anchor_name.replace('_', '')

    for position, g_names in pos_to_gname:
        pos_x, pos_y = position
        if len(g_names) > 1:
            sorted_g_names = sort_gnames(g_names)
            group_name = '@bGC_{}_{}'.format(
                sorted_g_names[0], anchor_name_no_underscore)
            group_list = ' '.join(sorted_g_names)
            mgroup_definitions.append('\t{} = [ {} ];'.format(
                group_name, group_list))
            mgroup_attachments.append(
                '\tpos base {} <anchor {} {}> mark @MC_{};'.format(
                    group_name, pos_x, pos_y, anchor_name_no_underscore))

        else:
            g_name = g_names[0]
            single_attachments.append(
                # pos base AE <anchor 559 683> mark @MC_above;
                '\tpos base {} <anchor {} {}> mark @MC_{};'.format(
                    g_name, pos_x, pos_y, anchor_name_no_underscore))

    output = [open_lookup]

    if mgroup_definitions:
        output.append('\n'.join(mgroup_definitions))
        output.append('\n'.join(mgroup_attachments))
    if single_attachments:
        output.append('\n'.join(single_attachments))

    output.append(close_lookup)

    return '\n'.join(output)


def make_mkmk_feature_lookup(anchor_name, a_mate):
    lookup_name = 'MKMK_MARK_{}'.format(anchor_name)
    open_lookup = (
        'lookup {} {{\n'
        '\tlookupflag MarkAttachmentType @MC_{};\n'.format(
            lookup_name, anchor_name))
    close_lookup = '}} {};'.format(lookup_name)

    pos_to_gname = []
    for position, g_list in a_mate.pos_name_dict.items():
        pos_to_gname.append((position, sort_gnames(g_list)))

    pos_to_gname.sort(key=lambda x: GLYPH_ORDER.index(x[1][0]))
    mkmk_attachments = []

    for position, g_names in pos_to_gname:
        pos_x, pos_y = position
        sorted_g_names = sort_gnames(g_names)
        for g_name in sorted_g_names:
            mkmk_attachments.append(
                # pos mark acmb <anchor 0 763> mark @MC_above;
                '\tpos mark {} <anchor {} {}> mark @MC_{};'.format(
                    g_name, pos_x, pos_y, anchor_name))

    output = [open_lookup]
    output.append('\n'.join(mkmk_attachments))
    output.append(close_lookup)

    return '\n'.join(output)


if __name__ == '__main__':

    ufo_path = sys.argv[-1]
    ufo_dir = os.path.dirname(
        os.path.normpath(ufo_path)
    )
    print(os.path.dirname(ufo_path))
    f = Font(ufo_path)

    GLYPH_ORDER = f.lib['public.glyphOrder']

    combining_anchor_dict = {}
    combining_marks = [f[g_name] for g_name in f.groups.get('COMBINING_MARKS')]

    mkmk_anchor_dict = {}
    mkmk_marks = [g for g in combining_marks if not all(
        [anchor.name.startswith('_') for anchor in g.anchors])]

    base_glyph_anchor_dict = {}
    base_glyphs = [
        g for g in f if
        g.anchors and
        g not in combining_marks and
        g.width != 0]

    for g in combining_marks:
        for anchor in g.anchors:
            if TRIM_TAGS:
                anchor_name = trim_anchor_name(anchor.name)
            else:
                anchor_name = anchor.name

            position = (anchor.x, anchor.y)
            am = combining_anchor_dict.setdefault(
                anchor_name, AnchorMate(anchor))
            am.pos_name_dict.setdefault(position, []).append(g.name)

    for g in base_glyphs:
        for anchor in g.anchors:
            if TRIM_TAGS:
                anchor_name = trim_anchor_name(anchor.name)
            else:
                anchor_name = anchor.name

            position = (anchor.x, anchor.y)
            am = base_glyph_anchor_dict.setdefault(
                anchor_name, AnchorMate(anchor))
            am.pos_name_dict.setdefault(position, []).append(g.name)

    for g in mkmk_marks:
        for anchor in g.anchors:
            if TRIM_TAGS:
                anchor_name = trim_anchor_name(anchor.name)
            else:
                anchor_name = anchor.name

            position = (anchor.x, anchor.y)
            am = mkmk_anchor_dict.setdefault(anchor_name, AnchorMate(anchor))
            am.pos_name_dict.setdefault(position, []).append(g.name)

    # markclasses.fea
    mark_class_content = []
    for anchor_name, a_mate in sorted(combining_anchor_dict.items()):
        if anchor_name.startswith('_'):
            mc = make_one_mark_class(anchor_name, a_mate)
            mark_class_content.append(mc)

    mark_class_output = make_mark_class_output(mark_class_content)
    write_output(ufo_dir, 'markclasses.fea', mark_class_output)

    # mark.fea
    mark_feature_content = []
    for anchor_name, a_mate in sorted(base_glyph_anchor_dict.items()):
        mark_lookup = make_mark_feature_lookup(anchor_name, a_mate)
        mark_feature_content.append(mark_lookup)
        mark_feature_content.append('\n')

    mark_feature_output = '\n'.join(mark_feature_content)
    write_output(ufo_dir, 'mark.fea', mark_feature_output)

    # mkmk.fea
    mkmk_feature_content = []
    for anchor_name, a_mate in sorted(mkmk_anchor_dict.items()):
        if not anchor_name.startswith('_'):
            mkmk_lookup = make_mkmk_feature_lookup(anchor_name, a_mate)
            mkmk_feature_content.append(mkmk_lookup)
            mkmk_feature_content.append('\n')

    mkmk_feature_output = '\n'.join(mkmk_feature_content)
    write_output(ufo_dir, 'mkmk.fea', mkmk_feature_output)
