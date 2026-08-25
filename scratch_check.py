from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp

raw = "[00:00:01] Welcome to the show. (1:23) Today we're talking about RSVP."
words = tokenize(clean_transcript(raw))
for w in words:
    r = split_at_orp(w)
    print(f"{w:>12} -> {r.before}[{r.focus}]{r.after}")