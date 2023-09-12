import defcon
import sys
from pathlib import Path

sys.path.append("..")
from kernFeatureWriter import *

TEST_DIR = Path(__file__).parent


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
    example_feature = read_file(TEST_DIR / 'kern_example.fea')
    args.input_file = ufo_path
    output_file = TEST_DIR / 'tmp_kern_example.fea'
    args.output_file = output_file
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(TEST_DIR / args.output_file) == example_feature
    output_file.unlink()


def test_subtable():
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_example.ufo'
    example_feature = read_file(TEST_DIR / 'kern_example_subs.fea')
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    output_file = TEST_DIR / 'tmp_kern_example_subs.fea'
    args.output_file = output_file
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(TEST_DIR / args.output_file)) == example_feature
    output_file.unlink()


def test_case_01():
    '''
    This case tests a single member of a left-side group (Adieresis for the
    A-group, Oslash for the O-group) having a kerning exception to a
    right-side item.
    '''
    args = Defaults()
    ufo_path = TEST_DIR / 'kern_case_01.ufo'
    example_feature = read_file(TEST_DIR / 'kern_case_01.fea')
    args.input_file = ufo_path
    output_file = TEST_DIR / 'tmp_case_01.fea'
    args.output_file = output_file
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(TEST_DIR / args.output_file)) == example_feature
    output_file.unlink()
