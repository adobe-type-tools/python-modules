import sys
sys.path.append("..")

from markFeatureWriter import *


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


def test_full_run():
    args = Defaults()
    args.input_file = 'mfw_simple.ufo'

    test_dir = os.path.dirname(__file__)
    ufo_path = os.path.join(test_dir, 'mfw_simple.ufo')
    example_feature = read_file(os.path.join(test_dir, 'mfw_simple.fea'))
    args.input_file = ufo_path
    MarkFeatureWriter(args)
    assert read_file(os.path.join(test_dir, 'mark.fea')) == example_feature


if __name__ == '__main__':
    test_full_run()
