# Readwise Reader → reMarkable 2 自動同步

每天自動把 Readwise Reader 的文章推送到 reMarkable 2，讓你在電子紙上閱讀儲存的文章。

---

## 這是什麼

這個專案透過 **GitHub Actions**（免費的雲端自動化服務）每天 00:30（台灣時間）執行：

1. 從 Readwise Reader 抓取你標記 `remarkable` tag 的文章，以及最新加入閱讀清單的文章
2. 轉換成 reMarkable 2 支援的 EPUB 格式
3. 上傳到你的 Google Drive 指定資料夾
4. reMarkable 2 透過原生 Google Drive 整合自動同步到裝置

**不需要一直開著電腦。** 設定完成後，整個流程完全在雲端自動執行。

```
Readwise Reader
      ↓  GitHub Actions（每天 00:30 自動觸發）
   Google Drive「Readwise Reader」資料夾
      ↓  reMarkable 原生 Google Drive 整合
   reMarkable 2 裝置
```

---

## 開始之前，你需要

| 項目 | 說明 |
|------|------|
| [Readwise Reader](https://readwise.io/read) 帳號 | 需付費方案 |
| Google 帳號 | 一般 Gmail 即可 |
| reMarkable 2 | 需訂閱 [Connect](https://remarkable.com/store/connect) 方案（才有 Google Drive 整合） |
| [GitHub](https://github.com) 帳號 | 免費方案即可 |
| 電腦（Mac 或 Windows） | 設定過程需要在本機執行一次腳本 |

---

## 設定步驟

### 步驟一：Fork 這個 Repo

1. 點擊本頁右上角的 **Fork** 按鈕
2. 選擇你的 GitHub 帳號，建立副本
3. 之後所有設定都在你自己的 Repo 裡進行

---

### 步驟二：取得 Readwise API Token

1. 前往 [readwise.io/access_token](https://readwise.io/access_token)
2. 複製頁面上顯示的 Token（一串英數字）
3. 先存到記事本備用，後面步驟六會用到

---

### 步驟三：設定 Google Cloud（取得 OAuth 憑證）

這是設定過程最複雜的部分，請一步一步來。

> **為什麼需要這個？** GitHub Actions 需要你的授權，才能把文章上傳到你的 Google Drive。

#### 3.1 建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)，登入你的 Google 帳號
2. 點擊頁面上方的專案選單（可能顯示「選取專案」或某個專案名稱）
3. 點擊「**新增專案**」
4. 專案名稱填入 `readwise-remarkable`，點擊「**建立**」

#### 3.2 啟用 Google Drive API

1. 確認目前專案是剛才建立的 `readwise-remarkable`
2. 前往 [啟用 Google Drive API](https://console.developers.google.com/apis/api/drive.googleapis.com)
3. 點擊「**啟用**」

#### 3.3 設定 OAuth 同意畫面

1. 在左側選單點擊「**API 和服務**」→「**OAuth 同意畫面**」
2. 使用者類型選「**外部**」，點擊「**建立**」
3. 填寫必填欄位：
   - **應用程式名稱**：`Readwise Sync`（隨意填）
   - **使用者支援電子郵件**：選你的 Gmail
   - **開發人員聯絡資訊**：填你的 Gmail
4. 點擊「**儲存並繼續**」
5. **範圍**頁面：點「**新增或移除範圍**」，搜尋並勾選 `https://www.googleapis.com/auth/drive`，點擊「**更新**」→「**儲存並繼續**」
6. **測試使用者**頁面：點「**新增使用者**」，填入你的 Gmail，點擊「**儲存並繼續**」
7. 最後點擊「**返回資訊主頁**」

#### 3.4 建立 OAuth 用戶端憑證

1. 在左側選單點擊「**憑證**」
2. 點擊上方「**+ 建立憑證**」→「**OAuth 用戶端 ID**」
3. 應用程式類型選「**電腦版應用程式**」
4. 名稱填 `readwise-sync`（隨意填），點擊「**建立**」
5. 視窗出現後，點擊「**下載 JSON**」，把檔案存到電腦（例如桌面）

#### 3.5 在本機執行授權腳本

這個步驟需要在你的電腦上執行一次，用來取得 refresh token。

**Mac 用戶：**

打開「終端機」（Terminal），複製貼上以下指令（一行一行執行）：

```bash
pip install google-auth-oauthlib
```

```bash
python get_token.py ~/Desktop/client_secret_xxx.json
```

> 把 `client_secret_xxx.json` 換成你剛才下載的檔案的實際名稱。

**Windows 用戶：**

打開「命令提示字元」（Command Prompt），執行：

```
pip install google-auth-oauthlib
python get_token.py C:\Users\你的名字\Desktop\client_secret_xxx.json
```

執行後瀏覽器會自動開啟 Google 授權頁面，登入並點擊「**允許**」。

回到終端機，你會看到類似以下的輸出，**完整複製這段 JSON**（從 `{` 到最後的 `}`）：

```json
{
  "token": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "...",
  "client_secret": "...",
  "scopes": ["https://www.googleapis.com/auth/drive"]
}
```

先存到記事本備用。

---

### 步驟四：建立 Google Drive 資料夾

1. 前往 [Google Drive](https://drive.google.com/)
2. 新增一個資料夾，命名為 `Readwise Reader`
3. 點進這個資料夾，看瀏覽器網址列，URL 長這樣：
   ```
   https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
   ```
4. 複製最後那串英數字（`1aBcDeFgHiJkLmNoPqRsTuVwXyZ` 這部分），這就是資料夾 ID

---

### 步驟五：連結 reMarkable 2 與 Google Drive

1. 在 reMarkable 2 上，進入 **Settings → Storage → Google Drive**
2. 點擊「**Connect**」，完成 Google 帳號授權
3. 授權後，選擇你剛建立的「**Readwise Reader**」資料夾進行同步
4. 回到 rM2 首頁，應該可以看到「Readwise Reader」資料夾出現

---

### 步驟六：設定 GitHub Secrets

GitHub Secrets 是安全儲存敏感資訊的地方，腳本執行時會自動讀取，不會暴露在程式碼裡。

1. 進入你 Fork 的 GitHub Repo 頁面
2. 點擊上方的「**Settings**」標籤
3. 在左側選單找到「**Secrets and variables**」→「**Actions**」
4. 點擊「**New repository secret**」，依序新增以下三個 Secret：

| Name | Value |
|------|-------|
| `READWISE_TOKEN` | 步驟二取得的 Readwise API Token |
| `GDRIVE_FOLDER_ID` | 步驟四取得的 Google Drive 資料夾 ID |
| `GOOGLE_OAUTH_CREDENTIALS` | 步驟三取得的完整 JSON（包含 `{` 和 `}`） |

---

### 步驟七：測試執行

1. 進入你的 Repo，點擊上方「**Actions**」標籤
2. 在左側選單點擊「**Readwise → reMarkable Daily Sync**」
3. 點擊「**Run workflow**」→「**Run workflow**」（綠色按鈕）
4. 等待約 2–5 分鐘，執行完成後狀態會顯示綠色勾勾 ✅
5. 前往 Google Drive 的「Readwise Reader」資料夾，確認 EPUB 文章已上傳
6. 在 rM2 確認文章已同步（rM2 需要連網才會同步）

---

## 自訂設定

在 `sync.py` 開頭的幾個常數可以調整：

```python
REMARKABLE_TAG = 'remarkable'   # 用哪個 tag 標記要同步的文章
MAX_INBOX_ARTICLES = 20         # 最多同步幾篇最新儲存的文章
MAX_HTML_CHARS = 300_000        # 單篇文章最大字元數（超過會截斷）
```

修改後，commit 並 push 到你的 Repo 即可生效。

---

## 文章同步規則

每天同步的文章來自兩個來源，合併後去重：

| 來源 | 規則 |
|------|------|
| 標記 `remarkable` tag 的文章 | 全部同步，不限數量 |
| 最新加入閱讀清單（new/later）| 最多 20 篇 |

> **注意：** 只有你主動儲存到 Readwise Reader 的文章才有完整內文。透過 RSS feed 訂閱的文章 Readwise 只保存標題和摘要，無法同步完整內容。

---

## 常見問題

**Q：執行失敗，顯示 403 錯誤？**
最常見的原因是 `GOOGLE_OAUTH_CREDENTIALS` 的 JSON 格式不正確。確認複製時包含最外層的 `{` 和 `}`，且中間沒有多餘的換行或空格被截斷。

**Q：rM2 上看不到新文章？**
確認 rM2 有連接 Wi-Fi。Google Drive 同步需要裝置連網，且可能有幾分鐘延遲。

**Q：文章只有標題，沒有內文？**
這篇文章來自 RSS feed，Readwise 沒有儲存完整內文。改用「儲存到 Readwise Reader」的方式加入，或在 Readwise Reader 中重新儲存該文章，再等下次同步。

**Q：排程時間可以改嗎？**
可以。在 `.github/workflows/sync.yml` 裡修改 cron 表達式。目前設定 `30 16 * * *` 代表 UTC 16:30，即台灣時間 00:30。

---

## 技術架構

| 元件 | 說明 |
|------|------|
| 執行環境 | GitHub Actions（免費） |
| 程式語言 | Python 3.11 |
| 文件格式 | EPUB |
| EPUB 產生 | `ebooklib` |
| Google Drive 操作 | `google-api-python-client` |
| Google 認證 | OAuth2 refresh token |
| 排程 | GitHub Actions cron（每天 UTC 16:30） |
