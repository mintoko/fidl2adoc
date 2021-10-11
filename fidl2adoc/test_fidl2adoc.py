from fidl2adoc import main
import hashlib
import os

def test_output():
    assert 0 == main(['-i', './examples/Test.fidl',
                     '-o', './examples/Test2.adoc'])
    hash1 = hashlib.md5(open('./examples/Test2.adoc','rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test.adoc','rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_fidl_error(capsys):
    assert 2 == main(['-i', './examples/TestError.fidl',
                     '-o', './examples/Test2.adoc'])
    captured = capsys.readouterr()
    assert 'ERROR' in captured.out


def test_wrong_args(capsys):
    assert 1 == main(['-a', './examples/Test.fidl',
                     '-o', './examples/Test2.adoc'])
    captured = capsys.readouterr()
    assert captured.out.startswith('fidl2adoc.py -i <input')


def test_help(capsys):
    assert 0 == main(['-h'])
    captured = capsys.readouterr()
    assert captured.out.startswith('fidl2adoc.py -i <input')
