import defcon
import sys

from afdko.fdkutils import get_temp_dir_path
from pathlib import Path


sys.path.append("..")
from kernFeatureWriter import *


TEST_DIR = Path(__file__).parent
TEMP_DIR = Path(get_temp_dir_path())


class Dummy(object):
    '''
    for ad-hoc arguments
    '''
    pass


def read_file(path):
    '''
    Read a file, split lines into a list, close the file.
    '''

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().splitlines()
    return data


# unit tests
# ----------

def test_get_args():
    argparse_args = vars(get_args(['dummy']))  # args through argparse
    dummy_args = Defaults().__dict__  # hard-coded dummy arguments
    dummy_args['input_file'] = 'dummy'
    assert argparse_args == dummy_args


def test_make_header():
    kfw = run(None, None)
    dummy_args = Dummy()
    dummy_args.min_value = 1
    dummy_args.write_timestamp = False
    header = kfw.make_header(dummy_args)
    assert len(header) == 2
    assert header[0] == '# PS Name: None'
    dummy_args.write_timestamp = True
    header = kfw.make_header(dummy_args)
    assert header[0].startswith('# Created:')


def test_dict2pos():
    kfw = run(None, None)
    kfw.write_trimmed_pairs = False

    pv_dict = {
        ('A', 'V'): 3,
        ('A', 'X'): 2,
        ('A', 'A'): 1,
    }

    assert kfw._dict2pos(pv_dict) == (
        'pos A A 1;\n'
        'pos A V 3;\n'
        'pos A X 2;'
    )
    assert kfw._dict2pos(pv_dict, minimum=2) == (
        'pos A V 3;\n'
        'pos A X 2;'
    )
    assert kfw._dict2pos(pv_dict, rtl=True) == (
        'pos A A <1 0 1 0>;\n'
        'pos A V <3 0 3 0>;\n'
        'pos A X <2 0 2 0>;'
    )
    kfw.write_trimmed_pairs = True
    assert kfw._dict2pos(pv_dict, minimum=2) == (
        '# pos A A 1;\n'
        'pos A V 3;\n'
        'pos A X 2;'
    )


def test_remap_name():
    kp = KernProcessor()
    assert kp._remap_name('public.kern1.example') == '@MMK_L_example'
    assert kp._remap_name('public.kern1.@MMK_L_example') == '@MMK_L_example'
    assert kp._remap_name('public.kern2.example') == '@MMK_R_example'
    assert kp._remap_name('public.kern2.@MMK_R_example') == '@MMK_R_example'
    assert kp._remap_name('@example') == '@example'


def test_remap_groups():
    ufo_path = TEST_DIR / 'kern_example.ufo'
    f = defcon.Font(ufo_path)

    groups_l = {
        gr: gl for gr, gl in f.groups.items() if gr.startswith('public.kern1')}
    groups_r = {
        gr: gl for gr, gl in f.groups.items() if gr.startswith('public.kern2')}
    groups_other = {
        gr: gl for gr, gl in f.groups.items() if gr not in groups_l.keys() | groups_r.keys()}

    expected_groups_l = {
        gr.replace('public.kern1.', '@MMK_L_'): gl for gr, gl in groups_l.items()}
    expected_groups_r = {
        gr.replace('public.kern2.', '@MMK_R_'): gl for gr, gl in groups_r.items()}
    kp = KernProcessor()

    assert kp._remap_groups(groups_l) == expected_groups_l
    assert kp._remap_groups(groups_r) == expected_groups_r
    assert kp._remap_groups(groups_other) == groups_other


def test_remap_kerning():
    ufo_path = TEST_DIR / 'kern_example.ufo'
    f = defcon.Font(ufo_path)

    # https://stackoverflow.com/a/15175239
    import re
    remapped_pairs = []
    replacements = {
        'public.kern1.': '@MMK_L_',
        'public.kern2.': '@MMK_R_'
    }
    regex = re.compile("(%s)" % "|".join(map(re.escape, replacements.keys())))
    for pair in f.kerning.keys():
        new_pair = regex.sub(
            lambda mo: replacements[mo.group()], ' '.join(pair)).split()
        remapped_pairs.append(tuple(new_pair))

    kp = KernProcessor()
    assert list(kp._remap_kerning(f.kerning).keys()) == remapped_pairs


def test_sanityCheck(capsys):
    '''
    somehow trigger that sanity check (not sure how useful)
    '''
    ufo_path = TEST_DIR / 'kern_example.ufo'
    f = defcon.Font(ufo_path)
    kp = KernProcessor()
    kp.pairs_processed = ['some pair']
    kp.kerning = f.kerning
    kp._sanityCheck()
    out, err = capsys.readouterr()
    assert 'Something went wrong' in out


# integration tests
# -----------------

def test_no_kerning(capsys):
    ufo_path = TEST_DIR / 'kern_example.ufo'
    f = defcon.Font(ufo_path)
    f.kerning.clear()
    args = Defaults()
    run(f, args)
    out, err = capsys.readouterr()
    assert f'has no kerning' in out


def test_all_zero(capsys):
    ufo_path = TEST_DIR / 'kern_all_zero_value.ufo'
    f = defcon.Font(ufo_path)
    args = Defaults()
    run(f, args)
    out, err = capsys.readouterr()
    assert f'All kerning values are zero' in out


def test_default():
    '''
    normal LTR test with no options
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example.ufo'
    fea_example = TEST_DIR / 'kern_example.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)

    '''
    test with --dissolve_single option, which should not make a difference
    for this UFO (no single-item groups)
    '''
    args.dissolve_single = True
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_default_ufo2():
    '''
    normal LTR test for a UFO2 file
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example_ufo2.ufo'
    fea_example = TEST_DIR / 'kern_example.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_main():
    '''
    same as test_default, using the main() path into the module
    '''
    ufo_path = TEST_DIR / 'kern_example.ufo'
    fea_example = TEST_DIR / 'kern_example.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    main([str(ufo_path), '--output_name', str(fea_temp)])
    assert read_file(fea_example) == read_file(fea_temp)


def test_default_rtl():
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example_rtl.ufo'
    fea_example = TEST_DIR / 'kern_example_rtl.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_subtable():
    '''
    test writing a file with subtable breaks
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example.ufo'
    fea_example = TEST_DIR / 'kern_example_subs.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_subtable_rtl():
    '''
    test writing a file with subtable breaks
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example_rtl.ufo'
    fea_example = TEST_DIR / 'kern_example_rtl_subs.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_dissolve():
    '''
    test dissolving single-glyph groups
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_AV.ufo'
    fea_example_singletons = TEST_DIR / 'kern_AV_singletons.fea'
    fea_temp_singletons = TEMP_DIR / fea_example_singletons.name
    fea_example_dissolved = TEST_DIR / 'kern_AV_dissolved.fea'
    fea_temp_dissolved = TEMP_DIR / fea_example_dissolved.name
    args.input_file = ufo_path
    args.output_name = fea_temp_singletons
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp_singletons) == read_file(fea_example_singletons)

    args.dissolve_single = True
    args.output_name = fea_temp_dissolved
    run(f, args)
    assert read_file(fea_temp_dissolved) == read_file(fea_example_dissolved)


def test_left_side_exception():
    '''
    test a kerning exception of a single member of a left-side group
    (Adieresis for the A-group, Oslash for the O-group) to a right-side item.
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_left_side_exception.ufo'
    fea_example = TEST_DIR / 'kern_left_side_exception.fea'
    fea_temp = TEMP_DIR / fea_example.name
    args.input_file = ufo_path
    args.output_name = fea_temp
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(fea_temp) == read_file(fea_example)


def test_unused_groups():
    ufo_path = TEST_DIR / 'kern_unused_groups.ufo'
    fea_example = TEST_DIR / 'kern_unused_groups.fea'
    fea_temp = TEMP_DIR / fea_example.name
    f = defcon.Font(ufo_path)
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    run(f, args)
    assert read_file(fea_example) == read_file(fea_temp)


def test_ignored_groups():
    '''
    group/group kern value is 0, all pairs are exceptions
    '''
    ufo_path = TEST_DIR / 'kern_ignored_groups.ufo'
    fea_example = TEST_DIR / 'kern_ignored_groups.fea'
    fea_temp = TEMP_DIR / fea_example.name
    f = defcon.Font(ufo_path)
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    run(f, args)
    assert read_file(fea_example) == read_file(fea_temp)


def test_ss4_exceptions():
    '''
    This contains most exceptions from SS4.
    '''
    ufo_path = TEST_DIR / 'kern_ss4_exceptions.ufo'
    fea_example = TEST_DIR / 'kern_ss4_exceptions.fea'
    fea_temp = TEMP_DIR / fea_example.name
    f = defcon.Font(ufo_path)
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    run(f, args)
    assert read_file(fea_example) == read_file(fea_temp)


def test_mock_rtl():
    '''
    A mock RTL project (mirrored version of ss4_exceptions)
    '''
    ufo_path = TEST_DIR / 'kern_mock_rtl.ufo'
    fea_example = TEST_DIR / 'kern_mock_rtl.fea'
    fea_temp = TEMP_DIR / fea_example.name
    f = defcon.Font(ufo_path)
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    run(f, args)
    assert read_file(fea_example) == read_file(fea_temp)


def test_example_trim(capsys):
    ufo_path = TEST_DIR / 'kern_example.ufo'
    fea_example = TEST_DIR / 'kern_example_trim.fea'
    fea_temp = TEMP_DIR / fea_example.name
    f = defcon.Font(ufo_path)
    args = Defaults()
    args.input_file = ufo_path
    args.output_name = fea_temp
    args.min_value = 100
    args.write_trimmed_pairs = True
    run(f, args)

    out, err = capsys.readouterr()
    assert 'Trimmed pairs: 33' in out

    assert read_file(fea_example) == read_file(fea_temp)
    fea_temp.unlink()
