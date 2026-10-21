import yfinance as yf
import pandas as pd
import json
import os
import time
import requests

# Eulerpool API Key aus GitHub Secret
EULERPOOL_KEY = os.environ.get("EULERPOOL_API_KEY")

# S&P 500 Daten laden
csv_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
sp500_df = pd.read_csv(csv_url)
sp500_df['Symbol'] = sp500_df['Symbol'].str.replace('.', '-', regex=False)
ticker_info = sp500_df.set_index('Symbol')[['Security', 'GICS Sector']].to_dict('index')
sp500 = list(ticker_info.keys())
print(f"Geladene Ticker: {len(sp500)}")

def get_fundamental(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue")
        }
    except:
        return {"market_cap": None, "revenue": None}

def get_iv_metrics(ticker):
    print(f"IV-Abfrage für {ticker}...")
    if not EULERPOOL_KEY:
        print("  -> Kein API-Key vorhanden")
        return {"ivr": None, "ivp": None}
    try:
        url = f"https://api.eulerpool.com/v1/volatility/{ticker}/iv-rank"
        headers = {"Authorization": f"Bearer {EULERPOOL_KEY}"}
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  -> Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  -> Antwort: {r.text[:200]}")
            return {"ivr": None, "ivp": None}
        data = r.json()
        print(f"  -> Daten: {str(data)[:300]}")
        return {
            "ivr": data.get("iv_rank") or data.get("ivr"),
            "ivp": data.get("iv_percentile") or data.get("ivp")
        }
    except Exception as e:
        print(f"  -> Exception: {e}")
        return {"ivr": None, "ivp": None}

def calculate_metrics(ticker, period_days):
    try:
        data = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if data.empty or len(data) < period_days:
            return None
        close_series = data['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
        close = float(close_series.iloc[-1])
        sma = float(close_series.iloc[-period_days:].mean())
        rsl = round(close / sma, 4) if sma > 0 else None

        def pct_change(days):
            if len(close_series) > days:
                past = float(close_series.iloc[-days-1])
                return round((close / past - 1) * 100, 2) if past > 0 else None
            return None

        return {
            "rsl": rsl,
            "pct_1d": pct_change(1),
            "pct_1w": pct_change(5),
            "pct_1m": pct_change(21)
        }
    except Exception as e:
        print(f"Fehler bei {ticker}: {e}")
        return None

def load_previous(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            return {item["ticker"]: item["rank"] for item in data}
    return {}

def build_list(period_days, label, prev_ranks, top50_tickers):
    results = []
    print(f"\nBerechne {label}...")
    for i, ticker in enumerate(sp500):
        metrics = calculate_metrics(ticker, period_days)
        if metrics and metrics["rsl"]:
            info = ticker_info.get(ticker, {})
            fund = get_fundamental(ticker)
            iv = get_iv_metrics(ticker) if ticker in top50_tickers else {"ivr": None, "ivp": None}
            results.append({
                "ticker": ticker,
                "name": info.get("Security", ticker),
                "sector": info.get("GICS Sector", "-"),
                "rsl": metrics["rsl"],
                "pct_1d": metrics["pct_1d"],
                "pct_1w": metrics["pct_1w"],
                "pct_1m": metrics["pct_1m"],
                "market_cap": fund["market_cap"],
                "revenue": fund["revenue"],
                "ivr": iv["ivr"],
                "ivp": iv["ivp"]
            })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sp500)} verarbeitet")
        time.sleep(0.05)

    results.sort(key=lambda x: x["rsl"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1
        prev = prev_ranks.get(item["ticker"])
        item["delta"] = (prev - item["rank"]) if prev else None
    print(f"{label}: {len(results)} gültige Aktien")
    return results

# Zuerst Fundamentals holen, um Top 50 zu bestimmen
print("Hole Marktkapitalisierung für Top-50-Auswahl...")
fundamentals = []
for ticker in sp500:
    fund = get_fundamental(ticker)
    if fund["market_cap"]:
        fundamentals.append({"ticker": ticker, "market_cap": fund["market_cap"]})
    time.sleep(0.02)

fundamentals.sort(key=lambda x: x["market_cap"], reverse=True)
top50_tickers = {item["ticker"] for item in fundamentals[:50]}
print(f"Top 50 nach Marktkapitalisierung: {len(top50_tickers)} Titel")

prev_26d = load_previous("rsl_26d.json")
prev_26w = load_previous("rsl_26w.json")

list_26d = build_list(26, "26 Tage", prev_26d, top50_tickers)
list_26w = build_list(130, "26 Wochen", prev_26w, top50_tickers)

rank_26d = {item["ticker"]: item["rank"] for item in list_26d}
rank_26w = {item["ticker"]: item["rank"] for item in list_26w}

for item in list_26d:
    item["rank_other"] = rank_26w.get(item["ticker"], "-")
for item in list_26w:
    item["rank_other"] = rank_26d.get(item["ticker"], "-")

with open("rsl_26d.json", "w") as f:
    json.dump(list_26d, f, indent=2)
with open("rsl_26w.json", "w") as f:
    json.dump(list_26w, f, indent=2)

print("JSON-Dateien geschrieben.")
