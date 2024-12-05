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


def test_get_args():
    # args through argparse
    input_ufo = str(TEST_DIR / 'kern_example.ufo')
    argparse_args = vars(get_args([input_ufo]))
    # hard-coded dummy arguments
    dummy_args = Defaults().__dict__
    dummy_args['input_file'] = input_ufo
    assert argparse_args == dummy_args


def test_attaching():
    assert is_attaching('_') is True
    assert is_attaching('_a') is True
    assert is_attaching('__') is True
    assert is_attaching('x_') is False
    assert is_attaching('a') is False
    assert is_attaching('') is False


def test_process_anchor_name():
    assert process_anchor_name('anchorUC', trim=True) == 'anchor'
    assert process_anchor_name('anchorUC') == 'anchorUC'
    assert process_anchor_name('anchorLC', trim=True) == 'anchor'
    assert process_anchor_name('anchorLC') == 'anchorLC'
    assert process_anchor_name('anchorSC', trim=True) == 'anchor'
    assert process_anchor_name('anchor', trim=True) == 'anchor'
    assert process_anchor_name('anchor') == 'anchor'
    assert process_anchor_name('UCSC', trim=True) == 'UC'
    assert process_anchor_name('UCSC') == 'UCSC'


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


def test_ligature():
    '''
    test mark-to-ligature (GPOS Lookup Type 5)
    '''
    args = Defaults()
    tmp_fea_mark = TEST_DIR / 'tmp_mark.fea'
    args.mark_file = tmp_fea_mark
    args.input_file = TEST_DIR / 'mark_rtl_liga.ufo'
    MarkFeatureWriter(args)

    example_fea_mark = read_file(TEST_DIR / 'mark_rtl_liga.fea')
    assert read_file(tmp_fea_mark) == example_fea_mark
    tmp_fea_mark.unlink()


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

    # same should work through main()
    input_file = str(TEST_DIR / 'mark_simple.ufo')
    fea_file = str(TEST_DIR / 'tmp_mark_full.fea')
    main([input_file, '--mark_file', fea_file])
    example_feature = read_file(TEST_DIR / 'mark_simple.fea')
    assert read_file(tmp_fea_full) == example_feature
    tmp_fea_full.unlink()


def test_make_lookup_wrappers():
    mfw = MarkFeatureWriter()
    # default mark lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers('anchorLTR', 'MARK_BASE_')
    assert 'MARK_BASE_anchorLTR' in open_ltr
    assert 'MARK_BASE_anchorLTR' in close_ltr

    # RTL mark lookup
    open_rtl, close_rtl = mfw.make_lookup_wrappers('anchorAR', 'MARK_BASE_')
    assert 'lookupflag RightToLeft;' in open_rtl

    # RTL mark lookup
    open_rtl, close_rtl = mfw.make_lookup_wrappers('anchorRTL', 'MARK_BASE_')
    assert 'lookupflag RightToLeft;' in open_rtl

    # mkmk lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers(
        'anchorLTR', 'MKMK_MARK_', mkmk=True)
    assert 'MKMK_MARK_anchorLTR' in open_ltr
    assert 'lookupflag MarkAttachmentType @MC_anchorLTR;' in open_ltr

    # RTL mkmk lookup
    open_ltr, close_ltr = mfw.make_lookup_wrappers(
        'anchorHE', 'MKMK_MARK_', mkmk=True)
    assert 'MKMK_MARK_anchorHE' in open_ltr
    assert 'lookupflag RightToLeft MarkAttachmentType @MC_anchorHE;' in open_ltr


def test_liga_ltr():
    input_file = TEST_DIR / 'project_mark_liga_ltr' / 'liga_ltr.ufo'
    tmp_fea_mark = TEST_DIR / 'tmp_mark_liga_ltr.fea'
    example_fea_mark = TEST_DIR / 'project_mark_liga_ltr' / 'mark.fea'
    args = Defaults()
    args.input_file = input_file
    args.mark_file = tmp_fea_mark
    args.trim_tags = True
    MarkFeatureWriter(args)

    assert read_file(tmp_fea_mark) == read_file(example_fea_mark)
    tmp_fea_mark.unlink()


def test_liga_rtl():
    input_file = TEST_DIR / 'project_mark_liga_rtl' / 'liga_rtl.ufo'
    tmp_fea_mark = TEST_DIR / 'tmp_mark_liga_rtl.fea'
    tmp_fea_mkmk = TEST_DIR / 'tmp_mkmk_liga_rtl.fea'
    tmp_fea_classes = TEST_DIR / 'tmp_markclasses_liga_rtl.fea'
    example_fea_mark = TEST_DIR / 'project_mark_liga_rtl' / 'mark.fea'
    example_fea_mkmk = TEST_DIR / 'project_mark_liga_rtl' / 'mkmk.fea'
    example_fea_classes = TEST_DIR / 'project_mark_liga_rtl' / 'markclasses.fea'
    args = Defaults()
    args.input_file = input_file
    args.mark_file = tmp_fea_mark
    args.mkmk_file = tmp_fea_mkmk
    args.mkclass_file = tmp_fea_classes
    args.write_mkmk = True
    args.write_classes = True
    MarkFeatureWriter(args)

    assert read_file(tmp_fea_mark) == read_file(example_fea_mark)
    assert read_file(tmp_fea_mkmk) == read_file(example_fea_mkmk)
    assert read_file(tmp_fea_classes) == read_file(example_fea_classes)
    tmp_fea_mark.unlink()
    tmp_fea_mkmk.unlink()
    tmp_fea_classes.unlink()


def test_phantom_input_ufo(capsys):
    '''
    non-existent input UFO
    '''
    ufo_path = TEST_DIR / 'phantom.ufo'
    args = Defaults()
    args.input_file = ufo_path
    with pytest.raises(SystemExit):
        main([str(ufo_path)])
    out, err = capsys.readouterr()
    assert 'phantom.ufo does not exist' in err


def test_invalid_input_file(capsys):
    '''
    invalid input file
    '''
    ufo_path = TEST_DIR / 'some_file.xxx'
    args = Defaults()
    args.input_file = ufo_path
    with pytest.raises(SystemExit):
        main([str(ufo_path)])
    out, err = capsys.readouterr()
    assert 'Unrecognized input file type' in err
