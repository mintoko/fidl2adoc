from fidl2adoc import main
import hashlib


def test_output():
    main(['-i', '..\examples\Test.fidl', '-o', '..\examples\Test2.adoc'])
    hash1 = hashlib.md5(open('..\examples\Test2.adoc','rb').read()).hexdigest()
    hash2 = hashlib.md5(open('..\examples\Test.adoc','rb').read()).hexdigest()
    assert(hash1 == hash2)


if __name__ == "__main__":
   test_output()
