from core.reader import ReaderSession

raw = "[00:00:01] Welcome to the show. (1:23) Today we're talking about RSVP."
session = ReaderSession(raw, wpm=400)

while not session.is_finished:
    f = session.current_frame()
    print(f"{f.before}[{f.focus}]{f.after}  ({session.current_delay_ms()}ms)")
    session.advance()