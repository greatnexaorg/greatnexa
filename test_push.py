from supabase import create_client

SUPABASE_URL = "https://esqhansnosejkqapuhoo.supabase.co"
SUPABASE_KEY = "sb_publishable_FypTC1KRVE66YBURyEhT9A_H3fKhzLM"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

test_data = {
    "symbol": "BTC/USDT",
    "market_type": "crypto",
    "horizon": "24h",
    "direction": "long",
    "trading_mode": "mode2",
    "score": 99,
    "stage": "[TEST] Direct Push",
    "current_change_24h": 1.25,
    "sector": "Test",
    "est_potential": "+5.0%",
    "flow_metric": "Test Flow",
    "driver_metric": "Test Driver",
    "mtf_alignment": "Entry: $65000 | SL: $64000",
    "research_note": "Direct verification test."
}

print("Supabase-এ ডেটা পাঠানোর চেষ্টা চলছে...")
try:
    res = supabase.table("market_research").insert(test_data).execute()
    print("সফল! ডেটাবেজে ইনসার্ট হয়েছে:", res)
except Exception as e:
    print("\n[আসল সমস্যা ধরা পড়েছে!]")
    print("Error Details:", e)
