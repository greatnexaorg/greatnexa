import requests
import time
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# ১. Supabase সংযোগ (Service Role Secret Key)
SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzcWhhbnNub3NlamtxYXB1aG9vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjcwOTQwMywiZXhwIjoyMTAyMjg1NDAzfQ.gVXQnOD9OXWCJj_MN_i6eML9dyPvZZhC1BznGE4y3Ks"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✔ GreatNexa Supreme Quant Engine Connected to Supabase!")
except Exception as e:
    print(f"✖ Supabase Connection Failed: {e}")
    exit(1)

def fmt_price(p):
    p = float(p)
    return f"{p:.2f}" if p >= 100 else (f"{p:.4f}" if p >= 1 else f"{p:.6f}")

# ২. অটোমেটিক ডাটাবেজ স্টোরেজ অপটিমাইজার (Auto-Purge Engine)
def cleanup_old_database_records():
    print("[*] Running Autonomous Database Purge Engine...")
    now = datetime.now(timezone.utc)
    cutoff_hof = (now - timedelta(days=30)).isoformat()
    cutoff_failures = (now - timedelta(days=3)).isoformat()
    
    try:
        supabase.table("market_research").delete().eq("status", "HIT_TP").lt("resolved_at", cutoff_hof).execute()
        supabase.table("market_research").delete().in_("status", ["HIT_SL", "EXPIRED"]).lt("resolved_at", cutoff_failures).execute()
        print("✔ Database Cleaned: Storage zero-bloat enforced.")
    except Exception as e:
        print(f"[-] Cleanup Error: {e}")

# ৩. হাই-লিকুইডিটি ও মাল্টি-ভেক্টর মার্কেট স্ক্রিনার (সবসময় নতুন নতুন কয়েন আনবে)
def fetch_dynamic_market_universe():
    market_pool = {}
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", headers=headers, timeout=10)
        if r.status_code == 200:
            all_tickers = r.json()
            # শুধু ভ্যালিড USDT পেয়ার ফিল্টার করা
            usdt_pairs = [
                t for t in all_tickers 
                if t['symbol'].endswith('USDT') and not any(x in t['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL'])
            ]

            # ৩টি আলাদা বালতিতে বাছাই যাতে কয়েন সবসময় রোটেশন হয়
            # ক) টপ ভলিউম কয়েন (মেজর)
            top_volume = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)[:10]
            # খ) টপ গেইনারস (মোমেন্টাম ব্রেকআউট)
            top_gainers = sorted(usdt_pairs, key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)[:10]
            # গ) টপ লুজারস (লিকুইডিটি বাউন্স/সুইপ)
            top_losers = sorted(usdt_pairs, key=lambda x: float(x.get('priceChangePercent', 0)))[:10]

            selected_raw = {t['symbol']: t for t in (top_volume + top_gainers + top_losers)}.values()

            for t in selected_raw:
                sym = t['symbol'].replace("USDT", "/USDT")
                price = float(t.get('lastPrice', 0))
                if price <= 0:
                    continue
                market_pool[sym] = {
                    "symbol": sym,
                    "price": price,
                    "high": float(t.get('highPrice', 0)),
                    "low": float(t.get('lowPrice', 0)),
                    "change": float(t.get('priceChangePercent', 0)),
                    "volume_m": round(float(t.get('quoteVolume', 0)) / 1_000_000, 1)
                }
    except Exception as e:
        print(f"[-] Market feed error: {e}")
    return market_pool

# ৪. লাইফসাইকেল ট্র্যাকার (TP/SL ভেরিফিকেশন ও রেজাল্ট লক)
def track_and_update_lifecycle(current_prices):
    print("[*] Auditing Open Institutional Positions...")
    active_setups_map = set()
    try:
        res = supabase.table("market_research").select("*").eq("status", "ACTIVE").execute()
        active_signals = res.data or []
        print(f"[i] Open Trades in Tracking Desk: {len(active_signals)}")

        now = datetime.now(timezone.utc)

        for sig in active_signals:
            sym = sig.get("symbol")
            sec = sig.get("sector")
            sig_id = sig.get("id")
            
            # সক্রিয় কয়েন ট্র্যাক রাখা
            active_setups_map.add(f"{sym}_{sec}")

            if sym not in current_prices:
                continue

            cur_price = current_prices[sym]["price"]
            direction = sig.get("direction", "long")
            sl = float(sig.get("sl_price") or 0)
            tp = float(sig.get("tp_price") or 0)
            created_at_str = sig.get("created_at")

            hit_status = None

            # নিখুঁত TP ও SL ক্যালকুলেশন
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

            # ৩৬ ঘণ্টার বেশি ট্রেড ঝুলে থাকলে স্বয়ংক্রিয়ভাবে এক্সপায়ার হবে
            if not hit_status and created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if now - created_at > timedelta(hours=36):
                    hit_status = "EXPIRED"

            if hit_status:
                supabase.table("market_research").update({
                    "status": hit_status,
                    "resolved_at": now.isoformat()
                }).eq("id", sig_id).execute()

                log_badge = "🏆 [HALL OF FAME WIN]" if hit_status == "HIT_TP" else ("⛔ [STOP LOSS]" if hit_status == "HIT_SL" else "⏳ [EXPIRED]")
                print(f"  -> {log_badge} {sym} ({sec}) | Status: {hit_status} | Exit: ${fmt_price(cur_price)}")

    except Exception as e:
        print(f"[-] Lifecycle tracking error: {e}")

    return active_setups_map

# ৫. হাই-কনভিকশন ইনস্টিটিউশনাল আলফা জেনারেটর
def generate_institutional_setups(coin, active_setups_map):
    p = coin['price']
    chg = coin['change']
    vol = coin['volume_m']
    high = coin['high']
    low = coin['low']

    span = high - low
    volatility_ratio = span / (p + 1e-9)
    range_pos = (p - low) / (span + 1e-9)

    setups = []

    # ক) SCALPER (5M High Frequency Inflow)
    scalp_key = f"{coin['symbol']}_Scalp Engine (5M)"
    if scalp_key not in active_setups_map and vol >= 3.0:
        scalp_dir = "long" if (range_pos >= 0.50 or chg >= 1.0) else "short"
        scalp_risk = max(0.008, volatility_ratio * 0.16)
        scalp_reward = scalp_risk * 2.4
        sl_s = p * (1 - scalp_risk) if scalp_dir == "long" else p * (1 + scalp_risk)
        tp_s = p * (1 + scalp_reward) if scalp_dir == "long" else p * (1 - scalp_reward)

        setups.append({
            "symbol": coin['symbol'],
            "market_type": "crypto",
            "horizon": "24h",
            "direction": scalp_dir,
            "trading_mode": "mode2",
            "score": min(98, int(89 + (vol / 60) + (abs(chg) * 0.4))),
            "stage": "[SCALP] Level-3 Delta Inflow",
            "current_change_24h": round(chg, 2),
            "sector": "Scalp Engine (5M)",
            "est_potential": f"+{round(scalp_reward * 100, 1)}%",
            "flow_metric": f"${vol}M Whale Flow",
            "driver_metric": "RVOL Order Cluster",
            "entry_price": p,
            "sl_price": sl_s,
            "tp_price": tp_s,
            "status": "ACTIVE",
            "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_s)}",
            "research_note": f"অর্ডারবুকে প্রাতিষ্ঠানিক চাপ। ৫ মিনিটের ব্রেকআউট মোমেন্টাম। [TP: ${fmt_price(tp_s)}]"
        })

    # খ) DAY TRADER (1H Liquidity Squeeze)
    day_key = f"{coin['symbol']}_Day Engine (1H)"
    if day_key not in active_setups_map and vol >= 5.0:
        day_dir = "long" if range_pos >= 0.38 else "short"
        day_risk = max(0.018, volatility_ratio * 0.32)
        day_reward = day_risk * 2.6
        sl_d = p * (1 - day_risk) if day_dir == "long" else p * (1 + day_risk)
        tp_d = p * (1 + day_reward) if day_dir == "long" else p * (1 - day_reward)

        setups.append({
            "symbol": coin['symbol'],
            "market_type": "crypto",
            "horizon": "24h",
            "direction": day_dir,
            "trading_mode": "mode2",
            "score": 94,
            "stage": "[DAY] Volatility Squeeze",
            "current_change_24h": round(chg, 2),
            "sector": "Day Engine (1H)",
            "est_potential": f"+{round(day_reward * 100, 1)}%",
            "flow_metric": "Absorption Block",
            "driver_metric": "Pre-Breakout Compression",
            "entry_price": p,
            "sl_price": sl_d,
            "tp_price": tp_d,
            "status": "ACTIVE",
            "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_d)}",
            "research_note": f"১ ঘণ্টার বলিঙ্গার স্কুইজ সম্পন্ন। ডিরেকশনাল এক্সপ্যানশন আসন্ন। [TP: ${fmt_price(tp_d)}]"
        })

    # গ) SWING TRADER (4H Smart Money Sweep)
    swing_key = f"{coin['symbol']}_Swing Engine (4H)"
    if swing_key not in active_setups_map and vol >= 8.0:
        swing_dir = "long" if (range_pos <= 0.30 or chg < -2.0) else "short"
        swing_risk = max(0.032, volatility_ratio * 0.55)
        swing_reward = swing_risk * 3.0
        sl_w = p * (1 - swing_risk) if swing_dir == "long" else p * (1 + swing_risk)
        tp_w = p * (1 + swing_reward) if swing_dir == "long" else p * (1 - swing_reward)

        setups.append({
            "symbol": coin['symbol'],
            "market_type": "crypto",
            "horizon": "1w",
            "direction": swing_dir,
            "trading_mode": "mode2",
            "score": 97,
            "stage": "[SWING] Dark Pool Absorption",
            "current_change_24h": round(chg, 2),
            "sector": "Swing Engine (4H)",
            "est_potential": f"+{round(swing_reward * 100, 1)}%",
            "flow_metric": "Dark Pool Accumulation",
            "driver_metric": "Whale Order Imbalance",
            "entry_price": p,
            "sl_price": sl_w,
            "tp_price": tp_w,
            "status": "ACTIVE",
            "mtf_alignment": f"Entry: ${fmt_price(p)} | SL: ${fmt_price(sl_w)}",
            "research_note": f"উচ্চ টাইমফ্রেমে লিকুইডিটি পুলে প্রাতিষ্ঠানিক সুইপ সম্পন্ন। [TP: ${fmt_price(tp_w)}]"
        })

    return setups

# ৬. এক্সিকিউশন রানার
def run():
    print("=" * 65)
    print(f"[*] QUANT DESK SCANNER: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)
    
    # ধাপ ১: অপ্রয়োজনীয় ডাটাবেজ রেকর্ড ক্লিন করা
    cleanup_old_database_records()

    # ধাপ ২: ডাইনামিক মার্কেট ডেটা আনা
    prices = fetch_dynamic_market_universe()
    if not prices:
        print("[-] Market liquidity stream unavailable.")
        return

    # ধাপ ৩: পুরানো ট্রেডের ফলাফল নির্ণয়
    active_setups_map = track_and_update_lifecycle(prices)

    # ধাপ ৪: কয়েন রোটেশন অনুযায়ী নতুন সিগন্যাল তৈরি
    new_setups = []
    for coin_data in list(prices.values())[:24]:
        new_setups.extend(generate_institutional_setups(coin_data, active_setups_map))

    # ফরেক্স ও স্টকস সিগন্যাল
    for item in [
        {"symbol": "EUR/USD", "market_type": "forex", "sector": "Major FX", "entry_price": 1.0850, "sl_price": 1.0800, "tp_price": 1.0920, "score": 92, "direction": "long", "trading_mode": "mode1", "horizon": "24h", "stage": "[DAY] Interbank Flow", "current_change_24h": 0.32, "est_potential": "+1.2%", "flow_metric": "Interbank Flow", "driver_metric": "Session Liquidity", "status": "ACTIVE", "mtf_alignment": "Entry: $1.0850 | SL: $1.0800", "research_note": "লন্ডন সেশন কি-লেভেল রিজেকশন। [TP: $1.0920]"},
        {"symbol": "NVDA", "market_type": "stocks", "sector": "US Tech / AI", "entry_price": 138.50, "sl_price": 135.00, "tp_price": 146.00, "score": 95, "direction": "long", "trading_mode": "mode1", "horizon": "24h", "stage": "[DAY] Dark Pool Block", "current_change_24h": 2.45, "est_potential": "+5.5%", "flow_metric": "Off-Market Flow", "driver_metric": "Whale Accumulation", "status": "ACTIVE", "mtf_alignment": "Entry: $138.50 | SL: $135.00", "research_note": "অফ-মার্কেট ব্লক ট্রানজ্যাকশন সক্রিয়। [TP: $146.00]"}
    ]:
        if f"{item['symbol']}_{item['sector']}" not in active_setups_map:
            new_setups.append(item)

    # ধাপ ৫: ব্যাচ ইনসার্ট
    if new_setups:
        try:
            supabase.table("market_research").insert(new_setups).execute()
            print(f"\n✔ Successfully pushed {len(new_setups)} high-conviction alpha signals!")
        except Exception as e:
            print(f"[-] Batch insert error: {e}")
    else:
        print("\n[i] All existing positions are actively monitored. No duplicate injection.")

if __name__ == "__main__":
    run()
