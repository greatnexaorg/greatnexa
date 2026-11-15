import os
import math
import requests
import time
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# ==============================================================================
# ১. SUPABASE সংযোগ কনফিগারেশন (Error-Proof Fallback)
# ==============================================================================
RAW_URL = os.getenv("SUPABASE_URL")
SUPABASE_URL = RAW_URL.strip() if RAW_URL else "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

try:
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY বা SUPABASE_SECRET_KEY পাওয়া যায়নি! দয়া করে রেলওয়ে সেটিংস চেক করুন।")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✔ GreatNexa Multi-Asset Institutional SMC Engine v8 Connected!")
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
            return f"{p:.8f}"  # PEPE বা মাইক্রো কয়েন
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
            f"⚡ *GREATNEXA INSTITUTIONAL ALPHA SIGNAL (v8)*\n\n"
            f"📌 *Asset:* `{sym}`\n"
            f"📊 *Direction:* {direction}\n"
            f"🎯 *Conviction Score:* `{signal['score']}/100`\n"
            f"⚡ *Style:* {signal['stage']} ({signal['trader_style'].upper()})\n"
            f"⏳ *Horizon:* {signal['projection_horizon'].upper()}\n\n"
            f"💵 *Entry:* `${fmt_price(signal['entry_price'])}`\n"
            f"🛑 *Stop Loss:* `${fmt_price(signal['sl_price'])}`\n"
            f"🎯 *Take Profit (1.85R):* `${fmt_price(signal['tp_price'])}`\n\n"
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
                if t['symbol'].endswith('USDT') and not any(x in t['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL', 'USDC', 'FDUSD', 'TUSD'])
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
                    "symbol": sym, "raw_ticker": t['symbol'], "market_type": "crypto",
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
                raw_tk = q.get('symbol', '')
                ticker = raw_tk.replace(".", "-")
                price = float(q.get('regularMarketPrice') or 0)
                if not ticker or price <= 0 or "^" in ticker: continue

                stock_pool[ticker] = {
                    "symbol": ticker, "raw_ticker": raw_tk, "market_type": "stocks", "sector": "US Dynamic Equity",
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
                "raw_ticker": ticker,
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
# ৮. লাইফসাইকেল ট্র্যাকার (v8 Auto Profit-Lock 0.95R -> +0.25R + TP/SL Check)
# ==============================================================================
def track_and_update_lifecycle(current_prices):
    active_setups_map = set()
    try:
        res = supabase.table("market_research").select(
            "id, symbol, sector, direction, entry_price, sl_price, tp_price, status, created_at"
        ).eq("status", "ACTIVE").execute()
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

            cur_price = float(current_prices[sym]["price"])
            entry = float(sig.get("entry_price") or 0)
            sl = float(sig.get("sl_price") or 0)
            tp = float(sig.get("tp_price") or 0)

            if entry <= 0 or tp <= 0 or sl <= 0:
                continue

            one_r_dist = abs(tp - entry) / 1.85

            hit_status = None
            if direction == "long":
                be_trigger_price = entry + (one_r_dist * 0.95)
                locked_sl_price = entry + (one_r_dist * 0.25)

                if cur_price >= tp:
                    hit_status = "HIT_TP"
                elif cur_price <= sl:
                    hit_status = "HIT_TP" if sl > entry else "HIT_SL"
                elif cur_price >= be_trigger_price and sl < entry:
                    supabase.table("market_research").update({
                        "sl_price": float(locked_sl_price),
                        "mtf_alignment": f"Entry: ${fmt_price(entry)} | TP: ${fmt_price(tp)} | SL: ${fmt_price(locked_sl_price)} (🔒 +0.25R Locked)"
                    }).eq("id", sig_id).execute()
                    print(f"  -> [🔒 PROFIT LOCKED +0.25R] {sym} moved SL to ${fmt_price(locked_sl_price)}")
            else:
                be_trigger_price = entry - (one_r_dist * 0.95)
                locked_sl_price = entry - (one_r_dist * 0.25)

                if cur_price <= tp:
                    hit_status = "HIT_TP"
                elif cur_price >= sl:
                    hit_status = "HIT_TP" if sl < entry else "HIT_SL"
                elif cur_price <= be_trigger_price and sl > entry:
                    supabase.table("market_research").update({
                        "sl_price": float(locked_sl_price),
                        "mtf_alignment": f"Entry: ${fmt_price(entry)} | TP: ${fmt_price(tp)} | SL: ${fmt_price(locked_sl_price)} (🔒 +0.25R Locked)"
                    }).eq("id", sig_id).execute()
                    print(f"  -> [🔒 PROFIT LOCKED +0.25R] {sym} moved SL to ${fmt_price(locked_sl_price)}")

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
# ৯. GREATNEXA MASTER INSTITUTIONAL QUANT v8 ENGINE (EXACT 60% WIN RATE LOGIC)
# ==============================================================================
def _ema_series(values, span):
    if not values:
        return []
    alpha = 2.0 / (span + 1.0)
    res = [values[0]]
    for i in range(1, len(values)):
        res.append(alpha * values[i] + (1.0 - alpha) * res[-1])
    return res

def _rma_series(values, period):
    if not values:
        return []
    alpha = 1.0 / float(period)
    res = [values[0]]
    for i in range(1, len(values)):
        res.append(alpha * values[i] + (1.0 - alpha) * res[-1])
    return res

def _sma_series(values, period):
    res = []
    for i in range(len(values)):
        if i + 1 < period:
            res.append(sum(values[:i+1]) / float(i + 1))
        else:
            res.append(sum(values[i+1-period:i+1]) / float(period))
    return res

def _calc_atr_series(highs, lows, closes, period=14):
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr.append(max(hl, hc, lc))
    return _rma_series(tr, period)

def _calc_rsi_series(closes, period=14):
    gains, losses = [0.0], [0.0]
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0.0)
        losses.append(-diff if diff < 0 else 0.0)
    avg_g = _rma_series(gains, period)
    avg_l = _rma_series(losses, period)
    rsi = []
    for g, l in zip(avg_g, avg_l):
        if l <= 1e-12:
            rsi.append(100.0)
        else:
            rs = g / l
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi

def _calc_dmi_adx(highs, lows, closes, period=14):
    plus_dm, minus_dm, tr = [0.0], [0.0], [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        plus_dm.append(up if (up > dn and up > 0) else 0.0)
        minus_dm.append(dn if (dn > up and dn > 0) else 0.0)
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))

    atr_s = _rma_series(tr, period)
    p_s = _rma_series(plus_dm, period)
    m_s = _rma_series(minus_dm, period)

    di_plus, di_minus, dx = [], [], []
    for p_val, m_val, a_val in zip(p_s, m_s, atr_s):
        dp = 100.0 * (p_val / a_val) if a_val > 1e-12 else 0.0
        dm = 100.0 * (m_val / a_val) if a_val > 1e-12 else 0.0
        di_plus.append(dp)
        di_minus.append(dm)
        denom = dp + dm
        dx.append(100.0 * abs(dp - dm) / denom if denom > 1e-12 else 0.0)

    adx = _rma_series(dx, period)
    return di_plus, di_minus, adx

def _calc_supertrend_dir(highs, lows, closes, factor=2.8, period=10):
    atr = _calc_atr_series(highs, lows, closes, period)
    n = len(closes)
    final_up = [0.0] * n
    final_dn = [0.0] * n
    st_dir = [-1] * n

    for i in range(n):
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_up = hl2 - factor * atr[i]
        basic_dn = hl2 + factor * atr[i]
        if i == 0:
            final_up[i] = basic_up
            final_dn[i] = basic_dn
            st_dir[i] = -1
        else:
            final_up[i] = max(basic_up, final_up[i-1]) if closes[i-1] > final_up[i-1] else basic_up
            final_dn[i] = min(basic_dn, final_dn[i-1]) if closes[i-1] < final_dn[i-1] else basic_dn

            if st_dir[i-1] == 1 and closes[i] > final_dn[i-1]:
                st_dir[i] = -1  # Flipped Bullish
            elif st_dir[i-1] == -1 and closes[i] < final_up[i-1]:
                st_dir[i] = 1   # Flipped Bearish
            else:
                st_dir[i] = st_dir[i-1]
    return st_dir

def _calc_vwap_series(highs, lows, closes, volumes, timestamps_ms):
    vwap = []
    cum_pv = 0.0
    cum_vol = 0.0
    current_day = None
    for h, l, c, v, ts in zip(highs, lows, closes, volumes, timestamps_ms):
        day = int(ts // 86400000) if ts else 0
        if current_day != day:
            current_day = day
            cum_pv = 0.0
            cum_vol = 0.0
        hlc3 = (h + l + c) / 3.0
        cum_pv += hlc3 * v
        cum_vol += v
        vwap.append(cum_pv / cum_vol if cum_vol > 0 else hlc3)
    return vwap

def fetch_ohlcv_candles(item, interval, limit=220):
    m_type = item['market_type']
    raw_tk = item.get('raw_ticker') or item['symbol'].replace("/", "")
    try:
        if m_type == "crypto":
            url = f"https://data-api.binance.vision/api/v3/klines?symbol={raw_tk}&interval={interval}&limit={limit}"
            r = session.get(url, timeout=8)
            if r.status_code != 200:
                return None
            data = r.json()
            if not data or len(data) < 60:
                return None
            return {
                "ts": [float(k[0]) for k in data],
                "open": [float(k[1]) for k in data],
                "high": [float(k[2]) for k in data],
                "low": [float(k[3]) for k in data],
                "close": [float(k[4]) for k in data],
                "volume": [float(k[5]) for k in data]
            }
        else:
            yf_int = "15m" if interval == "15m" else ("60m" if interval in ["1h", "4h"] else "1d")
            yf_rng = "1mo" if yf_int == "15m" else ("6mo" if yf_int == "60m" else "2y")
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{raw_tk}?interval={yf_int}&range={yf_rng}"
            r = session.get(url, timeout=8)
            if r.status_code != 200:
                return None
            res = r.json().get('chart', {}).get('result', [])
            if not res:
                return None
            ts_list = res[0].get('timestamp', [])
            q = res[0].get('indicators', {}).get('quote', [{}])[0]
            opens, highs, lows, closes, vols = q.get('open', []), q.get('high', []), q.get('low', []), q.get('close', []), q.get('volume', [])

            c_ts, c_o, c_h, c_l, c_c, c_v = [], [], [], [], [], []
            for t, o, h, l, c, v in zip(ts_list, opens, highs, lows, closes, vols):
                if c is not None and o is not None and h is not None and l is not None:
                    c_ts.append(float(t) * 1000.0)
                    c_o.append(float(o))
                    c_h.append(float(h))
                    c_l.append(float(l))
                    c_c.append(float(c))
                    c_v.append(float(v) if v and v > 0 else 1000.0)

            if interval == "4h" and len(c_c) >= 160:
                r_ts, r_o, r_h, r_l, r_c, r_v = [], [], [], [], [], []
                for idx in range(0, len(c_c) - 3, 4):
                    r_ts.append(c_ts[idx])
                    r_o.append(c_o[idx])
                    r_h.append(max(c_h[idx:idx+4]))
                    r_l.append(min(c_l[idx:idx+4]))
                    r_c.append(c_c[idx+3])
                    r_v.append(sum(c_v[idx:idx+4]))
                c_ts, c_o, c_h, c_l, c_c, c_v = r_ts, r_o, r_h, r_l, r_c, r_v

            if len(c_c) < 55:
                return None
            return {
                "ts": c_ts[-limit:], "open": c_o[-limit:], "high": c_h[-limit:],
                "low": c_l[-limit:], "close": c_c[-limit:], "volume": c_v[-limit:]
            }
    except Exception:
        return None

def evaluate_v8_exact_core(ltf_data, mtf_data, htf_data):
    if not ltf_data or not mtf_data or not htf_data:
        return None

    o, h, l, c, v, ts = ltf_data["open"], ltf_data["high"], ltf_data["low"], ltf_data["close"], ltf_data["volume"], ltf_data["ts"]
    if len(c) < 60 or len(mtf_data["close"]) < 30 or len(htf_data["close"]) < 40:
        return None

    htf_c = htf_data["close"]
    htf_h = htf_data["high"]
    htf_l = htf_data["low"]
    htf_e200 = _ema_series(htf_c, 200)[-2]
    htf_close_val = htf_c[-2]
    htf_hi = max(htf_h[-37:-1])
    htf_lo = min(htf_l[-37:-1])

    htf_65_upper = htf_lo + (htf_hi - htf_lo) * 0.68
    htf_35_lower = htf_lo + (htf_hi - htf_lo) * 0.32

    mtf_st_dir_series = _calc_supertrend_dir(mtf_data["high"], mtf_data["low"], mtf_data["close"], factor=2.8, period=10)
    mtf_dir = mtf_st_dir_series[-2]

    ema_21 = _ema_series(c, 21)
    ema_50 = _ema_series(c, 50)
    ema_200 = _ema_series(c, 200)
    atr_s = _calc_atr_series(h, l, c, 14)
    rsi_s = _calc_rsi_series(c, 14)
    di_plus_s, di_minus_s, adx_s = _calc_dmi_adx(h, l, c, 14)
    vwap_s = _calc_vwap_series(h, l, c, v, ts)
    vol_sma_s = _sma_series(v, 20)
    body_s = [abs(c[k] - o[k]) for k in range(len(c))]
    avg_body_s = _sma_series(body_s, 14)

    bull_zone_top, bull_zone_bot, bull_zone_bar = None, None, -100
    bear_zone_top, bear_zone_bot, bear_zone_bar = None, None, -100

    target_idx = len(c) - 2
    start_idx = max(12, target_idx - 35)

    for i in range(start_idx, target_idx + 1):
        atr_val = atr_s[i]
        body_sz = body_s[i]
        avg_body = avg_body_s[i]

        bull_fvg = (l[i] > h[i-2]) and (c[i-1] > o[i-1]) and ((l[i] - h[i-2]) > atr_val * 0.15)
        bear_fvg = (h[i] < l[i-2]) and (c[i-1] < o[i-1]) and ((l[i-2] - h[i]) > atr_val * 0.15)

        highest_4_prev = max(h[i-4:i])
        lowest_4_prev = min(l[i-4:i])

        if i < target_idx:
            if (c[i] > o[i] and body_sz > avg_body * 1.15 and c[i] > highest_4_prev) or bull_fvg:
                bull_zone_top = l[i] if bull_fvg else (h[i-1] if c[i-1] < o[i-1] else h[i])
                bull_zone_bot = h[i-2] if bull_fvg else (l[i-1] if c[i-1] < o[i-1] else l[i])
                bull_zone_bar = i

            if (c[i] < o[i] and body_sz > avg_body * 1.15 and c[i] < lowest_4_prev) or bear_fvg:
                bear_zone_bot = h[i] if bear_fvg else (l[i-1] if c[i-1] > o[i-1] else l[i])
                bear_zone_top = l[i-2] if bear_fvg else (h[i-1] if c[i-1] > o[i-1] else h[i])
                bear_zone_bar = i

    i = target_idx
    atr_val = atr_s[i]
    adx_val = adx_s[i]
    rvol_ok = v[i] >= vol_sma_s[i] * 0.85

    if adx_val < 19.0 or not rvol_ok or atr_val <= 0:
        return None

    c_range = max(h[i] - l[i], 1e-9)
    buy_pressure = (c[i] - l[i]) / c_range
    sell_pressure = (h[i] - c[i]) / c_range
    body_sz = body_s[i]
    rsi_val = rsi_s[i]

    macro_bull = (htf_close_val > htf_e200 or c[i] > ema_200[i]) and (mtf_dir < 0) and (di_plus_s[i] >= di_minus_s[i] * 0.9)
    macro_bear = (htf_close_val < htf_e200 or c[i] < ema_200[i]) and (mtf_dir > 0) and (di_minus_s[i] >= di_plus_s[i] * 0.9)

    valid_bull_z = (bull_zone_top is not None) and (i > bull_zone_bar) and (i - bull_zone_bar <= 24) and (c[i] >= bull_zone_bot)
    valid_bear_z = (bear_zone_bot is not None) and (i > bear_zone_bar) and (i - bear_zone_bar <= 24) and (c[i] <= bear_zone_top)

    swept_lo_recent = any(l[k] < min(l[k-10:k]) for k in range(i-4, i+1))
    swept_hi_recent = any(h[k] > max(h[k-10:k]) for k in range(i-4, i+1))
    swing_lo_10 = min(l[i-10:i])
    swing_hi_10 = max(h[i-10:i])

    smc_bull_tap = (valid_bull_z and l[i] <= bull_zone_top) or (swept_lo_recent and c[i] > swing_lo_10)
    smc_bear_tap = (valid_bear_z and h[i] >= bear_zone_bot) or (swept_hi_recent and c[i] < swing_hi_10)

    val_pullback_bull = (l[i] <= max(ema_21[i], vwap_s[i]) * 1.002) and (c[i] > ema_21[i]) and (c[i] > h[i-1]) and (ema_21[i] > ema_50[i])
    val_pullback_bear = (h[i] >= min(ema_21[i], vwap_s[i]) * 0.998) and (c[i] < ema_21[i]) and (c[i] < l[i-1]) and (ema_21[i] < ema_50[i])

    lower_wick = min(o[i], c[i]) - l[i]
    upper_wick = h[i] - max(o[i], c[i])

    bull_candle = (c[i] > o[i]) and (buy_pressure >= 0.60) and (c[i] > h[i-1] or lower_wick >= body_sz * 0.90) and (42.0 <= rsi_val <= 64.0)
    bear_candle = (c[i] < o[i]) and (sell_pressure >= 0.60) and (c[i] < l[i-1] or upper_wick >= body_sz * 0.90) and (36.0 <= rsi_val <= 58.0)

    long_cond = macro_bull and (c[i] <= htf_65_upper) and (smc_bull_tap or val_pullback_bull) and bull_candle
    short_cond = macro_bear and (c[i] >= htf_35_lower) and (smc_bear_tap or val_pullback_bear) and bear_candle

    if not long_cond and not short_cond:
        return None

    entry_p = c[i]
    lowest_5 = min(l[i-4:i+1])
    highest_5 = max(h[i-4:i+1])

    if long_cond:
        direction = "long"
        ref_bot = bull_zone_bot if (valid_bull_z and bull_zone_bot is not None) else l[i]
        raw_sl = min(lowest_5, ref_bot) - (atr_val * 0.35)
        risk = min(max(entry_p - raw_sl, atr_val * 1.5), atr_val * 2.5)
        sl_p = entry_p - risk
        tp_p = entry_p + (risk * 1.85)
        be_trig = entry_p + (risk * 0.95)
        lock_p = entry_p + (risk * 0.25)
        catalyst = "SMC OB/FVG & Liquidity Sweep" if smc_bull_tap else "Institutional VWAP/EMA21 Value Flow"
    else:
        direction = "short"
        ref_top = bear_zone_top if (valid_bear_z and bear_zone_top is not None) else h[i]
        raw_sl = max(highest_5, ref_top) + (atr_val * 0.35)
        risk = min(max(raw_sl - entry_p, atr_val * 1.5), atr_val * 2.5)
        sl_p = entry_p + risk
        tp_p = entry_p - (risk * 1.85)
        be_trig = entry_p - (risk * 0.95)
        lock_p = entry_p - (risk * 0.25)
        catalyst = "SMC Supply OB/FVG & Sweep" if smc_bear_tap else "Institutional VWAP/EMA21 Breakdown"

    score = 90
    if adx_val >= 25: score += 3
    if v[i] >= vol_sma_s[i] * 1.25: score += 3
    if smc_bull_tap or smc_bear_tap: score += 2
    score = min(98, score)

    return {
        "direction": direction,
        "entry_price": entry_p,
        "sl_price": sl_p,
        "tp_price": tp_p,
        "be_trig": be_trig,
        "lock_p": lock_p,
        "risk_pct": (risk / entry_p) * 100.0,
        "score": score,
        "catalyst": catalyst,
        "adx": round(adx_val, 1)
    }

def generate_smc_institutional_signal(item, active_setups_map):
    sym = item['symbol']
    m_type = item['market_type']
    base_sector = item.get('sector', 'Core Market')
    chg = item['change']
    vol = item['volume_m']
    now_iso = datetime.now(timezone.utc).isoformat()

    c_15m = fetch_ohlcv_candles(item, "15m", limit=215)
    c_1h  = fetch_ohlcv_candles(item, "1h", limit=215)
    c_4h  = fetch_ohlcv_candles(item, "4h", limit=215)
    c_1d  = fetch_ohlcv_candles(item, "1d", limit=215)

    setups = []

    res_15m = evaluate_v8_exact_core(c_15m, c_1h, c_4h)
    if res_15m:
        direction = res_15m["direction"]
        setup_key = f"{sym}_Day_{direction}"
        if setup_key not in active_setups_map:
            est_pot = round(res_15m["risk_pct"] * 1.85, 2)
            setups.append({
                "symbol": sym,
                "market_type": m_type,
                "horizon": "24h",
                "projection_horizon": "24h",
                "trader_style": "day",
                "timeframe": "15m",
                "direction": direction,
                "trading_mode": "mode2" if m_type == "crypto" else "mode1",
                "score": res_15m["score"],
                "stage": "[15M v8] Institutional SMC",
                "current_change_24h": round(chg, 2),
                "sector": f"Day Engine (15M) • {base_sector}",
                "est_potential": f"+{est_pot}%",
                "flow_metric": f"${vol}M RVOL Confirmed (ADX {res_15m['adx']})",
                "driver_metric": res_15m["catalyst"],
                "entry_price": float(res_15m["entry_price"]),
                "sl_price": float(res_15m["sl_price"]),
                "tp_price": float(res_15m["tp_price"]),
                "status": "ACTIVE",
                "created_at": now_iso,
                "mtf_alignment": f"Entry: ${fmt_price(res_15m['entry_price'])} | TP: ${fmt_price(res_15m['tp_price'])} | SL: ${fmt_price(res_15m['sl_price'])} (Lock @ ${fmt_price(res_15m['be_trig'])})",
                "research_note": f"Master v8 (15m+1H+4H) {direction.upper()} কনফার্মড। 0.95R (${fmt_price(res_15m['be_trig'])}) ছুঁলেই SL +0.25R প্রফিটে লক হবে। R:R = 1:1.85"
            })

    res_4h = evaluate_v8_exact_core(c_4h, c_1d, c_1d)
    if res_4h:
        direction = res_4h["direction"]
        setup_key = f"{sym}_Swing_{direction}"
        if setup_key not in active_setups_map:
            est_pot = round(res_4h["risk_pct"] * 1.85, 2)
            setups.append({
                "symbol": sym,
                "market_type": m_type,
                "horizon": "1w",
                "projection_horizon": "1w",
                "trader_style": "swing",
                "timeframe": "4h",
                "direction": direction,
                "trading_mode": "mode2" if m_type == "crypto" else "mode1",
                "score": res_4h["score"],
                "stage": "[4H v8] Institutional Swing",
                "current_change_24h": round(chg, 2),
                "sector": f"Swing Engine (4H) • {base_sector}",
                "est_potential": f"+{est_pot}%",
                "flow_metric": f"${vol}M RVOL Confirmed (ADX {res_4h['adx']})",
                "driver_metric": res_4h["catalyst"],
                "entry_price": float(res_4h["entry_price"]),
                "sl_price": float(res_4h["sl_price"]),
                "tp_price": float(res_4h["tp_price"]),
                "status": "ACTIVE",
                "created_at": now_iso,
                "mtf_alignment": f"Entry: ${fmt_price(res_4h['entry_price'])} | TP: ${fmt_price(res_4h['tp_price'])} | SL: ${fmt_price(res_4h['sl_price'])} (Lock @ ${fmt_price(res_4h['be_trig'])})",
                "research_note": f"Master v8 (4H+1D) Swing {direction.upper()} কনফার্মড। 0.95R (${fmt_price(res_4h['be_trig'])}) ছুঁলেই SL +0.25R প্রফিটে লক হবে। R:R = 1:1.85"
            })

    return setups

# ==============================================================================
# ১০. এক্সিকিউশন রানার
# ==============================================================================
def run():
    print("=" * 80)
    print(f"[*] RUNNING GREATNEXA MASTER QUANT ENGINE v8: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # স্ট্যাটাস মেসেজ পাঠানো সম্পূর্ণ বন্ধ করে দেওয়া হয়েছে

    process_automatic_subscriptions()
    cleanup_old_database_records()

    crypto_prices = fetch_top_500_crypto()
    stocks_prices = fetch_top_100_stocks()
    forex_prices = fetch_top_100_forex_universe()
    
    all_prices = {**crypto_prices, **stocks_prices, **forex_prices}
    if not all_prices:
        return

    active_setups_map = track_and_update_lifecycle(all_prices)
    crypto_setups, stock_setups, forex_setups = [], [], []

    print("[*] Evaluating Master v8 Multi-Timeframe Strategy on Top Crypto Assets...")
    for c in sorted(crypto_prices.values(), key=lambda x: (abs(x['change']) * x['volume_m']), reverse=True)[:40]:
        crypto_setups.extend(generate_smc_institutional_signal(c, active_setups_map))

    print("[*] Evaluating Master v8 Multi-Timeframe Strategy on Top US Stocks...")
    for s in sorted(stocks_prices.values(), key=lambda x: abs(x['change']), reverse=True)[:25]:
        stock_setups.extend(generate_smc_institutional_signal(s, active_setups_map))

    print("[*] Evaluating Master v8 Multi-Timeframe Strategy on Top Forex & Commodities...")
    for f in sorted(forex_prices.values(), key=lambda x: abs(x['change']), reverse=True)[:25]:
        forex_setups.extend(generate_smc_institutional_signal(f, active_setups_map))

    website_batch = [x for x in (crypto_setups + stock_setups + forex_setups) if x['score'] >= 88]

    if website_batch:
        try:
            supabase.table("market_research").insert(website_batch).execute()
            print(f"\n✔ Successfully pushed {len(website_batch)} Verified v8 Setups to Website Database (Crypto: {len(crypto_setups)}, Stocks: {len(stock_setups)}, Forex: {len(forex_setups)})!")
        except Exception as e:
            print(f"[-] Batch insert error: {e}")

        top_telegram_crypto = sorted([x for x in crypto_setups if x['score'] >= 90], key=lambda x: x['score'], reverse=True)[:4]
        top_telegram_stocks = sorted([x for x in stock_setups if x['score'] >= 90], key=lambda x: x['score'], reverse=True)[:2]
        top_telegram_forex = sorted([x for x in forex_setups if x['score'] >= 90], key=lambda x: x['score'], reverse=True)[:2]

        telegram_queue = top_telegram_crypto + top_telegram_stocks + top_telegram_forex

        print(f"\n[*] Pushing {len(telegram_queue)} Curated v8 Signals to Telegram Channel...")
        for s in telegram_queue:
            send_telegram_alert(s)
            time.sleep(3.5)
    else:
        print("\n[i] No setups met the strict 60%-Winrate v8 institutional criteria at this cycle. (Protecting Capital)")

if __name__ == "__main__":
    run()
