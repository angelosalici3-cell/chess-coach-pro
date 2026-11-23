#!/usr/bin/env bash
# Scarica Stockfish durante la build su Render, così il server analizza da solo
# (niente più dipendenza dal servizio online chess-api.com).
# Render > Settings > Build Command:
#   pip install -r requirements.txt && bash scripts/get_stockfish.sh
# Poi Environment: STOCKFISH_PATH=/opt/render/project/src/backend/bin/stockfish  (adatta al tuo percorso: vedi l'ultima riga del log di build)
set -euo pipefail
VER="${SF_VERSION:-sf_17.1}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/bin"
mkdir -p "$DEST" && cd "$DEST"
if [ -x ./stockfish ]; then echo "Stockfish già presente: $DEST/stockfish"; exit 0; fi
URL="https://github.com/official-stockfish/Stockfish/releases/download/${VER}/stockfish-ubuntu-x86-64.tar"   # versione base: gira su qualsiasi CPU
curl -fsSL "$URL" -o sf.tar
tar -xf sf.tar
BIN="$(find . -type f -name 'stockfish*' ! -name '*.tar' ! -name '*.txt' | head -n1)"
[ -n "$BIN" ] || { echo "Stockfish non trovato nell'archivio"; exit 1; }
mv "$BIN" ./stockfish && chmod +x ./stockfish
rm -rf sf.tar stockfish-ubuntu* 2>/dev/null || true
echo "STOCKFISH_PATH=$DEST/stockfish"
echo "uci" | ./stockfish | head -n2
