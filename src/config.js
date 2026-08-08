// 單一部署環境的公開設定。
// Supabase publishable/anon key 本來就會公開給瀏覽器；絕不可填入 secret 或 service_role key。
globalThis.STUDY_APP_CONFIG = Object.freeze({
  supabaseUrl: "https://qaingnceljcbtwpvqxbi.supabase.co",
  supabasePublishableKey: "sb_publishable_sa7q-9aB4480D_ftm1ccuA_g5Ac827L",
});
