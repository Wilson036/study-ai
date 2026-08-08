# 安裝與部署

以下流程不需要把 PDF 上傳到任何服務。你會用 Supabase 保存個人進度與私有題庫，再用 Cloudflare Pages Direct Upload 部署 `dist/`。

## 1. 建立 Supabase 專案與唯一使用者

1. 在 Supabase 建立專案，region 建議選離台灣較近的位置並記錄實際 region。
2. 到 **Authentication → Sign In / Providers → Email** 開啟 Email。
3. 關閉公開註冊；先由 Dashboard 手動建立你自己的使用者。若使用 Supabase 預設寄信服務，登入 Email 必須是專案組織的成員信箱。
4. 到 **Authentication → URL Configuration**，把 Site URL 與 Redirect URLs 加入 `http://localhost:8080/dist/`。使用預設 Magic Link，不需要修改 Email template。
5. 記下 **Project URL** 與 **publishable key**（舊專案也可用 anon key）。`sb_secret_*` 與 `service_role` 權限極高，絕不可貼進網頁。
6. 從 Authentication 使用者清單複製自己的 UUID。

## 2. 建立資料表、RLS 與私有題庫

1. 開啟 `supabase/schema.sql`。
2. 把 Storage policy 中的 `00000000-0000-0000-0000-000000000000` 換成你的使用者 UUID。
3. 在 SQL Editor 執行整份 SQL。它會建立事件、設定、trigger、RLS、私有 `bank` bucket 與單一使用者讀取 policy。
4. 在本機完成題庫驗證與建置：

   ```bash
   python3 tools/validate.py
   python3 tools/build.py
   ```

5. 到 Storage 的私有 `bank` bucket，上傳 `data/questions.json` 與 `data/manifest.json`，檔名與路徑不要改。

## 3. 部署 Cloudflare Pages

1. Cloudflare Dashboard → Workers & Pages → Create → Pages → Direct Upload。
2. 上傳整個 `dist/` 目錄並取得 `*.pages.dev` 網址。
3. Direct Upload 的 Dashboard 限制是 1,000 個檔、單檔 25 MiB；本專案只有 3 個 shell 檔案，低於限制。
4. Direct Upload 專案之後不能直接切換成 Git integration；若要改用 Git，請另建 Pages 專案。
5. 把正式 `https://專案名稱.pages.dev/` 加到 Supabase 的 Site URL / Redirect URLs，開正式網址，在設定頁貼 Project URL、publishable key、email，寄送登入連結並在同一瀏覽器點開。登入後網站會從私有 bucket 驗證並下載題庫。

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
- **題庫 403**：確認 bucket 是 private、policy 的 UUID 是目前登入者、兩個檔案位於 bucket 根目錄。
- **同步卡住**：先按「立即同步」，仍未完成再按「檢查完整性」。若後台曾刪資料或重建專案，執行「強制全量重建本機」。
- **Service Worker 沒更新**：確認 `sw.js` no-cache，重新部署後等「有新版本」提示，再主動重新載入。
- **換時區後日期不對**：設定 IANA 時區並儲存；學習日以當地 04:00 為日界。
- **待上傳筆數不減**：確認仍有登入 session、網路可連 Supabase、RLS insert policy 存在。資料不會因失敗而自動刪除。
- **後台手動刪列或重建專案**：count/digest 可能偵測到差異；一定要執行一次「強制全量重建本機」。
