"""7-11 相關新聞爬蟲（改抓新聞媒體，不直連官網）"""
import sqlite3, requests, feedparser, hashlib
from bs4 import BeautifulSoup
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
}

# 公開可抓的 7-11 / 超商相關新聞來源
NEWS_SOURCES = [
    # Yahoo 新聞搜尋 RSS（7-11 聯名）
    "https://tw.news.yahoo.com/rss/search?p=7-11+IP+聯名&lang=zh-TW&region=TW",
    # Yahoo 新聞搜尋 RSS（統一超商加價購）
    "https://tw.news.yahoo.com/rss/search?p=統一超商+加價購&lang=zh-TW&region=TW",
    # Yahoo 新聞搜尋 RSS（7-11 快閃）
    "https://tw.news.yahoo.com/rss/search?p=7-11+快閃&lang=zh-TW&region=TW",
]

KEYWORDS_CHECK = ["7-11", "711", "7-ELEVEN", "統一超商", "小七"]
IP_KEYWORDS    = ["IP", "聯名", "授權", "加價購", "快閃", "限定", "公仔", "周邊"]


def is_relevant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).upper()
    has_711 = any(k.upper() in text for k in KEYWORDS_CHECK)
    has_ip  = any(k.upper() in text for k in IP_KEYWORDS)
    return has_711 or has_ip   # 新聞來源已過濾，有一個符合即可


def run(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seven11 (
            item_id    TEXT PRIMARY KEY,
            title      TEXT,
            url        TEXT,
            summary    TEXT,
            source     TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    added = 0
    print("  7-11 相關新聞 ...")

    for rss_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title   = entry.get("title", "")
                url     = entry.get("link", "")
                summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:200]

                if not is_relevant(title, summary):
                    continue

                item_id = hashlib.md5(url.encode()).hexdigest()
                exists  = conn.execute("SELECT 1 FROM seven11 WHERE item_id=?", (item_id,)).fetchone()
                if not exists:
                    source = feed.feed.get("title", rss_url[:40])
                    conn.execute(
                        "INSERT INTO seven11 VALUES (?,?,?,?,?,?)",
                        (item_id, title, url, summary, source, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    added += 1
        except Exception as e:
            print(f"    ⚠️  {rss_url[:50]} 失敗：{e}")

    print(f"    ✅ 新增 {added} 則新聞")
    return added
