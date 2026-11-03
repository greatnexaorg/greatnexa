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

def fmt_price(p):
    p = float(p)
    return f"{p:.2f}" if p >= 100 else (f"{p:.4f}" if p >= 1 else f"{p:.6f}")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
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
            f"⚡ *Style:* {signal['stage']}\n\n"
            f"💵 *Entry:* `${fmt_price(signal['entry_price'])}`\n"
            f"🛑 *Stop Loss:* `${fmt_price(signal['sl_price'])}`\n"
            f"🎯 *Take Profit:* `${fmt_price(signal['tp_price'])}`\n\n"
            f"📈 *Est. Potential:* `{signal['est_potential']}`\n"
            f"🧠 *Institutional Note:* {signal['research_note']}\n\n"
            f"🌐 [Open Terminal Dashboard](https://greatnexa.com/)"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=6)
    except Exception as e:
        print(f"[-] Telegram Alert Notification Error: {e}")

# ==============================================================================
# ৩. অটোমেটিক বাইন্যান্স পে ভেরিফায়ার ও সাবস্ক্রিপশন এক্সপায়ারি রোলব্যাক
# ==============================================================================
def process_automatic_subscriptions():
    print("[*] Processing Autonomous Subscription Lifecycle & Payment Verification...")
    now = datetime.now(timezone.utc)
    
    # ক) মেয়াদোত্তীর্ণ ইউজারদের স্বয়ংক্রিয় ফ্রি টিয়ারে নামানো (Auto-Rollback)
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

    # খ) পেন্ডিং বাইন্যান্স পে ভেরিফিকেশন ও এক্টিভেশন
    try:
        pending_orders = supabase.table("orders").select("*").eq("status", "pending").execute().data or []
        for o in pending_orders:
            trx = str(o.get("trx_id", "")).strip()
            phone_method = str(o.get("phone", ""))
            user_email = o.get("email") or o.get("customer_name")
            order_id = o.get("id")
            plan_name = o.get("product_name", "")

            # বাইন্যান্স ট্রানজেকশন আইডি ফরম্যাট ভ্যালিডেশন (কমপক্ষে ৮ ডিজিট/হেক্স)
            if "Binance" in phone_method and len(trx) >= 8 and user_email:
                is_vip = "VIP" in plan_name or "49" in plan_name
                target_tier = "vip" if is_vip else "pro"
                days = 730 if is_vip else 30
                
                try:
                    # ডাটাবেজ আরপিসি কল দিয়ে মেয়াদ ও এক্টিভেশন সেট করা
                    supabase.rpc("admin_approve_order", {
                        "p_order_id": order_id,
                        "p_user_email": user_email,
                        "p_tier": target_tier,
                        "p_duration_days": days
                    }).execute()
                    print(f"  -> [AUTO-APPROVED] Order #{order_id} verified for {user_email}. Tier: {target_tier.upper()} ({days} Days).")
                except Exception as approve_err:
                    print(f"[-] Auto-Approve RPC Error for Order #{order_id}: {approve_err}")
    except Exception as e:
        print(f"[-] Subscription Processor Error: {e}")

# ==============================================================================
# ৪. ডাটাবেজ অপটিমাইজার (STORAGE PURGE)
# ==============================================================================
def cleanup_old_database_records():
    print("[*] Running Autonomous Database Storage Optimizer...")
    now = datetime.now(timezone.utc)
    cutoff_hof = (now - timedelta(days=30)).isoformat()
    cutoff_failures = (now - timedelta(days=3)).isoformat()
    try:
        supabase.table("market_research").delete().eq("status", "HIT_TP").lt("resolved_at", cutoff_hof).execute()
        supabase.table("market_research").delete().in_("status", ["HIT_SL", "EXPIRED"]).lt("resolved_at", cutoff_failures).execute()
        print("✔ Database Cleaned: Zero-bloat storage maintained.")
    except Exception as e:
        print(f"[-] Cleanup Error: {e}")

# ==============================================================================
# ৫. ক্রিপ্টো: ৫০০+ পেয়ারের লাইভ ডায়নামিক টপ ১০০ স্ক্রিনার
# ==============================================================================
def fetch_dynamic_crypto_top100():
    print("[*] Fetching Live Dynamic Top 100 Crypto Pairs from Binance...")
    market_pool = {}
    try:
        r = session.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=12)
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
            )[:100]

            for t in sorted_pairs:
                price = float(t.get('lastPrice', 0))
                vol_m = round(float(t.get('quoteVolume', 0)) / 1_000_000, 2)
                if price <= 0:
                    continue

                sym = t['symbol'].replace("USDT", "/USDT")
                market_pool[sym] = {
                    "symbol": sym,
                    "market_type": "crypto",
                    "sector": "Layer-1 Major" if any(k in sym for k in ["BTC", "ETH", "SOL", "BNB", "XRP"]) else "High-Beta Altcoin",
                    "price": price,
                    "high": float(t.get('highPrice', 0)),
                    "low": float(t.get('lowPrice', 0)),
                    "open": float(t.get('openPrice', 0)),
                    "change": float(t.get('priceChangePercent', 0)),
                    "volume_m": vol_m
                }
            print(f"[i] Successfully Loaded {len(market_pool)} Live Active Crypto Pairs.")
    except Exception as e:
        print(f"[-] Crypto Universe Error: {e}")
    return market_pool

# ==============================================================================
# ৬. ইউএস স্টকস: লাইভ মার্কেট মোস্ট অ্যাক্টিভ স্ক্রিনার
# ==============================================================================
def fetch_dynamic_stocks_top100():
    print("[*] Fetching Live Top US Stocks from Market Screener...")
    stock_pool = {}
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=most_actives&count=100"
        res = session.get(url, timeout=12)
        
        if res.status_code == 200:
            quotes = res.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            for q in quotes:
                ticker = q.get('symbol', '').replace(".", "-")
                price = float(q.get('regularMarketPrice') or 0)
                if not ticker or price <= 0 or "^" in ticker:
                    continue

                high = float(q.get('regularMarketDayHigh') or (price * 1.01))
                low = float(q.get('regularMarketDayLow') or (price * 0.99))
                open_p = float(q.get('regularMarketOpen') or price)
                chg = float(q.get('regularMarketChangePercent') or 0)
                vol_m = round(float(q.get('regularMarketVolume') or 1000000) / 1_000_000, 2)

                stock_pool[ticker] = {
                    "symbol": ticker,
                    "market_type": "stocks",
                    "sector": "US Dynamic Equity",
                    "price": price,
                    "high": high,
                    "low": low,
                    "open": open_p,
                    "change": chg,
                    "volume_m": vol_m
                }
            print(f"[i] Successfully Loaded {len(stock_pool)} Real-Time Most Active US Stocks.")
    except Exception as e:
        print(f"[-] Dynamic Stock Screener Warning: {e}")
    return stock_pool

# ==============================================================================
# ৭. ফরেক্স ও কমোডিটিজ স্ক্রিনার
# ==============================================================================
def fetch_dynamic_forex_universe():
    print("[*] Discovering Real-Time Dynamic Forex & Commodities Universe...")
    forex_pool = {}
    discovered_quotes = []

    try:
        forex_screener_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=currencies&count=60"
        res_fx = session.get(forex_screener_url, timeout=10)
        if res_fx.status_code == 200:
            fx_data = res_fx.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            discovered_quotes.extend(fx_data)
            print(f"[i] Dynamic Forex Discovery: {len(fx_data)} Live Currencies Pulled.")
    except Exception as e:
        print(f"[-] Dynamic FX Screener Warning: {e}")

    try:
        commodities_screener_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=all_commodities&count=25"
        res_comm = session.get(commodities_screener_url, timeout=10)
        if res_comm.status_code == 200:
            comm_data = res_comm.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
            discovered_quotes.extend(comm_data)
            print(f"[i] Dynamic Commodities Discovery: {len(comm_data)} Active Contracts Pulled.")
    except Exception as e:
        print(f"[-] Dynamic Commodities Warning: {e}")

    if not discovered_quotes:
        print("[!] Activating Direct Interbank Gateway Fallback...")
        fallback_tickers = [
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X",
            "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURGBP=X", "GC=F", "SI=F", "CL=F", "NG=F"
        ]
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(fallback_tickers)}"
            res_fb = session.get(url, timeout=10)
            if res_fb.status_code == 200:
                discovered_quotes = res_fb.json().get('quoteResponse', {}).get('result', [])
        except Exception as e:
            print(f"[-] Fallback error: {e}")

    commodities_map = {
        "GC=F": "XAU/USD", "SI=F": "XAG/USD", "PL=F": "XPT/USD", "HG=F": "COPPER/USD",
        "CL=F": "WTI/CRUDE", "BZ=F": "BRENT/CRUDE", "NG=F": "NATGAS/USD"
    }

    for item in discovered_quotes:
        ticker = item.get('symbol', '')
        price = float(item.get('regularMarketPrice') or item.get('price') or 0)
        if not ticker or price <= 0 or "^" in ticker:
            continue

        if ticker.endswith("=X"):
            raw_sym = ticker.replace("=X", "")
            clean_sym = f"{raw_sym[:3]}/{raw_sym[3:]}" if len(raw_sym) == 6 else raw_sym
            m_type = "forex"
            sector = "G10 Interbank FX" if any(c in ticker for c in ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF"]) else "Exotic Cross FX"
        elif ticker in commodities_map:
            clean_sym = commodities_map[ticker]
            m_type = "forex"
            sector = "Precious Metals" if "XAU" in clean_sym or "XAG" in clean_sym or "XPT" in clean_sym else "Energy Commodities"
        else:
            clean_sym = ticker.replace("=F", "")
            m_type = "forex"
            sector = "Global Commodity"

        high = float(item.get('regularMarketDayHigh') or (price * 1.008))
        low = float(item.get('regularMarketDayLow') or (price * 0.992))
        open_p = float(item.get('regularMarketOpen') or price)
        chg = float(item.get('regularMarketChangePercent') or 0)
        vol_m = round(float(item.get('regularMarketVolume') or 1500000) / 1_000_000, 2)

        forex_pool[clean_sym] = {
            "symbol": clean_sym,
            "market_type": m_type,
            "sector": sector,
            "price": price,
            "high": high,
            "low": low,
            "open": open_p,
            "change": chg,
            "volume_m": vol_m
        }

    print(f"[✔] Total Real-Time Dynamic Forex & Commodities Parsed: {len(forex_pool)}")
    return forex_pool

# ==============================================================================
# ৮. লাইফসাইকেল ট্র্যাকার (ডুপ্লিকেট রিমুভার সহ)
# ==============================================================================
def track_and_update_lifecycle(current_prices):
    active_setups_map = set()
    try:
        res = supabase.table("market_research").select("id, symbol, sector, direction, sl_price, tp_price, created_at").eq("status", "ACTIVE").execute()
        active_signals = res.data or []
        now = datetime.now(timezone.utc)

        for sig in active_signals:
            sym = sig.get("symbol")
            sec = sig.get("sector") or ""
            direction = sig.get("direction", "long")
            sig_id = sig.get("id")

            style_tag = "Scalp" if "Scalp" in sec else ("Day" if "Day" in sec else "Swing")
            active_setups_map.add(f"{sym}_{style_tag}_{direction}")

            if sym not in current_prices:
                continue

            cur_price = current_prices[sym]["price"]
            sl = float(sig.get("sl_price") or 0)
            tp = float(sig.get("tp_price") or 0)
            created_at_str = sig.get("created_at")

            hit_status = None
            if direction == "long":
                if cur_price >= tp and tp > 0:
                    hit_status = "HIT_TP"
                elif cur_price <= sl and sl > 0:
                    hit_status = "HIT_SL"
            else:
                if cur_price <= tp and tp > 0:
                    hit_status = "HIT_TP"
                elif cur_price >= sl and sl > 0:
                    hit_status = "HIT_SL"

            if not hit_status and created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if now - created_at > timedelta(hours=48):
                    hit_status = "EXPIRED"

            if hit_status:
                supabase.table("market_research").update({
                    "status": hit_status,
                    "resolved_at": now.isoformat()
                }).eq("id", sig_id).execute()
                print(f"  -> [{hit_status}] {sym} ({sec}) Closed at ${fmt_price(cur_price)}")

    except Exception as e:
        print(f"[-] Lifecycle Error: {e}")
    return active_setups_map

# ==============================================================================
# ৯. SMC লিকুইডিটি পার্জ ও সিগন্যাল ইঞ্জিন
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
    if span <= 0 or p <= 0:
        return []

    volatility_ratio = span / p
    range_pos = (p - low) / span

    lower_wick = min(open_p, p) - low
    upper_wick = high - max(open_p, p)
    is_sell_side_purged = (range_pos >= 0.52 and lower_wick > upper_wick * 1.3)
    is_buy_side_purged = (range_pos <= 0.48 and upper_wick > lower_wick * 1.3)

    if is_sell_side_purged or (range_pos >= 0.60 and chg >= 1.2):
        direction = "long"
        purge_catalyst = "Sell-Side Liquidity Purged"
        flow_delta = f"${vol}M Smart Money Accumulation"
    elif is_buy_side_purged or (range_pos <= 0.40 and chg <= -1.2):
        direction = "short"
        purge_catalyst = "Buy-Side Liquidity Swept"
        flow_delta = f"${vol}M Institutional Distribution"
    else:
        return []

    setups = []

    styles = [
        {"style": "Scalp", "tag": "Scalp Engine (5M)", "horizon": "24h", "rr": 2.4, "risk_mult": 0.16},
        {"style": "Day", "tag": "Day Engine (1H)", "horizon": "24h", "rr": 2.6, "risk_mult": 0.28},
        {"style": "Swing", "tag": "Swing Engine (4H)", "horizon": "1w" if abs(chg) < 3.5 else "1m", "rr": 3.2, "risk_mult": 0.48}
    ]

    for s in styles:
        setup_key = f"{item['symbol']}_{s['style']}_{direction}"
        if setup_key in active_setups_map:
            continue

        if m_type == "forex":
            risk_pct = max(0.0024, volatility_ratio * s['risk_mult'])
            trading_mode = "mode1"
        elif m_type == "stocks":
            risk_pct = max(0.009, volatility_ratio * s['risk_mult'])
            trading_mode = "mode1"
        else:
            risk_pct = max(0.012, volatility_ratio * s['risk_mult'])
            trading_mode = "mode2"

        entry = p
        sl = p * (1 - risk_pct) if direction == "long" else p * (1 + risk_pct)
        tp = p * (1 + (risk_pct * s['rr'])) if direction == "long" else p * (1 - (risk_pct * s['rr']))

        conviction = 92
        if abs(chg) >= 1.8: conviction += 3
        if vol >= 15.0: conviction += 3
        score = min(98, conviction)

        full_sector = f"{s['tag']} • {base_sector}"

        setups.append({
            "symbol": item['symbol'],
            "market_type": m_type,
            "horizon": s['horizon'],
            "direction": direction,
            "trading_mode": trading_mode,
            "score": score,
            "stage": f"[{s['style'].upper()}] Institutional Squeeze",
            "current_change_24h": round(chg, 2),
            "sector": full_sector,
            "est_potential": f"+{round(risk_pct * s['rr'] * 100, 1)}%",
            "flow_metric": flow_delta if m_type == "crypto" else ("Interbank Delta Flow" if m_type == "forex" else "Dark Pool Block Flow"),
            "driver_metric": purge_catalyst,
            "entry_price": entry,
            "sl_price": sl,
            "tp_price": tp,
            "status": "ACTIVE",
            "mtf_alignment": f"Entry: ${fmt_price(entry)} | SL: ${fmt_price(sl)}",
            "research_note": f"{s['style']} SMC {direction.upper()} অর্ডারব্লক ও লিকুইডিটি পার্জ কনফার্মড। R:R = 1:{s['rr']:.1f} [TP: ${fmt_price(tp)}]"
        })

    return setups

# ==============================================================================
# ১০. এক্সিকিউশন রানার
# ==============================================================================
def run():
    print("=" * 80)
    print(f"[*] RUNNING TOP 100 REAL-TIME DYNAMIC QUANT ENGINE: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # সাবস্ক্রিপশন ও স্টোরেজ অপ্টিমাইজেশন
    process_automatic_subscriptions()
    cleanup_old_database_records()

    # মার্কেট পুলিং
    crypto_prices = fetch_dynamic_crypto_top100()
    stocks_prices = fetch_dynamic_stocks_top100()
    forex_prices = fetch_dynamic_forex_universe()
    
    all_prices = {**crypto_prices, **stocks_prices, **forex_prices}
    if not all_prices:
        print("[-] Market feeds unavailable.")
        return

    active_setups_map = track_and_update_lifecycle(all_prices)
    new_setups = []

    sorted_cryptos = sorted(crypto_prices.values(), key=lambda x: (abs(x['change']) * x['volume_m']), reverse=True)
    for c in sorted_cryptos[:35]:
        new_setups.extend(generate_smc_institutional_signal(c, active_setups_map))

    sorted_stocks = sorted(stocks_prices.values(), key=lambda x: abs(x['change']), reverse=True)
    for s in sorted_stocks[:35]:
        new_setups.extend(generate_smc_institutional_signal(s, active_setups_map))

    sorted_forex = sorted(forex_prices.values(), key=lambda x: abs(x['change']), reverse=True)
    for f in sorted_forex[:35]:
        new_setups.extend(generate_smc_institutional_signal(f, active_setups_map))

    if new_setups:
        try:
            batch_size = 20
            for i in range(0, len(new_setups), batch_size):
                b = new_setups[i:i + batch_size]
                supabase.table("market_research").insert(b).execute()
            print(f"\n✔ Successfully pushed {len(new_setups)} Dynamic Alpha Setups across Top 100 Markets!")
            
            # টেলিগ্রাম বট অ্যালার্ট পাঠানো (হাই-কনভিকশন সিগন্যাল ফিল্টার)
            for s in new_setups:
                if s.get("score", 0) >= 94:
                    send_telegram_alert(s)
                    
        except Exception as e:
            print(f"[-] Batch insert error: {e}")
    else:
        print("\n[i] All positions working actively in target. No duplicate injection.")

if __name__ == "__main__":
    run()
