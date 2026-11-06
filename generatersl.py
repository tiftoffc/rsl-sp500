import yfinance as yf
import pandas as pd
import json
import os
import time
import datetime
from collections import defaultdict

# S&P 500 Daten laden
csv_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
sp500_df = pd.read_csv(csv_url)
sp500_df['Symbol'] = sp500_df['Symbol'].str.replace('.', '-', regex=False)
ticker_info = sp500_df.set_index('Symbol')[['Security', 'GICS Sector', 'GICS Sub-Industry']].to_dict('index')
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

def get_expiration_count(ticker):
    try:
        opts = yf.Ticker(ticker).options
        return len(opts) if opts else 0
    except:
        return 0

def get_trend_strength(ticker, lookback=15):
    try:
        data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if data.empty or len(data) < lookback + 5:
            return None

        high = data['High'].dropna().iloc[-lookback-5:]
        low = data['Low'].dropna().iloc[-lookback-5:]

        if len(high) < lookback:
            return None

        hh = 0
        hl = 0
        consecutive_hhhl = 0
        max_consecutive = 0

        for i in range(1, len(high)):
            is_hh = high.iloc[-i] > high.iloc[-i-1]
            is_hl = low.iloc[-i] > low.iloc[-i-1]

            if is_hh:
                hh += 1
            if is_hl:
                hl += 1

            if is_hh and is_hl:
                consecutive_hhhl += 1
                max_consecutive = max(max_consecutive, consecutive_hhhl)
            else:
                consecutive_hhhl = 0

        if max_consecutive >= 3:
            return f"HHHL{max_consecutive}"
        elif hh >= 6 and hl >= 5:
            return f"HH{hh}/HL{hl}"
        elif max_consecutive >= 2:
            return f"HHHL{max_consecutive}"
        return None

    except Exception as e:
        print(f"Trend-Fehler bei {ticker}: {e}")
        return None

def calculate_metrics(ticker, period_days):
    try:
        data = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if data.empty or len(data) < period_days:
            return None
        
        close_series = data['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
        
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

def load_history():
    if os.path.exists("rank_history.json"):
        with open("rank_history.json", "r") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open("rank_history.json", "w") as f:
        json.dump(history, f, indent=2)

def update_history(results, is_weekly=False):
    history = load_history()
    today = datetime.date.today()
    is_saturday = today.weekday() == 5

    for item in results:
        ticker = item["ticker"]
        if ticker not in history:
            history[ticker] = {"daily": [], "weekly": []}
        
        key = "weekly" if is_weekly else "daily"
        ranks = history[ticker][key]
        ranks.append(item["rank"])
        history[ticker][key] = ranks[-30:]

        last_5 = ranks[-5:][::-1]
        item[f"last_5_{'weekly_' if is_weekly else ''}ranks"] = last_5

        if not is_weekly:
            item["days_in_top50"] = sum(1 for r in ranks[-30:] if r <= 50)

    if is_weekly and not is_saturday:
        for item in results:
            ticker = item["ticker"]
            if ticker in history and history[ticker]["weekly"]:
                last_5 = history[ticker]["weekly"][-5:][::-1]
                item["last_5_weekly_ranks"] = last_5
            else:
                item["last_5_weekly_ranks"] = []

    save_history(history)
    return results

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
                "industry": info.get("GICS Sub-Industry", "-"),
                "rsl": metrics["rsl"],
                "pct_1d": metrics["pct_1d"],
                "pct_1w": metrics["pct_1w"],
                "pct_1m": metrics["pct_1m"],
                "market_cap": fund["market_cap"],
                "revenue": fund["revenue"],
                "exp_count": get_expiration_count(ticker),
                "trend": get_trend_strength(ticker),
                "ivr": None,
                "ivp": None
            })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sp500)} verarbeitet")
        time.sleep(0.08)

    results.sort(key=lambda x: x["rsl"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1
        prev = prev_ranks.get(item["ticker"])
        item["delta"] = (prev - item["rank"]) if prev else None

    # Relative Stärke zum Sektor
    sector_rsls = defaultdict(list)
    for item in results:
        if item.get("sector") and item["sector"] != "-":
            sector_rsls[item["sector"]].append(item["rsl"])

    sector_avg = {sec: sum(vals)/len(vals) for sec, vals in sector_rsls.items() if vals}

    for item in results:
        avg = sector_avg.get(item.get("sector"))
        if avg and avg > 0:
            item["rsl_vs_sector"] = round(item["rsl"] / avg, 4)
        else:
            item["rsl_vs_sector"] = None

    # History & Score
    is_weekly = (period_days == 130)
    results = update_history(results, is_weekly=is_weekly)

    for item in results:
        score = 0
        if item.get("rsl", 0) > 1.0:
            score += 1
        if item.get("rsl_vs_sector") and item["rsl_vs_sector"] > 1.0:
            score += 1
        if item.get("delta") and item["delta"] > 0:
            score += 1
        if item.get("rank", 999) <= 50:
            score += 1
        if item.get("days_in_top50", 0) >= 10:
            score += 1
        item["score"] = score

    print(f"{label}: {len(results)} gültige Aktien")
    return results

# Hauptablauf
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

update_info = {
    "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}
with open("last_update.json", "w") as f:
    json.dump(update_info, f)

print("Fertig.")
