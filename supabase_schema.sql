-- Psychology CPD Portfolio Tracker v3.0
-- Run this once in Supabase SQL Editor.

create table if not exists public.portfolios (
    user_id uuid primary key references auth.users(id) on delete cascade,
    portfolio jsonb not null default '{}'::jsonb,
    revision bigint not null default 1 check (revision >= 1),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create or replace function public.set_portfolio_user_id()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
    if new.user_id is null then
        new.user_id := auth.uid();
    end if;
    return new;
end;
$$;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists portfolios_set_user_id on public.portfolios;
create trigger portfolios_set_user_id
before insert on public.portfolios
for each row execute function public.set_portfolio_user_id();

drop trigger if exists portfolios_set_updated_at on public.portfolios;
create trigger portfolios_set_updated_at
before update on public.portfolios
for each row execute function public.set_updated_at();

alter table public.portfolios enable row level security;

revoke all on public.portfolios from anon;
grant select, insert, update, delete on public.portfolios to authenticated;

drop policy if exists "Users can read their own portfolio" on public.portfolios;
create policy "Users can read their own portfolio"
on public.portfolios for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own portfolio" on public.portfolios;
create policy "Users can create their own portfolio"
on public.portfolios for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own portfolio" on public.portfolios;
create policy "Users can update their own portfolio"
on public.portfolios for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own portfolio" on public.portfolios;
create policy "Users can delete their own portfolio"
on public.portfolios for delete
to authenticated
using ((select auth.uid()) = user_id);
