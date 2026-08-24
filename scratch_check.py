from core.parser import clean_transcript
from core.tokenizer import tokenize

raw = "[00:00:01] Welcome to the show. (1:23) Today we're talking about RSVP."
words = tokenize(clean_transcript(raw))
print(words)