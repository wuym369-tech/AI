# AI OS Dashboard｜部署到 Streamlit Cloud 步驟

這份 Dashboard 打開就會即時去讀你的 Notion 資料，不是固定的假資料。部署一次之後，之後你在 Notion 更新內容，重新整理網頁就會看到最新狀況。

## 第一步：建立 Notion Internal Integration（取得存取權杖）

1. 到 Notion 網頁版，點左下角工作區名稱 → **Settings**（設定）→ **Connections**（連結）分頁。
2. 找到「Develop your own connections」（開發你自己的連結）連結並點進去。
3. 點 **+ New connection**（新增連結）。
4. 幫它取個名字，例如 `AI OS Dashboard`，選擇要連結的工作區，建立。
5. 建立完成後，回到 Connections 列表，點你剛建立的連結旁邊的 **···** → 複製 **Internal Integration Secret**（一長串以 `secret_` 或 `ntn_` 開頭的字串）。**這串就是等一下要放進 Streamlit Secrets 的 NOTION_TOKEN，請妥善保管，不要外流。**

## 第二步：把 Notion 頁面分享給這個 Integration

Integration 預設看不到任何頁面，要手動授權：

1. 打開 Notion 裡的「🧠 AI OS｜我的第二大腦與企業系統」頁面。
2. 點右上角 **Share**（分享）按鈕 → 在下方 **Connections** 欄位搜尋你剛建立的 Integration 名字 → 點選加入。
3. Notion 通常會問要不要把權限套用到底下的子頁面/子資料庫，選「包含所有子頁面」最省事；如果沒有這個選項，就到「🏢 公司營運 OS」頁面重複一次同樣的分享步驟（子資料庫是掛在這個頁面底下）。

## 第三步：把程式碼放到 GitHub

1. 建立一個新的 GitHub repo（可以設成 Private，比較保險）。
2. 把這次收到的 `app.py`、`requirements.txt` 兩個檔案放進去（`DEPLOY_GUIDE.md` 放不放都可以，只是說明文件）。
3. Commit、Push 上去。

## 第四步：在 Streamlit Cloud 部署

1. 到 [share.streamlit.io](https://share.streamlit.io) 登入你的帳號。
2. 點 **New app** → 選你剛建立的 repo、分支（通常是 main）、Main file path 填 `app.py`。
3. 部署前或部署後，進入這個 App 的 **Settings → Secrets**，貼上：

   ```
   NOTION_TOKEN = "貼上第一步複製的那串權杖"
   ```

4. 儲存後 App 會自動重新啟動。等個一兩分鐘，打開 App 的網址，就能看到即時的 Notion 資料。

## 之後的使用方式

- 側邊欄有「🔄 重新整理」按鈕，可以強制立刻抓最新資料（平常資料每 60 秒會自動更新一次，不用一直按）。
- 之後要新增部門、SOP、會議紀錄等資料庫，或是調整欄位名稱，記得同步更新 `app.py` 裡對應的欄位名稱，不然畫面上會抓不到新欄位。
- 如果之後想要更漂亮的介面（配色、卡片樣式對齊原本那份 HTML 的視覺），可以再回來找我，我可以用 Streamlit 的 custom CSS 或改用 `st.components` 內嵌原本的 HTML/CSS 版面，資料照樣是即時的。
