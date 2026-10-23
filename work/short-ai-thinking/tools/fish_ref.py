"""Fish TTS with an inline reference clip (zero-shot), so every line keeps the same accent.
usage: fish_ref.py jobs.json ref.mp3 "ref transcript" """
import json, os, sys, urllib.request, ormsgpack
jobs, ref, ref_text = json.load(open(sys.argv[1])), open(sys.argv[2], "rb").read(), sys.argv[3]
for j in jobs:
    body = {"text": j["text"], "references": [{"audio": ref, "text": ref_text}], "format": "mp3", "mp3_bitrate": 192,
            "language": "en", "prosody": {"speed": j.get("speed", 1.0)}}
    if j.get("voice"): body["reference_id"] = j["voice"]
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=ormsgpack.packb(body), method="POST",
        headers={"Authorization": f"Bearer {os.environ['FISH_API_KEY']}", "Content-Type": "application/msgpack", "model": "drama-3"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r: open(j["out"], "wb").write(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {e.read()[:300]}")
    print("ok", j["out"], flush=True)
