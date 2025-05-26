import os, re, time, requests, tweepy

# ── 1) 인증 세트 ──────────────────────────────
# 읽기용 (v2 Recent Search) → Bearer Token
search_client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER"),
    wait_on_rate_limit=True
)

# 쓰기용 (트윗 답글) → OAuth 1.0a User Token
write_auth = tweepy.OAuth1UserHandler(
    os.getenv("X_CONSUMER"),
    os.getenv("X_CONSUMER_SECRET"),
    os.getenv("X_ACCESS"),
    os.getenv("X_ACCESS_SECRET")
)
write_client = tweepy.Client(
    consumer_key        = os.getenv("X_CONSUMER"),
    consumer_secret     = os.getenv("X_CONSUMER_SECRET"),
    access_token        = os.getenv("X_ACCESS"),
    access_token_secret = os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit  = True
)

BOT_USERNAME = os.getenv("BOT_USERNAME").lstrip("@")          # 예: MyTokenBot
BOT_USER_ID  = os.getenv("BOT_USER_ID")                       # 숫자 ID

# ── 2) 유틸 ──────────────────────────────────
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
    resp = requests.get(url, timeout=5)
    return resp.json() if resp.ok else None

def format_reply(data):
    name  = data["name"]
    price = data["market_data"]["current_price"]["usd"]
    mcap  = data["market_data"]["market_cap"]["usd"]
    return f"🔍 {name}\n💲 Price: ${price:,.4f}\n🧢 Mcap: ${mcap:,.0f}"

# ── 3) 메인 루프 ──────────────────────────────
def run_bot():
    since_id = None
    query = f"@{BOT_USERNAME} -is:retweet"

    while True:
        tweets = search_client.search_recent_tweets(
            query=query,
            since_id=since_id,
            tweet_fields=["author_id"],
            max_results=100
        )

        if tweets.data:
            for tw in reversed(tweets.data):
                since_id = max(since_id or 0, tw.id)
                if str(tw.author_id) == BOT_USER_ID:
                    continue        # 내 트윗이면 패스
                ca, tick = parse_ids(tw.text)
                if not (ca or tick):
                    continue
                data = fetch_token_data(ca, tick)
                if data:
                    reply = format_reply(data)
                    write_client.create_tweet(
                        in_reply_to_tweet_id=tw.id,
                        text=reply,
                        user_auth=True
                    )
        time.sleep(60)              # Free 쿼터(450/15 min) 내에서 넉넉

if __name__ == "__main__":
    run_bot()
