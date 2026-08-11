"""
AI OS · CEO Dashboard (Streamlit + Notion 即時版)
--------------------------------------------------
每次打開這個網頁，都會即時去 Notion 抓最新資料再畫出來。
Notion 存取權杖存在 Streamlit 的 Secrets，瀏覽器端看不到，安全。

部署方式請見 DEPLOY_GUIDE.md。
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# 固定資料庫 ID（這些是公開的識別碼，不是機密，可以放在程式碼裡）
# ---------------------------------------------------------------------------
DB_DEPARTMENTS = "7d1ef39de6444a7b85f1b65560368c0d"   # 部門管理
DB_UNITS       = "09e7b28d48c74dd299baa9deda08484c"   # 事業體總覽
DB_TODOS       = "68967bdb8f364d6d99294fbea8fd880f"   # 公司代辦事項
DB_SOP         = "c9dfd66d9d754bb0b922e9b15a822000"   # SOP 流程庫
DB_MEETINGS    = "d36e85f4c91448bf86c06dfcc2993f25"   # 會議紀錄
DB_DECISIONS   = "def438b2b4ba418a92ad3262970616b6"   # 決策紀錄
DB_KPI         = "c281849c660b4e8b8bcb22413b118dab"   # KPI 追蹤

NOTION_API = "https://api.notion.com/v1"

st.set_page_config(page_title="AI OS · CEO Dashboard", page_icon="🧠", layout="wide")

# ---------------------------------------------------------------------------
# Notion 連線（直接打 REST API，避免 SDK 版本差異造成的相容性問題）
# ---------------------------------------------------------------------------
def get_headers():
    token = st.secrets.get("NOTION_TOKEN")
    if not token:
        st.error("找不到 NOTION_TOKEN，請到 Streamlit App 的 Settings → Secrets 設定。")
        st.stop()
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


@st.cache_data(ttl=60, show_spinner="正在向 Notion 取得最新資料...")
def query_db(db_id: str):
    """回傳資料庫所有列（已攤平成 dict list）"""
    headers = get_headers()
    results, cursor = [], None
    while True:
        payload = {"start_cursor": cursor} if cursor else {}
        resp = requests.post(f"{NOTION_API}/databases/{db_id}/query", headers=headers, json=payload, timeout=30)
        if not resp.ok:
            st.error(f"Notion API 錯誤（{resp.status_code}）：{resp.text[:500]}")
            st.stop()
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return [flatten(p) for p in results]


def flatten(page: dict) -> dict:
    """把 Notion 的 page properties 轉成單層 dict，方便畫表格"""
    out = {"_id": page["id"], "_url": page.get("url", "")}
    for name, prop in page.get("properties", {}).items():
        out[name] = extract(prop)
    return out


def extract(prop: dict):
    t = prop.get("type")
    if t == "title":
        return "".join(x["plain_text"] for x in prop["title"]) or None
    if t == "rich_text":
        return "".join(x["plain_text"] for x in prop["rich_text"]) or None
    if t == "select":
        return prop["select"]["name"] if prop["select"] else None
    if t == "status":
        return prop["status"]["name"] if prop["status"] else None
    if t == "multi_select":
        return "、".join(x["name"] for x in prop["multi_select"]) or None
    if t == "date":
        if not prop["date"]:
            return None
        d = prop["date"]
        return d["start"] + (f" → {d['end']}" if d.get("end") else "")
    if t == "people":
        return "、".join(p.get("name", "") for p in prop["people"]) or None
    if t == "relation":
        return [r["id"] for r in prop["relation"]]
    if t == "checkbox":
        return prop["checkbox"]
    if t == "number":
        return prop["number"]
    return None


def id_to_title_map(rows: list, title_field: str) -> dict:
    return {r["_id"]: r.get(title_field) for r in rows}


def resolve_relation(ids, mapping):
    if not ids:
        return ""
    return "、".join(mapping.get(i, "（未知）") for i in ids)


# ---------------------------------------------------------------------------
# 讀資料
# ---------------------------------------------------------------------------
depts   = query_db(DB_DEPARTMENTS)
units   = query_db(DB_UNITS)
todos   = query_db(DB_TODOS)
sops    = query_db(DB_SOP)
meets   = query_db(DB_MEETINGS)
decides = query_db(DB_DECISIONS)
kpis    = query_db(DB_KPI)

dept_map = id_to_title_map(depts, "部門")
unit_map = id_to_title_map(units, "事業體")

for r in sops:
    r["部門"] = resolve_relation(r.get("部門"), dept_map)
for r in meets:
    r["部門"] = resolve_relation(r.get("部門"), dept_map)
    r["事業體"] = resolve_relation(r.get("事業體"), unit_map)
for r in decides:
    r["部門"] = resolve_relation(r.get("部門"), dept_map)
for r in kpis:
    r["部門"] = resolve_relation(r.get("部門"), dept_map)
    r["事業體"] = resolve_relation(r.get("事業體"), unit_map)

# ---------------------------------------------------------------------------
# 側邊欄
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🧠 AI OS\n我的第二大腦與企業系統")
if st.sidebar.button("🔄 重新整理（清快取，立即抓最新）"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"資料每 60 秒自動更新一次\n上次載入：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

page = st.sidebar.radio(
    "前往",
    ["🏠 CEO Dashboard", "👥 部門管理", "🏢 事業體總覽", "📋 SOP 流程庫",
     "📝 會議紀錄", "🧭 決策紀錄", "📈 KPI 追蹤", "✅ 公司代辦事項"],
)

# ---------------------------------------------------------------------------
# Dashboard 頁
# ---------------------------------------------------------------------------
def dashboard():
    st.title("早安 🌿")
    st.caption("這裡是目前 Notion 真實資料的即時總覽。")

    depts_filled = sum(1 for d in depts if d.get("狀態") not in (None, "待補充"))
    units_filled = sum(1 for u in units if u.get("狀態") not in (None, "待補充"))
    open_todos = sum(1 for t in todos if t.get("狀態") not in ("完成", "已封存"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("事業體資料", f"{units_filled} / {len(units)}")
    c2.metric("部門資料", f"{depts_filled} / {len(depts)}")
    c3.metric("SOP 項目數", len(sops))
    c4.metric("待辦事項（未完成）", open_todos)

    st.divider()
    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("部門狀態")
        if depts:
            st.dataframe(pd.DataFrame(depts)[["部門", "狀態"]], hide_index=True, use_container_width=True)
        st.subheader("本週 SOP（依星期排序）")
        if sops:
            order = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
            df = pd.DataFrame(sops)
            df["_順序"] = df["星期"].map(order)
            df = df.sort_values("_順序")
            st.dataframe(df[["星期", "項目名稱", "部門", "狀態"]], hide_index=True, use_container_width=True)
        else:
            st.info("尚無 SOP 資料")

    with right:
        st.subheader("公司代辦事項")
        if todos:
            df = pd.DataFrame(todos)
            cols = [c for c in ["任務名稱", "狀態", "截止時間", "負責人"] if c in df.columns]
            st.dataframe(df[cols], hide_index=True, use_container_width=True)
        else:
            st.info("尚無代辦事項")

        st.subheader("最近會議")
        if meets:
            df = pd.DataFrame(meets).sort_values("日期", ascending=False, na_position="last")
            cols = [c for c in ["標題", "日期", "部門"] if c in df.columns]
            st.dataframe(df[cols].head(5), hide_index=True, use_container_width=True)
        else:
            st.info("尚無會議紀錄")


def simple_table(rows, title, cols=None):
    st.title(title)
    if not rows:
        st.info("尚無資料")
        return
    df = pd.DataFrame(rows)
    if cols:
        cols = [c for c in cols if c in df.columns]
        df = df[cols]
    st.dataframe(df, hide_index=True, use_container_width=True)


if page == "🏠 CEO Dashboard":
    dashboard()
elif page == "👥 部門管理":
    simple_table(depts, "👥 部門管理", ["部門", "狀態"])
elif page == "🏢 事業體總覽":
    simple_table(units, "🏢 事業體總覽", ["事業體", "主要部門", "基本資料", "組織架構", "狀態"])
elif page == "📋 SOP 流程庫":
    simple_table(sops, "📋 SOP 流程庫", ["星期", "項目名稱", "工作內容", "部門", "負責人", "使用工具", "狀態"])
elif page == "📝 會議紀錄":
    simple_table(meets, "📝 會議紀錄", ["標題", "日期", "部門", "事業體", "出席人", "重點摘要", "決議事項"])
elif page == "🧭 決策紀錄":
    simple_table(decides, "🧭 決策紀錄", ["決策名稱", "日期", "部門", "背景", "決策內容", "決策人"])
elif page == "📈 KPI 追蹤":
    simple_table(kpis, "📈 KPI 追蹤", ["KPI 名稱", "部門", "事業體", "週期", "目標值", "實際值", "狀態"])
elif page == "✅ 公司代辦事項":
    simple_table(todos, "✅ 公司代辦事項", ["任務名稱", "狀態", "截止時間", "負責人"])
