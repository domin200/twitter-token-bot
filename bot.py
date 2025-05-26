import os, re, time, requests, tweepy

# ──────────────────────────────────────
# 1) 트위터 인증 (OAuth 1.0a User Context)
# ──────────────────────────────────────
client = tweepy.Client(
    consumer_key        = os.getenv("X_CONSUMER"),
    consumer_secret     = os.getenv("X_CONSUMER_SECRET"),
    access_token        = os.getenv("X_ACCESS"),
    access_token_secret = os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit  = True          # 429 시 자동 슬립
)

# ──────────────────────────────────────
# 2) 봇 계정 숫자 ID 확보 (API 호출은 최대 1회)
# ──────────────────────────────────────
USER_ID = os.getenv("BOT_USER_ID")
if not USER_ID:
    USER_ID = str(client.get_me(user_auth=True).data.id)

# ──────────────────────────────────────
# 3) 유틸 정규식 · 외부 API 함수
# ──────────────────────────────────────
CA_RE   = re.compile(r'0x[a-fA-F0-9]{40}')
TICK_RE = re.compile(r'\$(\w{2,10})')

def parse_ids(text: str):
    """트윗 텍스트에서 CA / 티커 추출"""
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

# ──────────────────────────────────────
# 4) 메인 루프: 60초 폴링 → 멘션 처리
# ──────────────────────────────────────
def run_bot():
    since_id = None
    while True:
        mentions = client.get_users_mentions(id=USER_ID,
                                             since_id=since_id,
                                             max_results=5,
                                             user_auth=True)
        for tw in reversed(mentions.data or []):
            since_id = max(since_id or 0, tw.id)
            if tw.author_id == int(USER_ID):
                continue  # 내 트윗이면 패스
            ca, tick = parse_ids(tw.text)
            if not (ca or tick):
                continue
            data = fetch_token_data(ca, tick)
            if data:
                reply = format_reply(data)
                client.create_tweet(in_reply_to_tweet_id=tw.id,
                                    text=reply,
                                    user_auth=True)
        time.sleep(60)   # 호출 빈도 ↓ (100 read/일 범위 내)

# ──────────────────────────────────────
if __name__ == "__main__":
    run_bot()
