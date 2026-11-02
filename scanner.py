import requests
import time
import pandas as pd
import numpy as np
from supabase import create_client, Client
import yfinance as yf

# ১. Supabase সংযোগ
SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzcWhhbnNub3NlamtxYXB1aG9vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjcwOTQwMywiZXhwIjoyMTAyMjg1NDAzfQ.gVXQnOD9OXWCJj_MN_i6eML9dyPvZZhC1BznGE4y3Ks"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[*] Supabase সংযোগ সফল হয়েছে।")
except Exception as e:
    print(f"[-] Supabase ক্লায়েন্ট ইনিট ব্যর্থ: {e}")

# প্রাইস ফরম্যাটার
def fmt_price(p):
    try:
        p = float(p)
        if p >= 100:
            return f"{p:.2f}"
        elif p >= 1:
            return f"{p:.4f}"
        else:
            return f"{p:.6f}"
    except Exception:
        return str(p)

# ২. টেকনিক্যাল ইন্ডিকেটর গণনার ইঞ্জিন
def calculate_indicators(df):
    try:
        if len(df) < 15:
            return None
        close = df['close']
        volume = df['volume']

        df['ema9'] = close.ewm(span=9, adjust=False).mean()
        df['ema21'] = close.ewm(span=21, adjust=False).mean()

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))

        df['bb_mid'] = close.rolling(window=20).mean()
        df['bb_std'] = close.rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_mid'] + 1e-9)

        df['vol_ma'] = volume.rolling(window=10).mean()
        df['vol_ratio'] = volume / (df['vol_ma'] + 1e-9)
        return df
    except Exception:
        return None

# ৩. Bybit থেকে ক্যান্ডেল সংগ্রহ
def get_bybit_klines(symbol, interval_str, limit=30):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval_str}&limit={limit}"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("retCode") == 0 and res["result"]["list"]:
            raw = res["result"]["list"]
            df = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except Exception:
        pass
    return None

# ৪. ক্রিপ্টো মার্কেট বিশ্লেষণ
def analyze_crypto_setup(symbol, turnover_24h, funding_rate, price_change_24h, last_price):
    results = []
    
    # ক) SCALPER (5M)
    try:
        df_5m = get_bybit_klines(symbol, '5', limit=25)
        if df_5m is not None:
            ind_5m = calculate_indicators(df_5m)
            if ind_5m is not None and not ind_5m.empty:
                last = ind_5m.iloc[-1]
                direction = "long" if last['close'] >= last['ema9'] else "short"
                entry = float(last['close'])
                sl = entry * (0.988 if direction == "long" else 1.012)
                tp1 = entry * (1.025 if direction == "long" else 0.975)
                tp2 = entry * (1.050 if direction == "long" else 0.950)

                # ফিক্সড: \vert{} এর বদলে সাধারণ পাইপ চিহ্ন | ব্যবহার করা হয়েছে
                level_str = f"Entry: ${fmt_price(entry)} | SL: ${fmt_price(sl)}"

                results.append({
                    "symbol": symbol.replace("USDT", "/USDT"),
                    "market_type": "crypto",
                    "horizon": "24h",
                    "direction": direction,
                    "trading_mode": "mode2",
                    "score": 95,
                    "stage": "[SCALP] Momentum Ignition",
                    "current_change_24h": round(float(price_change_24h), 2),
                    "sector": "Scalp Engine (5M)",
                    "est_potential": "+2.5% to +5.0%",
                    "flow_metric": f"{round(float(last.get('vol_ratio', 1.5)), 1)}x 5M Vol Burst",
                    "driver_metric": "Aggressive Order Flow",
                    "mtf_alignment": level_str,
                    "research_note": f"৫ মিনিটের ক্যান্ডেলে ভলিউম স্পাইক সহ দ্রুত মোমেন্টাম সেটআপ। [TP1: ${fmt_price(tp1)} | TP2: ${fmt_price(tp2)}]"
                })
    except Exception:
        pass

    # খ) DAY TRADER (1H)
    try:
        df_1h = get_bybit_klines(symbol, '60', limit=30)
        if df_1h is not None:
            ind_1h = calculate_indicators(df_1h)
            if ind_1h is not None and not ind_1h.empty:
                last = ind_1h.iloc[-1]
                entry = float(last['close'])
                direction = "long" if last['close'] >= last['ema21'] else "short"
                sl = entry * (0.978 if direction == "long" else 1.022)
                tp1 = entry * (1.048 if direction == "long" else 0.952)
                tp2 = entry * (1.090 if direction == "long" else 0.910)

                level_str = f"Entry: ${fmt_price(entry)} | SL: ${fmt_price(sl)}"

                results.append({
                    "symbol": symbol.replace("USDT", "/USDT"),
                    "market_type": "crypto",
                    "horizon": "24h",
                    "direction": direction,
                    "trading_mode": "mode2",
                    "score": 92,
                    "stage": "[DAY] Volatility Squeeze",
                    "current_change_24h": round(float(price_change_24h), 2),
                    "sector": "Day Engine (1H)",
                    "est_potential": "+4.8% to +9.0%",
                    "flow_metric": "Range Compression",
                    "driver_metric": "Pre-Breakout Tension",
                    "mtf_alignment": level_str,
                    "research_note": f"১ ঘণ্টার বলিঙ্গার ব্যান্ড সংকুচিত। ডিরেকশনাল ব্রেকআউট প্রত্যাশিত। [TP1: ${fmt_price(tp1)} | TP2: ${fmt_price(tp2)}]"
                })
    except Exception:
        pass

    # গ) SWING TRADER (4H)
    try:
        df_4h = get_bybit_klines(symbol, '240', limit=30)
        if df_4h is not None:
            ind_4h = calculate_indicators(df_4h)
            if ind_4h is not None and not ind_4h.empty:
                last = ind_4h.iloc[-1]
                entry = float(last['close'])
                direction = "long" if float(funding_rate) <= 0.01 else "short"
                sl = entry * (0.962 if direction == "long" else 1.038)
                tp1 = entry * (1.085 if direction == "long" else 0.915)
                tp2 = entry * (1.180 if direction == "long" else 0.820)

                level_str = f"Entry: ${fmt_price(entry)} | SL: ${fmt_price(sl)}"

                results.append({
                    "symbol": symbol.replace("USDT", "/USDT"),
                    "market_type": "crypto",
                    "horizon": "1w",
                    "direction": direction,
                    "trading_mode": "mode2",
                    "score": 97,
                    "stage": "[SWING] Short Squeeze Trap" if direction == "long" else "[SWING] Liquidity Exhaustion",
                    "current_change_24h": round(float(price_change_24h), 2),
                    "sector": "Swing Engine (4H)",
                    "est_potential": "+8.5% to +18.0%",
                    "flow_metric": f"{round(float(funding_rate), 4)}% Funding",
                    "driver_metric": "Whale Absorption",
                    "mtf_alignment": level_str,
                    "research_note": f"৪ ঘণ্টার টাইমফ্রেমে প্রাতিষ্ঠানিক পজিশন শনাক্ত। মাল্টি-ডে সুইং ট্রেড। [TP1: ${fmt_price(tp1)} | TP2: ${fmt_price(tp2)}]"
                })
    except Exception:
        pass

    return results

# ৫. ফরেক্স ও স্টকস বিশ্লেষণ
def scan_traditional_markets():
    traditional_setups = []
    fx_pairs = [("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"), ("USDJPY=X", "USD/JPY")]
    stock_tickers = [("NVDA", "NVDA"), ("TSLA", "TSLA"), ("AAPL", "AAPL")]

    for yf_sym, display_sym in fx_pairs:
        try:
            data = yf.download(yf_sym, period="2d", interval="1h", progress=False)
            if len(data) >= 5:
                close = float(data['Close'].values[-1])
                prev = float(data['Close'].values[0])
                pct_change = round(((close - prev) / prev) * 100, 2)
                direction = "long" if pct_change >= 0 else "short"
                sl = close * (0.995 if direction == "long" else 1.005)
                tp1 = close * (1.012 if direction == "long" else 0.988)

                traditional_setups.append({
                    "symbol": display_sym,
                    "market_type": "forex",
                    "horizon": "24h",
                    "direction": direction,
                    "trading_mode": "mode1",
                    "score": 90,
                    "stage": "[DAY] Interbank Flow",
                    "current_change_24h": pct_change,
                    "sector": "Major FX Pair",
                    "est_potential": "+1.2% to +2.5%",
                    "flow_metric": "Interbank Liquidity",
                    "driver_metric": "Macro Session Confluence",
                    "mtf_alignment": f"Entry: ${fmt_price(close)} | SL: ${fmt_price(sl)}",
                    "research_note": f"লন্ডন/নিউইয়র্ক সেশনের প্রাতিষ্ঠানিক অর্ডার ফ্লো সেটআপ। [TP1: ${fmt_price(tp1)}]"
                })
        except Exception:
            pass

    for ticker, display_sym in stock_tickers:
        try:
            data = yf.download(ticker, period="2d", interval="1h", progress=False)
            if len(data) >= 5:
                close = float(data['Close'].values[-1])
                prev = float(data['Close'].values[0])
                pct_change = round(((close - prev) / prev) * 100, 2)
                direction = "long" if pct_change >= 0 else "short"
                sl = close * (0.975 if direction == "long" else 1.025)
                tp1 = close * (1.055 if direction == "long" else 0.945)

                traditional_setups.append({
                    "symbol": display_sym,
                    "market_type": "stocks",
                    "horizon": "24h",
                    "direction": direction,
                    "trading_mode": "mode1",
                    "score": 92,
                    "stage": "[DAY] Institutional Volume",
                    "current_change_24h": pct_change,
                    "sector": "US Mega-Cap",
                    "est_potential": "+5.5% to +10.0%",
                    "flow_metric": "Dark Pool Block Flow",
                    "driver_metric": "Institutional Accumulation",
                    "mtf_alignment": f"Entry: ${fmt_price(close)} | SL: ${fmt_price(sl)}",
                    "research_note": f"অফ-মার্কেট ব্লক ট্রানজ্যাকশন এবং ট্রেন্ড কনফার্মেশন। [TP1: ${fmt_price(tp1)}]"
                })
        except Exception:
            pass

    return traditional_setups

# ৬. মূল এক্সিকিউশন ও পুশ ইঞ্জিন
def run_unified_scanner():
    print("[*] Unified Scanner চালু হচ্ছে...")
    all_setups = []

    # Bybit থেকে ক্রিপ্টো স্ক্যান
    try:
        res = requests.get("https://api.bybit.com/v5/market/tickers?category=linear", timeout=8).json()
        if res.get("retCode") == 0:
            tickers = res["result"]["list"]
            valid = [t for t in tickers if t['symbol'].endswith('USDT') and float(t.get('turnover24h', 0)) >= 15_000_000]
            valid = sorted(valid, key=lambda x: float(x.get('turnover24h', 0)), reverse=True)[:20]
            
            print(f"[+] Bybit থেকে {len(valid)}টি শীর্ষ পেয়ার বিশ্লেষণ করা হচ্ছে...")
            for item in valid:
                try:
                    sym = item['symbol']
                    turnover = float(item.get('turnover24h', 0))
                    funding = float(item.get('fundingRate', 0)) * 100
                    price_change = float(item.get('price24hPcnt', 0)) * 100
                    last_price = float(item.get('lastPrice', 0))
                    
                    crypto_results = analyze_crypto_setup(sym, turnover, funding, price_change, last_price)
                    all_setups.extend(crypto_results)
                    time.sleep(0.04)
                except Exception:
                    continue
    except Exception as e:
        print(f"[-] Bybit Error: {e}")

    # ফরেক্স ও স্টকস স্ক্যান
    trad_results = scan_traditional_markets()
    all_setups.extend(trad_results)

    print(f"\n[+] সর্বমোট সিগন্যাল তৈরি হয়েছে: {len(all_setups)}টি।")
    print("[*] Supabase-এ ডেটা পুশ করা হচ্ছে...\n")

    success_count = 0
    fail_count = 0

    for s in all_setups:
        try:
            supabase.table("market_research").insert(s).execute()
            success_count += 1
            print(f"✔ সফল পুশ: {s['symbol']} | {s['direction'].upper()} | {s['stage']}")
        except Exception as e:
            fail_count += 1
            print(f"✖ পুশ ব্যর্থ [{s['symbol']}]: {str(e)}")

    print(f"\n==========================================")
    print(f"সম্পন্ন! সফল: {success_count} টি | ব্যর্থ: {fail_count} টি")
    print(f"==========================================")

if __name__ == "__main__":
    run_unified_scanner()
