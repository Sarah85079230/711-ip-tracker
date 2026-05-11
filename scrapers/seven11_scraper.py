"""7-11 IP 相關新聞爬蟲（Google News RSS + Yahoo News RSS）"""
import sqlite3, feedparser, hashlib
from bs4 import BeautifulSoup
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Google News RSS 台灣版（從任何 IP 都能抓到台灣中文新聞）
NEWS_SOURCES = [
    {
        "name": "Google News｜7-11聯名",
        "url": "https://news.google.com/rss/search?q=7-11+聯名+台灣&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
    {
        "name": "Google News｜7-11加價購",
        "url": "https://news.google.com/rss/search?q=7-11+加價購&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
    {
        "name": "Google News｜統一超商IP",
        "url": "https://news.google.com/rss/search?q=統一超商+IP+授權&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
    {
        "name": "Google News｜7-11快閃",
        "url": "https://news.google.com/rss/search?q=7-11+快閃+限定&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
]


def run(conn: sqlite3.Connection):
    # 若舊版資料表欄位不足，先刪除重建
    try:
        conn.execute("SELECT published FROM seven11 LIMIT 1")
    except Exception:
        conn.execute("DROP TABLE IF EXISTS seven11")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS seven11 (
            item_id    TEXT PRIMARY KEY,
            title      TEXT,
            url        TEXT,
            summary    TEXT,
            source     TEXT,
            published  TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    added = 0
    print("  7-11 新聞（Google News RSS）...")

    for src in NEWS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries:
                title   = entry.get("title", "")
                url     = entry.get("link", "")
                summary = BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text()[:300]
                pub     = entry.get("published", "")[:10]

                item_id = hashlib.md5(url.encode()).hexdigest()
                exists  = conn.execute(
                    "SELECT 1 FROM seven11 WHERE item_id=?", (item_id,)
                ).fetchone()

                if not exists:
                    conn.execute(
                        "INSERT INTO seven11 VALUES (?,?,?,?,?,?,?)",
                        (item_id, title, url, summary, src["name"],
                         pub, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    added += 1

            print(f"    {src['name']}：{len(feed.entries)} 則")

        except Exception as e:
            print(f"    ⚠️  {src['name']} 失敗：{e}")

    print(f"    ✅ 共新增 {added} 則新聞")
    return added
