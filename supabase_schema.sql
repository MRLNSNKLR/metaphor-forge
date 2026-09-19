create extension if not exists pgcrypto;

create table if not exists public.saved_results (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'Untitled',
    tags text[] not null default '{}',
    notes text not null default '',
    source text not null default '',
    result text not null default '',
    rhyme_target text not null default '',
    mode text not null default '',
    output_style text not null default '',
    strictness text not null default '',
    tone text not null default '',
    complexity text not null default '',
    imagery text[] not null default '{}',
    creativity text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists public.rhyme_bank (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    term text not null check (length(trim(term)) > 0),
    created_at timestamptz not null default now()
);

create index if not exists saved_results_user_id_idx on public.saved_results using btree (user_id);
create index if not exists rhyme_bank_user_id_idx on public.rhyme_bank using btree (user_id);
create unique index if not exists rhyme_bank_user_term_unique_idx on public.rhyme_bank (user_id, lower(term));

alter table public.saved_results enable row level security;
alter table public.rhyme_bank enable row level security;

revoke all on table public.saved_results from anon, authenticated;
revoke all on table public.rhyme_bank from anon, authenticated;
grant select, insert, update, delete on table public.saved_results to authenticated;
grant select, insert, update, delete on table public.rhyme_bank to authenticated;

drop policy if exists "saved_results_select_own" on public.saved_results;
drop policy if exists "saved_results_insert_own" on public.saved_results;
drop policy if exists "saved_results_update_own" on public.saved_results;
drop policy if exists "saved_results_delete_own" on public.saved_results;

create policy "saved_results_select_own" on public.saved_results for select to authenticated
using ((select auth.uid()) = user_id);
create policy "saved_results_insert_own" on public.saved_results for insert to authenticated
with check ((select auth.uid()) = user_id);
create policy "saved_results_update_own" on public.saved_results for update to authenticated
using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "saved_results_delete_own" on public.saved_results for delete to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "rhyme_bank_select_own" on public.rhyme_bank;
drop policy if exists "rhyme_bank_insert_own" on public.rhyme_bank;
drop policy if exists "rhyme_bank_update_own" on public.rhyme_bank;
drop policy if exists "rhyme_bank_delete_own" on public.rhyme_bank;

create policy "rhyme_bank_select_own" on public.rhyme_bank for select to authenticated
using ((select auth.uid()) = user_id);
create policy "rhyme_bank_insert_own" on public.rhyme_bank for insert to authenticated
with check ((select auth.uid()) = user_id);
create policy "rhyme_bank_update_own" on public.rhyme_bank for update to authenticated
using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "rhyme_bank_delete_own" on public.rhyme_bank for delete to authenticated
using ((select auth.uid()) = user_id);
