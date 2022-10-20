import defcon
import sys
sys.path.append("..")

from kernFeatureWriter import *


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
    test_dir = os.path.dirname(__file__)
    ufo_path = os.path.join(test_dir, 'example.ufo')
    example_feature = read_file(os.path.join(test_dir, 'example.fea'))
    args.input_file = ufo_path
    f = defcon.Font(ufo_path)
    run(f, args)
    assert read_file(os.path.join(test_dir, 'kern.fea')) == example_feature


def test_subtable():
    args = Defaults()
    test_dir = os.path.dirname(__file__)
    ufo_path = os.path.join(test_dir, 'example.ufo')
    example_feature = read_file(os.path.join(test_dir, 'example_subs.fea'))
    args.input_file = ufo_path
    args.write_subtables = True
    args.subtable_size = 128
    args.output_file = 'temp_subs.fea'
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(os.path.join(test_dir, args.output_file)) == example_feature)


def test_case_01():
    args = Defaults()
    test_dir = os.path.dirname(__file__)
    ufo_path = os.path.join(test_dir, 'case_01.ufo')
    example_feature = read_file(os.path.join(test_dir, 'case_01.fea'))
    args.input_file = ufo_path
    args.output_file = 'temp_case_01.fea'
    f = defcon.Font(ufo_path)
    run(f, args)
    assert (
        read_file(os.path.join(test_dir, args.output_file)) == example_feature)
