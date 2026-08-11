"""
AI OS · CEO Dashboard (Streamlit + Notion 即時版)
--------------------------------------------------
每次打開這個網頁，都會即時去 Notion 抓最新資料再畫出來。
Notion 存取權杖存在 Streamlit 的 Secrets，瀏覽器端看不到，安全。

視覺風格：沿用深色科技底，並加入 Apple / Rolls-Royce 官網那種「大氣」質感——
更大的留白、細金色分隔線、優雅襯線大標、極簡的資料呈現方式。
部署方式請見 DEPLOY_GUIDE.md。

注意：所有自訂 HTML 一律透過 st.html() 輸出，不要改用 st.markdown(unsafe_allow_html=True) ——
Streamlit 的 markdown 解析器會把縮排超過 4 個空白的行當成「程式碼區塊」，
導致 <style> 內容整段變成頁面上的亂碼文字。st.html() 直接輸出原始 HTML，沒有這個問題。
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
DB_NOTES       = "41f420e39b8541059fd806ebe8f79020"   # 學習筆記（Knowledge OS）
DB_CONTENT     = "edcee0adb48244c1a85de65b783e4c2b"   # 內容項目（Content OS）
DB_LIFE_GOALS  = "a77069e3aa214d0b9feedacddb3c6a0e"   # 人生目標（Life OS）
DB_PROJECTS    = "932b40be8f154bdca8c74c6189af9833"   # 專案管理

NOTION_API = "https://api.notion.com/v1"

st.set_page_config(page_title="AI OS · CEO Dashboard", page_icon="🧠", layout="wide")

# ---------------------------------------------------------------------------
# 視覺風格
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#08090D", "panel": "#12141C", "panel2": "#171A24", "line": "#232631",
    "text": "#F0F0F2", "text_soft": "#9B9EAC", "text_faint": "#5C5F6C",
    "grad1": "#6C5CE7", "grad2": "#4FD1E8",
    "gold": "#C9A24B", "gold_soft": "rgba(201,162,75,.14)", "gold_line": "rgba(201,162,75,.35)",
    "green": "#3ECF8E", "green_soft": "rgba(62,207,142,.12)",
    "amber": "#E8B85C", "amber_soft": "rgba(232,184,92,.12)",
    "grey": "#565A68", "grey_soft": "rgba(255,255,255,.05)",
    "red": "#E07A7A", "red_soft": "rgba(224,122,122,.12)",
}

STATUS_COLOR = {
    "完成": ("green", "green_soft"), "已建立": ("green", "green_soft"), "達標": ("green", "green_soft"),
    "已發布": ("green", "green_soft"),
    "進行中": ("amber", "amber_soft"), "待優化": ("amber", "amber_soft"),
    "腳本撰寫": ("amber", "amber_soft"), "拍攝中": ("amber", "amber_soft"),
    "剪輯中": ("amber", "amber_soft"), "待發布": ("amber", "amber_soft"),
    "待補充": ("grey", "grey_soft"), "未開始": ("grey", "grey_soft"), "已封存": ("grey", "grey_soft"),
    "發想中": ("grey", "grey_soft"), "規劃中": ("grey", "grey_soft"),
    "落後": ("red", "red_soft"), "暫停": ("red", "red_soft"),
}


def inject_css():
    css = "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    css += ("<link href='https://fonts.googleapis.com/css2?"
            "family=Noto+Sans+TC:wght@300;400;500;600;700&"
            "family=Inter:wght@400;500;600;700&"
            "family=Playfair+Display:wght@500;600;700&"
            "family=JetBrains+Mono:wght@400;500;600&display=swap' rel='stylesheet'>")
    css += "<style>"
    css += "html,body,[class*='css']{font-family:'Inter','Noto Sans TC',sans-serif;}"
    css += (".stApp{background:radial-gradient(1400px 700px at 50% -20%,rgba(201,162,75,.05),transparent 60%),"
            + PALETTE['bg'] + ";color:" + PALETTE['text'] + ";}")
    css += "div.block-container{padding-top:3.2rem;padding-left:4.5rem;padding-right:4.5rem;padding-bottom:4rem;max-width:1440px;}"
    css += "section[data-testid='stSidebar']{background:#08090D;border-right:1px solid " + PALETTE['line'] + ";}"
    css += "section[data-testid='stSidebar'] .block-container{padding-top:2.6rem;padding-left:1.8rem;padding-right:1.6rem;}"

    # 品牌區
    css += ".aios-brand{padding:0 2px 8px;}"
    css += ".aios-brand .eyebrow{font-size:9.5px;letter-spacing:.24em;color:" + PALETTE['gold'] + ";text-transform:uppercase;margin-bottom:9px;}"
    css += ".aios-brand .name{font-family:'Playfair Display',serif;font-weight:600;font-size:21px;color:" + PALETTE['text'] + ";letter-spacing:.01em;}"
    css += ".aios-brand .tag{font-size:10.5px;color:" + PALETTE['text_faint'] + ";margin-top:6px;letter-spacing:.03em;}"
    css += ".aios-rule{border:none;border-top:1px solid " + PALETTE['gold_line'] + ";margin:20px 0 22px;}"

    # 側邊導覽
    css += "section[data-testid='stSidebar'] div[role='radiogroup']{gap:2px;}"
    css += "section[data-testid='stSidebar'] div[role='radiogroup'] label{padding:11px 12px;border-radius:8px;margin-bottom:1px;transition:.18s;}"
    css += "section[data-testid='stSidebar'] div[role='radiogroup'] label:hover{background:rgba(201,162,75,.07);}"
    css += "section[data-testid='stSidebar'] p{font-size:13px;letter-spacing:.01em;}"
    css += "section[data-testid='stSidebar'] hr{border-color:" + PALETTE['line'] + ";margin:22px 0;}"
    css += "section[data-testid='stSidebar'] .stButton button{background:transparent;color:" + PALETTE['text_soft'] + ";border:1px solid " + PALETTE['line'] + ";border-radius:8px;font-size:12.5px;letter-spacing:.02em;}"
    css += "section[data-testid='stSidebar'] .stButton button:hover{border-color:" + PALETTE['gold_line'] + ";color:" + PALETTE['gold'] + ";}"
    css += "section[data-testid='stSidebar'] .stCaption{color:" + PALETTE['text_faint'] + " !important;}"

    # Hero
    css += ".aios-eyebrow{font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:" + PALETTE['gold'] + ";margin-bottom:14px;}"
    css += ".aios-hero-title{font-family:'Playfair Display',serif;font-weight:600;font-size:44px;letter-spacing:.005em;color:" + PALETTE['text'] + ";margin:0 0 14px;line-height:1.15;}"
    css += ".aios-hero-sub{font-size:14px;color:" + PALETTE['text_soft'] + ";font-weight:300;max-width:640px;line-height:1.7;margin-bottom:6px;}"
    css += ".aios-hero-rule{border:none;border-top:1px solid " + PALETTE['gold_line'] + ";width:64px;margin:26px 0 38px;}"

    # 統計卡
    css += ("div[data-testid='stMetric']{background:" + PALETTE['panel'] + ";border:1px solid " + PALETTE['line'] +
            ";border-top:1px solid " + PALETTE['gold_line'] + ";border-radius:2px;padding:26px 28px;}")
    css += "div[data-testid='stMetricLabel']{color:" + PALETTE['text_faint'] + ";font-size:10.5px;text-transform:uppercase;letter-spacing:.16em;font-weight:500;}"
    css += "div[data-testid='stMetricValue']{color:" + PALETTE['text'] + ";font-family:'Playfair Display',serif;font-weight:600;font-size:34px;margin-top:6px;}"

    # 面板
    css += ".aios-panel{background:" + PALETTE['panel'] + ";border:1px solid " + PALETTE['line'] + ";border-radius:2px;padding:30px 32px;margin-bottom:26px;}"
    css += (".aios-panel h3{font-size:11px;font-weight:600;margin:0 0 22px;color:" + PALETTE['text_soft'] +
            ";text-transform:uppercase;letter-spacing:.18em;padding-bottom:16px;border-bottom:1px solid " + PALETTE['gold_line'] + ";}")
    css += ".aios-panel h3 .hint{font-size:10.5px;color:" + PALETTE['text_faint'] + ";font-weight:400;text-transform:none;letter-spacing:.02em;margin-left:10px;}"

    # 列
    css += ".aios-row{display:flex;align-items:center;gap:16px;padding:16px 2px;border-bottom:1px solid " + PALETTE['grey_soft'] + ";font-size:13.5px;}"
    css += ".aios-row:last-child{border-bottom:none;padding-bottom:2px;}"
    css += ".aios-row:first-child{padding-top:2px;}"
    css += ".aios-row .label{flex:1;color:" + PALETTE['text'] + ";font-weight:400;}"
    css += ".aios-row .sub{color:" + PALETTE['text_faint'] + ";font-size:11.5px;}"
    css += ".aios-track{flex:2;height:2px;background:" + PALETTE['grey_soft'] + ";overflow:hidden;}"
    css += ".aios-fill{height:100%;}"

    # 狀態標籤：改成細邊框、無填色的低調樣式
    css += (".aios-pill{font-family:'JetBrains Mono',monospace;font-size:9.5px;padding:4px 10px;border-radius:1px;"
            "font-weight:500;white-space:nowrap;letter-spacing:.05em;text-transform:uppercase;border:1px solid currentColor;background:transparent !important;}")

    # 表格
    css += "div[data-testid='stDataFrame']{background:" + PALETTE['panel'] + ";border-radius:2px;border:1px solid " + PALETTE['line'] + ";overflow:hidden;}"

    css += "h1,h2,h3{letter-spacing:-.01em;}"
    css += "</style>"
    st.html(css)


def status_pill(status: str) -> str:
    if not status:
        status = "待補充"
    color_key, bg_key = STATUS_COLOR.get(status, ("grey", "grey_soft"))
    return f'<span class="aios-pill" style="color:{PALETTE[color_key]}">{status}</span>'


def render_panel(title: str, rows: list, line_fn, hint: str = "", empty_text: str = "尚無資料"):
    hint_html = f'<span class="hint">{hint}</span>' if hint else ""
    body = f'<div class="aios-panel"><h3>{title}{hint_html}</h3>'
    if not rows:
        body += f'<div style="color:{PALETTE["text_faint"]};font-size:12.5px;padding:10px 2px;">{empty_text}</div>'
    else:
        body += "".join(line_fn(r) for r in rows)
    body += "</div>"
    st.html(body)


def hero(eyebrow: str, title: str, subtitle: str = ""):
    sub_html = f'<div class="aios-hero-sub">{subtitle}</div>' if subtitle else ""
    st.html(f'<div class="aios-eyebrow">{eyebrow}</div>'
            f'<div class="aios-hero-title">{title}</div>'
            f'{sub_html}<hr class="aios-hero-rule">')


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
notes   = query_db(DB_NOTES)
content = query_db(DB_CONTENT)
goals   = query_db(DB_LIFE_GOALS)
projects = query_db(DB_PROJECTS)

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
for r in notes:
    r["對應事業體"] = resolve_relation(r.get("對應事業體"), unit_map)
    r["對應部門"] = resolve_relation(r.get("對應部門"), dept_map)
for r in content:
    r["所屬事業體"] = resolve_relation(r.get("所屬事業體"), unit_map)
for r in projects:
    r["部門"] = resolve_relation(r.get("部門"), dept_map)
    r["事業體"] = resolve_relation(r.get("事業體"), unit_map)

# ---------------------------------------------------------------------------
# 側邊欄
# ---------------------------------------------------------------------------
st.sidebar.html(
    '<div class="aios-brand">'
    '<div class="eyebrow">Second Brain</div>'
    '<div class="name">AI OS</div>'
    '<div class="tag">我的第二大腦與企業管理系統</div>'
    '</div><hr class="aios-rule">'
)
if st.sidebar.button("重新整理　·　立即抓取最新資料"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"每 60 秒自動更新　·　{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "前往",
    ["🏠 CEO Dashboard",
     "👥 部門管理", "🏢 事業體總覽", "📋 SOP 流程庫", "📁 專案管理",
     "📝 會議紀錄", "🧭 決策紀錄", "📈 KPI 追蹤", "✅ 公司代辦事項",
     "📖 學習筆記", "✍️ 內容項目", "🎯 人生目標"],
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Dashboard 頁
# ---------------------------------------------------------------------------
def dashboard():
    hero("AI OS · CEO Dashboard", "早安", "這裡是目前 Notion 真實資料的即時總覽，涵蓋公司營運、知識、內容與人生四大系統。")

    depts_filled = sum(1 for d in depts if d.get("狀態") not in (None, "待補充"))
    units_filled = sum(1 for u in units if u.get("狀態") not in (None, "待補充"))
    open_todos = sum(1 for t in todos if t.get("狀態") not in ("完成", "已封存"))

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.metric("事業體資料", f"{units_filled} / {len(units)}")
    c2.metric("部門資料", f"{depts_filled} / {len(depts)}")
    c3.metric("SOP 項目數", len(sops))
    c4.metric("待辦事項", open_todos)

    st.write("")
    st.write("")
    left, right = st.columns([1.5, 1], gap="large")

    with left:
        order = {"待補充": 0, "進行中": 60, "完成": 100}
        color_map = {"待補充": PALETTE["grey"], "進行中": PALETTE["amber"], "完成": PALETTE["green"]}

        def dept_row(d):
            status = d.get("狀態") or "待補充"
            pct = order.get(status, 0)
            color = color_map.get(status, PALETTE["grey"])
            return (f'<div class="aios-row">'
                    f'<span class="label" style="flex:0 0 100px;">{d.get("部門","")}</span>'
                    f'<div class="aios-track"><div class="aios-fill" style="width:{pct}%;background:{color}"></div></div>'
                    f'{status_pill(status)}</div>')

        render_panel("部門狀態", depts, dept_row, hint="依實際填寫內容")

        order2 = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
        sorted_sops = sorted(sops, key=lambda r: order2.get(r.get("星期"), 9))
        render_panel(
            "本週 SOP", sorted_sops,
            lambda r: (f'<div class="aios-row">'
                       f'<span style="flex:0 0 26px;color:{PALETTE["text_faint"]}">{r.get("星期","")}</span>'
                       f'<span class="label">{r.get("項目名稱","")}<span class="sub"> · {r.get("部門","")}</span></span>'
                       f'{status_pill(r.get("狀態"))}</div>'),
            hint="依星期排序", empty_text="尚無 SOP 資料",
        )

        render_panel(
            "進行中專案", [p for p in projects if p.get("進度") not in ("已完成",)],
            lambda r: (f'<div class="aios-row">'
                       f'<span class="label">{r.get("專案名稱","")}<span class="sub"> · {r.get("部門","") or r.get("事業體","")}</span></span>'
                       f'{status_pill(r.get("進度"))}</div>'),
            empty_text="尚無進行中的專案",
        )

    with right:
        render_panel(
            "公司代辦事項", todos,
            lambda r: (f'<div class="aios-row">'
                       f'<span class="label">{r.get("任務名稱","")}<span class="sub"> · {r.get("負責人") or "未指派"}</span></span>'
                       f'{status_pill(r.get("狀態"))}</div>'),
            empty_text="尚無代辦事項",
        )

        sorted_meets = sorted(meets, key=lambda r: r.get("日期") or "", reverse=True)[:5]
        render_panel(
            "最近會議", sorted_meets,
            lambda r: (f'<div class="aios-row">'
                       f'<span class="label">{r.get("標題","")}<span class="sub"> · {r.get("部門","")}</span></span>'
                       f'<span class="sub">{r.get("日期") or ""}</span></div>'),
            empty_text="尚無會議紀錄",
        )

        sorted_notes = sorted(notes, key=lambda r: r.get("日期") or "", reverse=True)[:5]
        render_panel(
            "最新學習筆記", sorted_notes,
            lambda r: (f'<div class="aios-row">'
                       f'<span class="label">{r.get("標題","")}<span class="sub"> · {r.get("分類","")}</span></span>'
                       f'{status_pill(r.get("狀態"))}</div>'),
            empty_text="尚無筆記",
        )


def simple_table(rows, eyebrow, title, cols=None):
    hero(eyebrow, title)
    if not rows:
        st.html(f'<div style="color:{PALETTE["text_faint"]};padding:10px 0;">尚無資料</div>')
        return
    df = pd.DataFrame(rows)
    if cols:
        cols = [c for c in cols if c in df.columns]
        df = df[cols]
    st.dataframe(df, hide_index=True, use_container_width=True)


if page == "🏠 CEO Dashboard":
    dashboard()
elif page == "👥 部門管理":
    simple_table(depts, "公司營運 OS", "部門管理", ["部門", "狀態"])
elif page == "🏢 事業體總覽":
    simple_table(units, "公司營運 OS", "事業體總覽", ["事業體", "主要部門", "基本資料", "組織架構", "狀態"])
elif page == "📋 SOP 流程庫":
    simple_table(sops, "公司營運 OS", "SOP 流程庫", ["星期", "項目名稱", "工作內容", "部門", "負責人", "使用工具", "狀態"])
elif page == "📁 專案管理":
    simple_table(projects, "公司營運 OS", "專案管理", ["專案名稱", "部門", "事業體", "目標", "負責人", "開始日期", "預計完成", "進度", "風險"])
elif page == "📝 會議紀錄":
    simple_table(meets, "公司營運 OS", "會議紀錄", ["標題", "日期", "部門", "事業體", "出席人", "重點摘要", "決議事項"])
elif page == "🧭 決策紀錄":
    simple_table(decides, "公司營運 OS", "決策紀錄", ["決策名稱", "日期", "部門", "背景", "決策內容", "決策人"])
elif page == "📈 KPI 追蹤":
    simple_table(kpis, "公司營運 OS", "KPI 追蹤", ["KPI 名稱", "部門", "事業體", "週期", "目標值", "實際值", "狀態"])
elif page == "✅ 公司代辦事項":
    simple_table(todos, "公司營運 OS", "公司代辦事項", ["任務名稱", "狀態", "截止時間", "負責人"])
elif page == "📖 學習筆記":
    simple_table(notes, "Knowledge OS", "學習筆記",
                 ["標題", "分類", "來源", "核心概念", "我的理解", "實際案例", "如何應用到我的公司", "延伸思考問題", "對應事業體", "對應部門", "日期", "狀態"])
elif page == "✍️ 內容項目":
    simple_table(content, "Content OS", "內容項目",
                 ["標題", "平台", "內容主題", "所屬事業體", "內容方向", "腳本文案", "拍攝想法", "品牌故事連結", "發布日期", "狀態"])
elif page == "🎯 人生目標":
    simple_table(goals, "Life OS", "人生目標",
                 ["項目", "類別", "目標內容", "為什麼重要", "關鍵行動", "衡量方式", "與公司目標的關聯", "年度", "狀態"])
