"""Level picked takes to -16 LUFS, join with gaps, word timings. usage: master.py DIR OUT.mp3 WORDS.json"""
import json, subprocess, sys, re, numpy as np
D, OUT, WJ = sys.argv[1:4]; GAP = .28
picks = json.load(open(f"{D}/picks.json"))
chain = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06:stop_periods=-1:stop_duration=0.5:stop_threshold=-45dB:stop_silence=0.35,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,atempo=1.04,highpass=f=70,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=160:makeup=1"
def lufs(f):
    e = subprocess.run(["ffmpeg","-i",f,"-af","ebur128","-f","null","-"],capture_output=True,text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])
for i, f in sorted(picks.items(), key=lambda x: int(x[0])):
    src, out = f, f"{D}/beat{int(i):02d}.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-af",chain+",aresample=44100","-ac","1",f"{D}/tmp.wav"],check=True)
    gain = -16 - lufs(f"{D}/tmp.wav")
    subprocess.run(["ffmpeg","-v","error","-y","-i",f"{D}/tmp.wav","-af",f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false","-ac","1",out],check=True)
n = len(picks); ins = []; fc = ""
for k in range(n): ins += ["-i", f"{D}/beat{k+1:02d}.wav"]; fc += f"[{k}:a]" + (f"[{n}:a]" if k < n-1 else "")
subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-t",str(GAP),"-i","anullsrc=r=44100:cl=mono",f"{D}/gap.wav"],check=True)
subprocess.run(["ffmpeg","-v","error","-y",*ins,"-i",f"{D}/gap.wav","-filter_complex",fc+f"concat=n={2*n-1}:v=0:a=1,alimiter=limit=0.89[o]","-map","[o]","-ac","1","-b:a","192k",OUT],check=True)
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8"); t = 0; res = []
for k in range(1, n+1):
    f = f"{D}/beat{k:02d}.wav"
    d = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
    segs,_ = m.transcribe(np.frombuffer(raw,np.int16).astype(np.float32)/32768.0, word_timestamps=True)
    ws = [{"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)} for s in segs for w in s.words]
    res.append({"beat":k,"start":round(t,3),"dur":round(d,3),"words":ws}); t += d + GAP
    print(f"line {k}: {lufs(f):6.1f} LUFS  {len(ws)/(ws[-1]['e']-ws[0]['s']):.2f} w/s  {' '.join(w['w'] for w in ws)}")
json.dump(res, open(WJ, "w"))
print("total", round(t - GAP, 2), "s")
