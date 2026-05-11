"""Dcard 搜尋爬蟲"""
import sqlite3, requests, time
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import MAX_POSTS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Referer": "https://www.dcard.tw/",
}

# 直接用搜尋 API，不依賴特定論壇
SEARCH_QUERIES = [
    "7-11 聯名",
    "7-11 加價購",
    "統一超商 IP",
    "7-11 快閃",
]


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

    added = 0
    for query in SEARCH_QUERIES:
        print(f"  Dcard 搜尋「{query}」...")
        try:
            r = requests.get(
                "https://www.dcard.tw/service/api/v2/search/posts",
                headers=HEADERS,
                params={"query": query, "limit": 20},
                timeout=15,
            )
            if r.status_code != 200 or not r.text.strip():
                print(f"    回應 {r.status_code}，略過")
                time.sleep(2)
                continue

            posts = r.json()
            if not isinstance(posts, list):
                posts = posts.get("posts", [])

            for post in posts:
                post_id  = str(post.get("id", ""))
                title    = post.get("title", "")
                excerpt  = (post.get("excerpt") or "")[:200]
                forum    = post.get("forumAlias", "")
                likes    = post.get("likeCount", 0)
                comments = post.get("commentCount", 0)
                url      = f"https://www.dcard.tw/f/{forum}/p/{post_id}"

                exists = conn.execute(
                    "SELECT 1 FROM dcard WHERE post_id=?", (post_id,)
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO dcard VALUES (?,?,?,?,?,?,?,?)",
                        (post_id, forum, title, excerpt, url, likes,
                         comments, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    added += 1

            print(f"    ✅ 新增 {added} 篇")

        except Exception as e:
            print(f"    ⚠️  失敗：{e}")

        time.sleep(3)

    return added
