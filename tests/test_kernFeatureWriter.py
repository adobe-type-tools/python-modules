import defcon
import sys
from pathlib import Path

sys.path.append("..")
from kernFeatureWriter import *

TEST_DIR = Path(__file__).parent


class Dummy(object):
    pass


def read_file(path):
    '''
    Read a file, split lines into a list, close the file.
    '''

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().splitlines()
    return data


def test_WhichApp():
    assert WhichApp().appName == 'Defcon'
    # import __mocks__ as flsys ???
    # assert WhichApp().appName == 'FontLab'


def test_get_args():
    argparse_args = vars(get_args(['dummy']))  # args through argparse
    dummy_args = Defaults().__dict__  # hard-coded dummy arguments
    dummy_args['input_file'] = 'dummy'
    assert argparse_args == dummy_args


def test_full_run():
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example.ufo'
    tmp_feature = TEST_DIR / 'tmp_kern_example.fea'
    example_feature = read_file(TEST_DIR / 'kern_example.fea')
    args.input_file = ufo_path
    args.output_name = tmp_feature
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature) == example_feature

    '''
    test with --dissolve_single option, which should not make a difference
    for this UFO (no single-item groups)
    '''
    args.dissolve_single = True
    run(f, args)
    assert read_file(tmp_feature) == example_feature
    tmp_feature.unlink()


def test_full_run_rtl():
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example_rtl.ufo'
    tmp_feature = TEST_DIR / 'tmp_kern_example_rtl.fea'
    example_feature = read_file(TEST_DIR / 'kern_example_rtl.fea')
    args.input_file = ufo_path
    args.output_name = tmp_feature
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature) == example_feature
    tmp_feature.unlink()


def test_subtable():
    '''
    test writing a file with subtable breaks
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example.ufo'
    tmp_feature = TEST_DIR / 'tmp_kern_example_subs.fea'
    example_feature = read_file(TEST_DIR / 'kern_example_subs.fea')
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    args.output_name = tmp_feature
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature) == example_feature
    tmp_feature.unlink()


def test_subtable_rtl():
    '''
    test writing a file with subtable breaks
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example_rtl.ufo'
    tmp_feature = TEST_DIR / 'tmp_kern_example_rtl_subs.fea'
    example_feature = read_file(TEST_DIR / 'kern_example_rtl_subs.fea')
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    args.output_name = tmp_feature
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature) == example_feature
    tmp_feature.unlink()


def test_dissolve():
    '''
    test dissolving single-glyph groups
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_AV.ufo'
    tmp_feature_undissolved = TEST_DIR / 'tmp_kern_AV_undissolved.fea'
    tmp_feature_dissolved = TEST_DIR / 'tmp_kern_AV_dissolved.fea'
    example_feature_undissolved = read_file(
        TEST_DIR / 'kern_AV_undissolved.fea')
    example_feature_dissolved = read_file(
        TEST_DIR / 'kern_AV_dissolved.fea')
    args.input_file = ufo_path
    args.output_name = tmp_feature_undissolved
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature_undissolved) == example_feature_undissolved
    args.dissolve_single = True
    args.output_name = tmp_feature_dissolved
    run(f, args)
    assert read_file(tmp_feature_dissolved) == example_feature_dissolved
    tmp_feature_undissolved.unlink()
    tmp_feature_dissolved.unlink()


def test_case_01():
    '''
    test a kerning exception of a single member of a left-side group
    (Adieresis for the A-group, Oslash for the O-group) to a right-side item.
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_case_01.ufo'
    tmp_feature = TEST_DIR / 'tmp_case_01.fea'
    example_feature = read_file(TEST_DIR / 'kern_case_01.fea')
    args.input_file = ufo_path
    args.output_name = tmp_feature
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(tmp_feature) == example_feature
    tmp_feature.unlink()


def test_make_header():
    kfw = run(None, None)
    dummy_args = Dummy()
    dummy_args.min_value = 1
    dummy_args.write_timestamp = False
    header = kfw.make_header(dummy_args)
    assert len(header) == 3
    assert header[0] == '# PS Name: None'
    dummy_args.write_timestamp = True
    header = kfw.make_header(dummy_args)
    assert len(header) == 4
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


def test_no_kerning(capsys):
    ufo_path = TEST_DIR / 'kern_example.ufo'
    f = defcon.Font(ufo_path)
    f.kerning.clear()
    args = Defaults()
    run(f, args)
    out, err = capsys.readouterr()
    assert f'has no kerning' in out
