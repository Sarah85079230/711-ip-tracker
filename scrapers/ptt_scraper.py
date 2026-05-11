"""PTT 超商板 爬蟲"""
import sqlite3, time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import PTT_BOARDS, KEYWORDS_711, IP_KEYWORDS, MAX_POSTS, DB_PATH

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    pass

BASE_URL = "https://www.ptt.cc"


def make_session():
    s = requests.Session()
    s.cookies.set("over18", "1", domain="www.ptt.cc")
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
        "Referer": "https://www.ptt.cc/bbs/c_store/index.html",
        "Connection": "keep-alive",
    })
    return s


def is_relevant(title: str) -> bool:
    t = title.upper()
    has_711 = any(k.upper() in t for k in KEYWORDS_711)
    has_ip  = any(k.upper() in t for k in IP_KEYWORDS)
    return has_711 and has_ip


def scrape_board(board: str, conn: sqlite3.Connection) -> int:
    added   = 0
    session = make_session()
    url     = f"{BASE_URL}/bbs/{board}/index.html"

    for attempt in range(3):   # 最多 3 次重試
        try:
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                print(f"    PTT 回應 {r.status_code}，重試...")
                time.sleep(3)
                continue
            break
        except Exception as e:
            print(f"    PTT 連線失敗（第{attempt+1}次）：{e}")
            time.sleep(5)
    else:
        return 0

    for page_num in range(5):
        try:
            r = session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"    PTT 第{page_num+1}頁失敗：{e}")
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

            push_el = div.select_one("div.nrec span")
            pushes  = push_el.text.strip() if push_el else "0"
            pushes  = 100 if pushes == "爆" else (0 if not pushes.lstrip("-").isdigit() else int(pushes))
            date_el = div.select_one("div.date")
            date_str = date_el.text.strip() if date_el else ""

            from datetime import datetime
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

        prev = soup.find("a", string=lambda t: t and "上頁" in t)
        if not prev:
            break
        url = BASE_URL + prev["href"]
        time.sleep(2)

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
