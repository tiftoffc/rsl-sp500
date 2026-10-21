import yfinance as yf
import pandas as pd
import json
from datetime import datetime

# S&P 500 Ticker holen (Wikipedia)
url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
tables = pd.read_html(url)
sp500 = tables[0]['Symbol'].tolist()
sp500 = [t.replace('.', '-') for t in sp500]  # yfinance Format

def calculate_rsl(ticker, period_days):
    try:
        data = yf.download(ticker, period=f"{period_days + 30}d", progress=False)
        if len(data) < period_days:
            return None
        close = data['Close'].iloc[-1]
        sma = data['Close'].iloc[-period_days:].mean()
        return round(close / sma, 4) if sma > 0 else None
    except:
        return None

def build_list(period_days, label):
    results = []
    for ticker in sp500:
        rsl = calculate_rsl(ticker, period_days)
        if rsl:
            results.append({
                "ticker": ticker,
                "rsl": rsl
            })
    # Sortieren und Rank vergeben
    results.sort(key=lambda x: x["rsl"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1
    return results

# 26 Tage und 26 Wochen (26*5 ≈ 130 Handelstage)
list_26d = build_list(26, "26d")
list_26w = build_list(130, "26w")

# Ranks der anderen Liste zuordnen
rank_26d = {item["ticker"]: item["rank"] for item in list_26d}
rank_26w = {item["ticker"]: item["rank"] for item in list_26w}

for item in list_26d:
    item["rank_other"] = rank_26w.get(item["ticker"], "-")
for item in list_26w:
    item["rank_other"] = rank_26d.get(item["ticker"], "-")

# JSON speichern
with open("rsl_26d.json", "w") as f:
    json.dump(list_26d, f, indent=2)
with open("rsl_26w.json", "w") as f:
    json.dump(list_26w, f, indent=2)

print(f"Fertig: {len(list_26d)} Aktien (26d), {len(list_26w)} Aktien (26w)")
