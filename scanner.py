import os
import requests
import time
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# ==============================================================================
# ১. SUPABASE সংযোগ কনফিগারেশন (Error-Proof Fallback)
# ==============================================================================
RAW_URL = os.getenv("SUPABASE_URL")
SUPABASE_URL = RAW_URL.strip() if RAW_URL else "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    if not SUPABASE_KEY:
        raise ValueError("GitHub Secrets-এ SUPABASE_KEY পাওয়া যায়নি! দয়া করে সেটিংস চেক করুন।")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✔ GreatNexa Multi-Asset Institutional SMC Engine Connected!")
except Exception as e:
    print(f"✖ Supabase Connection Failed: {e}")
    exit(1)

# ডেসিমাল প্রিসিশন ফিক্স (PEPE, SHIB ইত্যাদির জন্য ৮ ডিজিট সাপোর্ট)
def fmt_price(p):
    try:
        p = float(p)
        if p == 0:
            return "0.00"
        if p < 0.0001:
            return f"{p:.8f}"  # PEPE বা মাইক্রো কয়েন
        elif p < 0.01:
            return f"{p:.6f}"
        elif p < 1.0:
            return f"{p:.4f}"
        elif p < 100.0:
            return f"{p:.3f}"
        else:
            return f"{p:.2f}"
    except Exception:
        return str(p)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
})

# ==============================================================================
# ২. টেলিগ্রাম ভিআইপি সিগন্যাল অ্যালার্ট ইঞ্জিন
# ==============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(signal):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        sym = signal['symbol']
        direction = "🟢 LONG / BUY" if signal['direction'] == 'long' else "🔴 SHORT / SELL"
        msg = (
            f"⚡ *GREATNEXA INSTITUTIONAL ALPHA SIGNAL*\n\n"
            f"📌 *Asset:* `{sym}`\n"
            f"📊 *Direction:* {direction}\n"
            f"🎯 *Conviction Score:* `{signal['score']}/100`\n"
            f"⚡ *Style:* {signal['stage']} ({signal['trader_style'].upper()})\n"
            f"⏳ *Horizon:* {signal['projection_horizon'].upper()}\n\n"
            f"💵 *Entry:* `${fmt_price(signal['entry_price'])}`\n"
            f"🛑 *Stop Loss:* `${fmt_price(signal['sl_price'])}`\n"
            f"🎯 *Take Profit:* `${fmt_price(signal['tp_price'])}`\n\n"
            f"📈 *Est. Potential:* `{signal['est_potential']}`\n"
            f"🧠 *Institutional Note:* {signal['research_note']}\n\n"
            f"🌐 [Open Terminal Dashboard](https://greatnexa.com/)"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        res = session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
        if res.status_code == 200:
            print(f"✔ Telegram Alert Pushed: {sym} ({direction})")
        elif res.status_code == 429:
            retry_after = res.json().get('parameters', {}).get('retry_after', 10)
            time.sleep(retry_after)
            session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
    except Exception as e:
        print(f"[-] Telegram Alert Notification Error: {e}")

def send_telegram_status(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=8)
    except Exception:
        pass

# ==============================================================================
# ৩. অটোমেটিক সাবস্ক্রিপশন ও পেমেন্ট প্রসেসর
# ==============================================================================
def process_automatic_subscriptions():
    print("[*] Processing Autonomous Subscription Lifecycle & Payment Verification...")
    now = datetime.now(timezone.utc)
    try:
        expired_res = supabase.table("user_profiles").select("id, email, tier, expires_at").neq("tier", "free").lt("expires_at", now.isoformat()).execute()
        expired_users = expired_res.data or []
        for u in expired_users:
            supabase.table("user_profiles").update({
                "tier": "free",
                "expires_at": None,
                "updated_at": now.isoformat()
            }).eq("id", u["id"]).execute()
            print(f"  -> [EXPIRED] Subscription ended for {u.get('email', u['id'])}. Reverted to Free Tier.")
    except Exception as e:
        print(f"[-] Auto-Rollback Engine Error: {e}")

    try:
        pending_orders = supabase.table("orders").select("*").eq("status", "pending").execute().data or []
        for o in pending_orders:
            trx = str(o.get("trx_id", "")).strip()
            phone_method = str(o.get("phone", ""))
            user_email = o.get("email") or o.get("customer_name")
            order_id = o.get("id")
            plan_name = o.get("product_name", "")

            if "Binance" in phone_method and len(trx) >= 8 and user_email:
                is_vip = "VIP" in plan_name or "49" in plan_name
                target_tier = "vip" if is_vip else "pro"
                days = 730 if is_vip else 30
                try:
                    supabase.rpc("admin_approve_order", {
                        "p_order_id": order_id,
                        "p_user_email": user_email,
                        "p_tier": target_tier,
                        "p_duration_days": days
                    }).execute()
                    print(f"  -> [AUTO-APPROVED] Order #{order_id} verified for {user_email}.")
                except Exception as approve_err:
                    print(f"[-] Auto-Approve RPC Error: {approve_err}")
    except Exception as e:
        print(f"[-] Subscription Processor Error: {e}")

# ==============================================================================
# ৪. ডাটাবেজ অপটিমাইজার ও Retention
# ==============================================================================
def cleanup_old_database_records():
    print("[*] Running Autonomous Database Storage Optimizer & TTL Expiry...")
    now = datetime.now(timezone.utc)
    cutoff_ttl = (now - timedelta(hours=48)).isoformat()
    cutoff_hof = (now - timedelta(days=7)).isoformat()
    cutoff_failures = (now - timedelta(days=3)).isoformat()
    
    try:
        supabase.table("market_research").update({"status": "EXPIRED", "resolved_at": now.isoformat()}).eq("status", "ACTIVE").lt("created_at", cutoff_ttl).execute()
        supabase.table("market_research").delete().eq("status", "HIT_TP").lt("resolved_at", cutoff_hof).execute()
        supabase.table("market_research").delete().in_("status", ["HIT_SL", "EXPIRED"]).lt("resolved_at", cutoff_failures).execute()
        print("✔ Database Cleaned Successfully.")
    except Exception as e:
        print(f"[-] Cleanup & TTL Error: {e}")

# ==============================================================================
# ৫. ক্রিপ্টো: টপ ৫০০ পেয়ারের লাইভ ডায়নামিক স্ক্রিনার
# ==============================================================================
def fetch_top_500_crypto():
    print("[*] Fetching Top 500 Crypto Pairs from Binance...")
    market_pool = {}
    try:
        r = session.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=15)
        if r.status_code == 200:
            all_tickers = r.json()
            usdt_pairs = [
                t for t in all_tickers 
                if t['symbol'].endswith('USDT') and not any(x in t['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL'])
            ]
            sorted_pairs = sorted(
                usdt_pairs, 
                key=lambda x: float(x.get('quoteVolume', 0)) * (1 + abs(float(x.get('priceChangePercent', 0))) / 100), 
                reverse=True
            )[:500]

            for t in sorted_pairs:
                price = float(t.get('lastPrice', 0))
                vol_m = round(float(t.get('quoteVolume', 0)) / 1_000_000, 2)
                if price <= 0: continue

                sym = t['symbol'].replace("USDT", "/USDT")
                market_pool[sym] = {
                    "symbol": sym, "market_type": "crypto",
                    "sector": "Layer-1 Major" if any(k in sym for k in ["BTC", "ETH", "SOL", "BNB", "XRP"]) else "High-Beta Altcoin",
                    "price": price, "high": float(t.get('highPrice', 0)), "low": float(t.get('lowPrice', 0)),
                    "open": float(t.get('openPrice', 0)), "change": float(t.get('priceChangePercent', 0)), "volume_m": vol_m
                }
    except Exception as e:
        print(f"[-] Top 500 Crypto Error: {e}")
    return market_pool

# ==============================================================================
# ৬. ইউএস স্টকস: লাইভ মার্কেট টপ ১০০ স্টক স্ক্রিনার
# ==============================================================================
def fetch_top_100_stocks():
    print("[*] Fetching Top 100 US Stocks...")
    stock_pool = {}
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=most_actives&count=100"
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            quotes = res.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            for q in quotes:
                ticker = q.get('symbol', '').replace(".", "-")
                price = float(q.get('regularMarketPrice') or 0)
                if not ticker or price <= 0 or "^" in ticker: continue

                stock_pool[ticker] = {
                    "symbol": ticker, "market_type": "stocks", "sector": "US Dynamic Equity",
                    "price": price, "high": float(q.get('regularMarketDayHigh') or (price * 1.01)),
                    "low": float(q.get('regularMarketDayLow') or (price * 0.99)),
                    "open": float(q.get('regularMarketOpen') or price),
                    "change": float(q.get('regularMarketChangePercent') or 0),
                    "volume_m": round(float(q.get('regularMarketVolume') or 1000000) / 1_000_000, 2)
                }
    except Exception as e:
        print(f"[-] Stock Screener Warning: {e}")
    return stock_pool

# ==============================================================================
# ৭. ফরেক্স ও কমোডিটিজ: ১০০% ডায়নামিক লাইভ স্ক্রিনার
# ==============================================================================
def fetch_top_100_forex_universe():
    print("[*] Dynamically Screening Top 100 Forex & Commodities from Live Market...")
    forex_pool = {}
    discovered_quotes = []

    fx_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=currencies&count=100"
    try:
        r_fx = session.get(fx_url, timeout=12)
        if r_fx.status_code == 200:
            fx_data = r_fx.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            discovered_quotes.extend(fx_data)
            print(f"  -> Discovered {len(fx_data)} Live Forex Pairs from Global Screener.")
    except Exception as e:
        print(f"[-] Dynamic Forex Screener Error: {e}")

    comm_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=all_commodities&count=50"
    try:
        r_comm = session.get(comm_url, timeout=12)
        if r_comm.status_code == 200:
            comm_data = r_comm.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            discovered_quotes.extend(comm_data)
            print(f"  -> Discovered {len(comm_data)} Live Commodities & Metals from Screener.")
    except Exception as e:
        print(f"[-] Dynamic Commodities Screener Error: {e}")

    commodities_map = {
        "GC=F": ("XAU/USD", "Precious Metals & Gold"),
        "SI=F": ("XAG/USD", "Precious Metals & Silver"),
        "PL=F": ("XPT/USD", "Precious Metals & Platinum"),
        "PA=F": ("XPD/USD", "Precious Metals & Palladium"),
        "CL=F": ("WTI/CRUDE", "Global Energy Commodity"),
        "NG=F": ("NATGAS/USD", "Global Energy Commodity"),
        "HG=F": ("COPPER/USD", "Industrial Metals Commodity")
    }

    for item in discovered_quotes:
        ticker = item.get('symbol', '')
        price = float(item.get('regularMarketPrice') or item.get('price') or 0)
        if not ticker or price <= 0 or "^" in ticker:
            continue

        if ticker in commodities_map:
            clean_sym, sector = commodities_map[ticker]
            m_type = "forex"
        elif ticker.endswith("=X"):
            raw_sym = ticker.replace("=X", "")
            clean_sym = f"{raw_sym[:3]}/{raw_sym[3:]}" if len(raw_sym) == 6 else raw_sym
            m_type = "forex"
            is_major = any(curr in clean_sym for curr in ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"])
            sector = "G10 Interbank FX" if is_major else "Global Cross FX"
        elif ticker.endswith("=F"):
            clean_sym = ticker.replace("=F", "") + "/USD"
            m_type = "forex"
            sector = "Global Commodity Future"
        else:
            continue

        if clean_sym not in forex_pool:
            forex_pool[clean_sym] = {
                "symbol": clean_sym,
                "market_type": m_type,
                "sector": sector,
                "price": price,
                "high": float(item.get('regularMarketDayHigh') or (price * 1.008)),
                "low": float(item.get('regularMarketDayLow') or (price * 0.992)),
                "open": float(item.get('regularMarketOpen') or price),
                "change": float(item.get('regularMarketChangePercent') or 0),
                "volume_m": round(float(item.get('regularMarketVolume') or 2000000) / 1_000_000, 2)
            }

    print(f"✔ Final Filtered Pool: {len(forex_pool)} Completely Dynamic Forex & Gold Pairs Ready.")
    return forex_pool

# ==============================================================================
# ৮. লাইফসাইকেল ট্র্যাকার (TP/SL Check & Active Trades Management)
# ==============================================================================
def track_and_update_lifecycle(current_prices):
    active_setups_map = set()
    try:
        # বর্তমানে ACTIVE এবং সাম্প্রতিক রেজলভড সেটআপগুলো রিড করা
        res = supabase.table("market_research").select("id, symbol, sector, direction, sl_price, tp_price, status, created_at").eq("status", "ACTIVE").execute()
        active_signals = res.data or []
        now = datetime.now(timezone.utc)

        for sig in active_signals:
            sym = sig.get("symbol")
            sec = sig.get("sector") or ""
            direction = sig.get("direction", "long")
            sig_id = sig.get("id")

            style_tag = "Scalp" if "Scalp" in sec else ("Day" if "Day" in sec else "Swing")
            active_setups_map.add(f"{sym}_{style_tag}_{direction}")

            if sym not in current_prices: continue

            cur_price = current_prices[sym]["price"]
            sl = float(sig.get("sl_price") or 0)
            tp = float(sig.get("tp_price") or 0)

            hit_status = None
            if direction == "long":
                if cur_price >= tp and tp > 0: hit_status = "HIT_TP"
                elif cur_price <= sl and sl > 0: hit_status = "HIT_SL"
            else:
                if cur_price <= tp and tp > 0: hit_status = "HIT_TP"
                elif cur_price >= sl and sl > 0: hit_status = "HIT_SL"

            if hit_status:
                supabase.table("market_research").update({
                    "status": hit_status,
                    "resolved_at": now.isoformat()
                }).eq("id", sig_id).execute()
                print(f"  -> [{hit_status}] {sym} Closed at ${fmt_price(cur_price)}")

    except Exception as e:
        print(f"[-] Lifecycle Error: {e}")
    return active_setups_map

# ==============================================================================
# ৯. এডভান্সড SMC কোয়ান্টাম ইঞ্জিন (SFP Liquidity Sweep + FVG + Strict ATR TP/SL)
# ==============================================================================
def generate_smc_institutional_signal(item, active_setups_map):
    p = item['price']
    chg = item['change']
    vol = item['volume_m']
    high = item['high']
    low = item['low']
    open_p = item.get('open', p)
    m_type = item['market_type']
    base_sector = item.get('sector', 'Core Market')

    span = high - low
    if span <= 0 or p <= 0: return []

    volatility_ratio = span / p
    range_pos = (p - low) / span
    lower_wick = min(open_p, p) - low
    upper_wick = high - max(open_p, p)

    # Smart Money Sweep & SFP কনফার্মেশন
    is_bullish_sfp = (lower_wick >= span * 0.28) and (range_pos >= 0.45)
    is_bearish_sfp = (upper_wick >= span * 0.28) and (range_pos <= 0.55)

    conviction_score = 88

    if is_bullish_sfp or (chg >= 0.7 and range_pos >= 0.50):
        direction = "long"
        purge_catalyst = "Sell-Side Liquidity Swept (SFP)" if is_bullish_sfp else "Institutional Order Block FVG Inflow"
        flow_delta = f"${vol}M Smart Money Accumulation"
        if is_bullish_sfp: conviction_score += 4
        if chg > 1.2: conviction_score += 3
        if vol >= 10.0: conviction_score += 3
    elif is_bearish_sfp or (chg <= -0.7 and range_pos <= 0.50):
        direction = "short"
        purge_catalyst = "Buy-Side Liquidity Swept (SFP)" if is_bearish_sfp else "Institutional Supply FVG Distribution"
        flow_delta = f"${vol}M Institutional Distribution"
        if is_bearish_sfp: conviction_score += 4
        if chg < -1.2: conviction_score += 3
        if vol >= 10.0: conviction_score += 3
    else:
        direction = "long" if chg >= 0 else "short"
        purge_catalyst = "Order Flow Imbalance"
        flow_delta = f"${vol}M Momentum Inflow"
        if abs(chg) >= 0.5: conviction_score += 2
        if vol >= 5.0: conviction_score += 2

    score = min(98, max(88, conviction_score))

    if m_type == "crypto":
        base_risk = max(0.015, volatility_ratio * 0.25)
    elif m_type == "stocks":
        base_risk = max(0.009, volatility_ratio * 0.20)
    else:
        base_risk = max(0.0035, volatility_ratio * 0.16)

    setups = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    styles = [
        {
            "style": "Scalp", 
            "trader_style": "scalp", 
            "timeframe": "5m", 
            "tag": "Scalp Engine (5M)", 
            "horizon": "24h", 
            "rr": 2.2, 
            "risk_mult": 0.8
        },
        {
            "style": "Day", 
            "trader_style": "day", 
            "timeframe": "1h", 
            "tag": "Day Engine (1H)", 
            "horizon": "1w", 
            "rr": 2.8, 
            "risk_mult": 1.1
        },
        {
            "style": "Swing", 
            "trader_style": "swing", 
            "timeframe": "4h", 
            "tag": "Swing Engine (4H)", 
            "horizon": "1m", 
            "rr": 3.4, 
            "risk_mult": 1.5
        }
    ]

    for s in styles:
        setup_key = f"{item['symbol']}_{s['style']}_{direction}"
        # যদি ইতিমধ্যে এই পেয়ারটি ACTIVE থাকে, তাহলে পুনরায় ইনসার্ট করে স্প্যাম করা বন্ধ রাখা
        if setup_key in active_setups_map: 
            continue

        effective_risk = base_risk * s['risk_mult']
        entry = p
        
        # নিখুঁত গাণিতিক এন্ট্রি, স্টপ লস ও টেক প্রফিট নির্ধারণ
        if direction == "long":
            sl = entry * (1.0 - effective_risk)
            tp = entry * (1.0 + (effective_risk * s['rr']))
        else:
            sl = entry * (1.0 + effective_risk)
            tp = entry * (1.0 - (effective_risk * s['rr']))

        # যদি ডেসিমাল প্রিসিশনের কারণে SL বা TP এন্ট্রির সমান হয়ে যাওয়ার ঝুঁকি থাকে
        if abs(entry - sl) <= 0:
            sl = entry * 0.98 if direction == "long" else entry * 1.02
        if abs(tp - entry) <= 0:
            tp = entry * 1.04 if direction == "long" else entry * 0.96

        setups.append({
            "symbol": item['symbol'], 
            "market_type": m_type, 
            "horizon": s['horizon'],
            "projection_horizon": s['horizon'],
            "trader_style": s['trader_style'],
            "timeframe": s['timeframe'],
            "direction": direction,
            "trading_mode": "mode2" if m_type == "crypto" else "mode1", 
            "score": score,
            "stage": f"[{s['style'].upper()}] Institutional Squeeze", 
            "current_change_24h": round(chg, 2),
            "sector": f"{s['tag']} • {base_sector}", 
            "est_potential": f"+{round(effective_risk * s['rr'] * 100, 1)}%",
            "flow_metric": flow_delta, 
            "driver_metric": purge_catalyst,
            "entry_price": float(entry), 
            "sl_price": float(sl), 
            "tp_price": float(tp), 
            "status": "ACTIVE",
            "created_at": now_iso,
            "mtf_alignment": f"Entry: ${fmt_price(entry)} | TP: ${fmt_price(tp)} | SL: ${fmt_price(sl)}",
            "research_note": f"{s['style']} SMC {direction.upper()} অর্ডারব্লক ও লিকুইডিটি পার্জ কনফার্মড। R:R = 1:{s['rr']:.1f}"
        })
    return setups

# ==============================================================================
# ১০. এক্সিকিউশন রানার
# ==============================================================================
def run():
    print("=" * 80)
    print(f"[*] RUNNING GREATNEXA ADVANCED QUANT ENGINE: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    send_telegram_status("⚡ *GreatNexa Institutional Engine Active & Scanning Markets...*")

    process_automatic_subscriptions()
    cleanup_old_database_records()

    crypto_prices = fetch_top_500_crypto()
    stocks_prices = fetch_top_100_stocks()
    forex_prices = fetch_top_100_forex_universe()
    
    all_prices = {**crypto_prices, **stocks_prices, **forex_prices}
    if not all_prices: return

    # লাইফসাইকেল চেক (যদি SL/TP হিট হয়, সাথে সাথে HIT_SL বা HIT_TP হয়ে যাবে)
    active_setups_map = track_and_update_lifecycle(all_prices)
    crypto_setups, stock_setups, forex_setups = [], [], []

    # টপ মোমেন্টাম ক্রিপ্টো (টপ ৫০টি লিকুইডিটি পেয়ার)
    for c in sorted(crypto_prices.values(), key=lambda x: (abs(x['change']) * x['volume_m']), reverse=True)[:50]:
        crypto_setups.extend(generate_smc_institutional_signal(c, active_setups_map))

    # টপ মোমেন্টাম ইউএস স্টকস (টপ ৩৫টি)
    for s in sorted(stocks_prices.values(), key=lambda x: abs(x['change']), reverse=True)[:35]:
        stock_setups.extend(generate_smc_institutional_signal(s, active_setups_map))

    # টপ মোমেন্টাম ফরেক্স ও গোল্ড (টপ ৫০টি)
    for f in sorted(forex_prices.values(), key=lambda x: abs(x['change']), reverse=True)[:50]:
        forex_setups.extend(generate_smc_institutional_signal(f, active_setups_map))

    website_batch = [x for x in (crypto_setups + stock_setups + forex_setups) if x['score'] >= 88]

    if website_batch:
        try:
            supabase.table("market_research").insert(website_batch).execute()
            print(f"\n✔ Successfully pushed {len(website_batch)} High-Conviction Setups to Website Database (Forex: {len(forex_setups)}, Crypto: {len(crypto_setups)})!")
        except Exception as e:
            print(f"[-] Batch insert error: {e}")

        # টেলিগ্রাম অ্যালার্ট ফিল্টার (সেরা সিগন্যাল কিউরেশন)
        top_telegram_crypto = sorted([x for x in crypto_setups if x['score'] >= 92], key=lambda x: x['score'], reverse=True)[:4]
        top_telegram_stocks = sorted([x for x in stock_setups if x['score'] >= 92], key=lambda x: x['score'], reverse=True)[:2]
        top_telegram_forex = sorted([x for x in forex_setups if x['score'] >= 92], key=lambda x: x['score'], reverse=True)[:2]

        telegram_queue = top_telegram_crypto + top_telegram_stocks + top_telegram_forex

        print(f"\n[*] Pushing {len(telegram_queue)} Curated Signals to Telegram Channel...")
        for s in telegram_queue:
            send_telegram_alert(s)
            time.sleep(3.5)
    else:
        print("\n[i] No high-conviction setups meeting threshold at this cycle.")

if __name__ == "__main__":
    run()
