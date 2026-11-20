"""Sonda sul dataset Lichess/chess-position-evaluations (CC0): cosa contiene, che convenzione di segno usa e
quante delle posizioni delle TUE partite ci sono. Non scrive nulla. Serve a decidere se vale la pena usarlo come base per eval_cache.

Uso (da backend/):  python -m scripts.lichess_eval_probe --email TUA_EMAIL [--files 3]
Richiede: pip install duckdb huggingface_hub  (più i requisiti normali).  --files all = tutto il dataset (circa 44 GB)."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

REPO = "Lichess/chess-position-evaluations"
VAL = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9}


def key4(fen):
    return " ".join(fen.split()[:4])


def material(fen):
    """Bianco meno Nero in pedine, dal solo campo della posizione."""
    m = 0
    for c in fen.split(" ")[0]:
        if c.lower() in VAL:
            m += VAL[c.lower()] * (1 if c.isupper() else -1)
    return m


def sign_check(rows):
    """rows: [(fen, cp)] con cp non nullo. Confronta il segno di cp con il materiale, separando i casi per turno."""
    out = {"w": [0, 0], "b": [0, 0]}
    for fen, cp in rows:
        mat = material(fen)
        if abs(mat) < 3 or abs(cp) < 300:
            continue
        side = "w" if fen.split(" ")[1] == "w" else "b"
        out[side][1] += 1
        out[side][0] += (cp > 0) == (mat > 0)
    return {k: (round(a / n, 2) if n else None, n) for k, (a, n) in out.items()}


def our_positions(email):
    from app.patterns import load
    games, by = load(email, 150)
    pos = {key4("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"): 0}
    for rows in by.values():
        for r in rows:
            if r.get("fen_after"):
                k = key4(r["fen_after"])
                pos[k] = min(pos.get(k, 999), r["ply"])
    return pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--files", default="3")
    a = ap.parse_args()
    import duckdb
    from huggingface_hub import HfApi, hf_hub_download

    api, rev = HfApi(), None
    files = sorted(f for f in api.list_repo_files(REPO, repo_type="dataset") if f.endswith(".parquet"))
    if not files:   # a volte i parquet stanno solo nel ramo convertito automaticamente
        rev = "refs/convert/parquet"
        files = sorted(f for f in api.list_repo_files(REPO, repo_type="dataset", revision=rev) if f.endswith(".parquet"))
    print(f"File parquet nel dataset: {len(files)}" + (f" (ramo {rev})" if rev else ""))
    take = files if a.files == "all" else files[: int(a.files)]
    ours = our_positions(a.email)
    print(f"Posizioni distinte nelle tue partite: {len(ours)}")
    con = duckdb.connect()
    con.execute("create table ours(key varchar, ply int)")
    con.executemany("insert into ours values (?, ?)", list(ours.items()))
    found: dict = {}
    sign_rows, ranges, depths = [], [], []
    expr = "split_part(fen,' ',1)||' '||split_part(fen,' ',2)||' '||split_part(fen,' ',3)||' '||split_part(fen,' ',4)"
    for f in take:
        path = hf_hub_download(REPO, f, repo_type="dataset", revision=rev)
        print(f"\n{f}")
        cols = [r[0] for r in con.execute(f"describe select * from read_parquet('{path}')").fetchall()]
        n, lo, hi = con.execute(f"select count(*), min(fen), max(fen) from read_parquet('{path}')").fetchone()
        print(f"  colonne: {cols}  righe: {n:,}\n  fen minimo: {lo}\n  fen massimo: {hi}")
        ranges.append((lo, hi))
        sign_rows += con.execute(f"select fen, cp from read_parquet('{path}') using sample 100000 rows").fetchall()
        sign_rows = [(x, c) for x, c in sign_rows if c is not None]
        for key, ply, d in con.execute(
                f"select o.key, o.ply, max(p.depth) from ours o join (select {expr} as k, depth from read_parquet('{path}')) p on p.k = o.key group by o.key, o.ply").fetchall():
            found[key] = (ply, max(d, found.get(key, (0, 0))[1]))
    print("\n=== Convenzione del segno (quota di cp concordi con il materiale) ===")
    sc = sign_check(sign_rows)
    print(f"  Bianco al tratto: {sc['w']}   Nero al tratto: {sc['b']}")
    if sc["w"][0] and sc["b"][0]:
        print("  Verdetto:", "punto di vista del BIANCO (come il nostro eval_pawns)" if sc["b"][0] > 0.6
              else "punto di vista di CHI HA IL TRATTO (va invertito per il Nero)" if sc["b"][0] < 0.4 else "non chiaro")
    print("\n=== Copertura delle tue posizioni ===")
    print(f"  Trovate: {len(found)} su {len(ours)} ({100 * len(found) / max(1, len(ours)):.1f}%) in {len(take)} file su {len(files)}")
    for lo_p, hi_p in ((0, 10), (11, 20), (21, 30), (31, 400)):
        tot = sum(1 for p in ours.values() if lo_p <= p <= hi_p)
        got = sum(1 for k, (p, _) in found.items() if lo_p <= p <= hi_p)
        print(f"  semimosse {lo_p}-{hi_p}: {got}/{tot}" + (f" ({100 * got / tot:.0f}%)" if tot else ""))
    if found:
        ds = sorted(d for _, d in found.values())
        print(f"  Profondità delle valutazioni trovate: minima {ds[0]}, mediana {ds[len(ds) // 2]}, massima {ds[-1]}")
    if a.files != "all":
        print("  Nota: è solo un campione dei file; la copertura sull'intero dataset può essere più alta.")
    print("\n=== Ordinamento ===")
    ov = sum(1 for i in range(len(ranges)) for j in range(i + 1, len(ranges)) if ranges[i][0] <= ranges[j][1] and ranges[j][0] <= ranges[i][1])
    print("  Intervalli di FEN dei file che si sovrappongono:", ov, "(0 = file ordinati per FEN, ricerca mirata possibile)" if ov == 0 else "(i file non sono ordinati per FEN: serve leggerli tutti)")


if __name__ == "__main__":
    main()
