import fs from "node:fs";
import assert from "node:assert/strict";

const html = fs.readFileSync(new URL("../src/index.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0]?.[1];
if (!script) throw new Error("找不到 inline app script");
const prefix = script.slice(0, script.indexOf("function request("));
const signalGate = script.match(/async function signalGate\([^\n]+/)?.[0];
const core = new Function("crypto", `${prefix}\n${signalGate}; return {addDays,studyDay,dayOutcome,deriveItem,deriveAll,normalizeAnswer,editDistance,judge,signalGate,parseMagicLink,deploymentConfig,configReady};`)(globalThis.crypto);
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
await test("Magic Link fragment 可安全解析", () => {
  const session = core.parseMagicLink("#access_token=user-jwt&refresh_token=refresh-value&expires_at=1900000000&expires_in=3600&token_type=bearer&type=magiclink");
  assert.equal(session.access_token, "user-jwt");
  assert.equal(session.refresh_token, "refresh-value");
  assert.equal(session.expires_at, 1900000000);
  assert.equal(core.parseMagicLink(""), null);
  assert.deepEqual(core.parseMagicLink("#error_description=Link%20expired"), {error:"Link expired"});
});

await test("部署設定正規化並拒絕未替換 placeholder", () => {
  assert.deepEqual(core.deploymentConfig({supabaseUrl:" https://demo.supabase.co/ ",supabasePublishableKey:" public-key "}), {url:"https://demo.supabase.co",key:"public-key"});
  assert.equal(core.configReady({url:"https://demo.supabase.co",key:"sb_publishable_REPLACE_ME"}), false);
  assert.equal(core.configReady({url:"https://demo.supabase.co",key:"public-key"}), true);
});

await test("Magic Link 允許首次使用自動建立帳號", () => {
  assert.match(html, /should_create_user:true/);
  assert.doesNotMatch(html, /should_create_user:false/);
});

console.log(`core tests: ${tests.length}/${tests.length} passed`);
for (const name of tests) console.log(`✓ ${name}`);
