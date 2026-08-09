# RLS 與同步手動測試

執行環境、Supabase region、日期與測試帳號 UUID（可遮末段）應記入驗收報告。不要使用 `service_role` 模擬網頁。

## 權限與註冊

- 未登入查 `answer_events`：回傳 0 列。
- A 查詢 B 的事件：回傳 0 列。
- A 插入 `user_id=B`：被 RLS 拒絕。
- A 對既有事件 update/delete：重新 select 後逐欄確認資料未變；HTTP 200 本身不算通過。
- 未登入下載私有 `bank/questions.json`：403；自動註冊並登入的 A、B 帳號都能下載，但不能上傳、修改或刪除題庫。
- 用全新 Email 與密碼註冊：建立使用者；之後可用密碼登入，且只能讀寫自己的事件、設定與觀念複習狀態。
- A 對 `concept_reviews` 新增自己的觀念勾選後，B 查不到；A 嘗試替 B 寫入時被 RLS 拒絕。
- 插入早於 2026-01-01 或晚於伺服器當日 + 1 的 `study_day`：trigger 拒絕。

## 同時寫入與收斂

1. 手機、電腦離線各答 5 題，其中一題相同且同一 study day；一台答對、一台答錯。
2. 同時恢復連線。
3. 伺服器事件數應為 10、唯一 `item_id` 為 9、重疊題日結果為 `wrong`。
4. 兩台強制重算後的 `level/due/lapseDays/successDays/inMistakes` 逐欄相同。

## 同步邊界

- keyset 分頁掃描時由第二台插入：最終須 `SYNCED` 或明示「同步未完成」，不可假綠。
- 任一分頁失敗：不更新 confirmed 狀態。
- ack 回來後、清 outbox 前關頁：重開後安全重送且不重複伺服器列。
- 後台刪一列：count 對帳抓到；按「強制全量重建本機」可恢復。
- 後台刪一列並新增一列（count 不變）：按「檢查完整性」的 ID digest 抓到。
- 本機放入同 event_id、不同 payload：ack 後 canonical 以伺服器為準且 divergence store 留紀錄。
- 兩帳號輪流登入：分區、confirmed count、題庫與事件互不相見。

## 題庫與跨分頁

- 兩個 tab 同時更新：pointer 只能單調升版；讀取不得混版。
- 新題庫缺歷史 item 且無 tombstone：拒絕切換並保留舊版。
- `.in()` ack 以 50 UUID 實測並記錄 URL 長度、HTTP 狀態；逼近服務限制則下修批次。
