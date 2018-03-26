from processor.processor import normalize

def test_normalize():
    assert normalize(1.3) == normalize('  0001.3000 ')
