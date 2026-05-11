"""7-11 官網活動頁爬蟲"""
import sqlite3, requests, hashlib
from bs4 import BeautifulSoup
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH

ACTIVITY_URLS = [
    "https://www.7-eleven.com.tw/activity/",
    "https://www.7-eleven.com.tw/about/newmsg.aspx",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
}


def scrape_activities(conn: sqlite3.Connection) -> int:
    added = 0

    for url in ACTIVITY_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"    7-11 官網連線失敗（{url}）：{e}")
            continue

        # 找所有活動連結/標題（7-11網站結構可能調整，廣撒網）
        items = []

        # 嘗試各種常見的活動列表結構
        for el in soup.select("a[href]"):
            title = el.get_text(strip=True)
            href  = el.get("href", "")
            if not title or len(title) < 4:
                continue
            # 過濾導覽列等無用連結
            if any(skip in title for skip in ["登入", "會員", "首頁", "關於", "門市"]):
                continue
            full_url = href if href.startswith("http") else "https://www.7-eleven.com.tw" + href
            items.append((title, full_url))

        for title, item_url in items[:30]:
            item_id = hashlib.md5(item_url.encode()).hexdigest()
            exists  = conn.execute("SELECT 1 FROM seven11 WHERE item_id=?", (item_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO seven11 VALUES (?,?,?,?)",
                    (item_id, title, item_url, datetime.utcnow().isoformat()),
                )
                conn.commit()
                added += 1

    return added


def run(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seven11 (
            item_id    TEXT PRIMARY KEY,
            title      TEXT,
            url        TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    print("  7-11 官網 ...")
    n = scrape_activities(conn)
    print(f"    ✅ 新增 {n} 筆活動")
    return n
