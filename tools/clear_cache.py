import os

if os.path.exists("transcript_cache.json"):
    os.remove("transcript_cache.json")
    print("Transcript cache cleared.")
else:
    print("No transcript cache found.")
