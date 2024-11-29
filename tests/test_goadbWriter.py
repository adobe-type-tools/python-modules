import pytest
import sys

from afdko.fdkutils import get_temp_dir_path
from pathlib import Path


sys.path.append("..")
from goadbWriter import *


TEST_DIR = Path(__file__).parent
TEMP_DIR = Path(get_temp_dir_path())


def read_file(path):
    '''
    Read a file, split lines into a list, close the file.
    '''

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().splitlines()
    return data


# unit tests
# -----------------

def test_get_args():
    # args through argparse
    ufo_path = str(TEST_DIR / 'goadb_full.ufo')
    argparse_args = vars(get_args([ufo_path, '-o', 'goadb']))
    expected_args = {
        'input_file': ufo_path,
        'output': 'goadb',
        'template': False,
    }
    assert argparse_args == expected_args


def test_phantom_input_ufo(capsys):
    '''
    non-existent input UFO
    '''
    ufo_path = TEST_DIR / 'phantom.ufo'
    args = [str(ufo_path)]
    with pytest.raises(SystemExit):
        main(args)
    out, err = capsys.readouterr()
    assert 'phantom.ufo does not exist' in err


def test_invalid_input_file(capsys):
    '''
    invalid input file
    '''
    ufo_path = TEST_DIR / 'some_file.xxx'
    args = [str(ufo_path)]
    with pytest.raises(SystemExit):
        main(args)
    out, err = capsys.readouterr()
    assert 'some_file.xxx is not a UFO file' in err


# integration tests
# -----------------

def test_default():
    '''
    testing UFO with all kinds of glyph names
    '''
    ufo_path = str(TEST_DIR / 'goadb_full.ufo')
    goadb_example = TEST_DIR / 'goadb_full'
    goadb_temp = str(TEMP_DIR / 'goadb')
    args = [ufo_path, '-o', goadb_temp]
    main(args)
    assert read_file(goadb_temp) == read_file(goadb_example)


def test_template():
    '''
    testing UFO with template glyphs only
    '''
    ufo_path = str(TEST_DIR / 'goadb_template_glyphs.ufo')
    goadb_example = TEST_DIR / 'goadb_template_glyphs'
    goadb_temp = str(TEMP_DIR / 'goadb')
    args = [ufo_path, '-o', goadb_temp, '-t']
    main(args)
    assert read_file(goadb_temp) == read_file(goadb_example)


def test_no_glyphorder():
    '''
    testing UFO without a glyph order
    '''
    ufo_path = str(TEST_DIR / 'goadb_no_glyphorder.ufo')
    goadb_example = TEST_DIR / 'goadb_no_glyphorder'
    goadb_temp = str(TEMP_DIR / 'goadb')
    args = [ufo_path, '-o', goadb_temp]
    main(args)
    assert read_file(goadb_temp) == read_file(goadb_example)


def test_stdout(capsys):
    ufo_path = str(TEST_DIR / 'goadb_full.ufo')
    goadb_example = TEST_DIR / 'goadb_full'
    args = [ufo_path]
    main(args)
    out, err = capsys.readouterr()
    assert '\n'.join(read_file(goadb_example)) + '\n' == out
