import yfinance as yf
import pandas as pd
import json
import os
import time

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

def calculate_metrics(ticker, period_days):
    try:
        data = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if data.empty or len(data) < period_days:
            return None
        
        close_series = data['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
        
        # NaN-Werte entfernen
        close_series = close_series.dropna()
        if len(close_series) < period_days:
            return None
        
        close = float(close_series.iloc[-1])
        sma = float(close_series.iloc[-period_days:].mean())
        
        if pd.isna(close) or pd.isna(sma) or sma <= 0:
            return None
        
        rsl = round(close / sma, 4)

        def pct_change(days):
            if len(close_series) > days:
                past = float(close_series.iloc[-days-1])
                if past > 0 and not pd.isna(past):
                    return round((close / past - 1) * 100, 2)
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

def build_list(period_days, label, prev_ranks):
    results = []
    print(f"\nBerechne {label}...")
    for i, ticker in enumerate(sp500):
        metrics = calculate_metrics(ticker, period_days)
        if metrics and metrics["rsl"]:
            info = ticker_info.get(ticker, {})
            fund = get_fundamental(ticker)
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
                "ivr": None,
                "ivp": None
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

prev_26d = load_previous("rsl_26d.json")
prev_26w = load_previous("rsl_26w.json")

list_26d = build_list(26, "26 Tage", prev_26d)
list_26w = build_list(130, "26 Wochen", prev_26w)

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
