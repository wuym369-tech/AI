import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="AI OS · CEO Dashboard", page_icon="🧠", layout="wide")

st.title("🧠 AI OS")
st.caption(f"CEO + Life Dashboard · {date.today().strftime('%Y-%m-%d')}")

# ---- Demo state: later replace with your existing Notion data ----
if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"title": "完成 9–11 月商品銷售企劃", "due": date.today(), "done": False, "type": "公司"},
        {"title": "跟進 1688 客戶", "due": date.today(), "done": False, "type": "公司"},
        {"title": "完成今日讀書筆記", "due": date.today(), "done": False, "type": "成長"},
        {"title": "重量訓練", "due": date.today(), "done": False, "type": "健康"},
        {"title": "整理本週內容企劃", "due": date.today() - timedelta(days=1), "done": False, "type": "公司"},
    ]

tasks = st.session_state.tasks
open_tasks = [t for t in tasks if not t["done"]]
today_tasks = [t for t in open_tasks if t["due"] == date.today()]
overdue = [t for t in open_tasks if t["due"] < date.today()]

# 1
st.subheader("⭐ 今日最重要的事")
priorities = [
    ("完成 9–11 月商品銷售企劃", "公司營收", "公司"),
    ("完成今日讀書 / 學習", "專業能力", "人生"),
    ("完成今天的健康訓練", "身體與能量", "人生"),
]
cols = st.columns(3)
for i, (col, item) in enumerate(zip(cols, priorities)):
    title, impact, kind = item
    with col:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.caption(f"{kind} · 影響：{impact}")
            st.button("→ 執行", key=f"priority_{i}", use_container_width=True)

# 2
st.subheader("📊 今日狀態")
c = st.columns(6)
c[0].metric("公司 KPI", "72%")
c[1].metric("進行中專案", "7")
c[2].metric("逾期任務", str(len(overdue)))
c[3].metric("今日待辦", str(len(today_tasks)))
c[4].metric("本週學習", "4.5 h")
c[5].metric("進行中目標", "6")

# 3
st.subheader("🚨 待處理")
if overdue:
    for task in overdue[:5]:
        with st.container(border=True):
            st.markdown(f"🔴 **{task['title']}**")
            st.caption(f"逾期 {(date.today()-task['due']).days} 天 · {task['type']}")
else:
    st.success("目前沒有逾期任務。")

# 4
st.subheader("📋 今天要做什麼")
if today_tasks:
    for i, task in enumerate(today_tasks):
        checked = st.checkbox(
            f"{task['title']} · {task['type']}",
            value=task["done"],
            key=f"today_{i}_{task['title']}",
        )
        if checked and not task["done"]:
            task["done"] = True
            st.toast(f"完成：{task['title']}")
else:
    st.info("今天沒有排程任務。")

# 5
st.subheader("🎯 本週重點")
weekly = [
    ("9–11 月銷售企劃", 70, "公司"),
    ("茉莉純露推廣", 50, "公司"),
    ("專業學習", 60, "人生"),
    ("健身", 80, "人生"),
]
for name, progress, kind in weekly:
    a, b = st.columns([5, 1])
    with a:
        st.write(f"**{name}** · {kind}")
        st.progress(progress / 100)
    with b:
        st.write(f"**{progress}%**")

# 6
st.subheader("📈 核心 KPI")
kpis = [
    ("三產收入", 72),
    ("商品銷售", 61),
    ("社群成長", 42),
    ("學習進度", 60),
]
for name, progress in kpis:
    a, b = st.columns([5, 1])
    with a:
        st.write(name)
        st.progress(progress / 100)
    with b:
        st.write(f"**{progress}%**")

st.caption("V2.1：首頁只留下現在最值得知道、最值得做的資訊。")
