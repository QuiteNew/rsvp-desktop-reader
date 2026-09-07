from core.transcript_store import TranscriptStore

store = TranscriptStore()
print("Loaded spaces:", store.spaces)
print("Loaded transcripts:", [t.title for t in store.transcripts])

store.add_space("Testing")
store.add_transcript("Persistence check", store.current_space)
print("After adding — spaces:", store.spaces)