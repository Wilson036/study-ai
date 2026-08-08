# 安裝與部署

以下流程不需要把 PDF 上傳到任何服務。你會用一個預先設定的 Supabase 環境保存最多約 10 位使用者的個人進度與私有題庫，再用 Cloudflare Pages 部署 `dist/`。一般使用者只需輸入 Email，不需要接觸 Supabase 設定。

## 1. 建立單一 Supabase 專案與自動註冊

1. 在 Supabase 建立專案，region 建議選離台灣較近的位置並記錄實際 region。
2. 到 **Authentication → Sign In / Providers → Email** 開啟 Email。
3. 開啟 **Allow new users to sign up**。使用者第一次寄送並完成 Magic Link 後會自動建立帳號，不需要在 Dashboard 預先建立 Email。
4. 若使用者不是 Supabase 專案組織成員，必須設定 Custom SMTP；內建寄信服務只適合專案成員測試，而且額度很低。
5. 到 **Authentication → URL Configuration**，把 Site URL 與 Redirect URLs 加入 `http://localhost:8080/dist/`。使用預設 Magic Link，不需要修改 Email template。
6. 記下 **Project URL** 與 **publishable key**（舊專案也可用 anon key），填入 `src/config.js` 的 `supabaseUrl` 與 `supabasePublishableKey`。這是部署者唯一一次需要設定連線資料；`sb_secret_*` 與 `service_role` 權限極高，絕不可填入。

## 2. 建立資料表、RLS 與私有題庫

1. 開啟 `supabase/schema.sql`。
2. 在 SQL Editor 執行整份 SQL。它會建立事件、設定、trigger、RLS、私有 `bank` bucket，以及僅限已登入帳號讀取的 policy；不需要替換 UUID。
3. 在本機完成題庫驗證與建置：

   ```bash
   python3 tools/validate.py
   python3 tools/build.py
   ```

4. 到 Storage 的私有 `bank` bucket，上傳 `data/questions.json` 與 `data/manifest.json`，檔名與路徑不要改。

## 3. 部署 Cloudflare Pages

1. 重新執行 `python3 tools/build.py`，確認最新的 `src/config.js` 已複製到 `dist/config.js`。
2. 將乾淨版本推送到 GitHub Private repository。
3. Cloudflare Dashboard → Workers & Pages → Create application → Pages → Connect to Git，選擇該 repository。
4. Production branch 設 `main`、Framework preset 設 `None`、Build command 設 `exit 0`、Build output directory 設 `dist`、Root directory 留空。
5. 部署並取得 `https://專案名稱.pages.dev/`。
6. 把正式 Pages 網址加到 Supabase 的 Site URL / Redirect URLs。使用者開啟正式網址後只需輸入 Email，點信箱裡的登入連結即可下載私有題庫。

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

- **登入信沒收到**：確認使用者已由 Dashboard 建立、Email provider 開啟；使用 Supabase 預設寄信服務時，收件信箱必須是專案組織成員，且寄信額度很低。再檢查垃圾郵件與 Auth Logs。
- **點連結後網址錯誤**：確認目前的 localhost 或 Pages 網址已完整加入 Authentication → URL Configuration 的 Redirect URLs。
- **題庫 403**：確認 bucket 是 private、`bank_authenticated_read` policy 已建立、帳號已登入，且兩個檔案位於 bucket 根目錄。
- **同步卡住**：先按「立即同步」，仍未完成再按「檢查完整性」。若後台曾刪資料或重建專案，執行「強制全量重建本機」。
- **Service Worker 沒更新**：確認 `sw.js` no-cache，重新部署後等「有新版本」提示，再主動重新載入。
- **換時區後日期不對**：設定 IANA 時區並儲存；學習日以當地 04:00 為日界。
- **待上傳筆數不減**：確認仍有登入 session、網路可連 Supabase、RLS insert policy 存在。資料不會因失敗而自動刪除。
- **後台手動刪列或重建專案**：count/digest 可能偵測到差異；一定要執行一次「強制全量重建本機」。
