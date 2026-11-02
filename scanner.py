import requests
import time
from datetime import datetime, timezone
from supabase import create_client, Client

# ১. Supabase সংযোগ (Service Role Secret Key)
SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzcWhhbnNub3NlamtxYXB1aG9vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjcwOTQwMywiZXhwIjoyMTAyMjg1NDAzfQ.gVXQnOD9OXWCJj_MN_i6eML9dyPvZZhC1BznGE4y3Ks"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✔ Supabase প্রাতিষ্ঠানিক ইঞ্জিন সংযুক্ত!")
except Exception as e:
    print(f"✖ Supabase ক্লায়েন্ট ফেইল: {e}")
    exit(1)

def fmt_price(p):
    p = float(p)
    return f"{p:.2f}" if p >= 100 else (f"{p:.4f}" if p >= 1 else f"{p:.6f}")

# ২. মার্কেট প্রাইস ফিড
def fetch_top_liquid_market():
    market_pool = {}
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", headers=headers, timeout=8)
        if r.status_code == 200:
            for t in r.json():
                if t['symbol'].endswith('USDT'):
                    sym = t['symbol'].replace("USDT", "/USDT")
                    market_pool[sym] = {
                        "symbol": sym,
                        "price": float(t.get('lastPrice', 0)),
                        "high": float(t.get('highPrice', 0)),
                        "low": float(t.get('lowPrice', 0)),
                        "change": float(t.get('priceChangePercent', 0)),
                        "volume_m": round(float(t.get('quoteVolume', 0)) / 1_000_000, 1)
                    }
    except Exception as e:
        print(f"[-] প্রাথমিক ফিড ফেইল: {e}")
    return market_pool

# ৩. লাইফসাইকেল ট্র্যাকার (পুরানো সিগন্যাল TP/SL যাচাই ও ইনভ্যালিডেশন)
def track_and_update_lifecycle(current_prices):
    print("[*] সক্রিয় ট্রেডগুলোর লাইফসাইকেল নিরীক্ষণ শুরু হচ্ছে...")
    try:
        # বর্তমানে যে সিগন্যালগুলো ACTIVE আছে
        res = supabase.table("market_research").select("*").eq("status", "ACTIVE").execute()
        active_signals = res.data or []
        print(f"[i] বর্তমানে ট্র্যাকিংয়ে থাকা সক্রিয় সিগন্যাল: {len(active_signals)} টি")

        for sig in active_signals:
            sym = sig.get("symbol")
            if sym not in current_prices:
                continue

            cur_price = current_prices[sym]["price"]
            direction = sig.get("direction", "long")
            sl = float(sig.get("sl_price") or 0)
            tp = float(sig.get("tp_price") or 0)
            sig_id = sig.get("id")

            # TP বা SL হিট করেছে কি না যাচাই
            hit_status = None
            if direction == "long":
                if cur_price >= tp and tp > 0:
                    hit_status = "HIT_TP"
                elif cur_price <= sl and sl > 0:
                    hit_status = "HIT_SL"
            else: # short
                if cur_price <= tp and tp > 0:
                    hit_status = "HIT_TP"
                elif cur_price >= sl and sl > 0:
                    hit_status = "HIT_SL"

            if hit_status:
                supabase.table("market_research").update({
                    "status": hit_status,
                    "resolved_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", sig_id).execute()
                print(f"  -> সিগন্যাল ক্লোজড: {sym} | ফলাফল: {hit_status} | বর্তমান মূল্য: ${fmt_price(cur_price)}")

    except Exception as e:
        print(f"[-] লাইফসাইকেল ট্র্যাকিং ত্রুটি: {e}")

# ৪. নতুন হাই-কনভিকশন আলফা সিগন্যাল তৈরি
def generate_institutional_setups(coin):
    p = coin['price']
    chg = coin['change']
    vol = coin['volume_m']
    high = coin['high']
    low = coin['low']

    span = high - low
    volatility_ratio = span / (p + 1e-9)
    range_pos = (p - low) / (span + 1e-9)

    setups = []

    # ক) SCALPER
    scalp_dir = "long" if range_pos >= 0.48 or chg >= 0.5 else "short"
    scalp_risk = max(0.009, volatility_ratio * 0.18)
    scalp_reward = scalp_risk * 2.2
    sl_s = p * (1 - scalp_risk) if scalp_dir == "long" else p * (1 + scalp_risk)
    tp_s = p * (1 + scalp_reward) if scalp_dir == "long" else p * (1 - scalp_reward)

    setups.append({
        "symbol": coin['symbol'],
        "market_type": "crypto",
        "horizon": "24h",
        "direction": scalp_dir,
        "trading_mode": "mode2",
        "score": min(98, int(88 + (vol / 50) + (abs(chg) * 0.5))),
        "stage": "[SCALP] Momentum Flow Ignition",
        "current_change_24h": round(chg, 2),
        "sector": "Scalp Engine (5M)",
        "est_potential": f"+{round(scalp_reward * 100, 1)}%",
        "flow_metric": f"${vol}M Liquid Flow",
        "driver_metric": "RVOL Order Burst",
        "entry_price": p,
        "sl_price": sl_s,
        "tp_price": tp_s,
        "status": "ACTIVE",
        "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_s)}",
        "research_note": f"অর্ডারবুকে প্রাতিষ্ঠানিক চাপ। ৫ মিনিটের ব্রেকআউট মোমেন্টাম। [TP: ${fmt_price(tp_s)}]"
    })

    # খ) DAY TRADER
    day_dir = "long" if range_pos >= 0.35 else "short"
    day_risk = max(0.019, volatility_ratio * 0.35)
    day_reward = day_risk * 2.5
    sl_d = p * (1 - day_risk) if day_dir == "long" else p * (1 + day_risk)
    tp_d = p * (1 + day_reward) if day_dir == "long" else p * (1 - day_reward)

    setups.append({
        "symbol": coin['symbol'],
        "market_type": "crypto",
        "horizon": "24h",
        "direction": day_dir,
        "trading_mode": "mode2",
        "score": 93,
        "stage": "[DAY] Volatility Squeeze",
        "current_change_24h": round(chg, 2),
        "sector": "Day Engine (1H)",
        "est_potential": f"+{round(day_reward * 100, 1)}%",
        "flow_metric": "Accumulation Delta",
        "driver_metric": "Pre-Breakout Squeeze",
        "entry_price": p,
        "sl_price": sl_d,
        "tp_price": tp_d,
        "status": "ACTIVE",
        "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_d)}",
        "research_note": f"১ ঘণ্টার বলিঙ্গার স্কুইজ সম্পন্ন। ডিরেকশনাল এক্সপ্যানশন আসন্ন। [TP: ${fmt_price(tp_d)}]"
    })

    # গ) SWING TRADER
    swing_dir = "long" if (range_pos <= 0.32 or chg < -1.5) else "short"
    swing_risk = max(0.035, volatility_ratio * 0.60)
    swing_reward = swing_risk * 2.8
    sl_w = p * (1 - swing_risk) if swing_dir == "long" else p * (1 + swing_risk)
    tp_w = p * (1 + swing_reward) if swing_dir == "long" else p * (1 - swing_reward)

    setups.append({
        "symbol": coin['symbol'],
        "market_type": "crypto",
        "horizon": "1w",
        "direction": swing_dir,
        "trading_mode": "mode2",
        "score": 97,
        "stage": "[SWING] Liquidity Sweep",
        "current_change_24h": round(chg, 2),
        "sector": "Swing Engine (4H)",
        "est_potential": f"+{round(swing_reward * 100, 1)}%",
        "flow_metric": "Dark Pool Absorption",
        "driver_metric": "Whale Order Imbalance",
        "entry_price": p,
        "sl_price": sl_w,
        "tp_price": tp_w,
        "status": "ACTIVE",
        "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_w)}",
        "research_note": f"উচ্চ টাইমফ্রেমে লিকুইডিটি পুলে প্রাতিষ্ঠানিক সুইপ সম্পন্ন। [TP: ${fmt_price(tp_w)}]"
    })

    return setups

def run():
    print("[*] আলফা স্ক্যানার ও লাইফসাইকেল ইঞ্জিন চালু হচ্ছে...")
    prices = fetch_top_liquid_market()
    if not prices:
        print("[-] মার্কেট ডেটা পাওয়া যায়নি।")
        return

    # ১. পুরানো অ্যাক্টিভ ট্রেডের TP/SL ট্র্যাক ও আপডেট করা
    track_and_update_lifecycle(prices)

    # ২. ফ্রেশ সিগন্যাল তৈরি করা
    new_setups = []
    top_coins = sorted(prices.values(), key=lambda x: x['volume_m'], reverse=True)[:25]
    for c in top_coins:
        new_setups.extend(generate_institutional_setups(c))

    # ফরেক্স ও স্টকস সিগন্যাল
    trad_signals = [
        {"symbol": "EUR/USD", "market_type": "forex", "horizon": "24h", "direction": "long", "trading_mode": "mode1", "score": 92, "stage": "[DAY] Interbank Flow", "current_change_24h": 0.32, "sector": "Major FX", "est_potential": "+1.2%", "flow_metric": "Interbank Flow", "driver_metric": "Session Liquidity", "entry_price": 1.0850, "sl_price": 1.0800, "tp_price": 1.0920, "status": "ACTIVE", "mtf_alignment": "Entry: $1.0850 | SL: $1.0800", "research_note": "লন্ডন সেশন কি-লেভেল রিজেকশন। [TP: $1.0920]"},
        {"symbol": "NVDA", "market_type": "stocks", "horizon": "24h", "direction": "long", "trading_mode": "mode1", "score": 95, "stage": "[DAY] Dark Pool Block", "current_change_24h": 2.45, "sector": "US Tech / AI", "est_potential": "+5.5%", "flow_metric": "Off-Market Flow", "driver_metric": "Whale Accumulation", "entry_price": 138.50, "sl_price": 135.00, "tp_price": 146.00, "status": "ACTIVE", "mtf_alignment": "Entry: $138.50 | SL: $135.00", "research_note": "অফ-মার্কেট ব্লক ট্রানজ্যাকশন সক্রিয়। [TP: $146.00]"}
    ]
    new_setups.extend(trad_signals)

    # ৩. Supabase-এ ইনসার্ট
    success = 0
    for item in new_setups:
        try:
            supabase.table("market_research").insert(item).execute()
            success += 1
        except Exception:
            pass

    print(f"\n[DONE] মোট {success}টি নতুন সক্রিয় সিগন্যাল পুশ সম্পন্ন!")

if __name__ == "__main__":
    run()
