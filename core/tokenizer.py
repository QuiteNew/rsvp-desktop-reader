def tokenize(clean_text: str) -> list[str]:
    """Split cleaned transcript text into a list of individual word tokens."""
    return clean_text.split()


if __name__ == "__main__":
    sample = "Welcome to the show. Today we're talking about RSVP reading."
    words = tokenize(sample)
    print(words)
    print(f"Word count: {len(words)}")

