"""Dcard 爬蟲"""
import sqlite3, requests, time
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DCARD_FORUMS, KEYWORDS_711, IP_KEYWORDS, MAX_POSTS

API_BASE = "https://www.dcard.tw/service/api/v2"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Referer": "https://www.dcard.tw/",
    "Origin": "https://www.dcard.tw",
}


def is_relevant(title: str, excerpt: str = "") -> bool:
    text = (title + " " + excerpt).upper()
    has_711 = any(k.upper() in text for k in KEYWORDS_711)
    has_ip  = any(k.upper() in text for k in IP_KEYWORDS)
    return has_711 and has_ip


def scrape_forum(forum: str, conn: sqlite3.Connection) -> int:
    added  = 0
    # 嘗試兩種 API 格式
    endpoints = [
        f"{API_BASE}/posts?forumAlias={forum}&limit=30",
        f"{API_BASE}/posts?forum={forum}&limit=30",
    ]

    posts = []
    for endpoint in endpoints:
        try:
            r = requests.get(endpoint, headers=HEADERS, timeout=15)
            if r.status_code == 200 and r.text.strip():
                posts = r.json()
                if isinstance(posts, list) and posts:
                    break
        except Exception as e:
            print(f"    Dcard {endpoint} 失敗：{e}")
        time.sleep(1)

    if not posts:
        # 備用：直接搜尋 7-11 關鍵字
        try:
            r = requests.get(
                f"{API_BASE}/search/posts",
                headers=HEADERS,
                params={"query": "7-11 IP 聯名", "limit": 20},
                timeout=15,
            )
            if r.status_code == 200 and r.text.strip():
                result = r.json()
                posts = result if isinstance(result, list) else result.get("posts", [])
        except Exception as e:
            print(f"    Dcard 搜尋失敗：{e}")

    for post in posts:
        post_id = str(post.get("id", ""))
        title   = post.get("title", "")
        excerpt = post.get("excerpt", "") or post.get("content", "")[:100]

        if not is_relevant(title, excerpt):
            continue

        likes    = post.get("likeCount", 0)
        comments = post.get("commentCount", 0)
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
            break

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
        time.sleep(3)
    return total
