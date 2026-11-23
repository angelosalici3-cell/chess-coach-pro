import numpy as np, wave
SR = 44100; DUR = 53.0; bpm = 118; beat = 60/bpm
N = int(SR*DUR); L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
def add(sig, t0, pan=0.0, g=1.0):
    i = int(t0*SR)
    if i >= N: return
    sig = sig[:N-i]*g
    L[i:i+len(sig)] += sig*(1-max(0, pan)); R[i:i+len(sig)] += sig*(1+min(0, pan))
def hz(m): return 440*2**((m-69)/12)
def pluck(f, d=0.35):
    t = np.arange(int(d*SR))/SR; e = np.exp(-t*9)
    return (np.sin(2*np.pi*f*t)+0.45*np.sin(4*np.pi*f*t)*np.exp(-t*14)+0.2*np.sin(6*np.pi*f*t)*np.exp(-t*20))*e*0.5
def bass(f, d):
    t = np.arange(int(d*SR))/SR; e = np.minimum(1, t*80)*np.exp(-t*3.2)
    return np.sin(2*np.pi*f*t)*e*0.9
def kick():
    t = np.arange(int(0.28*SR))/SR; f = 48+110*np.exp(-t*28)
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*11)*1.1
def hat():
    t = np.arange(int(0.06*SR))/SR; n = np.random.RandomState(3).randn(len(t))
    n = np.diff(n, prepend=0); return n*np.exp(-t*70)*0.35
def clap():
    t = np.arange(int(0.18*SR))/SR; n = np.random.RandomState(5).randn(len(t))
    return n*np.exp(-t*26)*0.4*(0.5+0.5*np.sin(t*900))
def pad(freqs, d):
    t = np.arange(int(d*SR))/SR; e = np.minimum(1, t*3)*np.minimum(1, (d-t)*3)
    return sum(np.sin(2*np.pi*f*t)+0.5*np.sin(2*np.pi*f*1.004*t) for f in freqs)*e*0.045
chords = [(48, [60, 64, 67, 72]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]), (43, [55, 59, 62, 67])]  # C Am F G
bars = int(DUR/(4*beat))
for b in range(bars):
    root, tones = chords[b % 4]; t0 = b*4*beat; first = b < 2; last = b >= bars-2
    add(pad([hz(m) for m in tones[:3]], 4*beat), t0, 0, 1.0)
    for i in range(8):          # arpeggio a crome
        m = tones[[0, 1, 2, 3, 2, 1, 2, 3][i]] + (12 if (b % 4 == 3 and i > 5) else 0)
        add(pluck(hz(m)), t0+i*beat/2, (-0.4 if i % 2 else 0.4), 0.9 if not first else 0.6)
    if not first:
        for q in range(4):
            add(bass(hz(root), beat*0.9), t0+q*beat, 0, 1.0 if q % 2 == 0 else 0.7)
            add(kick(), t0+q*beat, 0, 1.0)
            add(hat(), t0+q*beat+beat/2, 0.3, 1.0)
            if q in (1, 3): add(clap(), t0+q*beat, 0, 0.8)
    else:
        add(kick(), t0, 0, 0.8)
    if last and b == bars-1: add(pluck(hz(84), 1.5), t0, 0, 0.9)
x = np.stack([L, R], 1)
x = np.tanh(x*0.9)
x /= np.max(np.abs(x))/0.8
fi = int(1.0*SR); fo = int(2.5*SR); x[:fi] *= np.linspace(0, 1, fi)[:, None]; x[-fo:] *= np.linspace(1, 0, fo)[:, None]
w = wave.open("/tmp/vid/music.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((x*32767).astype(np.int16).tobytes()); w.close(); print("ok")
