import pytest
from core.timing import wpm_to_delay_ms


def test_300_wpm_gives_200ms():
    assert wpm_to_delay_ms(300) == 200


def test_200_wpm_gives_300ms():
    assert wpm_to_delay_ms(200) == 300


def test_400_wpm_gives_150ms():
    assert wpm_to_delay_ms(400) == 150


def test_600_wpm_gives_100ms():
    assert wpm_to_delay_ms(600) == 100


def test_minimum_app_wpm_100_gives_600ms():
    assert wpm_to_delay_ms(100) == 600


def test_maximum_app_wpm_1000_gives_60ms():
    assert wpm_to_delay_ms(1000) == 60


def test_rounds_rather_than_truncates():
    assert wpm_to_delay_ms(700) == 86


def test_zero_wpm_raises_value_error():
    with pytest.raises(ValueError):
        wpm_to_delay_ms(0)


def test_negative_wpm_raises_value_error():
    with pytest.raises(ValueError):
        wpm_to_delay_ms(-50)


def test_higher_wpm_gives_shorter_delay():
    assert wpm_to_delay_ms(600) < wpm_to_delay_ms(300)