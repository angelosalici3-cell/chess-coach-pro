"""Importa un campione di puzzle Lichess (dataset Lichess/chess-puzzles su Hugging Face, licenza CC0) nella tabella `puzzles`.

Interroga il "dataset viewer" di Hugging Face a fasce di rating da 100 punti e prende pagine casuali di puzzle molto apprezzati.
Variabili: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (obbligatorie), PER_BAND (default 200), MIN_POPULARITY (default 80), HF_TOKEN (facoltativa).
Si lancia dal workflow GitHub "import-puzzles" oppure a mano: python backend/scripts/import_puzzles.py
"""
import math
import os
import random
import sys
import time

import httpx
from supabase import create_client

API = "https://datasets-server.huggingface.co/filter"
PER_BAND = int(os.environ.get("PER_BAND", "200"))
MIN_POP = int(os.environ.get("MIN_POPULARITY", "80"))
HEADERS = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"} if os.environ.get("HF_TOKEN") else {}


def fetch(client: httpx.Client, where: str, offset: int, length: int) -> dict:
    params = {"dataset": "Lichess/chess-puzzles", "config": "default", "split": "train", "where": where, "offset": offset, "length": length}
    for attempt in range(6):
        r = client.get(API, params=params, headers=HEADERS, timeout=60.0)
        if r.status_code == 200:
            return r.json()
        wait = 2 ** attempt * 2
        print(f"  HTTP {r.status_code}, riprovo tra {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"richiesta fallita: {where} offset={offset}")


def to_row(r: dict) -> dict | None:
    d = r.get("row", {})
    if not d.get("PuzzleId") or not d.get("FEN") or not d.get("Moves") or d.get("Rating") is None:
        return None
    return {"id": d["PuzzleId"], "fen": d["FEN"], "moves": d["Moves"], "rating": int(d["Rating"]), "popularity": d.get("Popularity"),
            "themes": d.get("Themes") or [], "opening_tags": d.get("OpeningTags") or None}


def main() -> int:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows: dict[str, dict] = {}
    with httpx.Client() as c:
        for lo in range(400, 3000, 100):
            where = f'"Rating">={lo} AND "Rating"<{lo + 100} AND "Popularity">={MIN_POP}'
            try:
                total = fetch(c, where, 0, 1).get("num_rows_total", 0)
                if not total:
                    print(f"{lo}-{lo + 99}: nessun puzzle", flush=True)
                    continue
                got = 0
                for _ in range(math.ceil(PER_BAND / 100)):
                    data = fetch(c, where, random.randint(0, max(0, total - 100)), 100)
                    for r in data.get("rows", []):
                        row = to_row(r)
                        if row and row["id"] not in rows:
                            rows[row["id"]] = row
                            got += 1
                print(f"{lo}-{lo + 99}: +{got} (disponibili {total})", flush=True)
            except Exception as e:
                print(f"{lo}-{lo + 99}: saltata ({e})", flush=True)
    if len(rows) < 100:
        print("Troppi pochi puzzle scaricati: non scrivo nulla.", file=sys.stderr)
        return 1
    batch = list(rows.values())
    for i in range(0, len(batch), 500):
        sb.table("puzzles").upsert(batch[i:i + 500], on_conflict="id").execute()
    print(f"Importati {len(batch)} puzzle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
