import json, os, sys, urllib.request
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
LINES = [
 "Ten minutes. That's all it took.",
 "In April 2026, researchers from Carnegie Mellon, Oxford, MIT and UCLA posted a study with a bold claim: a short burst of AI help can make you worse at the next task, once the AI is gone.",
 "Here's the setup. Hundreds of people solved fraction problems. Some had an AI assistant.",
 "Then the AI was taken away, and everyone worked solo.",
 "The AI group solved about twenty percent fewer problems. And they skipped far more questions, as if they'd simply stopped trying.",
 "But here's the twist. People who asked for hints were fine. The ones who asked for answers fell the hardest.",
 "So, is AI rotting our brains? Not so fast. This is a preprint: not peer-reviewed, not replicated. Online volunteers, simple math, measured minutes later, not months.",
 "What it might show is smaller, and more useful: the tool isn't the problem. How we lean on it might be.",
 "So let's do what good science asks. Read it together, and wait for the replication.",
]
key = os.environ["FISH_API_KEY"]
for i, text in enumerate(LINES, 1):
    body = json.dumps({"text": text, "reference_id": "536d3a5e000945adb7038665781a4aca",
                       "format": "mp3", "mp3_bitrate": 192, "language": "en"}).encode()
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "model": "drama-3"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        print(i, "HTTP", e.code, e.read()[:300]); sys.exit(1)
    path = os.path.join(OUT, f"beat{i:02d}.mp3")
    open(path, "wb").write(data)
    print(i, len(data), "bytes")
