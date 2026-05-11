"""每天自動執行的主程式（GitHub Actions 呼叫這個）"""
import sqlite3
from config import DB_PATH
from scrapers import dcard_scraper, seven11_scraper, alerts_scraper

# 注意：PTT 封鎖非台灣 IP，暫時停用
# from scrapers import ptt_scraper


def main():
    print("=" * 50)
    print("開始抓取 7-11 IP 情報...")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    total = 0

    total += dcard_scraper.run(conn)
    total += seven11_scraper.run(conn)
    total += alerts_scraper.run(conn)

    conn.close()
    print("=" * 50)
    print(f"完成！共新增 {total} 筆資料")


if __name__ == "__main__":
    main()
