from fidl2adoc import main
import hashlib
import os

def test_output():
    files = [f for f in os.listdir('./examples') if os.path.isfile(f)]
    for f in files:
        print(f)  # do something
    assert 0 == main(['-i', './examples/Test.fidl',
                     '-o', './examples/Test2.adoc'])
    hash1 = hashlib.md5(open('./examples/Test2.adoc','rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test.adoc','rb').read()).hexdigest()
    assert(hash1 == hash2)


def test_wrong_args(capsys):
    assert 1 == main(['-a', './examples/Test.fidl',
                     '-o', './examples/Test2.adoc'])
    captured = capsys.readouterr()
    assert captured.out.startswith('fidl2adoc.py -i <input')


def test_help(capsys):
    assert 0 == main(['-h'])
    captured = capsys.readouterr()
    assert captured.out.startswith('fidl2adoc.py -i <input')


if __name__ == "__main__":
    test_output()
