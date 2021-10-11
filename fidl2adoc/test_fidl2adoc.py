from fidl2adoc import main
import hashlib
import os

def test_output():
    import os
    files = [f for f in os.listdir('./examples') if os.path.isfile(f)]
    for f in files:
        print(f)  # do something
    main(['-i', './examples/Test.fidl', '-o', './examples/Test2.adoc'])
    hash1 = hashlib.md5(open('./examples/Test2.adoc','rb').read()).hexdigest()
    hash2 = hashlib.md5(open('./examples/Test.adoc','rb').read()).hexdigest()
    assert(hash1 == hash2)


if __name__ == "__main__":
   test_output()
