create table if not exists public.subscriptions (
  email text primary key,
  status text not null default 'active' check (status in ('active', 'inactive')),
  section_ids text[] not null default '{}',
  section_labels text[] not null default '{}',
  source text not null default 'website',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.set_subscription_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists subscriptions_set_updated_at on public.subscriptions;
create trigger subscriptions_set_updated_at
before update on public.subscriptions
for each row
execute function public.set_subscription_updated_at();

alter table public.subscriptions enable row level security;

grant insert, update on public.subscriptions to anon, authenticated;

drop policy if exists "public_insert_subscriptions" on public.subscriptions;
create policy "public_insert_subscriptions"
on public.subscriptions
for insert
to anon, authenticated
with check (true);

drop policy if exists "public_update_subscriptions" on public.subscriptions;
create policy "public_update_subscriptions"
on public.subscriptions
for update
to anon, authenticated
using (true)
with check (true);
