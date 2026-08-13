# AI OS V2

這一版是在你目前 GitHub `wuym369-tech/AI` 的架構上直接升級，不需要重建 Notion。

## V2 新增

- AI CEO 頁面
- 今日 CEO Brief
- 逾期任務 / 7 天內到期任務 / 落後 KPI / 風險專案統計
- 可選擇接 OpenAI API，讓 AI 直接讀取目前 Notion 資料並產生管理建議
- 保留原本的 Notion CRUD、CEO Dashboard、KPI、專案、SOP、會議、決策、知識、內容與人生 OS
- 任務與其他日期欄位繼續使用 Streamlit 日期選擇器，不需要手打日期

## 上傳方式

最簡單：

1. 備份你目前 GitHub 的 `app.py`
2. 用這個版本的 `app.py` 覆蓋 GitHub 裡的 `app.py`
3. 如果 `requirements.txt` 沒有這三行，就一併覆蓋
4. Commit changes
5. Streamlit Cloud 會重新部署

## Streamlit Secrets

原本的：

```toml
NOTION_TOKEN = "你的 Notion Token"
```

保留不動。

如果要啟用 AI CEO，再加入：

```toml
OPENAI_API_KEY = "你的 OpenAI API Key"
OPENAI_MODEL = "gpt-5.6"
```

如果沒有 OPENAI_API_KEY，App 仍然可以正常使用；AI CEO 頁面會使用內建規則產生 CEO Brief。

## 重要

不要把 `OPENAI_API_KEY` 或 `NOTION_TOKEN` 寫進 GitHub 程式碼。
