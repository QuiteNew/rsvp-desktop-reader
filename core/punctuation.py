"""Separates leading/trailing punctuation from a word token, and
classifies what pause (if any) should follow it during RSVP playback.

core/tokenizer.py only splits on whitespace, so "reading." still has
its period attached. Left alone, that period would throw off
core/orp.py's Optimal Recognition Point letter, and there'd be no
signal for core/timing.py to know a word ends a sentence or clause.

split_punctuation() strips non-alphanumeric characters from each end
of a token, working inward. It only works from the ends, never the
middle, so "well-known" and "$5.99" keep their internal punctuation
intact."""

PACE_NONE = "none"
PACE_CLAUSE = "clause"
PACE_SENTENCE = "sentence"

_SENTENCE_MARKS = set(".!?")
_CLAUSE_MARKS = set(",;:")


def split_punctuation(token: str) -> tuple[str, str, str]:
    """Split a token into (leading, core, trailing) punctuation/word
    parts. core is empty for an all-punctuation token (e.g. "--"), with
    everything landing in leading in that case."""
    start = 0
    end = len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[:start], token[start:end], token[end:]


def classify_pacing(stripped_marks: str) -> str:
    """Classify the pause that should follow a word, from the stripped
    punctuation split_punctuation() returned. Callers pass leading +
    trailing combined so an all-punctuation token still classifies
    correctly instead of defaulting to PACE_NONE.

    Matches "does any character match," not "does it end with exactly
    one mark," so "?!", "...", or '."' still classify in one pass.
    Sentence marks win over clause marks if both are present."""
    marks = set(stripped_marks)
    if marks & _SENTENCE_MARKS:
        return PACE_SENTENCE
    if marks & _CLAUSE_MARKS:
        return PACE_CLAUSE
    return PACE_NONE