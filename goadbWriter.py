#!/usr/bin/env python3

'''
GOADB writer -- write a GlyphOrderAndAliasDB file using a UFO as an input.

More reading on the GOADB format:
https://github.com/adobe-type-tools/afdko/issues/1662
https://github.com/adobe-type-tools/afdko/issues/1273


'''

import argparse
import re
from afdko import agd, fdkutils
from pathlib import Path
from defcon import Font, Glyph


def _check_input_file(parser, file_name):
    fn = Path(file_name)
    if fn.suffix.lower() != '.ufo':
        parser.error(f'{fn.name} is not a UFO file')
    if not fn.exists():
        parser.error(f'{fn.name} does not exist')
    return file_name


def _get_args(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        '-t', '--template',
        action='store_true',
        default=False,
        help='include template glyphs in GOADB',
    )

    parser.add_argument(
        '-o', '--output',
        action='store',
        help=(
            'output file or directory. '
            'If not defined, the GOABD is written to stdout.'),
        type=Path,
        metavar='PATH',
        default=None,
    )

    parser.add_argument(
        'input_ufo',
        type=lambda f: _check_input_file(parser, f),
        action='store',
        help='UFO file',
    )

    return parser.parse_args(args)


def _load_agd_data():
    '''
    read and load the AGD.txt file
    '''
    agd_txt = Path(fdkutils.get_resources_dir()) / 'AGD.txt'

    with open(agd_txt, "r") as agd_blob:
        agd_data = agd_blob.read()

    # This object is called “dictionary”, but it doesn’t have dict methods.
    # However, it contains two dicts -- .glyphs and .unicode.
    return agd.dictionary(agd_data)


def _make_agd_dict():
    '''
    AGD glyph name mapped to final name (often equivalent to the AGD name),
    and codepoint.

    Mappings to private us codepoints (and mappings to esoteric final names)
    are deliberately omitted.
    '''
    agd_data = _load_agd_data()
    rx_uni_name = r'^(?:u|uni)([0-9A-F]{4,16})$'
    # (?:u|uni): the ?: is flagging a non-capturing group
    # the AGD may contains final names which combine multiple code points,
    # such as uni093F0930094D0902
    agd_name_dict = {}

    private_use = (
        set(range(0xe000, 0xf8ff + 1)) |
        set(range(0xf0000, 0xffffd + 1)) |
        set(range(0x100000, 0x10fffd + 1)))

    for gname, agdglyph in agd_data.glyphs.items():
        if agdglyph.uni and not agdglyph.fin:
            gname_final = gname
            # The friendly name is equivalent to the final name.
            # makeotf will know which code point to assign
            # based on the name alone
            codepoint = int(agdglyph.uni, 16)
            if codepoint not in private_use:
                agd_name_dict[gname] = gname_final, codepoint
            else:
                pass
            #     130 (irrelevant) PUA glyphs, such as
            #     ae.sc F7E6
            #     aacute.sc F7E1
            # The AGD contains a number of private use code points.
            # Those are outdated, we do not need to consider them.

        elif agdglyph.uni and agdglyph.fin:
            gname_final = agdglyph.fin
            # makeotf knows that a specific name is associated with a certain
            # code point, but comparefamily complains about a “working name”
            # being assigned. This includes florin, for example.
            uni_match = re.match(rx_uni_name, agdglyph.fin)
            if uni_match:
                codepoint = int(uni_match.group(1), 16)
                if codepoint not in private_use:
                    agd_name_dict[gname] = gname_final, codepoint
                else:
                    pass
                    # 25 PUA glyphs such as
                    # LL F6BF
                    # arrowhorizex F8E7
                    # arrowvertex F8E6
                    # braceex F8F4
            else:
                # mostly, glyph names with suffixed/ligated final names.
                # except
                # triangleblackdown 25BC
                # pointerblackleft 25C4
                # pointerblackright 25BA
                # triangleblackup 25B2
                codepoint = int(agdglyph.uni, 16)
                gname_final = agdglyph.fin
                if codepoint not in private_use:
                    agd_name_dict[gname] = gname_final, codepoint
                else:
                    pass
                    # 16 PUA glyphs such as
                    # emdash.alt F6DE
                    # rupiah F6DD
                    # dieresisacute.cap F6CC

        elif not agdglyph.uni and agdglyph.fin:
            gname_final = agdglyph.fin
            # some glyphs may have a preferred final name, such as
            # Gtilde (which combines two code points): uni00470303
            # Rringbelowmacron (three code points): uni005203250304
            uni_match = re.match(rx_uni_name, agdglyph.fin)
            agd_name_dict[gname] = gname_final, None

        else:
            pass
            # 1635 glyph names.
            # as far as I can tell, these are either
            # - PUA code points
            # - ligatures
            # - dotted alternates
            # - glyph names without any aliasing (and therefore no function)
            #   (like TimeFlies, WingedHead1, or ObeseAngel)

    return agd_name_dict


# inspired by
# https://github.com/fonttools/fonttools/blob/main/Lib/fontTools/agl.py#L5107
AGD_DICT = _make_agd_dict()


def get_glyph_order(f, include_template_glyphs=False):
    '''
    Figure out the glyph order of a UFO file.
        * make sure .notdef is first,
        * respect skipExportGlyphs,
        * include (un-filled) template glyphs if desired

    In the case that the public.glyphOrder key does not exist, resort to
    unrefined sorting:
        * encoded glyphs: by code point
        * unencoded glyphs: following code point sorting, deduced by glyph name
        * remaining unencoded glyphs: alphabetically by name (for the rest)

    NB: defcon and RF have different ways of determining template glyphs.
        in defcon, `f.glyphOrder` includes template glyphs
        in RF, `f.glyphOrder` excludes them
    '''

    glyph_order = f.glyphOrder
    skip = f.lib.get('public.skipExportGlyphs', [])
    if glyph_order:
        if include_template_glyphs:
            order_wo_notdef = [
                gn for gn in glyph_order if
                gn != '.notdef' and
                gn not in skip]
        else:
            # only filled-in glyphs, not template glyphs
            order_wo_notdef = [
                gn for gn in glyph_order if
                gn in f.keys() and
                gn != '.notdef' and
                gn not in skip
            ]

        order = ['.notdef'] + order_wo_notdef

    else:
        # first, all encoded glyphs are sorted by code point
        # then, the rest is sorted alphabetically.

        # all glyphs
        glyphs_encoded = sorted(
            [g for g in f if g.unicode], key=lambda g: g.unicode)
        gnames_encoded = [g.name for g in glyphs_encoded]

        glyphs_unencoded = [
            g for g in f if g.unicode is None and g.name != '.notdef']

        # more specific sub-groups:
        # glyphs which alternates of the encoded glyphs
        glyphs_alternates = [
            g for g in glyphs_unencoded if
            g.name.split('.')[0] in gnames_encoded]
        # sort names by their suffix first,
        # then by the order of related names of encoded glyphs.
        gnames_alternates = sorted(
            [g.name for g in glyphs_alternates],
            key=lambda gn:
                (gn.split('.')[1], gnames_encoded.index(gn.split('.')[0])))

        # glyphs not related to encoded glyphs are sorted alphabetically
        glyphs_rest = [
            g for g in glyphs_unencoded if g not in glyphs_alternates]
        gnames_rest = sorted([g.name for g in glyphs_rest])

        order = ['.notdef'] + gnames_encoded + gnames_alternates + gnames_rest

    return order


def make_uni_gname(cp):
    '''
    convert codepoint to uniXXXX (or uXXXXX) glyph name
    '''
    if cp <= 0xFFFF:
        uni_name = f'uni{cp:0>4X}'
    else:
        uni_name = f'u{cp:0>5X}'
    return uni_name


def _make_uni_override(cp_list):
    '''
    comma-separated Unicode override string
    (or a single string if len(cp_list) == 1)
    '''
    unicode_override = ','.join([make_uni_gname(cp) for cp in cp_list])
    return unicode_override


def _make_unique_final_name(gname):
    '''
    Since final glyph names need to be sanitized, a duplication of
    names is possible. This adds a 4-digit index to the glyph name.

    If the glyph name already has a 4-digit index, the index is incremented.
    '''

    # glyph name already has an index
    index_match = re.match(r'(.+?)(\d{4})', gname)
    if index_match:
        gname_stem = index_match.group(1)
        index = int(index_match.group(2)) + 1
    # no index yet
    else:
        gname_stem = gname
        index = 0
    return f'{gname_stem}{index:0>4}'


def sanitize_final_gname(gname):
    '''
    The following characters are allowed in friendly- but not final names:
        U+002A * asterisk
        U+002B + plus sign
        U+002D - hyphen-minus
        U+003A : colon
        U+005E ^ circumflex accent
        U+007C | vertical bar
        U+007E ~ tilde

    In addition to that, final glyph names
        * may not start with a period
        * may not start with a digit

    see also
    https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#2fi-glyph-name
    '''
    sorts = '*+-:^|~._'
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digits = '0123456789'

    # remove any unexpected chars
    chars_allowed = (alphabet + alphabet.lower() + digits + sorts)
    chars_illegal = sorted(set(gname) - set(chars_allowed))
    if chars_illegal:
        for char in chars_illegal:
            gname = gname.replace(char, '')

    # remove any chars not allowed in final names
    for char in '*+-:^|~':
        gname = gname.replace(char, '')

    # make sure final name does not start with period (except .notdef)
    if gname.startswith('.') and gname != '.notdef':
        gname = gname[1:]

    # make sure name does not start with digit
    figure_match = re.match(r'\d+?(\D*)', gname)
    if figure_match:
        gname = figure_match.group(1)

    if gname == '':  # nothing left, original name all digits (or illegal)
        gname = 'dummy'

    return gname


def _dummy_glyph(f, gname):
    '''
    make sure a glyph object is present -- no matter if it exists in the UFO
    or not.
    '''
    try:
        # glyph exists in the UFO
        glyph = f[gname]
    except KeyError:
        # template glyph
        glyph = Glyph()
        glyph.name = gname
    return glyph


class GlyphBaptism(object):
    '''
    Simple deduction of final glyph name.
    (Deliberately ignoring ligatures and alternates here.)

    Considering either one of the following scenarios:
    - glyph name is in the AGD dict, makeotf associates the code point
    - glyph name is not in the AGD, but the glyph has attached code point(s)
    - glyph name implies a code point (uniXXXX or uXXXXX)
    - glyph is not encoded

    '''

    def __init__(self, gn_friendly, g=None, gn_final=None, cp_override=None):
        if g is None:
            self.glyph = Glyph()
        else:
            self.glyph = g

        self.gn_friendly = gn_friendly
        self.gn_final = gn_final
        self.cp_override = cp_override

        # this is the normal expectation for most glyphs
        if self.gn_final is None:
            self.assign_final_and_cp_override()
            self.gn_final = sanitize_final_gname(self.gn_final)

        # in other cases (alternates/ligatures), we generate the final name
        # outside, and use this object for data storage only.

    def assign_final_and_cp_override(self):
        is_agd_name = self.gn_friendly in AGD_DICT.keys()
        # The uni name is something like `uni0020`. In theory, the zero-padding
        # could be omitted (`uni20` -- although I have not seen that yet).
        # The last Unicode Plane (16) ends at 10FFFF, so allowing code points
        # up to FFFFFF should be enough.
        rx_uni_name = r'^(?:u|uni)([0-9A-F]{1,6})$'
        uni_name_match = re.match(rx_uni_name, self.gn_friendly)

        # glyph name is in AGD
        if is_agd_name:
            agd_final, agd_cp = AGD_DICT.get(self.gn_friendly)
            if self.glyph.unicodes == []:
                # no codepoint assigned to glyph, codepoint will be assigned
                # through the glyph name only (or, in some cases, the AGD
                # dict has a different final name)
                self.gn_final = agd_final
            elif len(self.glyph.unicodes) > 1:
                # glyph name is in AGD, but multiple code points attached;
                # override is needed
                self.gn_final = self.gn_friendly
                self.cp_override = _make_uni_override(self.glyph.unicodes)
            else:
                # just one codepoint
                expected_codepoint = agd_cp
                actual_codepoint = self.glyph.unicode
                if expected_codepoint == actual_codepoint:
                    # codepoint is the expected one.
                    self.gn_final = agd_final
                else:
                    # codepoint is different from what we expect
                    self.gn_final = make_uni_gname(self.glyph.unicode)

        # glyph name implies Unicode value (uniXXXX or uXXXXX)
        elif uni_name_match:
            cp_hex = uni_name_match.group(1)
            cp_int = int(cp_hex, 16)

            if self.glyph.unicodes == []:
                # no codepoint assigned to glyph, codepoint will be assigned
                # through the glyph name only
                # The glyph name could be uniFFFFF, which is not a legal final
                # name, so we are sending it through make_uni_gname.
                self.gn_final = make_uni_gname(cp_int)
            elif len(self.glyph.unicodes) > 1:
                # glyph name implies one code point, but multiple code points
                # are attached -- override needed.
                # Overriding a uniXXXX name used to be a makeotf problem, but
                # this has been solved here:
                # https://github.com/adobe-type-tools/afdko/pull/1615

                # The final name does not matter, because it is
                # overridden anyway.
                self.gn_final = self.gn_friendly
                self.cp_override = _make_uni_override(self.glyph.unicodes)
            else:
                # just one codepoint
                actual_codepoint = self.glyph.unicode
                if cp_int == actual_codepoint:
                    # codepoint is the expected one. Name could be uniFFFFF,
                    # which makeotf only understands as uFFFFF.
                    self.gn_final = make_uni_gname(cp_int)
                else:
                    # codepoint is different from what the name implies
                    # (weird flex but OK)
                    self.gn_final = make_uni_gname(self.glyph.unicode)

        # custom glyph name
        else:
            if self.glyph.unicodes == []:
                # no codepoint assigned to glyph, unencoded glyph
                self.gn_final = self.gn_friendly
            elif len(self.glyph.unicodes) > 1:
                # multiple code points are attached -- override needed
                self.gn_final = self.gn_friendly
                self.cp_override = _make_uni_override(self.glyph.unicodes)
            else:
                # just one codepoint, the final name will tell makeotf about it
                self.gn_final = make_uni_gname(self.glyph.unicode)


def _fill_gn_dict(gb, glyph_name_dict):
    '''
    This slightly awkward method of adding values to a dictionary ensures that
    the final glyph name is unique.
    '''
    final_name = gb.gn_final
    while final_name in [gb.gn_final for gb in glyph_name_dict.values()]:
        final_name = _make_unique_final_name(final_name)
    gb.gn_final = final_name
    glyph_name_dict[gb.gn_friendly] = gb
    return glyph_name_dict


def _make_glyph_name_dict(f, glyph_order):
    '''
    make a dictionary:
        {friendly name: gb object}

    the gb (GlyphBaptism) object contains:
        .gn_final (name)
        .gn_friendly (name)
        .cp_override (unicode override(s) as a string)
        .glyph (glyph object)
    '''

    glyph_name_dict = {
        '.notdef': GlyphBaptism('.notdef', gn_final='.notdef')
    }

    # break the glyphs down into three categories:
    # 1. any glyphs that are neither ligatures nor alternates
    # 2. alternate glyphs (which are not also ligatures) (. but not _ in name)
    # 3. ligatures (_ in name)

    # The thinking behind (2) is that ligatures like f_f_l.alt are possible.
    # It’s a bit of a confusing glyph name -- does this mean that l is an
    # alternate, or is it an alternate ligature in itself?
    # I interpret it as a combination of two fs and one l.alt.

    base_glyphs = [gn for gn in glyph_order if not any(['.' in gn, '_' in gn])]
    alt_glyphs = [
        gn for gn in glyph_order if '.' in gn and '_' not in gn and
        gn != '.notdef']
    liga_glyphs = [gn for gn in glyph_order if '_' in gn]

    for gn in base_glyphs:
        g = _dummy_glyph(f, gn)
        gb = GlyphBaptism(g.name, g)
        glyph_name_dict = _fill_gn_dict(gb, glyph_name_dict)

    for gn in alt_glyphs:
        g = _dummy_glyph(f, gn)
        stem, suffixes = g.name.split('.', 1)
        if stem in glyph_name_dict:
            final_name_stem = glyph_name_dict.get(stem).gn_final
            final_name = f'{final_name_stem}.{suffixes}'
            gb = GlyphBaptism(g.name, g, gn_final=final_name)

        else:
            gb = GlyphBaptism(g.name, g)
            final_name = gb.gn_final

        if g.unicodes:
            # the alt glyph itself may have a codepoint
            gb.cp_override = _make_uni_override(g.unicodes)

        glyph_name_dict = _fill_gn_dict(gb, glyph_name_dict)

    for gn in liga_glyphs:
        g = _dummy_glyph(f, gn)
        liga_chunks = g.name.split('_')
        liga_chunks_final = []
        for chunk in liga_chunks:
            if chunk in glyph_name_dict:
                # chunk with known glyph name
                final_name_chunk = glyph_name_dict.get(chunk).gn_final
            else:
                # chunk with unknown glyph name
                final_name_chunk = GlyphBaptism(chunk).gn_final
            liga_chunks_final.append(final_name_chunk)
        final_name = '_'.join(liga_chunks_final)
        gb = GlyphBaptism(g.name, g, gn_final=final_name)

        if g.unicodes:
            # some ligatures have codepoints
            gb.cp_override = _make_uni_override(g.unicodes)

        glyph_name_dict = _fill_gn_dict(gb, glyph_name_dict)

    return glyph_name_dict


def _make_goadb_content(glyph_order, glyph_name_dict):
    goadb = []
    for gname in glyph_order:
        gb = glyph_name_dict.get(gname)
        goadb_line = [gb.gn_final, gb.gn_friendly]
        if gb.cp_override:
            goadb_line.append(gb.cp_override)
        goadb.append('\t'.join(goadb_line))
    return '\n'.join(goadb)


def make_goadb(input_ufo, include_template_glyphs=False):
    '''
    Make a GOADB from an input UFO.
    Optionally, template glyphs can be included.
    '''
    f = Font(input_ufo)
    glyph_order = get_glyph_order(f, include_template_glyphs)
    glyph_name_dict = _make_glyph_name_dict(f, glyph_order)
    goadb_content = _make_goadb_content(glyph_order, glyph_name_dict)
    return goadb_content


def write_goadb(goadb_content, output_path=None):
    '''
    Write the GOADB to an output file or folder.
    '''
    if output_path and output_path.is_file():
        with open(output_path, 'w') as blob:
            blob.write(goadb_content + '\n')
    elif output_path and output_path.is_dir():
        with open(output_path / 'GlyphOrderAndAliasDB', 'w') as blob:
            blob.write(goadb_content + '\n')
    else:
        print(goadb_content)


def main(test_args=None):
    args = _get_args(test_args)
    goadb_content = make_goadb(args.input_ufo, args.template)
    write_goadb(goadb_content, args.output_path)


if __name__ == '__main__':
    main()
