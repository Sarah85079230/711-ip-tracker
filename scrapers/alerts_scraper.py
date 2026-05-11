"""Google Alerts RSS 爬蟲"""
import sqlite3, feedparser, hashlib
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import GOOGLE_ALERTS_RSS, DB_PATH


def run(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            item_id    TEXT PRIMARY KEY,
            title      TEXT,
            summary    TEXT,
            url        TEXT,
            published  TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    if not GOOGLE_ALERTS_RSS:
        print("  Google Alerts：尚未設定 RSS 網址，略過")
        return 0

    added = 0
    for rss_url in GOOGLE_ALERTS_RSS:
        print(f"  Google Alerts RSS: {rss_url[:60]}...")
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                item_id = hashlib.md5(entry.link.encode()).hexdigest()
                exists  = conn.execute("SELECT 1 FROM alerts WHERE item_id=?", (item_id,)).fetchone()
                if not exists:
                    published = entry.get("published", "")[:10]
                    summary   = entry.get("summary", "")[:300]
                    # 去除 HTML 標籤
                    from bs4 import BeautifulSoup
                    summary = BeautifulSoup(summary, "html.parser").get_text()
                    conn.execute(
                        "INSERT INTO alerts VALUES (?,?,?,?,?,?)",
                        (item_id, entry.title, summary, entry.link,
                         published, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    added += 1
        except Exception as e:
            print(f"    ⚠️  RSS 讀取失敗：{e}")

    print(f"    ✅ 新增 {added} 則新聞")
    return added
