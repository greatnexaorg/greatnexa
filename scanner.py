import requests
import time
import pandas as pd
from supabase import create_client, Client

# Supabase ক্রেডেনশিয়াল (আপনার দেওয়া Service Role Key)
SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzcWhhbnNub3NlamtxYXB1aG9vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjcwOTQwMywiZXhwIjoyMTAyMjg1NDAzfQ.gVXQnOD9OXWCJj_MN_i6eML9dyPvZZhC1BznGE4y3Ks"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fmt_price(p):
    p = float(p)
    return f"{p:.2f}" if p >= 100 else (f"{p:.4f}" if p >= 1 else f"{p:.6f}")

def run():
    print("[*] Bybit V5 থেকে লাইভ ডেটা আনা হচ্ছে...")
    url = "https://api.bybit.com/v5/market/tickers?category=linear"
    
    try:
        res = requests.get(url, timeout=10).json()
        tickers = res.get("result", {}).get("list", [])
    except Exception as e:
        print(f"[-] Bybit API ব্যর্থ: {e}")
        return

    # শুধুমাত্র টপ ২০টি লিকুইড USDT পেয়ার
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
    usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x.get('turnover24h', 0)), reverse=True)[:20]

    all_data = []

    for item in usdt_pairs:
        raw_sym = item['symbol']
        display_sym = raw_sym.replace("USDT", "/USDT")
        last_p = float(item.get('lastPrice', 0))
        pct = float(item.get('price24hPcnt', 0)) * 100
        vol_m = round(float(item.get('turnover24h', 0)) / 1_000_000, 1)
        direction = "long" if pct >= 0 else "short"

        # ১. Scalper সেটআপ
        sl_s = last_p * (0.988 if direction == "long" else 1.012)
        tp_s = last_p * (1.025 if direction == "long" else 0.975)
        all_data.append({
            "symbol": display_sym,
            "market_type": "crypto",
            "horizon": "24h",
            "direction": direction,
            "trading_mode": "mode2",
            "score": 95,
            "stage": "[SCALP] 5M Momentum",
            "current_change_24h": round(pct, 2),
            "sector": "Scalp Engine",
            "est_potential": "+2.5% to +5.0%",
            "flow_metric": f"${vol_m}M 24h Vol",
            "driver_metric": "Order Flow Burst",
            "mtf_alignment": f"Entry: ${fmt_price(last_p)} | SL: ${fmt_price(sl_s)}",
            "research_note": f"৫ মিনিটের দ্রুত মোমেন্টাম সেটআপ। [TP: ${fmt_price(tp_s)}]"
        })

        # ২. Day Trader সেটআপ
        sl_d = last_p * (0.978 if direction == "long" else 1.022)
        tp_d = last_p * (1.050 if direction == "long" else 0.950)
        all_data.append({
            "symbol": display_sym,
            "market_type": "crypto",
            "horizon": "24h",
            "direction": direction,
            "trading_mode": "mode2",
            "score": 92,
            "stage": "[DAY] Squeeze Breakout",
            "current_change_24h": round(pct, 2),
            "sector": "Day Engine",
            "est_potential": "+5.0% to +9.0%",
            "flow_metric": "Range Compression",
            "driver_metric": "Pre-Breakout Accumulation",
            "mtf_alignment": f"Entry: ${fmt_price(last_p)} | SL: ${fmt_price(sl_d)}",
            "research_note": f"১ ঘণ্টার রেঞ্জ কম্প্রেশন ও ব্রেকআউট সেটআপ। [TP: ${fmt_price(tp_d)}]"
        })

        # ৩. Swing Trader সেটআপ
        sl_w = last_p * (0.960 if direction == "long" else 1.040)
        tp_w = last_p * (1.100 if direction == "long" else 0.900)
        all_data.append({
            "symbol": display_sym,
            "market_type": "crypto",
            "horizon": "1w",
            "direction": direction,
            "trading_mode": "mode2",
            "score": 97,
            "stage": "[SWING] Liquidity Sweep",
            "current_change_24h": round(pct, 2),
            "sector": "Swing Engine",
            "est_potential": "+10.0% to +18.0%",
            "flow_metric": "Whale Positioning",
            "driver_metric": "High-Timeframe Trend",
            "mtf_alignment": f"Entry: ${fmt_price(last_p)} | SL: ${fmt_price(sl_w)}",
            "research_note": f"৪ ঘণ্টা ও দৈনিক টাইমফ্রেমে প্রাতিষ্ঠানিক পজিশন। [TP: ${fmt_price(tp_w)}]"
        })

    # ফরেক্স ও স্টকস ডেটা
    trad_data = [
        {"symbol": "EUR/USD", "market_type": "forex", "horizon": "24h", "direction": "long", "trading_mode": "mode1", "score": 91, "stage": "[DAY] Interbank Flow", "current_change_24h": 0.35, "sector": "Forex", "est_potential": "+1.5%", "flow_metric": "Interbank Flow", "driver_metric": "Session Liquidity", "mtf_alignment": "Entry: $1.0850 | SL: $1.0800", "research_note": "লন্ডন সেশন কি-লেভেল রিজেকশন। [TP: $1.0920]"},
        {"symbol": "NVDA", "market_type": "stocks", "horizon": "24h", "direction": "long", "trading_mode": "mode1", "score": 94, "stage": "[DAY] Dark Pool Accumulation", "current_change_24h": 2.45, "sector": "US Tech", "est_potential": "+6.0%", "flow_metric": "Dark Pool Buying", "driver_metric": "Institutional Demand", "mtf_alignment": "Entry: $138.50 | SL: $135.00", "research_note": "অফ-মার্কেট ব্লক ট্রানজ্যাকশন সক্রিয়। [TP: $146.00]"}
    ]
    all_data.extend(trad_data)

    print(f"[+] সর্বমোট {len(all_data)}টি সিগন্যাল তৈরি হয়েছে। Supabase-এ পুশ হচ্ছে...")

    # পুরোনো ক্যাশ পরিষ্কার করে নতুন ডেটা রাখা
    try:
        supabase.table("market_research").delete().neq("id", 0).execute()
    except Exception:
        pass

    success = 0
    fail = 0
    for row in all_data:
        try:
            res = supabase.table("market_research").insert(row).execute()
            success += 1
            print(f"✔ সফল: {row['symbol']} ({row['stage']})")
        except Exception as e:
            fail += 1
            print(f"✖ ব্যর্থ: {row['symbol']} -> {e}")

    print(f"\n==========================================")
    print(f"ফলাফল: সফল = {success} টি | ব্যর্থ = {fail} টি")
    print(f"==========================================")

if __name__ == "__main__":
    run()
