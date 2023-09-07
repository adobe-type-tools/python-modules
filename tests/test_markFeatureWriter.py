import sys
import pytest
from pathlib import Path

sys.path.append("..")
from markFeatureWriter import *

TEST_DIR = Path(__file__).parent


def read_file(path):
    '''
    Read a file, split lines into a list, close the file.
    '''

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().splitlines()
    return data


# def test_WhichApp():
#     assert WhichApp().appName == 'Defcon'
#     # import __mocks__ as flsys ???
#     # assert WhichApp().appName == 'FontLab'

def test_get_args():
    argparse_args = vars(get_args(['dummy']))  # args through argparse
    dummy_args = Defaults().__dict__  # hard-coded dummy arguments
    dummy_args['input_file'] = 'dummy'
    assert argparse_args == dummy_args


def test_no_group():
    args = Defaults()
    args.input_file = TEST_DIR / 'mark_no_group.ufo'
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        MarkFeatureWriter(args)
    assert pytest_wrapped_e.type == SystemExit


def test_trim():
    args = Defaults()
    tmp_fea_trim = TEST_DIR / 'tmp_mark_trim.fea'
    args.trim_tags = True
    args.mark_file = tmp_fea_trim
    args.input_file = TEST_DIR / 'mark_trim.ufo'
    MarkFeatureWriter(args)

    example_feature = read_file(TEST_DIR / 'mark_trim.fea')
    assert read_file(tmp_fea_trim) == example_feature
    tmp_fea_trim.unlink()


def test_mkclass_file():
    '''
    write external mark classes file
    '''
    args = Defaults()
    tmp_fea_noclasses = TEST_DIR / 'tmp_mark.fea'
    tmp_fea_classes = TEST_DIR / 'tmp_classes.fea'
    args.mark_file = tmp_fea_noclasses
    args.mkclass_file = tmp_fea_classes
    args.write_classes = True
    args.input_file = TEST_DIR / 'mark_simple.ufo'
    MarkFeatureWriter(args)

    example_fea_noclasses = read_file(TEST_DIR / 'mark_simple_noclasses.fea')
    example_fea_markclasses = read_file(TEST_DIR / 'mark_simple_classes.fea')
    assert read_file(tmp_fea_noclasses) == example_fea_noclasses
    assert read_file(tmp_fea_classes) == example_fea_markclasses
    tmp_fea_noclasses.unlink()
    tmp_fea_classes.unlink()


def test_full_run():
    '''
    very basic run without any options
    '''
    args = Defaults()
    tmp_fea_full = TEST_DIR / 'tmp_mark_full.fea'
    args.mark_file = tmp_fea_full
    args.input_file = TEST_DIR / 'mark_simple.ufo'
    MarkFeatureWriter(args)

    example_feature = read_file(TEST_DIR / 'mark_simple.fea')
    assert read_file(tmp_fea_full) == example_feature
    tmp_fea_full.unlink()


if __name__ == '__main__':
    test_full_run()
