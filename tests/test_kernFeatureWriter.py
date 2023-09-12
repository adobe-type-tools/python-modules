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


def test_full_run():
    args = Defaults()
    ufo_path = TEST_DIR / 'example.ufo'
    example_feature = read_file(TEST_DIR / 'example.fea')
    args.input_file = ufo_path
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(TEST_DIR / 'kern.fea') == example_feature


def test_subtable():
    args = Defaults()
    ufo_path = TEST_DIR / 'example.ufo'
    example_feature = read_file(TEST_DIR / 'example_subs.fea')
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    output_file = TEST_DIR / 'temp_subs.fea'
    args.output_file = output_file
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(TEST_DIR / args.output_file)) == example_feature
    output_file.unlink()


def test_case_01():
    args = Defaults()
    ufo_path = TEST_DIR / 'case_01.ufo'
    example_feature = read_file(TEST_DIR / 'case_01.fea')
    args.input_file = ufo_path
    output_file = TEST_DIR / 'temp_case_01.fea'
    args.output_file = output_file
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(TEST_DIR / args.output_file)) == example_feature
    output_file.unlink()
