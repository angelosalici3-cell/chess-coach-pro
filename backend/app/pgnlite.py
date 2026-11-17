"""Lettura leggera del PGN senza python-chess: intestazioni, mosse (SAN) e orologio [%clk] per ogni semimossa."""
import re

_HDR = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
_TOKEN = re.compile(r"\{([^}]*)\}|(\([^)]*\))|(\$\d+)|([^\s{}()]+)")
_NUM = re.compile(r"^\d+\.(\.\.)?$")
_CLK = re.compile(r"\[%clk\s+(\d+):(\d{1,2}):(\d{1,2}(?:\.\d+)?)\]")
_RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}


def headers(pgn: str) -> dict:
    return dict(_HDR.findall(pgn or ""))


def plies(pgn: str) -> list[dict]:
    """[{san, clk}] in ordine; clk = secondi rimasti dopo la mossa, o None."""
    body = _HDR.sub(" ", pgn or "")
    out: list[dict] = []
    for m in _TOKEN.finditer(body):
        comment, var, nag, tok = m.groups()
        if comment is not None:
            if out and out[-1]["clk"] is None:
                c = _CLK.search(comment)
                if c:
                    out[-1]["clk"] = int(c.group(1)) * 3600 + int(c.group(2)) * 60 + float(c.group(3))
        elif tok:
            if tok in _RESULTS or _NUM.match(tok):
                continue
            tok = re.sub(r"^\d+\.(\.\.)?", "", tok)  # "1.e4" senza spazio
            tok = tok.rstrip("!?")
            if tok:
                out.append({"san": tok, "clk": None})
    return out


def parse_tc(tc: str | None):
    """'600+5' -> (600, 5); '180' -> (180, 0); giornaliera o sconosciuta -> None."""
    m = re.match(r"^(\d+)(?:\+(\d+))?$", tc or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def move_times(pgn: str, tc: str | None) -> list[dict] | None:
    """Per ogni semimossa: secondi spesi e orologio residuo. None se la partita non ha orologio utilizzabile."""
    t = parse_tc(tc or headers(pgn).get("TimeControl"))
    pl = plies(pgn)
    if not t or not pl or not any(p["clk"] is not None for p in pl):
        return None
    base, inc = t
    left = {0: float(base), 1: float(base)}
    out = []
    for i, p in enumerate(pl):
        side = i % 2
        if p["clk"] is None:
            out.append({"ply": i + 1, "san": p["san"], "spent": None, "clock": None})
            continue
        spent = max(0.0, left[side] - p["clk"] + (inc if i >= 2 else 0))  # niente incremento sulla prima mossa
        left[side] = p["clk"]
        out.append({"ply": i + 1, "san": p["san"], "spent": round(spent, 1), "clock": round(p["clk"], 1)})
    return out


def trouble_threshold(tc: str | None) -> float:
    t = parse_tc(tc)
    return max(10.0, 0.1 * t[0]) if t else 10.0
