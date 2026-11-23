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
if [ -f ./stockfish ] && [ -x ./stockfish ]; then echo "Stockfish già presente: $DEST/stockfish"; exit 0; fi
rm -rf ./stockfish sf.tar sf_tmp
URL="https://github.com/official-stockfish/Stockfish/releases/download/${VER}/stockfish-ubuntu-x86-64.tar"   # versione base: gira su qualsiasi CPU
curl -fsSL "$URL" -o sf.tar
mkdir sf_tmp && tar -xf sf.tar -C sf_tmp
BIN="$(find sf_tmp -type f -name 'stockfish*' ! -name '*.txt' ! -name '*.md' | head -n1)"
[ -n "$BIN" ] || { echo "Stockfish non trovato nell'archivio"; exit 1; }
mv "$BIN" ./stockfish.bin && rm -rf sf.tar sf_tmp
mv ./stockfish.bin ./stockfish && chmod +x ./stockfish
echo "STOCKFISH_PATH=$DEST/stockfish"
echo "uci" | ./stockfish | head -n2
