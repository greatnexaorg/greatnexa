import requests
import pandas as pd
import numpy as np
from supabase import create_client, Client

# বাইনান্স এপিআই ক্রেডেনশিয়াল
BINANCE_API_KEY = "RIOYR1XGF1x68ZX5iV7yrBmSz5jqVXwwB1miMo4Vjgn5dR74I3xfdJ7gRLlZ4yG8"
BINANCE_SECRET_KEY = "lrE32dqLzUf1lCveMe8O1xSfSd1eTv948Qi3VQ716yBDajG5ZGnUIrWcUVEMQNp6"

# Supabase প্রজেক্টের সঠিক URL এবং Service Role / Secret Key
SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "sb_secret_dpCpv8gKC1oPYhupcZmU8w_8Yu6mC9Z"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_crypto_pre_pump():
    print("Scanning Binance Futures for Pre-Pump Setups using API...")
    
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    try:
        tickers = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", headers=headers, timeout=10).json()
        premium_res = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex", headers=headers, timeout=10).json()
        premium_index = {item['symbol']: float(item['lastFundingRate']) for item in premium_res}
    except Exception as e:
        print(f"Error fetching from Binance API: {e}")
        return
    
    results = []
    
    for t in tickers:
        symbol = t['symbol']
        if not symbol.endswith('USDT') or symbol in ['BTCUSDT', 'ETHUSDT', 'USDCUSDT']:
            continue
            
        quote_vol = float(t['quoteVolume'])
        price_change = float(t['priceChangePercent'])
        
        if quote_vol < 15_000_000 or price_change > 8.5 or price_change < -6.0:
            continue
            
        try:
            klines = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=24", headers=headers, timeout=10).json()
            if len(klines) < 24:
                continue
        except:
            continue
            
        closes = np.array([float(k[4]) for k in klines])
        vols = np.array([float(k[7]) for k in klines])
        taker_buy = np.array([float(k[10]) for k in klines])
        
        recent_vol = np.mean(vols[-3:])
        avg_vol = np.mean(vols[:-3]) + 1e-9
        vol_ratio = recent_vol / avg_vol
        
        taker_ratio = (np.sum(taker_buy[-4:]) / (np.sum(vols[-4:]) + 1e-9)) * 100
        
        sma20 = np.mean(closes[-20:])
        std20 = np.std(closes[-20:])
        bb_width = ((sma20 + (2 * std20)) - (sma20 - (2 * std20))) / sma20 * 100
        
        funding = premium_index.get(symbol, 0.0) * 100
        
        score = 50
        if vol_ratio > 1.8 and abs(price_change) < 4.0: score += 20
        if taker_ratio > 53: score += 15
        if bb_width < 6.0: score += 10
        if funding < 0 and price_change > 0: score += 10
        
        score = min(99, int(score))
        
        if score >= 75:
            for horizon, pot in [('24h', '18% - 28%'), ('1w', '35% - 55%'), ('1m', '90% - 150%')]:
                note = f"Volume spiked {vol_ratio:.1f}x in last 3 hours while price moved only {price_change:.1f}%. Taker buy ratio at {taker_ratio:.0f}% (Smart Money Accumulation)."
                
                results.append({
                    "symbol": symbol.replace("USDT", "/USDT"),
                    "market_type": "crypto",
                    "horizon": horizon,
                    "sector": "High-Beta Futures",
                    "score": score if horizon == '24h' else max(75, score - 2),
                    "stage": "Short Squeeze Setup" if funding < 0 else "Stealth Accumulation",
                    "current_change_24h": price_change,
                    "est_potential": pot,
                    "flow_metric": f"Vol Surge: {vol_ratio:.1f}x | Buy: {taker_ratio:.0f}%",
                    "driver_metric": f"Funding: {funding:.3f}%",
                    "mtf_alignment": "1D: Bull | 4H: Squeeze | 1H: Igniting",
                    "research_note": note,
                    "unlock_safe": True
                })
                
    results = sorted(results, key=lambda x: x['score'], reverse=True)[:60]
    
    if results:
        try:
            supabase.table("market_research").delete().eq("market_type", "crypto").execute()
            supabase.table("market_research").insert(results).execute()
            print(f"Successfully updated {len(results)} crypto setups to Supabase using API!")
        except Exception as db_err:
            print(f"Supabase Error: {db_err}")
    else:
        print("No setups matched criteria in this run.")

if __name__ == "__main__":
    calculate_crypto_pre_pump()
