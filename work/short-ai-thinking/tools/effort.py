import subprocess, numpy as np
def effort(f):
    """Vocal effort proxy: 2-5 kHz vs 100-1000 Hz energy (dB) over voiced frames, plus raw level."""
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = 512; fr = np.lib.stride_tricks.sliding_window_view(x, n)[::256] * np.hanning(n)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2; fq = np.fft.rfftfreq(n, 1 / 16000)
    e = P.sum(1); v = e > np.percentile(e, 60)
    hi = P[v][:, (fq > 2000) & (fq < 5000)].sum(1); lo = P[v][:, (fq > 100) & (fq < 1000)].sum(1)
    return float(np.median(10 * np.log10(hi / lo))), float(10 * np.log10(np.mean(e[v]) + 1e-12))
