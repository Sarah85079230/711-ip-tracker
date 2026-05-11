import sqlite3
import subprocess
import pandas as pd
import plotly.express as px
import streamlit as st
from config import DB_PATH

st.set_page_config(page_title="7-11 IP 情報儀表板", page_icon="🏪", layout="wide")
st.title("🏪 7-11 IP 活動情報儀表板")
st.caption("監控來源：PTT 超商板・Dcard・7-11官網・Google Alerts")


# ── 資料讀取 ────────────────────────────────────────
@st.cache_data(ttl=0)
def load_all():
    conn = sqlite3.connect(DB_PATH)
    tables = {}
    for t in ["ptt", "dcard", "seven11", "alerts"]:
        try:
            tables[t] = pd.read_sql_query(f"SELECT * FROM {t} ORDER BY fetched_at DESC", conn)
        except Exception:
            tables[t] = pd.DataFrame()
    conn.close()
    return tables


# ── 重新抓取 ────────────────────────────────────────
col_btn, _ = st.columns([2, 5])
with col_btn:
    if st.button("🔄 立即抓取最新情報", type="primary"):
        with st.spinner("抓取中，約 1~2 分鐘..."):
            result = subprocess.run(
                ["python3", "run_all.py"], capture_output=True, text=True, cwd="."
            )
        if result.returncode == 0:
            st.success("✅ 抓取完成！")
        else:
            st.error(f"❌ 錯誤：{result.stderr[-300:]}")
        st.cache_data.clear()
        st.rerun()

data = load_all()
has_any = any(not df.empty for df in data.values())

if not has_any:
    st.warning("⚠️ 還沒有資料，請點「立即抓取最新情報」")
    st.stop()

# ── 整體數字 ────────────────────────────────────────
st.divider()
st.subheader("📊 情報總覽")
c1, c2, c3, c4 = st.columns(4)
c1.metric("PTT 相關文章", f"{len(data['ptt']):,}")
c2.metric("Dcard 相關文章", f"{len(data['dcard']):,}")
c3.metric("7-11 官網活動", f"{len(data['seven11']):,}")
c4.metric("Google Alerts 新聞", f"{len(data['alerts']):,}")

# ── PTT ────────────────────────────────────────────
st.divider()
st.subheader("💬 PTT 超商板 熱門討論")
if not data["ptt"].empty:
    df = data["ptt"].copy()
    df["推文數"] = pd.to_numeric(df["pushes"], errors="coerce").fillna(0).astype(int)
    df["連結"]  = df["url"].apply(lambda u: f'<a href="{u}" target="_blank">查看</a>')
    show = df.nlargest(20, "推文數")[["date_str", "board", "title", "推文數", "連結"]]
    show.columns = ["日期", "版面", "標題", "推文數", "連結"]
    st.write(show.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("尚無 PTT 資料")

# ── Dcard ───────────────────────────────────────────
st.divider()
st.subheader("📱 Dcard 熱門討論")
if not data["dcard"].empty:
    df = data["dcard"].copy()
    df["連結"] = df["url"].apply(lambda u: f'<a href="{u}" target="_blank">查看</a>')
    show = df.nlargest(20, "likes")[["forum", "title", "likes", "comments", "連結"]]
    show.columns = ["論壇", "標題", "愛心數", "留言數", "連結"]
    st.write(show.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("尚無 Dcard 資料")

# ── 7-11 官網 ───────────────────────────────────────
st.divider()
st.subheader("🏪 7-11 官網 最新活動")
if not data["seven11"].empty:
    df = data["seven11"].copy()
    df["fetched_at"] = pd.to_datetime(df["fetched_at"]).dt.strftime("%Y-%m-%d")
    df["連結"] = df["url"].apply(lambda u: f'<a href="{u}" target="_blank">查看</a>')
    cols = [c for c in ["fetched_at", "source", "title", "連結"] if c in df.columns]
    show = df[cols].head(30)
    show.columns = ["發現日期", "來源", "標題", "連結"][:len(cols)]
    st.write(show.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("尚無 7-11 官網資料")

# ── Google Alerts ───────────────────────────────────
st.divider()
st.subheader("📰 Google Alerts 新聞")
if not data["alerts"].empty:
    df = data["alerts"].copy()
    df["連結"] = df["url"].apply(lambda u: f'<a href="{u}" target="_blank">查看</a>')
    for _, row in df.head(20).iterrows():
        with st.expander(f"📄 {row['title']}　{row.get('published', '')}"):
            st.markdown(row.get("summary", "（無摘要）"))
            st.markdown(f"[🔗 閱讀原文]({row['url']})")
else:
    st.info("尚未設定 Google Alerts RSS，或尚無新聞資料")
    st.markdown("👉 請前往 [google.com/alerts](https://www.google.com/alerts) 設定關鍵字，選擇 RSS 傳遞方式，再將網址貼入 `config.py`")
