"""Score takes: transcript match, words/sec, loudness peakiness. Print best per line."""
import json, re, subprocess, glob, numpy as np, difflib, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-Mediguide-pro/5db476f1-d223-579a-818a-ff5690f6e4dd/scratchpad")
from effort import effort
from resemblyzer import VoiceEncoder, preprocess_wav
enc = VoiceEncoder("cpu")
def emb(f):
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
    return enc.embed_utterance(preprocess_wav(np.frombuffer(raw,np.int16).astype(np.float32)/32768.0, 16000))
REF = emb("audition_uk/5_laura_british_direction.mp3")
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8")
L = json.load(open("script_v6.json"))
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", re.sub(r"\[[^\]]*\]|<[^>]*>", "", s).lower().replace("twenty percent", "20").replace("%", "").replace("-", " ")).split()
best = {}
for i, line in enumerate(L, 1):
    ref = norm(line); rows = []
    for f in sorted(glob.glob(f"laura6/takes/b{i:02d}_t*.mp3")):
        raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
        segs,_ = m.transcribe(np.frombuffer(raw,np.int16).astype(np.float32)/32768.0, word_timestamps=True)
        ws = [w for s in segs for w in s.words]
        hyp = norm(" ".join(w.word for w in ws).replace("%"," percent"))
        hyp = [x if x != "percent" else "" for x in hyp]; hyp=[x for x in hyp if x]
        match = difflib.SequenceMatcher(None, ref, hyp).ratio()
        speech = ws[-1].end - ws[0].start if ws else 1
        out = subprocess.run(["ffmpeg","-i",f,"-af","ebur128","-f","null","-"],capture_output=True,text=True).stderr
        M = [float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", out) if float(x) > -50]
        I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
        wps = len(ref) / speech; peak = np.percentile(M, 98) - I
        tilt = effort(f)[0]; sim = float(np.dot(emb(f), REF)); score = (0 if match > .93 else 10) + max(0, 2.5 - wps) * 2 + .2 * peak + .3 * (tilt + 25) + 25 * (1 - sim)
        rows.append((score, f, match, wps, I, peak))
        print(f"  {f.split('/')[-1]} sim={sim:.3f} match={match:.2f} wps={wps:.2f} I={I:.1f} peak98-I={peak:.1f} score={score:.2f}")
    b = min(rows); best[i] = b[1]; print(f"line {i}: pick {b[1].split('/')[-1]}")
json.dump(best, open("laura6/picks.json", "w"), indent=1)
