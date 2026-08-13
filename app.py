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
from datetime import datetime, date, timedelta
import json
import re

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
OPENAI_API = "https://api.openai.com/v1/responses"

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

    # 分組側邊導覽標籤
    css += (".aios-navgroup-label{font-size:10px;letter-spacing:.14em;color:" + PALETTE['text_faint'] +
            ";text-transform:uppercase;font-weight:600;margin:18px 4px 6px;}")
    css += "section[data-testid='stSidebar'] .stButton button{justify-content:flex-start;text-align:left;}"
    css += ("section[data-testid='stSidebar'] .stButton button[kind='primary']{background:linear-gradient(90deg, rgba(201,162,75,.22), rgba(201,162,75,.06));"
            "color:#fff;border:1px solid " + PALETTE['gold_line'] + ";font-weight:600;}")

    # 一般按鈕（主內容區）
    css += "div.stButton button{background:" + PALETTE['panel2'] + ";color:" + PALETTE['text_soft'] + ";border:1px solid " + PALETTE['line'] + ";border-radius:8px;font-size:12.5px;}"
    css += "div.stButton button:hover{border-color:" + PALETTE['gold_line'] + ";color:" + PALETTE['gold'] + ";}"
    css += "div.stButton button[kind='primary'],.stFormSubmitButton button[kind='primary']{background:" + PALETTE['gold'] + ";color:#08090D;border:none;font-weight:600;}"
    css += "div.stButton button[kind='primary']:hover,.stFormSubmitButton button[kind='primary']:hover{opacity:.88;}"
    css += "div[data-testid='stExpander']{background:" + PALETTE['panel'] + ";border:1px solid " + PALETTE['line'] + ";border-radius:2px;}"

    # 統計卡（stat-grid）
    css += ".aios-statgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:8px;}"
    css += (".aios-statcard{background:" + PALETTE['panel'] + ";border:1px solid " + PALETTE['line'] +
            ";border-top:1px solid " + PALETTE['gold_line'] + ";border-radius:2px;padding:22px 24px;}")
    css += ".aios-statcard-top{display:flex;justify-content:space-between;align-items:flex-start;}"
    css += ".aios-statcard-label{font-size:10.5px;text-transform:uppercase;letter-spacing:.14em;color:" + PALETTE['text_faint'] + ";}"
    css += ".aios-statcard-icon{font-size:15px;opacity:.85;}"
    css += ".aios-statcard-num{font-family:'Playfair Display',serif;font-weight:600;font-size:30px;color:" + PALETTE['text'] + ";margin:8px 0 3px;}"
    css += ".aios-statcard-note{font-size:11px;color:" + PALETTE['text_faint'] + ";}"

    # 事業體 chip 網格
    css += ".aios-chipgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;}"
    css += (".aios-chip{display:flex;align-items:center;gap:9px;padding:11px 13px;background:" + PALETTE['panel2'] +
            ";border:1px solid " + PALETTE['line'] + ";border-radius:2px;font-size:12.5px;}")
    css += ".aios-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;background:" + PALETTE['grey'] + ";}"
    css += ".aios-chip-status{font-size:10.5px;color:" + PALETTE['text_faint'] + ";display:block;margin-top:2px;}"

    # 觀察小語（tips / 排程摘要）
    css += (".aios-tip{display:flex;gap:9px;padding:11px 2px;border-bottom:1px solid " + PALETTE['grey_soft'] +
            ";font-size:12.5px;line-height:1.6;}")
    css += ".aios-tip:last-child{border-bottom:none;}"
    css += ".aios-tip .aios-dot{margin-top:5px;}"
    css += ".aios-tip b{color:" + PALETTE['text'] + ";font-weight:600;}"
    css += ".aios-tip span{color:" + PALETTE['text_soft'] + ";}"

    # 收集進度 checklist
    css += ".aios-checkrow{display:flex;align-items:center;gap:10px;padding:9px 2px;font-size:12.5px;}"
    css += ".aios-checkbox{width:14px;height:14px;border-radius:4px;border:1.5px solid " + PALETTE['grey'] + ";flex-shrink:0;}"
    css += ".aios-checkbox.done{background:" + PALETTE['green'] + ";border-color:" + PALETTE['green'] + ";}"
    css += ".aios-checkbox.progress{background:" + PALETTE['amber_soft'] + ";border-color:" + PALETTE['amber'] + ";}"
    css += ".aios-checklabel{flex:1;color:" + PALETTE['text_soft'] + ";}"

    # 說明小卡（fact box）
    css += (".aios-factbox{display:flex;gap:8px;font-size:12.5px;color:" + PALETTE['text_soft'] + ";background:" + PALETTE['panel2'] +
            ";border:1px solid " + PALETTE['line'] + ";border-radius:2px;padding:12px 14px;margin-bottom:18px;line-height:1.6;}")

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


def resolve_and_keep(r: dict, field: str, mapping: dict):
    """把 relation 欄位轉成人看得懂的文字，同時把原始的 id 留一份給編輯表單用。"""
    r["_rel_" + field] = r.get(field) or []
    r[field] = resolve_relation(r.get(field), mapping)


# ---------------------------------------------------------------------------
# 新增／編輯／刪除（寫回 Notion）
# ---------------------------------------------------------------------------
def notion_create_page(db_id: str, properties: dict) -> bool:
    headers = get_headers()
    payload = {"parent": {"database_id": db_id}, "properties": properties}
    resp = requests.post(f"{NOTION_API}/pages", headers=headers, json=payload, timeout=30)
    if not resp.ok:
        st.error(f"新增失敗（{resp.status_code}）：{resp.text[:500]}")
        return False
    return True


def notion_update_page(page_id: str, properties: dict = None, archived: bool = None) -> bool:
    headers = get_headers()
    payload = {}
    if properties is not None:
        payload["properties"] = properties
    if archived is not None:
        payload["archived"] = archived
    resp = requests.patch(f"{NOTION_API}/pages/{page_id}", headers=headers, json=payload, timeout=30)
    if not resp.ok:
        st.error(f"更新失敗（{resp.status_code}）：{resp.text[:500]}")
        return False
    return True


def build_property(ftype: str, value):
    if ftype == "title":
        return {"title": [{"text": {"content": value}}] if value else []}
    if ftype == "text":
        return {"rich_text": [{"text": {"content": value}}] if value else []}
    if ftype == "select":
        return {"select": ({"name": value} if value else None)}
    if ftype == "status":
        return {"status": ({"name": value} if value else None)}
    if ftype == "date":
        if not value:
            return {"date": None}
        return {"date": {"start": value.isoformat() if hasattr(value, "isoformat") else str(value)}}
    if ftype == "relation":
        return {"relation": [{"id": i} for i in (value or [])]}
    return {}


# 每個資料庫的「新增/編輯」表單設定。
# fields 的每一項格式：(欄位名, 類型, ...額外參數)
# 類型："text"（多行文字）、"select"（單選）、"status"（Notion 狀態欄位）、"date"（日期）、"relation"（關聯到部門/事業體）
DB_FORMS = {
    "部門管理": {
        "db_id": None, "title_prop": "部門",
        "fields": [("狀態", "select", ["待補充", "進行中", "完成"])],
    },
    "事業體總覽": {
        "db_id": None, "title_prop": "事業體",
        "fields": [
            ("主要部門", "text"), ("基本資料", "text"), ("組織架構", "text"),
            ("狀態", "select", ["待補充", "進行中", "完成"]),
        ],
    },
    "SOP流程庫": {
        "db_id": None, "title_prop": "項目名稱",
        "fields": [
            ("星期", "select", ["一", "二", "三", "四", "五", "六", "日"]),
            ("工作內容", "text"), ("使用工具", "text"),
            ("狀態", "select", ["待補充", "已建立", "待優化"]),
            ("部門", "relation", "depts", "部門"),
        ],
    },
    "會議紀錄": {
        "db_id": None, "title_prop": "標題",
        "fields": [
            ("日期", "date"), ("重點摘要", "text"), ("決議事項", "text"),
            ("部門", "relation", "depts", "部門"),
            ("事業體", "relation", "units", "事業體"),
        ],
    },
    "決策紀錄": {
        "db_id": None, "title_prop": "決策名稱",
        "fields": [
            ("日期", "date"), ("背景", "text"), ("決策內容", "text"),
            ("部門", "relation", "depts", "部門"),
        ],
    },
    "KPI追蹤": {
        "db_id": None, "title_prop": "KPI 名稱",
        "fields": [
            ("週期", "select", ["週", "月", "季", "年"]),
            ("目標值", "text"), ("實際值", "text"),
            ("狀態", "select", ["待補充", "達標", "落後", "進行中"]),
            ("部門", "relation", "depts", "部門"),
            ("事業體", "relation", "units", "事業體"),
        ],
    },
    "公司代辦事項": {
        "db_id": None, "title_prop": "任務名稱",
        "fields": [
            ("截止時間", "date"),
            ("狀態", "status", ["未開始", "進行中", "完成", "已封存"]),
        ],
    },
    "學習筆記": {
        "db_id": None, "title_prop": "標題",
        "fields": [
            ("來源", "text"),
            ("分類", "select", ["MBA商業知識", "管理學", "芳療與香氛", "香水設計", "心理學", "AI與科技", "人生哲學"]),
            ("核心概念", "text"), ("我的理解", "text"), ("實際案例", "text"),
            ("如何應用到我的公司", "text"), ("延伸思考問題", "text"),
            ("日期", "date"),
            ("狀態", "select", ["待補充", "已建立"]),
            ("對應事業體", "relation", "units", "事業體"),
            ("對應部門", "relation", "depts", "部門"),
        ],
    },
    "內容項目": {
        "db_id": None, "title_prop": "標題",
        "fields": [
            ("平台", "select", ["微信服務號", "微信公眾號", "小紅書", "抖音", "Instagram"]),
            ("內容主題", "text"), ("內容方向", "text"), ("腳本文案", "text"),
            ("拍攝想法", "text"), ("品牌故事連結", "text"),
            ("發布日期", "date"),
            ("狀態", "select", ["發想中", "腳本撰寫", "拍攝中", "剪輯中", "待發布", "已發布"]),
            ("所屬事業體", "relation", "units", "事業體"),
        ],
    },
    "人生目標": {
        "db_id": None, "title_prop": "項目",
        "fields": [
            ("類別", "select", ["年度目標", "個人成長", "健康管理", "學習計畫", "理想生活規劃"]),
            ("目標內容", "text"), ("為什麼重要", "text"), ("關鍵行動", "text"),
            ("衡量方式", "text"), ("與公司目標的關聯", "text"), ("年度", "text"),
            ("狀態", "select", ["待補充", "進行中", "完成"]),
        ],
    },
    "專案管理": {
        "db_id": None, "title_prop": "專案名稱",
        "fields": [
            ("目標", "text"),
            ("開始日期", "date"), ("預計完成", "date"),
            ("進度", "select", ["規劃中", "進行中", "已完成", "暫停"]),
            ("風險", "text"),
            ("部門", "relation", "depts", "部門"),
            ("事業體", "relation", "units", "事業體"),
        ],
    },
}


def _parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def crud_section(form_key: str, rows: list, target_rows: dict, expand_add: bool = False):
    """畫出「➕ 新增」與「✏️ 編輯 / 🗑️ 刪除」兩個可展開區塊，並把變更寫回 Notion。"""
    cfg = DB_FORMS[form_key]
    db_id = cfg["db_id"]
    title_prop = cfg["title_prop"]

    with st.expander("➕ 新增一筆資料", expanded=expand_add):
        with st.form(f"add_{form_key}", clear_on_submit=True):
            title_val = st.text_input(title_prop)
            values = {}
            for f in cfg["fields"]:
                fname, ftype = f[0], f[1]
                key = f"add_{form_key}_{fname}"
                if ftype in ("select", "status"):
                    opts = f[2]
                    values[fname] = st.selectbox(fname, [""] + opts, key=key)
                elif ftype == "text":
                    values[fname] = st.text_area(fname, height=80, key=key)
                elif ftype == "date":
                    values[fname] = st.date_input(fname, value=None, key=key)
                elif ftype == "relation":
                    target_key, target_title = f[2], f[3]
                    opt_map = {r.get(target_title): r["_id"] for r in target_rows[target_key] if r.get(target_title)}
                    picks = st.multiselect(fname, list(opt_map.keys()), key=key)
                    values[fname] = [opt_map[p] for p in picks]
            submitted = st.form_submit_button("送出新增", type="primary")
            if submitted:
                if not title_val:
                    st.error("請輸入標題")
                else:
                    props = {title_prop: build_property("title", title_val)}
                    for f in cfg["fields"]:
                        fname, ftype = f[0], f[1]
                        props[fname] = build_property(ftype, values[fname])
                    if notion_create_page(db_id, props):
                        st.success("新增成功，已寫入 Notion。")
                        st.cache_data.clear()
                        st.rerun()

    if not rows:
        return

    with st.expander("✏️ 編輯或刪除既有資料"):
        options = {(r.get(title_prop) or "（未命名）") + f"　·　{r['_id'][:8]}": r for r in rows}
        picked_label = st.selectbox("選擇要編輯的項目", list(options.keys()), key=f"pick_{form_key}")
        picked = options[picked_label]

        with st.form(f"edit_{form_key}"):
            new_title = st.text_input(title_prop, value=picked.get(title_prop) or "", key=f"edit_title_{form_key}")
            values = {}
            for f in cfg["fields"]:
                fname, ftype = f[0], f[1]
                key = f"edit_{form_key}_{fname}"
                cur = picked.get(fname)
                if ftype in ("select", "status"):
                    opts = f[2]
                    idx = ([""] + opts).index(cur) if cur in opts else 0
                    values[fname] = st.selectbox(fname, [""] + opts, index=idx, key=key)
                elif ftype == "text":
                    values[fname] = st.text_area(fname, value=cur or "", height=80, key=key)
                elif ftype == "date":
                    values[fname] = st.date_input(fname, value=_parse_date(cur), key=key)
                elif ftype == "relation":
                    target_key, target_title = f[2], f[3]
                    opt_map = {r.get(target_title): r["_id"] for r in target_rows[target_key] if r.get(target_title)}
                    cur_ids = picked.get("_rel_" + fname) or []
                    defaults = [t for t, i in opt_map.items() if i in cur_ids]
                    picks = st.multiselect(fname, list(opt_map.keys()), default=defaults, key=key)
                    values[fname] = [opt_map[p] for p in picks]
            col_a, col_b = st.columns([1, 1])
            save = col_a.form_submit_button("儲存變更", type="primary")
            delete = col_b.form_submit_button("🗑️ 刪除（封存）此筆資料")
            if save:
                props = {title_prop: build_property("title", new_title)}
                for f in cfg["fields"]:
                    fname, ftype = f[0], f[1]
                    props[fname] = build_property(ftype, values[fname])
                if notion_update_page(picked["_id"], properties=props):
                    st.success("已更新，資料同步回 Notion。")
                    st.cache_data.clear()
                    st.rerun()
            if delete:
                if notion_update_page(picked["_id"], archived=True):
                    st.success("已刪除（封存）。")
                    st.cache_data.clear()
                    st.rerun()


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
    resolve_and_keep(r, "部門", dept_map)
for r in meets:
    resolve_and_keep(r, "部門", dept_map)
    resolve_and_keep(r, "事業體", unit_map)
for r in decides:
    resolve_and_keep(r, "部門", dept_map)
for r in kpis:
    resolve_and_keep(r, "部門", dept_map)
    resolve_and_keep(r, "事業體", unit_map)
for r in notes:
    resolve_and_keep(r, "對應事業體", unit_map)
    resolve_and_keep(r, "對應部門", dept_map)
for r in content:
    resolve_and_keep(r, "所屬事業體", unit_map)
for r in projects:
    resolve_and_keep(r, "部門", dept_map)
    resolve_and_keep(r, "事業體", unit_map)

# 把資料庫 ID 灌回表單設定，並準備關聯欄位選單要用的來源資料
DB_FORMS["部門管理"]["db_id"] = DB_DEPARTMENTS
DB_FORMS["事業體總覽"]["db_id"] = DB_UNITS
DB_FORMS["SOP流程庫"]["db_id"] = DB_SOP
DB_FORMS["會議紀錄"]["db_id"] = DB_MEETINGS
DB_FORMS["決策紀錄"]["db_id"] = DB_DECISIONS
DB_FORMS["KPI追蹤"]["db_id"] = DB_KPI
DB_FORMS["公司代辦事項"]["db_id"] = DB_TODOS
DB_FORMS["學習筆記"]["db_id"] = DB_NOTES
DB_FORMS["內容項目"]["db_id"] = DB_CONTENT
DB_FORMS["人生目標"]["db_id"] = DB_LIFE_GOALS
DB_FORMS["專案管理"]["db_id"] = DB_PROJECTS
RELATION_TARGETS = {"depts": depts, "units": units}

# ---------------------------------------------------------------------------
# 巡覽結構 — 比照原始設計稿：分組側邊欄 + 大氣主視覺 + 真的可以點的互動
# ---------------------------------------------------------------------------
NOTE_CATS = ["MBA商業知識", "管理學", "芳療與香氛", "香水設計", "心理學", "AI與科技", "人生哲學"]
NOTE_ICONS = {"MBA商業知識": "📖", "管理學": "📈", "芳療與香氛": "🌿", "香水設計": "🧪",
              "心理學": "🧠", "AI與科技": "🤖", "人生哲學": "☯️"}

CONTENT_PLATFORMS = ["微信服務號", "微信公眾號", "小紅書", "抖音", "Instagram"]
CONTENT_ICONS = {"微信服務號": "💬", "微信公眾號": "📰", "小紅書": "📕", "抖音": "🎬", "Instagram": "📷"}

GOAL_CATS = ["年度目標", "個人成長", "健康管理", "學習計畫", "理想生活規劃"]
GOAL_ICONS = {"年度目標": "🎯", "個人成長": "🌱", "健康管理": "❤️", "學習計畫": "📚", "理想生活規劃": "✨"}

NAV = [
    {"group": "AI OS", "items": [
        {"id": "dashboard", "label": "CEO Dashboard", "icon": "🏠"},
        {"id": "ai_ceo", "label": "AI CEO", "icon": "🧠"},
    ]},
    {"group": "公司營運 OS", "items": [
        {"id": "units", "label": "事業體總覽", "icon": "🏢"},
        {"id": "depts", "label": "部門管理", "icon": "👥"},
        {"id": "sop", "label": "SOP 流程庫", "icon": "📋"},
        {"id": "projects", "label": "專案管理", "icon": "📁"},
        {"id": "meetings", "label": "會議紀錄", "icon": "📝"},
        {"id": "decisions", "label": "決策紀錄", "icon": "🧭"},
        {"id": "kpi", "label": "KPI 追蹤", "icon": "📈"},
        {"id": "todo", "label": "公司代辦事項", "icon": "✅"},
    ]},
    {"group": "知識庫 OS", "items": [{"id": "notes_all", "label": "全部筆記", "icon": "📚"}] +
        [{"id": f"note_{c}", "label": c, "icon": NOTE_ICONS[c]} for c in NOTE_CATS]},
    {"group": "內容創作 OS", "items": [{"id": "content_all", "label": "全部內容", "icon": "✍️"}] +
        [{"id": f"content_{p}", "label": p, "icon": CONTENT_ICONS[p]} for p in CONTENT_PLATFORMS]},
    {"group": "人生 OS", "items": [{"id": "goals_all", "label": "全部目標", "icon": "🎯"}] +
        [{"id": f"goal_{c}", "label": c, "icon": GOAL_ICONS[c]} for c in GOAL_CATS]},
]

if "nav" not in st.session_state:
    st.session_state.nav = "dashboard"
if "expand_add" not in st.session_state:
    st.session_state.expand_add = False


def go_to(nav_id: str, expand_add: bool = False):
    st.session_state.nav = nav_id
    st.session_state.expand_add = expand_add
    st.rerun()


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
if st.sidebar.button("重新整理　·　立即抓取最新資料", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"每 60 秒自動更新　·　{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

for g in NAV:
    st.sidebar.html(f'<div class="aios-navgroup-label">{g["group"]}</div>')
    for it in g["items"]:
        active = st.session_state.nav == it["id"]
        if st.sidebar.button(f'{it["icon"]}　{it["label"]}', key=f'nav_{it["id"]}',
                              use_container_width=True, type=("primary" if active else "secondary")):
            go_to(it["id"])

nav_id = st.session_state.nav
expand_now = st.session_state.expand_add
st.session_state.expand_add = False

# ---------------------------------------------------------------------------
# 共用元件：統計卡 / 事業體 chip / AI 提醒 / 收集進度 / 快速新增 / 內容排程
# ---------------------------------------------------------------------------
def stat_grid(cards):
    body = '<div class="aios-statgrid">'
    for icon, label, value, note in cards:
        body += (f'<div class="aios-statcard"><div class="aios-statcard-top">'
                  f'<span class="aios-statcard-label">{label}</span><span class="aios-statcard-icon">{icon}</span></div>'
                  f'<div class="aios-statcard-num">{value}</div><div class="aios-statcard-note">{note}</div></div>')
    body += '</div>'
    st.html(body)


def unit_chip_panel(rows, title="事業體總覽", hint=""):
    hint_html = f'<span class="hint">{hint}</span>' if hint else ""
    body = f'<div class="aios-panel"><h3>{title}{hint_html}</h3>'
    if not rows:
        body += f'<div style="color:{PALETTE["text_faint"]};font-size:12.5px;">尚無事業體資料</div>'
    else:
        chips = ""
        for u in rows:
            status = u.get("狀態") or "待補充"
            color = {"完成": PALETTE["green"], "進行中": PALETTE["amber"]}.get(status, PALETTE["grey"])
            chips += (f'<div class="aios-chip"><span class="aios-dot" style="background:{color}"></span>'
                       f'<span><b>{u.get("事業體","")}</b><span class="aios-chip-status">{status}</span></span></div>')
        body += f'<div class="aios-chipgrid">{chips}</div>'
    body += '</div>'
    st.html(body)


def content_schedule_panel():
    rows_html = ""
    for p in CONTENT_PLATFORMS:
        items = [c for c in content if c.get("平台") == p]
        pending = [c for c in items if c.get("狀態") not in ("已發布",)]
        if not items:
            fact, color = "尚無內容項目，還沒排入固定流程", PALETTE["grey"]
        elif pending:
            fact, color = f"{len(pending)} 篇準備中，最新：{pending[0].get('標題','') or '未命名'}", PALETTE["amber"]
        else:
            fact, color = f"{len(items)} 篇皆已發布", PALETTE["green"]
        rows_html += (f'<div class="aios-tip"><span class="aios-dot" style="background:{color}"></span>'
                       f'<div><b>{CONTENT_ICONS[p]} {p}：</b><span>{fact}</span></div></div>')
    st.html(f'<div class="aios-panel"><h3>內容排程總覽</h3>{rows_html}</div>')


def ai_tips_panel():
    tips = []
    units_todo = sum(1 for u in units if (u.get("狀態") or "待補充") == "待補充")
    if units_todo:
        tips.append(f"還有 {units_todo} 個事業體尚未補基本資料，建議先從最重要的 1–2 個開始補。")
    depts_todo = sum(1 for d in depts if (d.get("狀態") or "待補充") == "待補充")
    if depts_todo:
        tips.append(f"還有 {depts_todo} 個部門尚未建立工作流程，可以參考企劃部的 SOP 補起來。")
    thin_platforms = [p for p in CONTENT_PLATFORMS if not any(c.get("平台") == p for c in content)]
    if thin_platforms:
        tips.append(f"「{'、'.join(thin_platforms)}」目前還沒有內容項目，值得確認是否要排入排程。")
    late_kpi = [k for k in kpis if k.get("狀態") == "落後"]
    if late_kpi:
        tips.append(f"有 {len(late_kpi)} 項 KPI 目前落後，建議排進本週會議討論。")
    open_todo = sum(1 for t in todos if t.get("狀態") not in ("完成", "已封存"))
    if open_todo:
        tips.append(f"目前有 {open_todo} 項代辦事項還沒完成。")
    if not tips:
        tips = ["目前資料完整度不錯，持續保持每週更新的習慣！"]
    rows_html = "".join(f'<div class="aios-tip"><span class="aios-dot" style="background:{PALETTE["amber"]}"></span><span>{t}</span></div>' for t in tips[:5])
    st.html(f'<div class="aios-panel"><h3>AI 提醒</h3>{rows_html}</div>')


def checklist_panel():
    def cov(rows):
        if not rows:
            return "pending"
        filled = sum(1 for r in rows if r.get("狀態") not in (None, "待補充"))
        if filled == 0:
            return "pending"
        return "done" if filled == len(rows) else "progress"

    items = [
        ("各部門固定工作流程（SOP）", cov(sops)),
        ("會議紀錄", "done" if meets else "pending"),
        ("工作任務／專案", "done" if (todos or projects) else "pending"),
        ("KPI 追蹤設定", "done" if kpis else "pending"),
        ("公司重要資料（事業體）", cov(units)),
    ]
    label = {"done": "已完成", "progress": "進行中", "pending": "未開始"}
    color = {"done": "green", "progress": "amber", "pending": "grey"}
    rows_html = "".join(
        f'<div class="aios-checkrow"><span class="aios-checkbox {s}"></span><span class="aios-checklabel">{name}</span>'
        f'<span class="aios-pill" style="color:{PALETTE[color[s]]}">{label[s]}</span></div>'
        for name, s in items
    )
    st.html(f'<div class="aios-panel"><h3>第一階段資料收集進度</h3>{rows_html}</div>')


def quick_add_panel():
    with st.container(border=True):
        st.markdown("**⚡ 快速新增**")
        c1, c2 = st.columns(2)
        if c1.button("📝 會議紀錄", use_container_width=True, key="qa_meet"):
            go_to("meetings", expand_add=True)
        if c2.button("✅ 代辦事項", use_container_width=True, key="qa_todo"):
            go_to("todo", expand_add=True)
        c3, c4 = st.columns(2)
        if c3.button("📖 學習筆記", use_container_width=True, key="qa_note"):
            go_to("notes_all", expand_add=True)
        if c4.button("🏢 事業體資料", use_container_width=True, key="qa_unit"):
            go_to("units", expand_add=True)



# ---------------------------------------------------------------------------
# AI CEO：把 Notion 現況整理成「今天該做什麼」
# ---------------------------------------------------------------------------
def _clean_for_ai(rows, fields, limit=30):
    cleaned = []
    for r in rows[:limit]:
        item = {}
        for f in fields:
            v = r.get(f)
            if v not in (None, "", [], {}):
                item[f] = v
        if item:
            cleaned.append(item)
    return cleaned


def _local_ceo_brief():
    """沒有 OPENAI_API_KEY 時也能工作的規則型 CEO Brief。"""
    today = date.today()
    overdue = []
    due_7 = []
    for t in todos:
        status = t.get("狀態")
        if status in ("完成", "已封存"):
            continue
        d = _parse_date(t.get("截止時間"))
        if d and d < today:
            overdue.append(t)
        elif d and d <= today + timedelta(days=7):
            due_7.append(t)
    late_kpi = [k for k in kpis if k.get("狀態") == "落後"]
    risky_projects = [p for p in projects if p.get("進度") in ("暫停",) or (p.get("風險") and str(p.get("風險")).strip())]
    actions = []
    if overdue:
        actions.append(f"先處理 {len(overdue)} 個逾期任務，避免把舊問題帶進下一週。")
    if late_kpi:
        actions.append(f"檢查 {len(late_kpi)} 項落後 KPI，找出一個可在本週改善的槓桿。")
    if risky_projects:
        actions.append(f"檢查 {len(risky_projects)} 個有風險／暫停中的專案，確認是否需要停止、調整或加資源。")
    if due_7:
        actions.append(f"安排未來 7 天內到期的 {len(due_7)} 個任務，避免集中爆量。")
    if not actions:
        actions.append("目前沒有明顯紅燈；今天優先推進一件能直接產生收入、客戶或長期資產的事情。")
    return {
        "headline": "今天先處理真正會改變結果的事情。",
        "actions": actions[:3],
        "overdue": overdue[:8],
        "due_7": due_7[:8],
        "late_kpi": late_kpi[:8],
    }


def _build_ai_context():
    return {
        "today": str(date.today()),
        "departments": _clean_for_ai(depts, ["部門", "狀態"], 30),
        "business_units": _clean_for_ai(units, ["事業體", "狀態", "主要部門"], 30),
        "tasks": _clean_for_ai(todos, ["任務名稱", "狀態", "截止時間"], 50),
        "kpis": _clean_for_ai(kpis, ["KPI 名稱", "週期", "目標值", "實際值", "狀態", "部門", "事業體"], 40),
        "projects": _clean_for_ai(projects, ["專案名稱", "目標", "進度", "預計完成", "風險", "部門", "事業體"], 40),
        "meetings": _clean_for_ai(meets, ["標題", "日期", "重點摘要", "決議事項"], 20),
        "decisions": _clean_for_ai(decides, ["決策名稱", "日期", "背景", "決策內容"], 20),
        "content": _clean_for_ai(content, ["標題", "平台", "內容主題", "發布日期", "狀態"], 30),
    }


def _extract_response_text(data):
    # Responses API 的常見輸出結構；同時保留相容性處理。
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    chunks = []
    for item in data.get("output", []) or []:
        for c in item.get("content", []) or []:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                chunks.append(c["text"])
    return "\n".join(chunks).strip()


@st.cache_data(ttl=300, show_spinner=False)
def ask_ai_ceo(context_json):
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    model = st.secrets.get("OPENAI_MODEL", "gpt-5.6")
    if not api_key:
        return None
    system = """你是使用者的 AI CEO。你正在讀取他的企業管理 OS。你的工作不是泛泛而談，而是根據資料找出真正重要的矛盾、風險與槓桿。\n\n請用繁體中文回答，結構固定：\n1. 今日 CEO 判斷：一句話\n2. 最重要的 3 件事：依優先級排序，每件說明原因\n3. 紅燈：列出 KPI、逾期任務、專案風險等真正需要注意的項目\n4. 本週建議：最多 3 個行動\n5. 你需要我決定的事：如果資料不足才提出問題，最多 2 個。\n\n不要虛構資料；如果資料不足，明確說明。"""
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system}]},
            {"role": "user", "content": [{"type": "input_text", "text": "以下是今天 AI OS 的即時資料：\n" + context_json}]},
        ],
        "max_output_tokens": 1800,
    }
    try:
        resp = requests.post(OPENAI_API, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=90)
        if not resp.ok:
            return f"AI API 錯誤（{resp.status_code}）：{resp.text[:500]}"
        text = _extract_response_text(resp.json())
        return text or "AI 沒有回傳文字。"
    except Exception as e:
        return f"AI 連線失敗：{e}"


def ai_ceo_page():
    hero("AI OS · INTELLIGENCE", "AI CEO", "把 Notion 裡的任務、KPI、專案、會議與決策，轉成今天可以採取的管理行動。")
    context = _build_ai_context()
    local = _local_ceo_brief()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("逾期任務", len(local["overdue"]))
    c2.metric("7 天內到期", len(local["due_7"]))
    c3.metric("落後 KPI", len(local["late_kpi"]))
    c4.metric("風險專案", len([p for p in projects if p.get("風險") or p.get("進度") == "暫停"]))

    st.write("")
    if st.button("🧠 執行 AI CEO 分析", type="primary", use_container_width=True):
        st.session_state["ai_ceo_result"] = ask_ai_ceo(json.dumps(context, ensure_ascii=False, default=str))

    result = st.session_state.get("ai_ceo_result")
    if result:
        with st.container(border=True):
            st.markdown("### AI CEO 判斷")
            st.markdown(result)
    else:
        st.info("尚未執行 AI 分析。沒有設定 OPENAI_API_KEY 時，系統仍會顯示規則型 CEO Brief。")
        st.markdown(f"### 今日判斷\n{local['headline']}")
        for i, action in enumerate(local["actions"], 1):
            st.markdown(f"**{i}.** {action}")

    left, right = st.columns(2, gap="large")
    with left:
        if local["overdue"]:
            render_panel("🔴 逾期任務", local["overdue"], lambda r: f'<div class="aios-row"><span class="label">{r.get("任務名稱", "未命名")}</span>{status_pill(r.get("狀態"))}</div>')
        else:
            render_panel("🔴 逾期任務", [], lambda r: "", empty_text="目前沒有逾期任務。很好，別讓它們復活。")
    with right:
        if local["late_kpi"]:
            render_panel("📉 落後 KPI", local["late_kpi"], lambda r: f'<div class="aios-row"><span class="label">{r.get("KPI 名稱", "未命名")}<span class="sub"> · {r.get("實際值", "未填")}/{r.get("目標值", "未填")}</span></span>{status_pill(r.get("狀態"))}</div>')
        else:
            render_panel("📉 落後 KPI", [], lambda r: "", empty_text="目前沒有標記為落後的 KPI。")

    st.markdown("### 快速處理")
    q1, q2, q3 = st.columns(3)
    if q1.button("➕ 新增任務", use_container_width=True):
        go_to("todo", expand_add=True)
    if q2.button("📈 更新 KPI", use_container_width=True):
        go_to("kpi", expand_add=True)
    if q3.button("📁 檢查專案", use_container_width=True):
        go_to("projects")

# ---------------------------------------------------------------------------
# Dashboard 頁
# ---------------------------------------------------------------------------
def dashboard():
    hero("AI OS · CEO Dashboard", "早安", "這裡是目前 Notion 真實資料的即時總覽，涵蓋公司營運、知識、內容與人生四大系統。")

    depts_filled = sum(1 for d in depts if d.get("狀態") not in (None, "待補充"))
    units_filled = sum(1 for u in units if u.get("狀態") not in (None, "待補充"))
    open_todos = sum(1 for t in todos if t.get("狀態") not in ("完成", "已封存"))

    stat_grid([
        ("🏢", "事業體資料", f"{units_filled} / {len(units) or 8}", f"{max(len(units), 8) - units_filled} 個事業體待補基本資料"),
        ("👥", "部門資料", f"{depts_filled} / {len(depts) or 6}", "依實際填寫內容計算"),
        ("📋", "SOP 項目數", len(sops), "涵蓋各部門固定流程"),
        ("🗂️", "代辦事項", open_todos, "尚未完成的任務"),
    ])

    st.write("")
    left, right = st.columns([1.6, 1], gap="large")

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

        render_panel("部門資料進度", depts, dept_row, hint="依實際填寫內容計算")
        content_schedule_panel()
        unit_chip_panel(units)

    with right:
        ai_tips_panel()
        checklist_panel()
        render_panel(
            "公司代辦事項", todos,
            lambda r: (f'<div class="aios-row">'
                       f'<span class="label">{r.get("任務名稱","")}<span class="sub"> · {r.get("負責人") or "未指派"}</span></span>'
                       f'{status_pill(r.get("狀態"))}</div>'),
            empty_text="尚無代辦事項，把任務交給我就會整理到這裡",
        )
        quick_add_panel()


def simple_table(rows, eyebrow, title, cols=None, form_key=None, expand_add=False):
    hero(eyebrow, title)
    if form_key:
        crud_section(form_key, rows, RELATION_TARGETS, expand_add=expand_add)
        st.write("")
    if not rows:
        st.html(f'<div style="color:{PALETTE["text_faint"]};padding:10px 0;">尚無資料</div>')
        return
    df = pd.DataFrame(rows)
    if cols:
        cols = [c for c in cols if c in df.columns]
        df = df[cols]
    st.dataframe(df, hide_index=True, use_container_width=True)


def notes_page(category=None, expand_add=False):
    rows = notes if category is None else [n for n in notes if n.get("分類") == category]
    simple_table(
        rows, "Knowledge OS", category or "全部筆記",
        ["標題", "分類", "來源", "核心概念", "我的理解", "實際案例", "如何應用到我的公司", "延伸思考問題", "對應事業體", "對應部門", "日期", "狀態"],
        form_key="學習筆記", expand_add=expand_add,
    )


def content_page(platform=None, expand_add=False):
    rows = content if platform is None else [c for c in content if c.get("平台") == platform]
    hero("Content OS", platform or "全部內容")
    if platform:
        pending = [c for c in rows if c.get("狀態") not in ("已發布",)]
        if rows:
            fact = f"共 {len(rows)} 篇，其中 {len(pending)} 篇尚未發布" if pending else f"共 {len(rows)} 篇，皆已發布"
        else:
            fact = "尚無內容項目，還沒排入固定流程"
        st.html(f'<div class="aios-factbox">📌 {fact}</div>')
    crud_section("內容項目", rows, RELATION_TARGETS, expand_add=expand_add)
    st.write("")
    if not rows:
        st.html(f'<div style="color:{PALETTE["text_faint"]};padding:10px 0;">尚無資料</div>')
        return
    df = pd.DataFrame(rows)
    cols = [c for c in ["標題", "平台", "內容主題", "所屬事業體", "內容方向", "腳本文案", "拍攝想法", "品牌故事連結", "發布日期", "狀態"] if c in df.columns]
    st.dataframe(df[cols], hide_index=True, use_container_width=True)


def goals_page(category=None, expand_add=False):
    rows = goals if category is None else [g for g in goals if g.get("類別") == category]
    simple_table(
        rows, "Life OS", category or "全部目標",
        ["項目", "類別", "目標內容", "為什麼重要", "關鍵行動", "衡量方式", "與公司目標的關聯", "年度", "狀態"],
        form_key="人生目標", expand_add=expand_add,
    )


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
if nav_id == "dashboard":
    dashboard()
elif nav_id == "ai_ceo":
    ai_ceo_page()
elif nav_id == "units":
    simple_table(units, "公司營運 OS", "事業體總覽", ["事業體", "主要部門", "基本資料", "組織架構", "狀態"], form_key="事業體總覽", expand_add=expand_now)
elif nav_id == "depts":
    simple_table(depts, "公司營運 OS", "部門管理", ["部門", "狀態"], form_key="部門管理", expand_add=expand_now)
elif nav_id == "sop":
    simple_table(sops, "公司營運 OS", "SOP 流程庫", ["星期", "項目名稱", "工作內容", "部門", "負責人", "使用工具", "狀態"], form_key="SOP流程庫", expand_add=expand_now)
elif nav_id == "projects":
    simple_table(projects, "公司營運 OS", "專案管理", ["專案名稱", "部門", "事業體", "目標", "負責人", "開始日期", "預計完成", "進度", "風險"], form_key="專案管理", expand_add=expand_now)
elif nav_id == "meetings":
    simple_table(meets, "公司營運 OS", "會議紀錄", ["標題", "日期", "部門", "事業體", "出席人", "重點摘要", "決議事項"], form_key="會議紀錄", expand_add=expand_now)
elif nav_id == "decisions":
    simple_table(decides, "公司營運 OS", "決策紀錄", ["決策名稱", "日期", "部門", "背景", "決策內容", "決策人"], form_key="決策紀錄", expand_add=expand_now)
elif nav_id == "kpi":
    simple_table(kpis, "公司營運 OS", "KPI 追蹤", ["KPI 名稱", "部門", "事業體", "週期", "目標值", "實際值", "狀態"], form_key="KPI追蹤", expand_add=expand_now)
elif nav_id == "todo":
    simple_table(todos, "公司營運 OS", "公司代辦事項", ["任務名稱", "狀態", "截止時間", "負責人"], form_key="公司代辦事項", expand_add=expand_now)
elif nav_id == "notes_all":
    notes_page(expand_add=expand_now)
elif nav_id.startswith("note_"):
    notes_page(nav_id[len("note_"):], expand_add=expand_now)
elif nav_id == "content_all":
    content_page(expand_add=expand_now)
elif nav_id.startswith("content_"):
    content_page(nav_id[len("content_"):], expand_add=expand_now)
elif nav_id == "goals_all":
    goals_page(expand_add=expand_now)
elif nav_id.startswith("goal_"):
    goals_page(nav_id[len("goal_"):], expand_add=expand_now)
else:
    dashboard()
