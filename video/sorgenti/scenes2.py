import os
from draw import *
LANG = os.environ.get("VLANG", "it")
TX = {"it": {
 "tag": ["Il Gran Maestro che studia", "le tue partite"],
 "p1": "Giochi tante partite.", "p2": "Ma gli errori tornano sempre.", "p1s": "Capire dove sbagli è la parte difficile.",
 "a_h": "Analizziamo ogni partita", "a1": "Le tue partite", "a1s": "Lichess · Chess.com", "a2": "Motore Stockfish", "a2s": "valuta ogni mossa", "a3": "I tuoi errori", "a3s": "trovati e ordinati",
 "a_err": "Errori", "a_inn": "Imprecisioni", "a_ok": "Mosse ottime", "a_cap": "Senza caricare niente a mano.",
 "g_h": "Il Gran Maestro ti spiega perché", "g_e": "Errore", "g_es": "Hai mosso senza guardare le difese.", "g_i": "Idea", "g_is": "Prima di catturare, controlla chi difende.", "g_r": "Regola", "g_rs": "Un pezzo non controllato è un pezzo regalato.", "g_cap": "Una lezione sulle TUE partite.",
 "t_h": "Alleni proprio i tuoi punti deboli", "t1": "I tuoi errori", "t2": "Esercizi su misura", "t3": "Ripasso nel tempo", "t_c": "giorni di fila", "t_cap": "Pochi minuti al giorno, risultati veri.",
 "c_h": "Colleziona carte rare", "c_r": ["Comune", "Rara", "Epica", "Leggendaria"], "c_s": "Vinci contro avversari più forti, ogni 100 punti", "c_ex": "esempio", "c_cap": "Ogni traguardo ha la sua carta.",
 "r_h": "Guarda i tuoi progressi", "r_pts": "punti", "r_op": "Le tue aperture", "r_names": ["Siciliana", "Italiana", "Francese", "Londra"], "r_cap": "Sai cosa funziona e cosa no.",
 "n_h": "Parti gratis, cresci quando vuoi", "n_names": ["Free", "Plus", "Pro", "Elite"], "n_sub": ["Prova", "Inizia", "Migliora", "Più account"], "n_cap": "Cambi piano o disdici quando vuoi.",
 "end1": "Allenati sulle tue partite.", "end2": "Italiano · English · Español", "cta": "Inizia gratis",
}}
T = TX[LANG]

def ss(w, h, fn, k=2):
    lay = Image.new("RGBA", (w*k, h*k), (0, 0, 0, 0)); fn(ImageDraw.Draw(lay), k)
    return lay.resize((w, h), Image.LANCZOS)
def head(im, s, t, y=290, size=74):
    ls = wrap(s, F(size), 920); a = ease(seg(t, 0.05, 0.5))
    for i, l in enumerate(ls):
        text(im, (W//2, int(y + i*(size+14) + (1-a)*30)), l, F(size), TXT if a > 0.98 else MUT, "mm")
def sub(im, s, t, st=0.6):
    a = ease(seg(t, st, st+0.5)); c = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
    text(c, (W//2, 45 + int((1-a)*14)), s, F(42, "Medium"), MUT + (int(255*a),), "mm"); im.paste(c, (0, 1690), c)
def brand(im, a=1): icon(im, 90, 100, 56, a)
def dur_fade(im, t, d, fi=0.2, fo=0.25): return fade(im, min(1, t/fi, (d - t)/fo))

# ---- 0 apertura logo
def o0(f, n):
    t = f/FPS; im = newf()
    k = back(seg(t, 0, 0.7)); icon(im, W//2, 800, 420*k)
    ring = ss(560, 560, lambda d, s: d.arc((20*s, 20*s, 540*s, 540*s), -90, -90 + 360*ease(seg(t, 0.2, 1.6)), fill=OR, width=10*s))
    if t > 0.2: paste_a(im, ring, (W//2-280, 800-280), 1 - seg(t, 1.8, 2.3))
    a = ease(seg(t, 1.0, 1.6)); text(im, (W//2, 1120), "Chess Coach", F(110), TXT if a > .98 else MUT, "mm")
    c = Image.new("RGBA", (W, 170), (0, 0, 0, 0)); 
    for i, l in enumerate(T["tag"]): text(c, (W//2, 40+i*66), l, F(50, "Medium"), MUT + (int(255*ease(seg(t, 1.6, 2.2))),), "mm")
    im.paste(c, (0, 1190), c)
    return dur_fade(im, t, 3.5, 0.15, 0.3)

# ---- 1 problema
def o1(f, n):
    t = f/FPS; im = newf(); brand(im)
    head(im, T["p1"] if t < 2.9 else T["p2"], t if t < 2.9 else t-2.9, 300)
    cols, rows, tw = 6, 6, 128; gx = (W - cols*tw - (cols-1)*14)//2; bad = {2, 9, 13, 14, 20, 26, 28, 33}
    for i in range(cols*rows):
        r, c = divmod(i, cols); st = 0.3 + i*0.055
        k = back(seg(t, st, st+0.3))
        if k < 0.05: continue
        x = gx + c*(tw+14); y = 520 + r*(tw+14); s = int(tw*min(1, k)); o = (tw-s)//2
        isbad = i in bad and t > 2.9 + (list(sorted(bad)).index(i))*0.12
        col = RED if isbad else PANEL2
        rr(im, (x+o, y+o, x+o+s, y+o+s), 24, col)
        if s > 60: text(im, (x+tw//2, y+tw//2+4), "?!" if isbad else "♟", F(56) if isbad else CF(64), (255, 255, 255) if isbad else (96, 108, 160), "mm")
    sub(im, T["p1s"], t, 3.6)
    return dur_fade(im, t, 5.5)

# ---- 2 analisi
def o2(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["a_h"], t, 290)
    nodes = [(T["a1"], T["a1s"], "♟", 620, OR), (T["a2"], T["a2s"], "♜", 960, (91, 140, 255)), (T["a3"], T["a3s"], "♚", 1300, RED)]
    d = ImageDraw.Draw(im)
    for i, (a, b, g, y, col) in enumerate(nodes):
        k = ease(seg(t, 0.4 + i*0.5, 0.9 + i*0.5)); x0 = int(90 - (1-k)*500*(1 if i % 2 else -1))
        rr(im, (x0, y-100, x0+W-180, y+100), 36, PANEL, (46, 56, 100))
        d.ellipse((x0+30, y-70, x0+170, y+70), fill=col); text(im, (x0+100, y+6), g, CF(86), (255, 255, 255), "mm")
        text(im, (x0+205, y-26), a, F(46), TXT, "lm"); text(im, (x0+205, y+28), b, F(34, "Medium"), MUT, "lm")
    for i, (y1, y2) in enumerate([(720, 860), (1060, 1200)]):   # pacchetti che scorrono
        if t > 1.2 + i*0.5:
            for j in range(3):
                p = ((t*0.9 - j/3) % 1); yy_ = y1 + (y2-y1)*p
                d.line((W//2, y1, W//2, y2), fill=(60, 72, 120), width=6)
                d.ellipse((W//2-14, yy_-14, W//2+14, yy_+14), fill=OR)
    if t > 3.6:
        vals = [(T["a_err"], 12, RED), (T["a_inn"], 27, OR), (T["a_ok"], 41, GRN)]
        for i, (lab, v, col) in enumerate(vals):
            k = ease(seg(t, 3.6 + i*0.4, 4.6 + i*0.4)); cx = 230 + i*310
            chip(im, cx, 1470, f"{int(v*k)}", col, font=F(56), scale=1.0)
            text(im, (cx, 1535), lab, F(30, "Medium"), MUT, "mm")
    sub(im, T["a_cap"], t, 5.3)
    return dur_fade(im, t, 7.0)

# ---- 3 lezione GM
def o3(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["g_h"], t, 290)
    k = back(seg(t, 0.3, 0.9)); cx, cy = W//2, 700
    for j in range(3):
        r = 150 + ((t*60 + j*40) % 120); a = 1 - ((t*60 + j*40) % 120)/120
        lay = ss(500, 500, lambda d, s: d.ellipse((250*s-r*s, 250*s-r*s, 250*s+r*s, 250*s+r*s), outline=(255, 107, 61, int(120*a)), width=4*s))
        paste_a(im, lay, (cx-250, cy-250))
    icon(im, cx, cy, 230*k)
    items = [(T["g_e"], T["g_es"], RED, 1050), (T["g_i"], T["g_is"], OR, 1280), (T["g_r"], T["g_rs"], GRN, 1510)]
    for i, (h, b, col, y) in enumerate(items):
        k2 = ease(seg(t, 1.3 + i*0.9, 1.9 + i*0.9)); x0 = int(80 + (1-k2)*(-1 if i % 2 else 1)*700)
        rr(im, (x0, y-95, x0+W-160, y+95), 32, PANEL, col, 3)
        rr(im, (x0, y-95, x0+18, y+95), 9, col)
        text(im, (x0+50, y-40), h, F(42), col, "lm")
        ls = wrap(b, F(34, "Medium"), 800)
        for j, l in enumerate(ls): text(im, (x0+50, y+18+j*42), l, F(34, "Medium"), TXT, "lm")
    sub(im, T["g_cap"], t, 4.6)
    return dur_fade(im, t, 7.0)

# ---- 4 allenamento
def o4(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["t_h"], t, 290)
    cx, cy = W//2, 1000; R = 300
    ring = ss(800, 800, lambda d, s: [d.arc((100*s, 100*s, 700*s, 700*s), -90+a0+14, -90+a0+106, fill=col, width=22*s) for a0, col in ((0, OR), (120, (91, 140, 255)), (240, GRN))])
    paste_a(im, ring, (cx-400, cy-400), ease(seg(t, 0.2, 0.8)))
    ang = math.radians(-90 + 360*((t-0.8)*0.22 % 1)) if t > 0.8 else math.radians(-90)
    d = ImageDraw.Draw(im); px, py = cx + R*math.cos(ang), cy + R*math.sin(ang)
    if t > 0.8: d.ellipse((px-22, py-22, px+22, py+22), fill=(255, 255, 255)); d.ellipse((px-10, py-10, px+10, py+10), fill=OR)
    for lab, a_, col, st in ((T["t1"], -90, OR, 0.8), (T["t2"], 30, (91, 140, 255), 1.3), (T["t3"], 150, GRN, 1.8)):
        k = back(seg(t, st, st+0.5)); x = cx + (R+10)*math.cos(math.radians(a_)); y = cy + (R+10)*math.sin(math.radians(a_))
        if k > 0.1: chip(im, x, y, lab, col, (11, 15, 30) if col == GRN else (255, 255, 255), scale=0.95*min(1, k))
    n = int(1 + 6*ease(seg(t, 2.2, 4.4)))
    text(im, (cx, cy-20), str(n), F(190), TXT, "mm"); text(im, (cx, cy+100), T["t_c"], F(38, "Medium"), MUT, "mm")
    sub(im, T["t_cap"], t, 4.8)
    return dur_fade(im, t, 7.0)

# ---- 5 carte
RC = [(120, 140, 190), (70, 150, 255), (176, 96, 255), (255, 190, 60)]; GLY = ["♟", "♞", "♛", "♚"]
def mini(i):
    w_, h_ = 250, 360; lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, w_-1, h_-1), 26, fill=(20, 26, 51), outline=RC[i], width=5)
    d.rounded_rectangle((12, 12, w_-13, 210), 20, fill=tuple(int(c*0.45+20) for c in RC[i]))
    d.text((w_//2, 118), GLY[i], font=CF(120), fill=(255, 255, 255), anchor="mm")
    d.rounded_rectangle((w_//2-95, 235, w_//2+95, 275), 20, fill=RC[i]); d.text((w_//2, 255), T["c_r"][i], font=F(22), fill=(11, 15, 30), anchor="mm")
    return lay
MC = [mini(i) for i in range(4)]
def o5(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["c_h"], t, 290)
    for i in range(4):
        k = ease(seg(t, 0.4 + i*0.25, 1.4 + i*0.25)); ang = (i-1.5)*14*k; 
        c = MC[i].rotate(-ang, expand=True, resample=Image.BICUBIC)
        x = W//2 + (i-1.5)*200*k; y = 690 - abs(i-1.5)*12*k
        paste_a(im, c, (int(x-c.width/2), int(y-c.height/2)))
    text(im, (W//2, 1010), T["c_s"], F(40, "Medium"), TXT, "mm")
    d = ImageDraw.Draw(im); labels = ["1500", "1600", "1700", "1800", "1900"]; bw = 150
    x0 = (W - 5*bw - 4*14)//2
    for i, lb in enumerate(labels):
        k = ease(seg(t, 1.8 + i*0.4, 2.6 + i*0.4)); h_ = int((150 + i*70) * k); x = x0 + i*(bw+14); yb = 1560
        if h_ > 4:
            col = RC[min(3, max(0, i-1))] if i > 0 else RC[0]
            rr(im, (x, yb-h_, x+bw, yb), 22, col); text(im, (x+bw//2, yb-h_+44), lb, F(40), (11, 15, 30) if i == 4 else (255, 255, 255), "mm")
            text(im, (x+bw//2, yb-h_+92), "♟" if i < 4 else "♚", CF(48), (11, 15, 30) if i == 4 else (255, 255, 255), "mm")
    if t > 4.6: 
        k = back(seg(t, 4.6, 5.2)); chip(im, W//2, 1130, "+100", OR, scale=min(1, k))
        chip(im, 900, 1590, T["c_ex"], PANEL2, MUT, F(28), 0.8)
    sub(im, T["c_cap"], t, 5.2)
    return dur_fade(im, t, 7.0)

# ---- 6 progressi
PTS = [1200, 1215, 1208, 1240, 1236, 1262, 1255, 1288, 1310, 1301, 1330, 1348, 1342, 1365, 1380]
def o6(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["r_h"], t, 290)
    rr(im, (70, 430, W-70, 960), 36, PANEL, (46, 56, 100)); d = ImageDraw.Draw(im)
    for g_ in range(1, 4): d.line((110, 430+g_*132, W-110, 430+g_*132), fill=(36, 46, 86), width=2)
    prog = ease(seg(t, 0.4, 3.2)); m = len(PTS)-1; pts = []
    for i, v in enumerate(PTS):
        pts.append((130 + i*(W-260)/m, 920 - (v-1180)/(1400-1180)*430))
    shown = prog*m; i0 = int(shown); xy = pts[:i0+1]
    if i0 < m: a, b = pts[i0], pts[i0+1]; fr = shown - i0; xy.append((a[0]+(b[0]-a[0])*fr, a[1]+(b[1]-a[1])*fr))
    lay = ss(W, 560, lambda dd, s: dd.line([(x*s, (y-400)*s) for x, y in xy], fill=OR, width=9*s, joint="curve") if len(xy) > 1 else None)
    im.paste(lay, (0, 400), lay)
    if len(xy) > 1:
        ex, ey = xy[-1]; d.ellipse((ex-16, ey-16, ex+16, ey+16), fill=(255, 255, 255)); d.ellipse((ex-8, ey-8, ex+8, ey+8), fill=OR)
    if t > 3.2:
        k = back(seg(t, 3.2, 3.7)); chip(im, 800, 520, "+180 " + T["r_pts"], GRN, (11, 15, 30), scale=min(1, k))
    text(im, (80, 1040), T["r_op"], F(42), TXT, "lm")
    vals = [0.82, 0.66, 0.52, 0.41]; cols = [OR, (91, 140, 255), GRN, (176, 96, 255)]
    for i, nm in enumerate(T["r_names"]):
        y = 1130 + i*110; k = ease(seg(t, 3.0 + i*0.35, 4.0 + i*0.35))
        text(im, (80, y), nm, F(34, "Medium"), MUT, "lm"); rr(im, (330, y-22, W-190, y+22), 22, PANEL)
        w_ = (W-190-330)*vals[i]*k
        if w_ > 20: rr(im, (330, y-22, 330+w_, y+22), 22, cols[i])
        text(im, (W-80, y), f"{int(vals[i]*100*k)}%", F(34), TXT, "rm")
    sub(im, T["r_cap"], t, 5.0)
    return dur_fade(im, t, 6.5)

# ---- 7 piani
def o7(f, n):
    t = f/FPS; im = newf(); brand(im); head(im, T["n_h"], t, 290)
    bw = 215; x0 = (W - 4*bw - 3*16)//2
    for i in range(4):
        k = ease(seg(t, 0.5 + i*0.3, 1.3 + i*0.3)); h_ = int((260 + i*150) * k); x = x0 + i*(bw+16); yb = 1440
        if h_ > 6:
            col = [(70, 84, 140), (91, 140, 255), OR, GOLD][i]
            rr(im, (x, yb-h_, x+bw, yb), 26, col)
            text(im, (x+bw//2, yb-h_+60), T["n_names"][i], F(44), (11, 15, 30) if i == 3 else (255, 255, 255), "mm")
            ls = wrap(T["n_sub"][i], F(30, "Medium"), bw-30)
            for j, l in enumerate(ls): text(im, (x+bw//2, yb-h_+115+j*38), l, F(30, "Medium"), (11, 15, 30) if i == 3 else (234, 238, 252), "mm")
    sub(im, T["n_cap"], t, 2.6)
    return dur_fade(im, t, 5.0)

# ---- 8 chiusura
def o8(f, n):
    t = f/FPS; im = newf()
    k = back(seg(t, 0, 0.6)); icon(im, W//2, 640, 400*k)
    text(im, (W//2, 960), "Chess Coach", F(110), TXT, "mm")
    a = ease(seg(t, 0.5, 1.1)); c = Image.new("RGBA", (W, 220), (0, 0, 0, 0))
    text(c, (W//2, 40), T["end1"], F(56), TXT + (int(255*a),), "mm"); text(c, (W//2, 130), T["end2"], F(38, "Medium"), MUT + (int(255*a),), "mm")
    im.paste(c, (0, 1040), c)
    k = back(seg(t, 1.4, 2.0)); pul = 1 + 0.03*math.sin(t*6) if t > 2 else 1
    if k > 0.05:
        w_, h_ = 580*k*pul, 130*k*pul; rr(im, (W/2-w_/2, 1450-h_/2, W/2+w_/2, 1450+h_/2), h_/2, OR)
        text(im, (W//2, 1450), T["cta"], F(max(10, int(56*k))), (255, 255, 255), "mm")
    return fade(im, min(1, t/0.25, (5 - t)/0.6))

SCENES = [(o0, 3.5), (o1, 5.5), (o2, 7.0), (o3, 7.0), (o4, 7.0), (o5, 7.0), (o6, 6.5), (o7, 5.0), (o8, 5.0)]
