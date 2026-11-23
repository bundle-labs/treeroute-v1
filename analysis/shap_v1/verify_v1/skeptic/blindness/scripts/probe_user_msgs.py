# Count the user-side messages of a transcript that are not tool results (the task prompt and any later message),
# and show the first 160 characters of each later one. Writes nothing.
# Usage: py -3.9 -I -B probe_user_msgs.py <transcript.jsonl>
import json
import sys

n_prompt = 0
later = []
with open(sys.argv[1], encoding="utf-8") as fh:
    for line in fh:
        obj = json.loads(line)
        if obj.get("type") != "user":
            continue
        c = (obj.get("message") or {}).get("content")
        texts = []
        if isinstance(c, str):
            texts = [c]
        elif isinstance(c, list):
            texts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
        for t in texts:
            n_prompt += 1
            if n_prompt > 1:
                later.append((obj.get("timestamp"), t[:160].replace("\n", " ")))
print("user text messages:", n_prompt)
for ts, t in later:
    print("  later message", ts, "::", t)
