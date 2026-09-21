"""Separates leading/trailing punctuation from a word token, and
classifies what kind of pause (if any) should follow it during RSVP
playback.

Tokenizing (core/tokenizer.py) only ever splits on whitespace, so a
raw token like "reading." still has its period attached. Without this
module, that period would count toward the word's length when
core/orp.py picks the Optimal Recognition Point letter -- a real
correctness bug, not just a pacing gap -- and there'd be no signal
anywhere for core/timing.py to know a word ends a sentence or clause.

split_punctuation() strips a RUN of non-alphanumeric characters from
each end of a token, working inward until it hits a real letter or
digit -- deliberately only from the ends, never the middle, so
internal punctuation (the hyphen in "well-known", the decimal point
in "$5.99") is left untouched, and only genuine leading/trailing marks
(quotes, sentence punctuation, parentheses) are separated out."""

PACE_NONE = "none"
PACE_CLAUSE = "clause"
PACE_SENTENCE = "sentence"

_SENTENCE_MARKS = set(".!?")
_CLAUSE_MARKS = set(",;:")


def split_punctuation(token: str) -> tuple[str, str, str]:
    """Split a raw token into (leading, core, trailing). core is the
    longest run of alphanumeric characters bounded by, at most, one
    leading and one trailing run of everything else -- core is empty
    if the token is entirely punctuation (e.g. a standalone "--"), in
    which case leading ends up holding the whole token."""
    start = 0
    end = len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[:start], token[start:end], token[end:]


def classify_pacing(stripped_marks: str) -> str:
    """Classify the pause that should follow a word, from the
    punctuation split_punctuation() stripped off it -- callers pass
    leading + trailing combined, not just trailing, so an
    all-punctuation token (where everything lands in "leading" -- see
    split_punctuation()) is still classified correctly rather than
    silently coming out as PACE_NONE.

    Checked as "does any character in there match", not "does it end
    with exactly one mark", so combinations like "?!", "...", or a
    closing-quote-after-a-period ('."') are still classified in one
    pass. Sentence marks win if a token improbably has both a sentence
    and a clause mark."""
    marks = set(stripped_marks)
    if marks & _SENTENCE_MARKS:
        return PACE_SENTENCE
    if marks & _CLAUSE_MARKS:
        return PACE_CLAUSE
    return PACE_NONE