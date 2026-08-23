import re

def clean_transcript(raw_text: str) -> str:
    """Strip timestamps from raw transcript text and normalize whitespace."""
    timestamp_pattern = r'\[?\(?\d{1,2}:\d{2}(:\d{2})?\)?\]?'
    text = re.sub(timestamp_pattern, '', raw_text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


if __name__ == "__main__":
    sample = """
    [00:00:01] Welcome to the show.
    (1:23) Today we're talking about
    00:02:45 rapid serial visual presentation.
    """
    print(clean_transcript(sample))