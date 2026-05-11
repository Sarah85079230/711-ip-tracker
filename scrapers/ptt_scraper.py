"""PTT 超商板 爬蟲"""
import sqlite3, requests, time
from bs4 import BeautifulSoup
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import PTT_BOARDS, KEYWORDS_711, IP_KEYWORDS, MAX_POSTS, DB_PATH

BASE_URL = "https://www.ptt.cc"
HEADERS  = {"User-Agent": "Mozilla/5.0", "Cookie": "over18=1"}


def is_relevant(title: str) -> bool:
    t = title.upper()
    has_711 = any(k.upper() in t for k in KEYWORDS_711)
    has_ip  = any(k.upper() in t for k in IP_KEYWORDS)
    return has_711 and has_ip


def scrape_board(board: str, conn: sqlite3.Connection) -> int:
    added = 0
    url   = f"{BASE_URL}/bbs/{board}/index.html"

    for _ in range(5):   # 最多抓 5 頁
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"    PTT 連線失敗：{e}")
            break

        for div in soup.select("div.r-ent"):
            title_a = div.select_one("div.title a")
            if not title_a:
                continue
            title   = title_a.text.strip()
            link    = BASE_URL + title_a["href"]
            post_id = title_a["href"].split("/")[-1]

            if not is_relevant(title):
                continue

            # 取得推文數
            push_el = div.select_one("div.nrec span")
            pushes  = push_el.text.strip() if push_el else "0"
            pushes  = 100 if pushes == "爆" else (0 if not pushes.lstrip("-").isdigit() else int(pushes))

            # 取得日期
            date_el = div.select_one("div.date")
            date_str = date_el.text.strip() if date_el else ""

            exists = conn.execute("SELECT 1 FROM ptt WHERE post_id=?", (post_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO ptt VALUES (?,?,?,?,?,?,?)",
                    (post_id, board, title, link, pushes, date_str, datetime.utcnow().isoformat()),
                )
                conn.commit()
                added += 1

            if added >= MAX_POSTS:
                return added

        # 前一頁
        prev = soup.select_one("a.btn.wide", string=lambda t: t and "上頁" in t)
        if not prev:
            break
        url = BASE_URL + prev["href"]
        time.sleep(1)

    return added


def run(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ptt (
            post_id    TEXT PRIMARY KEY,
            board      TEXT,
            title      TEXT,
            url        TEXT,
            pushes     INTEGER,
            date_str   TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    total = 0
    for board in PTT_BOARDS:
        print(f"  PTT /{board} ...")
        n = scrape_board(board, conn)
        print(f"    ✅ 新增 {n} 篇")
        total += n
    return total
