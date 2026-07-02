FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV STATE_FILE=/shared/state.json \
    TRADES_DB=/shared/trades.db

CMD ["python", "-u", "main.py"]
