# 安裝與部署

以下流程不需要把 PDF 上傳到任何服務。你會用一個預先設定的 Supabase 環境保存最多約 10 位使用者的個人進度與私有題庫，再用 Cloudflare Pages 部署 `dist/`。一般使用者以 Email 與密碼註冊、登入，不需要接觸 Supabase 設定。

## 1. 建立單一 Supabase 專案與自動註冊

1. 在 Supabase 建立專案，region 建議選離台灣較近的位置並記錄實際 region。
2. 到 **Authentication → Sign In / Providers → Email** 開啟 Email。
3. 開啟 **Allow new users to sign up**。使用者就能在網站彈窗直接建立帳號，不需要在 Dashboard 預先新增 Email。
4. 如果你希望註冊後立即登入、完全不寄驗證連結，請關閉 **Confirm Email**。這最符合目前需求，但代表只要能輸入某個 Email 就能註冊，安全性較低。
5. 如果保留 **Confirm Email**，使用者註冊時仍會收到一次驗證信；驗證後的日常登入只用密碼，不會再寄 Magic Link。此模式建議設定 Custom SMTP，並把本機與正式網址加入 **Authentication → URL Configuration**。
6. 記下 **Project URL** 與 **publishable key**（舊專案也可用 anon key），填入 `src/config.js` 的 `supabaseUrl` 與 `supabasePublishableKey`。這是部署者唯一一次需要設定連線資料；`sb_secret_*` 與 `service_role` 權限極高，絕不可填入。

## 2. 建立資料表、RLS 與私有題庫

1. 開啟 `supabase/schema.sql`。
2. 在 SQL Editor 執行整份 SQL。它會建立事件、設定、觀念複習狀態、trigger、RLS、私有 `bank` bucket，以及僅限已登入帳號讀取的 policy；不需要替換 UUID。即使以前執行過舊版，也要重新執行一次以補上 `concept_reviews`。
3. 在本機完成題庫驗證與建置：

   ```bash
   python3 tools/validate.py
   python3 tools/build.py
   ```

4. 到 Storage 的私有 `bank` bucket，上傳 `data/questions.json`、`data/concepts.json` 與 `data/manifest.json`，檔名與路徑不要改。

## 3. 部署 Cloudflare Pages

1. 重新執行 `python3 tools/build.py`，確認最新的 `src/config.js` 已複製到 `dist/config.js`。
2. 將乾淨版本推送到 GitHub Private repository。
3. Cloudflare Dashboard → Workers & Pages → Create application → Pages → Connect to Git，選擇該 repository。
4. Production branch 設 `main`、Framework preset 設 `None`、Build command 設 `exit 0`、Build output directory 設 `dist`、Root directory 留空。
5. 部署並取得 `https://專案名稱.pages.dev/`。
6. 若有開啟 Confirm Email，把正式 Pages 網址加到 Supabase 的 Site URL / Redirect URLs。使用者開啟正式網址後可直接註冊或以 Email、密碼登入，再下載私有題庫。

## 4. 手機與電腦驗證

1. 兩台裝置各登入一次，確認顯示同一帳號且都能看到 300 題。
2. 電腦答一題後按「立即同步」；手機回前景並同步，確認相同題目熟練度更新。
3. 手機切飛航模式答題，確認待同步數增加且重開仍存在；恢復網路後待同步數歸零。
4. 執行 `tests/rls_test.md` 與 `tests/offline_matrix.md`，將實測結果寫入 `data/audit/acceptance.md`。

## 5. 正式網域檢查

```bash
curl -I https://你的網域.pages.dev/
curl -I https://你的網域.pages.dev/sw.js
```

確認 HTML 與 JavaScript 的 `Content-Type` 正確，且 `sw.js` 是 `Cache-Control: no-cache`。再從正式 Pages 網域登入一次，確認瀏覽器對 Supabase 的 OPTIONS 預檢成功。

## 排錯

- **無法註冊**：確認 Email provider 與 Allow new users to sign up 都已開啟；再查看 Authentication Logs 的錯誤。
- **註冊後要求驗證信**：這表示 Confirm Email 仍開啟。想完全不使用 Email 連結就關閉它；想保留信箱驗證則設定 Custom SMTP 並檢查垃圾郵件。
- **驗證連結網址錯誤**：只在有開啟 Confirm Email 時需要處理；確認目前的 localhost 或 Pages 網址已加入 Authentication → URL Configuration 的 Redirect URLs。
- **題庫 403**：確認 bucket 是 private、`bank_authenticated_read` policy 已建立、帳號已登入，且三個檔案位於 bucket 根目錄。
- **同步卡住**：先按「立即同步」，仍未完成再按「檢查完整性」。若後台曾刪資料或重建專案，執行「強制全量重建本機」。
- **Service Worker 沒更新**：確認 `sw.js` no-cache，重新部署後等「有新版本」提示，再主動重新載入。
- **換時區後日期不對**：設定 IANA 時區並儲存；學習日以當地 04:00 為日界。
- **待上傳筆數不減**：確認仍有登入 session、網路可連 Supabase、RLS insert policy 存在。資料不會因失敗而自動刪除。
- **後台手動刪列或重建專案**：count/digest 可能偵測到差異；一定要執行一次「強制全量重建本機」。
