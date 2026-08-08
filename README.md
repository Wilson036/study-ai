# 拾光｜AI 應用規劃師（中級）互動記憶網頁

拾光是依兩份官方學習指引建立的主動回想網站。它不是完整 Anki，也不在使用時呼叫 LLM：題庫在部署前一次生成並凍結，網站只負責出題、間隔排程、離線保存與跨裝置同步。整個網站使用單一預先設定的 Supabase 環境，一般使用者只需輸入 Email，不會看到 Supabase 設定欄位。

## 已實作

- 300 題固定題庫：175 填空、77 四選一、48 名詞配對；175 個核心概念。
- 每題只考一個概念，附提示、白話解釋、章節、印刷頁碼與原文摘句。
- 日級最差優先聚合：同日有 `clean` 與 `wrong` 時以 `wrong` 為準；派生狀態每次由完整事件集合重算。
- 答錯隔天再見；答對間隔 1 → 3 → 7 → 21 → 60 天；錯題須在答錯後兩個不同日完整答對才畢業。
- 提示、揭答與首次提交各自先寫入不可變事件；保存失敗就不顯示提示、答案或判定。
- IndexedDB outbox、`projectRef:userId` 分區、Email Magic Link、RLS、私有 Storage 題庫。
- 上傳批次 50、ack 取完整伺服器列、keyset 全量下行、前後 count 穩定對帳、ID digest 與全量重建逃生口。
- SHA-256 原始 bytes 驗證、版本化題庫 keyspace、active pointer、Web Locks 與 lease/fencing fallback。
- 響應式手機/桌面介面、鍵盤操作、Service Worker 離線 shell 與新版提示。

## 本機產生與檢查

在 `study-app/` 內執行：

```bash
python3 tools/extract.py
python3 tools/concepts.py --count 175
python3 tools/generate.py --total 300
python3 tools/validate.py
python3 tools/sample_review.py
python3 tools/build.py
python3 -m http.server 8080
```

部署者要先在 `src/config.js` 填入 Supabase Project URL 與 publishable key，再執行 `python3 tools/build.py`。開啟 `http://localhost:8080/src/` 使用網站，或開啟 `http://localhost:8080/tests/unit.html` 執行瀏覽器單元測試。`dist/` 只含 app shell 與公開連線設定，不含私有題庫；部署前要把 `data/questions.json` 與 `data/manifest.json` 上傳到 Supabase Storage。

## 資料與隱私

兩份來源 PDF 只在本機被讀取，沒有移動到 `study-app/`、沒有複製到 `dist/`，也不應上傳到 Cloudflare 或 Supabase。瀏覽器中的 local profile 不是安全邊界；有本機瀏覽器存取權的人可以讀改刪該裝置的資料。使用者第一次完成 Magic Link 後會自動建立帳號；伺服器端以 JWT 與 RLS 隔離各使用者資料，私有題庫只開放給已登入帳號。

`src/config.js` 只能放 Supabase **publishable key**（舊專案的 anon key 亦可）。這類前端 key 本來就會傳給瀏覽器，真正的資料權限仍由 Auth、RLS 與 Storage policy 控制。任何 secret 或 `service_role` key 都不得進入網頁、版本庫或截圖。

## 品質限制

`tools/validate.py` 可以證明 schema、出處子字串、欄位與結構規則成立，但不能證明每道題的答案、解釋與誘答理由在語義上都正確。`data/audit/sample_review.md` 提供跨章節、科目、題型、頁段與邊界頁的分層抽樣；這只增加語義品質的抽樣信心，不是全庫保證。正式使用前應完成該審查包並修正不準確題目。

同步採全量集合對帳，成本隨事件數線性增加；容量模型上限以 10,000 個事件估算。真機 benchmark 的步驟與尚待填入的數字在 `data/audit/acceptance.md`。未完成真機、Supabase 與正式網域測試的項目不應宣稱通過。
