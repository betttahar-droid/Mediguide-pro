"""Render a canvas Short frame by frame and mux the narration.
usage: render.py page.html out.mp4 narration.mp3 [--stills t1,t2,...]"""
import base64, subprocess, sys, pathlib
from playwright.sync_api import sync_playwright
html, out, audio = sys.argv[1:4]
stills = sys.argv[sys.argv.index('--stills') + 1].split(',') if '--stills' in sys.argv else None
FPS = 30
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args=['--allow-file-access-from-files', '--disable-web-security', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 1080, 'height': 1920})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(pathlib.Path(html).resolve().as_uri()); pg.evaluate('document.fonts.ready')
    if errs: sys.exit('page error: ' + errs[0])
    if pg.evaluate('typeof window.whenReady') == 'function':
        pg.evaluate('window.whenReady()')
    grab = lambda t: base64.b64decode(pg.evaluate(f"(async () => {{ if (window.prepare) await prepare({t}); renderFrame({t}); return document.getElementById('c').toDataURL('image/jpeg', .93); }})()").split(',')[1])
    if stills:
        for t in stills:
            pathlib.Path(out).mkdir(parents=True, exist_ok=True)
            open(f"{out}/t{float(t):06.2f}.jpg", 'wb').write(grab(float(t)))
        if errs: print('errors:', errs[:3])
        sys.exit()
    end = pg.evaluate('window.END'); n = int(end * FPS)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(FPS), '-i', '-',
                           '-i', audio, '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
                           '-af', 'apad', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(grab(i / FPS))
        if i % 300 == 0: print(f'{i}/{n}', flush=True)
    ff.stdin.close(); ff.wait()
    if errs: print('errors:', errs[:3])
    b.close()
