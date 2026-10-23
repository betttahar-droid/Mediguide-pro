import json, os, sys, urllib.request
def tts(text, out, voice, model="drama-3", speed=1.0):
    body = {"text": text, "reference_id": voice, "format": "mp3", "mp3_bitrate": 192,
            "language": "en", "prosody": {"speed": speed}}
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {os.environ['FISH_API_KEY']}", "Content-Type": "application/json", "model": model})
    try:
        with urllib.request.urlopen(req, timeout=180) as r: open(out, "wb").write(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {e.read()[:300]}")
if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1]))
    for j in jobs: tts(**j); print("ok", j["out"])
