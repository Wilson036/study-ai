-- 拾光：AI 應用規劃師記憶練習
-- Authentication 啟用 Email signup；使用者第一次完成 Magic Link 後會自動建立帳號。
-- 所有已登入帳號可讀私有題庫；事件與設定仍由 RLS 依 auth.uid() 隔離。

create table if not exists public.answer_events (
  event_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id text not null,
  study_day date not null,
  outcome text not null check (outcome in ('clean','near','wrong')),
  hint_level int not null default 0 check (hint_level between 0 and 3),
  revealed boolean not null default false,
  first_attempt boolean not null default true,
  client_ts timestamptz not null,
  created_at timestamptz not null default now()
);

create or replace function public.reject_insane_study_day()
returns trigger language plpgsql set search_path = '' as $$
begin
  if new.study_day < date '2026-01-01' or new.study_day > current_date + 1 then
    raise exception 'invalid study_day';
  end if;
  return new;
end $$;

drop trigger if exists ae_sane_day on public.answer_events;
create trigger ae_sane_day before insert on public.answer_events
  for each row execute function public.reject_insane_study_day();

create index if not exists ae_user_created_idx on public.answer_events (user_id, created_at, event_id);
alter table public.answer_events enable row level security;
drop policy if exists ae_sel on public.answer_events;
drop policy if exists ae_ins on public.answer_events;
create policy ae_sel on public.answer_events for select using ((select auth.uid()) = user_id);
create policy ae_ins on public.answer_events for insert with check ((select auth.uid()) = user_id);
-- 故意沒有 update/delete policy：事件只能新增，不能改寫。

create table if not exists public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  timezone text not null default 'Asia/Taipei',
  new_per_day int not null default 12 check (new_per_day between 1 and 50),
  per_session int not null default 20 check (per_session between 5 and 100),
  updated_at timestamptz not null default now()
);
alter table public.user_settings enable row level security;
drop policy if exists us_all on public.user_settings;
create policy us_all on public.user_settings for all using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create or replace function public.touch_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists us_touch on public.user_settings;
create trigger us_touch before update on public.user_settings for each row execute function public.touch_updated_at();

insert into storage.buckets (id, name, public)
values ('bank', 'bank', false)
on conflict (id) do update set public = false;

drop policy if exists bank_single_user_read on storage.objects;
drop policy if exists bank_authenticated_read on storage.objects;
create policy bank_authenticated_read on storage.objects for select to authenticated
using (bucket_id = 'bank');
