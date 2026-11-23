"""Notturno su GitHub: (se DOWNLOAD_FIRST=1) scarica le partite nuove, poi analizza con il motore tutte le partite scaricate e non ancora analizzate.
Gira su GitHub Actions (non su Render): nessun limite di spegnimento del server.
Uso (da backend/): python -m scripts.analyze_worker   (variabile opzionale ANALYZE_BUDGET_MIN, default 300)"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
from app.sync import analyze_queue, run_cron  # noqa: E402

if __name__ == "__main__":
    if os.environ.get("DOWNLOAD_FIRST") == "1":   # fase 1 e fase 2 nello stesso lavoro: l'ordine è garantito anche se GitHub ritarda l'avvio
        run_cron()
    r = analyze_queue(int(os.environ.get("ANALYZE_BUDGET_MIN", "300")) * 60, int(os.environ.get("ANALYZE_WORKERS", "3")))
    print(r)
