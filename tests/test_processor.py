from processor.processor import normalize


def test_normalize():
    assert normalize(42) == normalize(42.0)
    assert normalize(1.3) == normalize('  0001.3000 ')
    assert normalize(' 012.3400') == normalize('12.34')
