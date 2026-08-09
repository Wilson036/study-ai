import fs from "node:fs";
import assert from "node:assert/strict";

const html = fs.readFileSync(new URL("../src/index.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0]?.[1];
if (!script) throw new Error("找不到 inline app script");
const prefix = script.slice(0, script.indexOf("function request("));
const signalGate = script.match(/async function signalGate\([^\n]+/)?.[0];
const core = new Function("crypto", `${prefix}\n${signalGate}; return {addDays,studyDay,dayOutcome,deriveItem,deriveAll,normalizeAnswer,editDistance,judge,groupConcepts,signalGate,deploymentConfig,configReady,parseRecoverySession};`)(globalThis.crypto);
const tests = [];
const test = async (name, fn) => { await fn(); tests.push(name); };
const permutations = a => a.length < 2 ? [a] : a.flatMap((x, i) => permutations(a.slice(0, i).concat(a.slice(i + 1))).map(r => [x, ...r]));

await test("日結果交換律、結合律、冪等律", () => {
  const outcomes = ["clean", "near", "wrong"];
  for (const a of outcomes) for (const b of outcomes) {
    assert.equal(core.dayOutcome([{outcome:a},{outcome:b}]), core.dayOutcome([{outcome:b},{outcome:a}]));
    assert.equal(core.dayOutcome([{outcome:a},{outcome:a}]), a);
    for (const c of outcomes) {
      const left = core.dayOutcome([{outcome:core.dayOutcome([{outcome:a},{outcome:b}])},{outcome:c}]);
      const right = core.dayOutcome([{outcome:a},{outcome:core.dayOutcome([{outcome:b},{outcome:c}])}]);
      assert.equal(left, right);
    }
  }
});

const events = [
  {study_day:"2026-01-01",outcome:"clean"}, {study_day:"2026-01-01",outcome:"wrong"},
  {study_day:"2026-01-02",outcome:"clean"}, {study_day:"2026-01-03",outcome:"near"},
  {study_day:"2026-01-04",outcome:"clean"},
];
await test("固定 multiset 全排列收斂", () => {
  const expected = core.deriveItem(events);
  for (const permutation of permutations(events)) assert.deepEqual(core.deriveItem(permutation), expected);
});
await test("晚到舊事件等於冷啟動重播", () => assert.deepEqual(core.deriveItem([...events.slice(2), events[1]]), core.deriveItem([events[1], ...events.slice(2)])));
await test("錯題兩個不同 clean 日畢業，near 不算", () => {
  assert.equal(core.deriveItem([{study_day:"2026-01-01",outcome:"wrong"},{study_day:"2026-01-02",outcome:"clean"}]).inMistakes, true);
  assert.equal(core.deriveItem([{study_day:"2026-01-01",outcome:"wrong"},{study_day:"2026-01-02",outcome:"near"},{study_day:"2026-01-03",outcome:"clean"}]).inMistakes, true);
  assert.equal(core.deriveItem([{study_day:"2026-01-01",outcome:"wrong"},{study_day:"2026-01-02",outcome:"clean"},{study_day:"2026-01-03",outcome:"clean"}]).inMistakes, false);
});
await test("答案正規化與編輯距離邊界", () => {
  assert.equal(core.normalizeAnswer(" ＰＣＡ， "), "pca");
  assert.equal(core.judge("transfomer", {answer:"transformer",accept:[]}), "near");
  assert.equal(core.judge("特徵直分解", {answer:"特徵值分解",accept:[]}), "wrong");
});
await test("04:00 日界、跨月、跨年、DST", () => {
  assert.equal(core.addDays("2026-01-31", 1), "2026-02-01");
  assert.equal(core.addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(core.studyDay(new Date("2026-02-01T19:59:00Z"), "Asia/Taipei"), "2026-02-01");
  assert.equal(core.studyDay(new Date("2026-02-01T20:00:00Z"), "Asia/Taipei"), "2026-02-02");
  assert.equal(core.studyDay(new Date("2026-03-08T07:30:00Z"), "America/New_York"), "2026-03-07");
});
await test("保存失敗時不執行揭示回呼", async () => {
  let shown = false;
  await assert.rejects(core.signalGate(async () => { throw new Error("quota"); }, () => { shown = true; }));
  assert.equal(shown, false);
});
await test("觀念題型依 conceptId 合併且保留較完整解釋", () => {
  const groups = core.groupConcepts([
    {id:"q1",conceptId:"c1",explanation:"短",tombstoned:false},
    {id:"q2",conceptId:"c1",explanation:"較完整的說明",tombstoned:false},
    {id:"q3",conceptId:"c2",explanation:"另一個觀念",tombstoned:false},
    {id:"q4",conceptId:"c3",explanation:"已刪除",tombstoned:true},
  ]);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0].items.map(x => x.id), ["q1", "q2"]);
  assert.equal(groups[0].primary.id, "q2");
});

await test("部署設定正規化並拒絕未替換 placeholder", () => {
  assert.deepEqual(core.deploymentConfig({supabaseUrl:" https://demo.supabase.co/ ",supabasePublishableKey:" public-key "}), {url:"https://demo.supabase.co",key:"public-key"});
  assert.equal(core.configReady({url:"https://demo.supabase.co",key:"sb_publishable_REPLACE_ME"}), false);
  assert.equal(core.configReady({url:"https://demo.supabase.co",key:"public-key"}), true);
});

await test("使用 Email 密碼註冊登入且不呼叫 Magic Link", () => {
  assert.match(html, /\/auth\/v1\/token\?grant_type=password/);
  assert.match(html, /\/auth\/v1\/signup/);
  assert.doesNotMatch(html, /\/auth\/v1\/otp/);
});

await test("忘記密碼只接受 recovery token 並可設定新密碼", () => {
  const recovery = core.parseRecoverySession("#access_token=recovery-jwt&refresh_token=refresh&type=recovery&expires_in=3600");
  assert.equal(recovery.access_token, "recovery-jwt");
  assert.equal(recovery.type, "recovery");
  assert.equal(core.parseRecoverySession("#access_token=login-jwt&type=magiclink"), null);
  assert.match(html, /\/auth\/v1\/recover\?redirect_to=/);
  assert.match(html, /method:"PUT",body:JSON\.stringify\(\{password\}\)/);
});

await test("設定頁已移除且頁首提供登入註冊按鈕", () => {
  assert.doesNotMatch(html, /<section id="settings"/);
  assert.doesNotMatch(html, /data-go="settings"/);
  assert.match(html, /id="openLogin">登入/);
  assert.match(html, /id="openRegister">註冊/);
});

await test("參考版藍綠介面與完整錯題卡已接入", () => {
  assert.match(html, /linear-gradient\(110deg,#1e3a8a 0%,#2563eb 45%,#0e9384 110%\)/);
  assert.match(html, /📘 學習筆記/);
  assert.match(html, /📝 錯題本/);
  assert.match(html, /data-mistake-review=/);
  assert.match(html, /正確答案：/);
  assert.match(html, /重新練習/);
});

await test("學習筆記採參考版雙欄、搜尋與重點術語結構", () => {
  assert.match(html, /class="notes-layout"/);
  assert.match(html, /id="notesSearch"/);
  assert.match(html, /章節導覽/);
  assert.match(html, /重點精華/);
  assert.match(html, /容易混淆的關鍵對照/);
  assert.match(html, /必背術語/);
  assert.match(html, /已複習這個觀念/);
});

console.log(`core tests: ${tests.length}/${tests.length} passed`);
for (const name of tests) console.log(`✓ ${name}`);
