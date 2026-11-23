# Alternativa a Render "Python": con Docker il motore Stockfish si installa da solo.
# Render > New > Web Service > Docker, Root Directory: backend
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends stockfish && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV STOCKFISH_PATH=/usr/games/stockfish LOCAL_DEPTH=12 LOCAL_TIME=0.8 LOCAL_HASH=32
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
