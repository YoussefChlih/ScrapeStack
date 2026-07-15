-- Migration to add same_domain_only and respect_robots to scrape_jobs
-- Run this in the Supabase SQL Editor if your tables are already created

alter table public.scrape_jobs 
add column if not exists same_domain_only boolean not null default true,
add column if not exists respect_robots boolean not null default true;
