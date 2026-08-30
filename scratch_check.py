from core.transcript_store import TranscriptStore

store = TranscriptStore()
print("Default space:", store.default_space)

store.add_transcript("Lecture 3 notes", store.default_space)
store.add_transcript("Podcast transcript", store.default_space)

for t in store.transcripts:
    print(t)