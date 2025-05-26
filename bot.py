import os, re, time, requests, tweepy

# ── 1) OAuth1 인증 ───────────────────────────
auth = tweepy.OAuth1UserHandler(
    os.getenv("X_CONSUMER"),
    os.getenv("X_CONSUMER_SECRET"),
    os.getenv("X_ACCESS"),
    os.getenv("X_ACCESS_SECRET")
)
api = tweepy.API(auth, wait_on_rate_limit=True)   # v1.1 전용 객체

BOT_USER_ID = int(os.getenv("BOT_USER_ID"))       # 환경변수 필수

# ── 2) 유틸 함수 ──────────────────────────────
CA_RE   = re.compile(r'0x[a-fA-F0-9]{40}')
TICK_RE = re.compile(r'\$(\w{2,10})')

def parse_ids(text):
    ca   = CA_RE.search(text)
    tick = TICK_RE.search(text)
    return (ca.group(0) if ca else None,
            tick.group(1) if tick else None)

def fetch_token_data(ca=None, ticker=None):
    if ticker:
        url = f"https://api.coingecko.com/api/v3/coins/{ticker.lower()}"
    elif ca:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    else:
        return None
    return requests.get(url, timeout=5).json()

def format_reply(data):
    name  = data["name"]
    price = data["market_data"]["current_price"]["usd"]
    mcap  = data["market_data"]["market_cap"]["usd"]
    return f"🔍 {name}\n💲 Price: ${price:,.4f}\n🧢 Mcap: ${mcap:,.0f}"

# ── 3) 메인 루프 ──────────────────────────────
def run_bot():
    since_id = None
    while True:
        mentions = api.mentions_timeline(
            since_id=since_id,
            tweet_mode="extended",
            count=20            # 20개 한 번에
        )
        for tw in reversed(mentions):
            since_id = max(since_id or 0, tw.id)
            if tw.user.id == BOT_USER_ID:
                continue        # 내 트윗 패스
            ca, tick = parse_ids(tw.full_text)
            if not (ca or tick):
                continue
            data = fetch_token_data(ca, tick)
            if data:
                reply = format_reply(data)
                api.update_status(
                    status=reply,
                    in_reply_to_status_id=tw.id,
                    auto_populate_reply_metadata=True
                )
        time.sleep(60)          # 1분 간격 → v1.1 쿼터(75 회/15 분) 여유

if __name__ == "__main__":
    run_bot()
