import subprocess, os, sys
sys.path.insert(0, "/tmp/vid")
from scenes2 import *
out = "/tmp/vid/out2"; os.makedirs(out, exist_ok=True)
for k, (fn, dur) in enumerate(SCENES):
    n = int(dur * FPS); tmp = f"{out}/s{k}.tmp.mp4"; fin = f"{out}/s{k}.mp4"
    if os.path.exists(fin): continue
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(fn(f, n).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() == 0: os.rename(tmp, fin); print("scena", k, "ok", flush=True)
