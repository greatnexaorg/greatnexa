import os
import requests
import numpy as np
from supabase import create_client, Client

# Supabase Credentials (Environment Variable থেকে নেওয়া নিরাপদ, অন্যথায় ডিফল্ট কী কাজ করবে)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://esqhansnosejkqapuhoo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_dpCpv8gKC1oPYhupcZmU8w_8Yu6mC9Z")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def get_open_interest_delta(symbol):
    """গত ৪ ঘণ্টায় ওপেন ইন্টারেস্ট (OI) কতটা বেড়েছে তা ক্যালকুলেট করে"""
    try:
        url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=1h&limit=5"
        res = requests.get(url, headers=HEADERS, timeout=8).json()
        if isinstance(res, list) and len(res) >= 4:
            initial_oi = float(res[0]['sumOpenInterestValue'])
            current_oi = float(res[-1]['sumOpenInterestValue'])
            if initial_oi > 0:
                oi_change = ((current_oi - initial_oi) / initial_oi) * 100
                return round(oi_change, 2)
    except Exception:
        pass
    return 0.0

def run_institutional_scanner():
    print("Initiating Institutional Grade Pre-Pump & Smart Money Scanner...")

    # ১. ফিউচার্স ও স্পট ২৪ ঘণ্টার মার্কেট স্ট্যাটস এবং ফান্ডিং রেট ফেচ
    try:
        futures_ticker_res = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", headers=HEADERS, timeout=12)
        if futures_ticker_res.status_code == 200:
            tickers = futures_ticker_res.json()
        else:
            ticker_res = requests.get("https://api.binance.com/api/v3/ticker/24hr", headers=HEADERS, timeout=12)
            tickers = ticker_res.json()

        premium_res = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex", headers=HEADERS, timeout=12).json()
        funding_dict = {item['symbol']: float(item['lastFundingRate']) for item in premium_res if 'symbol' in item}
    except Exception as e:
        print(f"Error fetching foundational market data: {e}")
        return

    screened_candidates = []

    # ২. ফিল্টারিং ফিল্টার: জাঙ্ক বা অতি উচ্চ ভোলাটিলিটি বাদ দিয়ে সম্ভাব্য অ্যাকুমুলেশন বাছাই
    for t in tickers:
        symbol = t.get('symbol', '')
        if not symbol.endswith('USDT') or symbol in ['BTCUSDT', 'ETHUSDT', 'USDCUSDT', 'FDUSDUSDT']:
            continue

        try:
            quote_vol = float(t.get('quoteVolume', 0))
            price_change = float(t.get('priceChangePercent', 0))
        except (ValueError, TypeError):
            continue

        # লিকুইডিটি ফিল্টার: ন্যূনতম $১০ মিলিয়ন ভলিউম এবং দাম এখনও ২০% এর বেশি পাম্প করেনি
        if quote_vol < 10_000_000 or price_change > 14.0 or price_change < -8.0:
            continue

        # ৩. 1H ক্যান্ডেল ডেটা ফেচ (ভলিউম ডেল্টা, টেকার বাই রেশিও ও বলিঞ্জার ব্যান্ড কম্প্রেশন)
        try:
            klines = requests.get(
                f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=24", 
                headers=HEADERS, 
                timeout=8
            ).json()
            if not isinstance(klines, list) or len(klines) < 24:
                continue
        except Exception:
            continue

        closes = np.array([float(k[4]) for k in klines])
        vols = np.array([float(k[7]) for k in klines])           # Quote Asset Volume
        taker_buys = np.array([float(k[10]) for k in klines])     # Taker Buy Quote Asset Volume

        # ৪. ভলিউম ভেলোসিটি ও স্মার্ট মানি ডেল্টা ক্যালকুলেশন
        recent_3h_vol = np.mean(vols[-3:])
        base_vol = np.mean(vols[:-3]) + 1e-9
        volume_spike = recent_3h_vol / base_vol

        recent_buys = np.sum(taker_buys[-4:])
        recent_total_vol = np.sum(vols[-4:]) + 1e-9
        taker_buy_percentage = (recent_buys / recent_total_vol) * 100

        # বলিঞ্জার ব্যান্ড কম্প্রেশন (ভোল্যাটিলিটি স্কুইজ)
        sma20 = np.mean(closes[-20:])
        std20 = np.std(closes[-20:])
        bb_width = ((2 * 2 * std20) / sma20) * 100

        funding_rate = funding_dict.get(symbol, 0.0) * 100

        # ৫. মাল্টি-ফ্যাক্টর প্রাতিষ্ঠানিক স্কোরিং অ্যালগরিদম (Base: 50)
        score = 50

        # শর্ত ১: কম্প্রেশন রেঞ্জে ভলিউম বিস্ফোরণ (দাম আটকে আছে কিন্তু ভলিউম ঢুকছে)
        if volume_spike >= 2.0 and abs(price_change) < 3.5:
            score += 18
        elif volume_spike >= 1.5:
            score += 10

        # শর্ত ২: টেকার ফ্লো ডমিন্যান্স (মার্কেট বাইয়াররা বড় অর্ডার নিচ্ছে)
        if taker_buy_percentage >= 58.0:
            score += 15
        elif taker_buy_percentage >= 52.0:
            score += 8

        # শর্ত ৩: ভোল্যাটিলিটি স্কুইজ (ব্রেকআউটের আগের শান্ত অবস্থা)
        if bb_width < 4.5:
            score += 12
        elif bb_width < 7.0:
            score += 6

        # শর্ত ৪: শর্ট স্কুইজ সেটআপ (নেগেটিভ ফান্ডিং রেট কিন্তু প্রাইস হোল্ড করছে)
        is_short_squeeze = False
        if funding_rate < -0.01:
            score += 15
            is_short_squeeze = True
        elif funding_rate < 0:
            score += 7

        # ফিল্টারে শীর্ষ ২০টি কয়েনের জন্য আরও গভীরে গিয়ে Open Interest পরিবর্তন মাপা
        if score >= 68:
            oi_change = get_open_interest_delta(symbol)
            if oi_change >= 8.0:
                score += 15  # পজিশন দ্রুত বিল্ডআপ হচ্ছে
            elif oi_change > 0:
                score += 5

            score = min(99, int(score))

            screened_candidates.append({
                "symbol": symbol,
                "score": score,
                "price_change": price_change,
                "vol_spike": volume_spike,
                "taker_buy": taker_buy_percentage,
                "bb_width": bb_width,
                "funding": funding_rate,
                "oi_change": oi_change,
                "is_squeeze": is_short_squeeze
            })

    # স্কোর অনুযায়ী সেরা সেটআপগুলোকে বাছাই করা
    screened_candidates = sorted(screened_candidates, key=lambda x: x['score'], reverse=True)[:15]

    final_payload = []
    
    # ৬. ফ্রন্টএন্ড টার্মিনালের জন্য রিয়েল-টাইম রিসার্চ মেকানিক্স তৈরি
    for cand in screened_candidates:
        sym_formatted = cand["symbol"].replace("USDT", "/USDT")
        
        # স্টেজ এবং মার্কেট মেকানিক্স নির্ধারণ
        if cand["is_squeeze"]:
            stage = "Short Squeeze Loading"
            catalyst = f"Negative Funding ({cand['funding']:.3f}%)"
        elif cand["oi_change"] > 10.0:
            stage = "Whale Accumulation"
            catalyst = f"OI Surge: +{cand['oi_change']}% in 4h"
        else:
            stage = "Volatility Compression"
            catalyst = f"BB Squeeze: {cand['bb_width']:.1f}% Width"

        flow_metric = f"Vol: {cand['vol_spike']:.1f}x | Taker: {cand['taker_buy']:.0f}%"

        for horizon, potential in [('24h', '12% - 24%'), ('1w', '35% - 65%'), ('1m', '80% - 140%')]:
            research_note = (
                f"Smart money footprint detected. Volume surged {cand['vol_spike']:.1f}x with {cand['taker_buy']:.0f}% aggressive buyer flow. "
                f"Open Interest expanded {cand['oi_change']:+.1f}% while 24h delta remained at {cand['price_change']:+.1f}%."
            )

            final_payload.append({
                "symbol": sym_formatted,
                "market_type": "crypto",
                "horizon": horizon,
                "sector": "Perpetual Alpha",
                "score": cand["score"] if horizon == '24h' else max(75, cand["score"] - 3),
                "stage": stage,
                "current_change_24h": round(cand["price_change"], 2),
                "est_potential": potential,
                "flow_metric": flow_metric,
                "driver_metric": catalyst,
                "mtf_alignment": "4H: Pre-Breakout | 1H: Accumulation",
                "research_note": research_note,
                "unlock_safe": True
            })

    # ৭. সুপাবেস ডাটাবেসে সেভ করা
    if final_payload:
        try:
            supabase.table("market_research").delete().eq("market_type", "crypto").execute()
            supabase.table("market_research").insert(final_payload).execute()
            print(f"Successfully published {len(screened_candidates)} alpha setups ({len(final_payload)} rows) to Supabase!")
        except Exception as db_err:
            print(f"Supabase sync failed: {db_err}")
    else:
        print("No market anomalies met institutional criteria in this cycle.")

if __name__ == "__main__":
    run_institutional_scanner()
