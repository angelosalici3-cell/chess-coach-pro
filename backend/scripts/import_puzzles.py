"""Importa un campione di puzzle Lichess (database ufficiale database.lichess.org, licenza CC0) nella tabella `puzzles`.

Legge il CSV scaricato dal workflow (in streaming, senza caricarlo in memoria) e per ogni fascia di rating da 100 punti
sceglie a caso PER_BAND puzzle con Popularity >= MIN_POPULARITY (campionamento "reservoir").
Uso: python backend/scripts/import_puzzles.py <file.csv>
Variabili: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (obbligatorie), PER_BAND (default 200), MIN_POPULARITY (default 80).
"""
import csv
import os
import random
import sys

PER_BAND = int(os.environ.get("PER_BAND", "200"))
MIN_POP = int(os.environ.get("MIN_POPULARITY", "80"))


def to_row(d: dict) -> dict | None:
    try:
        if not d["PuzzleId"] or not d["FEN"] or not d["Moves"]:
            return None
        return {"id": d["PuzzleId"], "fen": d["FEN"], "moves": d["Moves"], "rating": int(d["Rating"]),
                "popularity": int(d["Popularity"]), "themes": d["Themes"].split(),
                "opening_tags": d.get("OpeningTags", "").split() or None}
    except (KeyError, ValueError):
        return None


def sample(path: str) -> list[dict]:
    bands: dict[int, list[dict]] = {}
    seen: dict[int, int] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for d in csv.DictReader(f):
            row = to_row(d)
            if not row or row["popularity"] < MIN_POP or not (400 <= row["rating"] < 3000):
                continue
            b = row["rating"] // 100 * 100
            n = seen[b] = seen.get(b, 0) + 1
            res = bands.setdefault(b, [])
            if len(res) < PER_BAND:
                res.append(row)
            else:
                j = random.randrange(n)
                if j < PER_BAND:
                    res[j] = row
    for b in sorted(bands):
        print(f"{b}-{b + 99}: {len(bands[b])} scelti su {seen[b]}", flush=True)
    return [r for b in sorted(bands) for r in bands[b]]


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: import_puzzles.py <file.csv>", file=sys.stderr)
        return 2
    batch = sample(sys.argv[1])
    if len(batch) < 100:
        print("Troppi pochi puzzle nel file: non scrivo nulla.", file=sys.stderr)
        return 1
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    for i in range(0, len(batch), 500):
        sb.table("puzzles").upsert(batch[i:i + 500], on_conflict="id").execute()
        print(f"  scritti {min(i + 500, len(batch))}/{len(batch)}", flush=True)
    print(f"Importati {len(batch)} puzzle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
