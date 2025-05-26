import re, tweepy, requests, os

# ① 추출용 정규식
CA_RE   = re.compile(r'0x[a-fA-F0-9]{40}')
TICK_RE = re.compile(r'\$(\w{2,10})')

# ② X 인증
client = tweepy.Client(
    consumer_key=os.getenv("X_CONSUMER"),
    consumer_secret=os.getenv("X_CONSUMER_SECRET"),
    access_token=os.getenv("X_ACCESS"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
)

# ③ 멘션 스트림 (v2 Filtered Stream → 간단히 polling 예시)
user_id = client.get_me().data.id

def parse_ids(text: str):
    ca = CA_RE.search(text)
    tick = TICK_RE.search(text)
    return (ca.group(0) if ca else None,
            tick.group(1) if tick else None)

def fetch_token_data(ca=None, ticker=None):
    if ticker:  # CoinGecko 예시
        url = f"https://api.coingecko.com/api/v3/coins/{ticker.lower()}"
    elif ca:    # DexScreener 예시
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    else:
        return None
    return requests.get(url, timeout=5).json()

def format_reply(data):
    # 서비스마다 JSON 구조가 달라서 축약 예시
    name  = data["name"]
    price = data["market_data"]["current_price"]["usd"]
    mcap  = data["market_data"]["market_cap"]["usd"]
    return f"🔍 {name}\n💲 Price: ${price:,.4f}\n🧢 Mcap: ${mcap:,.0f}"

def run_bot():
    mentions = client.get_users_mentions(id=user_id, max_results=5)
    for tw in reversed(mentions.data or []):
        if tw.author_id == user_id or tw.in_reply_to_user_id == user_id:
            continue  # 이미 답장했거나 내 트윗이면 패스
        ca, tick = parse_ids(tw.text)
        if not (ca or tick):
            continue
        data = fetch_token_data(ca, tick)
        if not data:
            continue
        reply = format_reply(data)
        client.create_tweet(in_reply_to_tweet_id=tw.id,
                            text=reply)

if __name__ == "__main__":
    run_bot()
