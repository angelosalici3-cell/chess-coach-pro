import math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS = 1080, 1920, 30
BG, PANEL, PANEL2 = (11,15,30), (20,26,51), (28,36,70)
OR, RED, TXT, MUT, GRN, GOLD = (255,107,61), (255,61,90), (234,238,252), (154,164,199), (61,220,151), (255,200,70)
FD = "/usr/share/fonts/truetype/google-fonts/Poppins-"
_fc = {}
def F(sz, w="Bold"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + w + ".ttf", sz)
    return _fc[k]
def CF(sz):
    k = ("c", sz)
    if k not in _fc: _fc[k] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", sz)
    return _fc[k]
def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3
def eio(t): t = max(0, min(1, t)); return t*t*(3-2*t)
def back(t):
    t = max(0, min(1, t)); c = 1.70158; return 1 + (c+1)*(t-1)**3 + c*(t-1)**2
def seg(t, a, b): return max(0, min(1, (t-a)/(b-a)))

# sfondo: blu notte con un bagliore arancione in alto
yy, xx = np.mgrid[0:H, 0:W]
g = np.exp(-(((xx-W*0.5)/700)**2 + ((yy-120)/520)**2))
base = np.zeros((H, W, 3), np.float32); base[:] = BG
base += g[..., None] * np.array([46, 22, 14], np.float32)
base += (yy[..., None] / H) * np.array([4, 6, 18], np.float32)
BASE = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
ICON = Image.open("/mnt/user-data/outputs/chess-coach/frontend/public/icon-512.png").convert("RGBA")

def newf(): return BASE.copy()
def rr(im, box, r, fill, outline=None, w=2):
    ImageDraw.Draw(im).rounded_rectangle(box, r, fill=fill, outline=outline, width=w)
def text(im, xy, s, font, fill=TXT, anchor="la"):
    ImageDraw.Draw(im).text(xy, s, font=font, fill=fill, anchor=anchor)
def wrap(s, font, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (4, 4))); out, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: out.append(cur); cur = w
    return out + [cur]
def paste_a(im, sub, xy, a=1.0):
    if a < 1:
        sub = sub.copy(); al = sub.getchannel("A").point(lambda v: int(v*a)); sub.putalpha(al)
    im.paste(sub, xy, sub)
def icon(im, cx, cy, size, a=1.0):
    if size < 4: return
    s = ICON.resize((int(size), int(size)), Image.LANCZOS); paste_a(im, s, (int(cx-size/2), int(cy-size/2)), a)
def fade(im, a):  # a: 0 = sfondo, 1 = pieno
    return im if a >= 1 else Image.blend(BASE, im, max(0, a))
def topbar(im, a=1):
    icon(im, 96, 110, 64, a); text(im, (140, 110), "Chess Coach", F(34), TXT if a >= 1 else MUT, "lm")
def caption(im, s, t, lines_font=F(46, "Bold")):
    a = ease(seg(t, 0.1, 0.6)); ls = wrap(s, lines_font, 900)
    h = len(ls) * 64 + 56; y0 = 1700 - h//2 - 20
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rounded_rectangle((60, y0, W-60, y0+h), 36, fill=(20, 26, 51, int(235*a)), outline=(255, 107, 61, int(160*a)), width=2)
    for i, l in enumerate(ls):
        d.text((W//2, y0+28+i*64+32 + int((1-a)*20)), l, font=lines_font, fill=(234, 238, 252, int(255*a)), anchor="mm")
    im.paste(ov, (0, 0), ov)
def chip(im, cx, cy, s, fill, fg=(255,255,255), font=None, scale=1.0):
    font = font or F(int(34*scale)); d = ImageDraw.Draw(im)
    w = d.textlength(s, font=font) + 56*scale; h = 64*scale
    d.rounded_rectangle((cx-w/2, cy-h/2, cx+w/2, cy+h/2), h/2, fill=fill)
    d.text((cx, cy+1), s, font=font, fill=fg, anchor="mm")
