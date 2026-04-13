from calculator import calc

def test_calc():
    a = b = 2
    result = calc.calc(a, b)
    assert result == 4
