import yfinance as yf
import pandas as pd
import json
import time

# S&P 500 Ticker laden
csv_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
sp500_df = pd.read_csv(csv_url)
sp500 = sp500_df['Symbol'].tolist()
sp500 = [t.replace('.', '-') for t in sp500]
print(f"Geladene Ticker: {len(sp500)}")

def calculate_rsl(ticker, period_days):
    try:
        data = yf.download(ticker, period=f"{period_days + 40}d", progress=False, auto_adjust=True)
        if data.empty or len(data) < period_days:
            return None
        close = data['Close'].iloc[-1]
        sma = data['Close'].iloc[-period_days:].mean()
        if sma > 0:
            return round(float(close / sma), 4)
        return None
    except Exception as e:
        print(f"Fehler bei {ticker}: {e}")
        return None

def build_list(period_days, label):
    results = []
    print(f"\nBerechne {label}...")
    for i, ticker in enumerate(sp500):
        rsl = calculate_rsl(ticker, period_days)
        if rsl:
            results.append({"ticker": ticker, "rsl": rsl})
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sp500)} verarbeitet, bisher {len(results)} gültig")
        time.sleep(0.1)  # kurze Pause gegen Rate-Limits
    results.sort(key=lambda x: x["rsl"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1
    print(f"{label}: {len(results)} gültige Aktien")
    return results

list_26d = build_list(26, "26 Tage")
list_26w = build_list(130, "26 Wochen")

# Andere Ranks zuordnen
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
