from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp
from core.timing import wpm_to_delay_ms

raw = "[00:00:01] Welcome to the show. (1:23) Today we're talking about RSVP."
words = tokenize(clean_transcript(raw))
delay_ms = wpm_to_delay_ms(300)

for w in words:
    r = split_at_orp(w)
    print(f"{w:>12} -> {r.before}[{r.focus}]{r.after}  ({delay_ms}ms)")

total_seconds = (len(words) * delay_ms) / 1000
print(f"\nTotal estimated reading time: {total_seconds:.1f}s for {len(words)} words at 300 WPM")