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


def test_trim_anchor_name():
    assert trim_anchor_name('anchorUC') == 'anchor'
    assert trim_anchor_name('anchorLC') == 'anchor'
    assert trim_anchor_name('anchorSC') == 'anchor'
    assert trim_anchor_name('anchor') == 'anchor'
    assert trim_anchor_name('UCSC') == 'UC'


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


def test_mkmk_file():
    '''
    write external mark classes file
    '''
    args = Defaults()
    tmp_fea_mark = TEST_DIR / 'tmp_mark.fea'
    tmp_fea_mkmk = TEST_DIR / 'tmp_mkmk.fea'
    args.mark_file = tmp_fea_mark
    args.mkmk_file = tmp_fea_mkmk
    args.write_mkmk = True
    args.input_file = TEST_DIR / 'mark_simple.ufo'
    MarkFeatureWriter(args)

    example_fea_mark = read_file(TEST_DIR / 'mark_simple.fea')
    example_fea_mkmk = read_file(TEST_DIR / 'mkmk_simple.fea')
    assert read_file(tmp_fea_mark) == example_fea_mark
    assert read_file(tmp_fea_mkmk) == example_fea_mkmk
    tmp_fea_mark.unlink()
    tmp_fea_mkmk.unlink()


def test_indic_format():
    '''
    test abvm and blwm files
    '''
    args = Defaults()
    args.indic_format = True
    tmp_fea_mark = TEST_DIR / 'tmp_mark.fea'
    tmp_fea_abvm = TEST_DIR / 'tmp_abvm.fea'
    tmp_fea_blwm = TEST_DIR / 'tmp_blwm.fea'
    args.mark_file = tmp_fea_mark
    args.abvm_file = tmp_fea_abvm
    args.blwm_file = tmp_fea_blwm
    args.input_file = TEST_DIR / 'mark_deva_simple.ufo'
    MarkFeatureWriter(args)

    example_fea_mark = read_file(TEST_DIR / 'mark_deva_simple_mark.fea')
    example_fea_abvm = read_file(TEST_DIR / 'mark_deva_simple_abvm.fea')
    example_fea_blwm = read_file(TEST_DIR / 'mark_deva_simple_blwm.fea')
    assert read_file(tmp_fea_mark) == example_fea_mark
    assert read_file(tmp_fea_abvm) == example_fea_abvm
    assert read_file(tmp_fea_blwm) == example_fea_blwm
    tmp_fea_mark.unlink()
    tmp_fea_abvm.unlink()
    tmp_fea_blwm.unlink()


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


def test_make_lookup_wrappers():
    mfw = MarkFeatureWriter()
    # default mark lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers('anchorLTR')
    assert 'MARK_BASE_anchorLTR' in open_ltr
    assert 'MARK_BASE_anchorLTR' in close_ltr

    # RTL mark lookup
    open_rtl, close_rtl = mfw.make_lookup_wrappers('anchorAR')
    assert 'lookupflag RightToLeft;' in open_rtl

    # RTL mark lookup
    open_rtl, close_rtl = mfw.make_lookup_wrappers('anchorRTL')
    assert 'lookupflag RightToLeft;' in open_rtl

    # mkmk lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers('anchorLTR', mkmk=True)
    assert 'MKMK_MARK_anchorLTR' in open_ltr
    assert 'lookupflag MarkAttachmentType @MC_anchorLTR;' in open_ltr

    # RTL mkmk lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers('anchorHE', mkmk=True)
    assert 'MKMK_MARK_anchorHE' in open_ltr
    assert 'lookupflag RightToLeft MarkAttachmentType @MC_anchorHE;' in open_ltr
