"""每天自動執行的主程式（GitHub Actions 呼叫這個）"""
import sqlite3
from config import DB_PATH
from scrapers import seven11_scraper, alerts_scraper

# 以下來源因封鎖 GitHub Actions IP 暫停：
# - PTT（ConnectionResetError）
# - Dcard（403 Forbidden）
# - 7-11 官網（ConnectTimeout，geo-block）


def main():
    print("=" * 50)
    print("開始抓取 7-11 IP 情報...")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    total = 0

    total += seven11_scraper.run(conn)   # Google News RSS × 4 個關鍵字
    total += alerts_scraper.run(conn)    # Google Alerts RSS（你自設的快訊）

    conn.close()
    print("=" * 50)
    print(f"完成！共新增 {total} 筆資料")


if __name__ == "__main__":
    main()
