import pytest
from Modules.Needlework.Scheme import Scheme


def test_escaped_characters():
    """Тест схемы с экранированными символами"""
    scheme = Scheme("embroidery", [["^", "b", "b"], ["\\", "d", "d"]])
    encoded = scheme.encode()
    assert encoded == "1\\^2b^1\\\\2d"  # Исправлено количество слешей

    decoded = Scheme.decode(encoded, "embroidery")
    assert decoded.get_pattern() == [["^", "b", "b"], ["\\", "d", "d"]]


def test_digits_in_scheme():
    """Тест схемы с цифрами"""
    scheme = Scheme("knitting", [["1", "2", "2"], ["3", "4", "4"]])
    encoded = scheme.encode()
    assert encoded == "1\\12\\2^1\\32\\4"  # Исправлено представление цифр

    decoded = Scheme.decode(encoded, "knitting")
    assert decoded.get_pattern() == [["1", "2", "2"], ["3", "4", "4"]]


def test_special_case():
    """Тест специального случая с разными символами"""
    scheme = Scheme("knitting", [["a", "^", "b"], ["\\", "d", "d"]])
    encoded = scheme.encode()
    assert encoded == "1a1\\^1b^1\\\\2d"  # Исправлено количество слешей

    decoded = Scheme.decode(encoded, "knitting")
    assert decoded.get_pattern() == [["a", "^", "b"], ["\\", "d", "d"]]


def test_invalid_scheme_type():
    """Тест на недопустимый тип схемы"""
    with pytest.raises(ValueError):  # Теперь ожидаем ValueError
        Scheme("invalid_type", [["a", "b"]])