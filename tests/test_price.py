# tests/test_price.py
import pytest
from backend.services.price import format_price


def test_integer_cents_to_dollars():
    assert format_price(3999) == "$39.99"
    assert format_price(10999) == "$109.99"
    assert format_price(0) == "$0.00"


def test_float_already_dollars():
    assert format_price(12.5) == "$12.50"
    assert format_price(100.0) == "$100.00"
    assert format_price(0.99) == "$0.99"


def test_string_numeric_inputs():
    assert format_price("5499") == "$54.99"
    assert format_price("12.5") == "$12.50"
    assert format_price("000") == "$0.00"


def test_invalid_or_none_inputs():
    assert format_price(None) is None
    assert format_price("abc") is None
    assert format_price({}) is None
    assert format_price([]) is None


def test_custom_currency_symbols():
    assert format_price(3999, currency="€") == "€39.99"
    assert format_price(2500, currency="£") == "£25.00"


@pytest.mark.parametrize(
    "value,expected",
    [
        (199, "$1.99"),
        (200, "$2.00"),
        ("199", "$1.99"),
        ("200", "$2.00"),
        (199.0, "$199.00"),  # float treated as already dollars
    ],
)
def test_parametrized_cases(value, expected):
    assert format_price(value) == expected
