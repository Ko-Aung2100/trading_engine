# Algorithmic Trading Engine

A scalable, OOP-based automated trading backend using FastAPI and Flet. It listens for webhooks from TradingView and dynamically routes them to custom strategy execution classes.

## How to Run Locally

1. Install dependencies:
   `pip install -r requirements.txt`
2. Start the Uvicorn server:
   `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
3. Open the dashboard in your browser: `http://localhost:8000`

## How to Test Webhooks Locally

Use Postman or cURL to send a test payload to your running server:

```bash
curl -X POST http://localhost:8000/webhook \
-H "Content-Type: application/json" \
-d '{"strategy_id": "smc", "action": "buy", "symbol": "BTCUSDT", "price": 65000, "zone": "15m Bullish OB"}'