-- ============================================
-- ScrapeStack Database Schema
-- Run this in the Supabase SQL Editor
-- ============================================

-- ============================================
-- PROFILES (extends Supabase auth.users)
-- ============================================
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  plan text not null default 'free' check (plan in ('free','pro','enterprise')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ============================================
-- SCRAPE JOBS (one row per "scrape this site" run)
-- ============================================
create table public.scrape_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  target_url text not null,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled')),
  pages_total int default 0,
  pages_scraped int default 0,
  max_pages int default 100,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

-- ============================================
-- SCRAPED PAGES (one row per page crawled)
-- ============================================
create table public.scraped_pages (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.scrape_jobs(id) on delete cascade,
  url text not null,
  status_code int,
  title text,
  meta_description text,
  word_count int,
  links_found int,
  content_text text,
  content_html_storage_path text,
  scraped_at timestamptz not null default now()
);

-- ============================================
-- SCRAPED DATA (flexible structured extraction)
-- ============================================
create table public.scraped_data (
  id uuid primary key default gen_random_uuid(),
  page_id uuid not null references public.scraped_pages(id) on delete cascade,
  job_id uuid not null references public.scrape_jobs(id) on delete cascade,
  data_type text not null check (data_type in ('text','image','link','table','meta','heading','custom')),
  data jsonb not null,
  created_at timestamptz not null default now()
);

-- ============================================
-- AI RECOMMENDATIONS
-- ============================================
create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.scrape_jobs(id) on delete cascade,
  category text not null,
  title text not null,
  description text not null,
  priority text default 'medium' check (priority in ('low','medium','high')),
  created_at timestamptz not null default now()
);

-- ============================================
-- EXPORTS
-- ============================================
create table public.exports (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.scrape_jobs(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  format text not null check (format in ('json','csv','xlsx')),
  file_url text not null,
  created_at timestamptz not null default now()
);

-- ============================================
-- INDEXES
-- ============================================
create index idx_scrape_jobs_user on public.scrape_jobs(user_id);
create index idx_scraped_pages_job on public.scraped_pages(job_id);
create index idx_scraped_data_page on public.scraped_data(page_id);
create index idx_scraped_data_job on public.scraped_data(job_id);
create index idx_recommendations_job on public.recommendations(job_id);
create index idx_exports_job on public.exports(job_id);

-- ============================================
-- updated_at trigger
-- ============================================
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

-- ============================================
-- Auto-create profile row on signup
-- ============================================
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
alter table public.profiles enable row level security;
alter table public.scrape_jobs enable row level security;
alter table public.scraped_pages enable row level security;
alter table public.scraped_data enable row level security;
alter table public.recommendations enable row level security;
alter table public.exports enable row level security;

create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id);

create policy "jobs_select_own" on public.scrape_jobs
  for select using (auth.uid() = user_id);
create policy "jobs_insert_own" on public.scrape_jobs
  for insert with check (auth.uid() = user_id);
create policy "jobs_update_own" on public.scrape_jobs
  for update using (auth.uid() = user_id);
create policy "jobs_delete_own" on public.scrape_jobs
  for delete using (auth.uid() = user_id);

create policy "pages_select_own" on public.scraped_pages
  for select using (
    exists (select 1 from public.scrape_jobs j where j.id = job_id and j.user_id = auth.uid())
  );

create policy "data_select_own" on public.scraped_data
  for select using (
    exists (select 1 from public.scrape_jobs j where j.id = job_id and j.user_id = auth.uid())
  );

create policy "recs_select_own" on public.recommendations
  for select using (
    exists (select 1 from public.scrape_jobs j where j.id = job_id and j.user_id = auth.uid())
  );

create policy "exports_select_own" on public.exports
  for select using (auth.uid() = user_id);

-- ============================================
-- Enable Realtime for live progress
-- ============================================
alter publication supabase_realtime add table public.scrape_jobs;
