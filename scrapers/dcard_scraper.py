"""Dcard 爬蟲（使用公開 API）"""
import sqlite3, requests, time
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DCARD_FORUMS, KEYWORDS_711, IP_KEYWORDS, MAX_POSTS, DB_PATH

API_BASE = "https://www.dcard.tw/service/api/v2"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer":    "https://www.dcard.tw/",
}


def is_relevant(title: str, excerpt: str = "") -> bool:
    text = (title + " " + excerpt).upper()
    has_711 = any(k.upper() in text for k in KEYWORDS_711)
    has_ip  = any(k.upper() in text for k in IP_KEYWORDS)
    return has_711 and has_ip


def scrape_forum(forum: str, conn: sqlite3.Connection) -> int:
    added  = 0
    params = {"forumName": forum, "limit": 30}

    for _ in range(3):   # 最多抓 3 頁
        try:
            r = requests.get(f"{API_BASE}/posts", headers=HEADERS, params=params, timeout=10)
            posts = r.json()
            if not posts:
                break
        except Exception as e:
            print(f"    Dcard 連線失敗：{e}")
            break

        for post in posts:
            post_id = str(post.get("id", ""))
            title   = post.get("title", "")
            excerpt = post.get("excerpt", "")

            if not is_relevant(title, excerpt):
                continue

            likes    = post.get("likeCount", 0)
            comments = post.get("commentCount", 0)
            pub_date = post.get("createdAt", "")[:10]
            url      = f"https://www.dcard.tw/f/{forum}/p/{post_id}"

            exists = conn.execute("SELECT 1 FROM dcard WHERE post_id=?", (post_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO dcard VALUES (?,?,?,?,?,?,?,?)",
                    (post_id, forum, title, excerpt[:200], url, likes, comments,
                     datetime.utcnow().isoformat()),
                )
                conn.commit()
                added += 1

            if added >= MAX_POSTS:
                return added

        # 翻頁：用最後一篇的 ID 當 cursor
        params["before"] = posts[-1]["id"]
        time.sleep(1)

    return added


def run(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dcard (
            post_id    TEXT PRIMARY KEY,
            forum      TEXT,
            title      TEXT,
            excerpt    TEXT,
            url        TEXT,
            likes      INTEGER,
            comments   INTEGER,
            fetched_at TEXT
        )
    """)
    conn.commit()

    total = 0
    for forum in DCARD_FORUMS:
        print(f"  Dcard /{forum} ...")
        n = scrape_forum(forum, conn)
        print(f"    ✅ 新增 {n} 篇")
        total += n
        time.sleep(2)
    return total
