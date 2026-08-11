"""
AI OS · CEO Dashboard (Streamlit + Notion 即時版)
--------------------------------------------------
每次打開這個網頁，都會即時去 Notion 抓最新資料再畫出來。
Notion 存取權杖存在 Streamlit 的 Secrets，瀏覽器端看不到，安全。

視覺風格沿用原本那份深色 HTML Dashboard 的設計語言。
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
# 視覺風格：沿用原本 HTML 版本的深色配色
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#0E1016", "panel": "#181B25", "panel2": "#1D202B", "line": "#262A38",
    "text": "#E7E8EE", "text_soft": "#9296A8", "text_faint": "#5C6072",
    "grad1": "#6C5CE7", "grad2": "#4FD1E8",
    "green": "#3ECF8E", "green_soft": "rgba(62,207,142,.12)",
    "amber": "#F5B84D", "amber_soft": "rgba(245,184,77,.12)",
    "grey": "#4A4E5C", "grey_soft": "rgba(255,255,255,.05)",
    "red": "#F56B6B", "red_soft": "rgba(245,107,107,.12)",
}

STATUS_COLOR = {
    "完成": ("green", "green_soft"), "已建立": ("green", "green_soft"), "達標": ("green", "green_soft"),
    "進行中": ("amber", "amber_soft"), "待優化": ("amber", "amber_soft"),
    "待補充": ("grey", "grey_soft"), "未開始": ("grey", "grey_soft"), "已封存": ("grey", "grey_soft"),
    "落後": ("red", "red_soft"),
}


def inject_css():
    st.markdown(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] {{
        font-family: 'Inter','Noto Sans TC',sans-serif;
      }}
      .stApp {{ background: {PALETTE['bg']}; color: {PALETTE['text']}; }}
      section[data-testid="stSidebar"] {{
        background: #12141C; border-right: 1px solid {PALETTE['line']};
      }}
      .aios-brand {{ display:flex; align-items:center; gap:10px; padding:6px 4px 18px; }}
      .aios-logo {{
        width:32px; height:32px; border-radius:9px; flex-shrink:0;
        background: conic-gradient(from 180deg, {PALETTE['grad1']}, {PALETTE['grad2']}, {PALETTE['grad1']});
      }}
      .aios-brand .name {{ font-weight:700; font-size:15px; color:{PALETTE['text']}; }}
      .aios-brand .tag {{ font-size:10px; color:{PALETTE['text_faint']}; }}

      div[data-testid="stMetric"] {{
        background: {PALETTE['panel']}; border: 1px solid {PALETTE['line']};
        border-radius: 14px; padding: 14px 18px;
      }}
      div[data-testid="stMetricLabel"] {{ color: {PALETTE['text_soft']}; }}
      div[data-testid="stMetricValue"] {{ color: {PALETTE['text']}; }}

      .aios-panel {{
        background: {PALETTE['panel']}; border: 1px solid {PALETTE['line']};
        border-radius: 14px; padding: 18px 20px; margin-bottom: 16px;
      }}
      .aios-panel h3 {{ font-size:14px; font-weight:700; margin:0 0 12px; color:{PALETTE['text']}; }}
      .aios-panel h3 .hint {{ font-size:11px; color:{PALETTE['text_faint']}; font-weight:400; margin-left:6px; }}

      .aios-row {{
        display:flex; align-items:center; gap:12px; padding:8px 0;
        border-bottom:1px solid {PALETTE['grey_soft']}; font-size:13px;
      }}
      .aios-row:last-child {{ border-bottom:none; }}
      .aios-row .label {{ flex:1; color:{PALETTE['text']}; }}
      .aios-row .sub {{ color:{PALETTE['text_faint']}; font-size:11.5px; }}

      .aios-track {{ flex:2; height:7px; background:{PALETTE['grey_soft']}; border-radius:6px; overflow:hidden; }}
      .aios-fill {{ height:100%; border-radius:6px; }}

      .aios-pill {{
        font-size:10.5px; padding:3px 10px; border-radius:20px; font-weight:600;
        white-space:nowrap;
      }}

      div[data-testid="stDataFrame"] {{
        background: {PALETTE['panel']}; border-radius: 12px; border: 1px solid {PALETTE['line']};
      }}

      .stRadio > label {{ color: {PALETTE['text_soft']}; }}
      section[data-testid="stSidebar"] .stButton button {{
        background: {PALETTE['panel2']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['line']};
        border-radius: 9px;
      }}
    </style>
    """, unsafe_allow_html=True)


def status_pill(status: str) -> str:
    if not status:
        status = "待補充"
    color_key, bg_key = STATUS_COLOR.get(status, ("grey", "grey_soft"))
    return (f'<span class="aios-pill" style="color:{PALETTE[color_key]};'
            f'background:{PALETTE[bg_key]}">{status}</span>')


def panel_open(title: str, hint: str = ""):
    hint_html = f'<span class="hint">{hint}</span>' if hint else ""
    st.markdown(f'<div class="aios-panel"><h3>{title}{hint_html}</h3>', unsafe_allow_html=True)


def panel_close():
    st.markdown('</div>', unsafe_allow_html=True)


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
inject_css()

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
st.sidebar.markdown(
    '<div class="aios-brand"><div class="aios-logo"></div>'
    '<div><div class="name">AI OS</div><div class="tag">我的第二大腦與企業系統</div></div></div>',
    unsafe_allow_html=True,
)
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
# 小元件：部門進度條 / 狀態列表
# ---------------------------------------------------------------------------
def dept_progress_panel():
    panel_open("部門狀態", "依實際填寫內容")
    order = {"待補充": 0, "進行中": 60, "完成": 100}
    color_map = {"待補充": PALETTE["grey"], "進行中": PALETTE["amber"], "完成": PALETTE["green"]}
    for d in depts:
        status = d.get("狀態") or "待補充"
        pct = order.get(status, 0)
        color = color_map.get(status, PALETTE["grey"])
        st.markdown(f"""
        <div class="aios-row">
          <span class="label" style="flex:0 0 90px;">{d.get('部門','')}</span>
          <div class="aios-track"><div class="aios-fill" style="width:{pct}%;background:{color}"></div></div>
          {status_pill(status)}
        </div>
        """, unsafe_allow_html=True)
    panel_close()


def list_panel(title, rows, line_fn, hint="", empty_text="尚無資料"):
    panel_open(title, hint)
    if not rows:
        st.markdown(f'<div style="color:{PALETTE["text_faint"]};font-size:12.5px;padding:8px 0;">{empty_text}</div>',
                     unsafe_allow_html=True)
    else:
        for r in rows:
            st.markdown(line_fn(r), unsafe_allow_html=True)
    panel_close()


# ---------------------------------------------------------------------------
# Dashboard 頁
# ---------------------------------------------------------------------------
def dashboard():
    st.markdown(f"<h1 style='margin-bottom:2px'>早安 🌿</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{PALETTE['text_soft']};font-size:13px;margin-bottom:22px'>"
                f"這裡是目前 Notion 真實資料的即時總覽。</p>", unsafe_allow_html=True)

    depts_filled = sum(1 for d in depts if d.get("狀態") not in (None, "待補充"))
    units_filled = sum(1 for u in units if u.get("狀態") not in (None, "待補充"))
    open_todos = sum(1 for t in todos if t.get("狀態") not in ("完成", "已封存"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("事業體資料", f"{units_filled} / {len(units)}")
    c2.metric("部門資料", f"{depts_filled} / {len(depts)}")
    c3.metric("SOP 項目數", len(sops))
    c4.metric("待辦事項（未完成）", open_todos)

    st.write("")
    left, right = st.columns([1.5, 1])

    with left:
        dept_progress_panel()

        order = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
        sorted_sops = sorted(sops, key=lambda r: order.get(r.get("星期"), 9))
        list_panel(
            "本週 SOP", sorted_sops,
            lambda r: f"""<div class="aios-row">
                <span style="flex:0 0 24px;color:{PALETTE['text_faint']}">{r.get('星期','')}</span>
                <span class="label">{r.get('項目名稱','')}<span class="sub"> · {r.get('部門','')}</span></span>
                {status_pill(r.get('狀態'))}
              </div>""",
            hint="依星期排序", empty_text="尚無 SOP 資料",
        )

    with right:
        list_panel(
            "公司代辦事項", todos,
            lambda r: f"""<div class="aios-row">
                <span class="label">{r.get('任務名稱','')}<span class="sub"> · {r.get('負責人') or '未指派'}</span></span>
                {status_pill(r.get('狀態'))}
              </div>""",
            empty_text="尚無代辦事項",
        )

        sorted_meets = sorted(meets, key=lambda r: r.get("日期") or "", reverse=True)[:5]
        list_panel(
            "最近會議", sorted_meets,
            lambda r: f"""<div class="aios-row">
                <span class="label">{r.get('標題','')}<span class="sub"> · {r.get('部門','')}</span></span>
                <span class="sub">{r.get('日期') or ''}</span>
              </div>""",
            empty_text="尚無會議紀錄",
        )


def simple_table(rows, title, cols=None):
    st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
    if not rows:
        st.markdown(f'<div style="color:{PALETTE["text_faint"]};padding:20px 0;">尚無資料</div>',
                     unsafe_allow_html=True)
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
