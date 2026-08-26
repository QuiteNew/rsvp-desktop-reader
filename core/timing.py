def wpm_to_delay_ms(wpm: int) -> int:
    """Convert a words-per-minute rate into a per-word delay in milliseconds."""
    if wpm <= 0:
        raise ValueError("WPM must be greater than zero")
    return round(60000 / wpm)


if __name__ == "__main__":
    for test_wpm in [200, 300, 400, 600]:
        delay = wpm_to_delay_ms(test_wpm)
        print(f"{test_wpm} WPM -> {delay} ms per word")