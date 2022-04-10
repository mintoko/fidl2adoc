import hashlib
from fidl2adoc import main

def test_output():
    global adoc
    adoc = ''
    assert 0 == main(['-i', './examples/Test.fidl',
                     '-o', './examples/tmp.adoc'])
    hash1 = hashlib.md5(open('./examples/tmp.adoc', 'rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test.adoc', 'rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_output2():
    adoc = ''
    assert 0 == main(['-i', './examples/Test2.fidl',
                     '-o', './examples/tmp2.adoc'])
    hash1 = hashlib.md5(open('./examples/tmp2.adoc', 'rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test2.adoc', 'rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_output_s():
    assert 0 == main(['-i', './examples/Test.fidl',
                     '-o', './examples/tmp3.adoc',
                     '-s'])
    hash1 = hashlib.md5(open('./examples/tmp3.adoc', 'rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test_s.adoc', 'rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_output2_s():
    assert 0 == main(['-i', './examples/Test2.fidl',
                     '-o', './examples/tmp4.adoc',
                     '-s'])
    hash1 = hashlib.md5(open('./examples/tmp4.adoc', 'rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test2_s.adoc', 'rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_fidl_error(capsys):
    assert 2 == main(['-i', './examples/TestError.fidl',
                     '-o', './examples/tmp5.adoc'])
    captured = capsys.readouterr()
    assert 'ERROR' in captured.out


def test_wrong_args(capsys):
    assert 1 == main(['-a', './examples/Test.fidl',
                     '-o', './examples/tmp5.adoc'])
    captured = capsys.readouterr()
    assert captured.out.startswith('Input parameter error')


def test_help(capsys):
    assert 0 == main(['-h'])
    captured = capsys.readouterr()
    assert captured.out.startswith('fidl2adoc.py -i <input')


def test_no_args(capsys):
    assert 1 == main([])
    captured = capsys.readouterr()
    assert captured.out.startswith('Need at least 1 input and 1 output file.')
