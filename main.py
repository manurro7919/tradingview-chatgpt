from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timezone
from pathlib import Path
import json
import os

app = FastAPI(
    title="Trading Alerts API",
    version="1.0.0",
    description="API sencilla para recibir alertas de TradingView y consultarlas desde un GPT."
)

DATA_FILE = Path("alerts.json")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "cambia-esto-por-una-clave-larga")

WATCHLIST = {
    "BME:MAP": "Mapfre",
    "BME:ITX": "Inditex",
    "BME:TEF": "Telefonica",
    "BME:ACS": "ACS",
    "BME:ACX": "Acerinox",
    "BME:RED": "Redeia",
    "BME:IBE": "Iberdrola",
    "BME:NTGY": "Naturgy",
    "BME:REP": "Repsol",
    "BME:BBVA": "BBVA",
    "BME:SAN": "Banco Santander",
}

def load_alerts():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_alerts(alerts):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

def today_utc():
    return datetime.now(timezone.utc).date().isoformat()

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Trading Alerts API activa",
        "watchlist_count": len(WATCHLIST)
    }

@app.post("/tradingview/alert")
async def tradingview_alert(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")

    secret = payload.get("secret")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Secret incorrecto")

    required_fields = ["ticker", "signal", "price", "timestamp"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan campos obligatorios: {', '.join(missing)}"
        )

    payload["received_at"] = datetime.now(timezone.utc).isoformat()
    payload["in_watchlist"] = payload.get("ticker") in WATCHLIST
    payload["company_name"] = WATCHLIST.get(payload.get("ticker"), payload.get("ticker"))

    alerts = load_alerts()
    alerts.append(payload)
    save_alerts(alerts)

    return {"ok": True, "stored": payload}

@app.get("/alerts/today")
def get_alerts_today():
    alerts = load_alerts()
    today = today_utc()

    results = []
    for a in alerts:
        ts = str(a.get("timestamp") or a.get("received_at", ""))
        if ts[:10] == today:
            results.append(a)

    return {"count": len(results), "alerts": results}

@app.get("/alerts/{ticker}")
def get_alerts_by_ticker(ticker: str):
    alerts = load_alerts()
    ticker_upper = ticker.upper()

    results = [
        a for a in alerts
        if str(a.get("ticker", "")).upper() == ticker_upper
        or str(a.get("ticker", "")).upper().endswith(ticker_upper)
    ]

    return {"count": len(results), "alerts": results}

@app.get("/signals/best")
def get_best_signals():
    alerts = load_alerts()
    today = today_utc()
    today_alerts = [a for a in alerts if str(a.get("timestamp", ""))[:10] == today]

    priority = {"alta": 3, "media": 2, "baja": 1}

    ranked = sorted(
        today_alerts,
        key=lambda a: (
            priority.get(str(a.get("quality", "baja")).lower(), 1),
            1 if a.get("in_watchlist") else 0
        ),
        reverse=True
    )

    return {"count": len(ranked[:20]), "signals": ranked[:20]}

@app.get("/portfolio/signals")
def get_portfolio_signals():
    alerts = load_alerts()
    today = today_utc()

    results = [
        a for a in alerts
        if a.get("in_watchlist") and str(a.get("timestamp", ""))[:10] == today
    ]

    return {"count": len(results), "signals": results}
