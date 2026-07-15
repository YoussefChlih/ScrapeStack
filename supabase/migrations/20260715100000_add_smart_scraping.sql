-- Add smart scraping options to scrape_jobs table

ALTER TABLE public.scrape_jobs 
ADD COLUMN IF NOT EXISTS crawl_mode text NOT NULL DEFAULT 'full_site' 
  CHECK (crawl_mode IN ('single_page', 'smart_crawl', 'full_site')),
ADD COLUMN IF NOT EXISTS selected_data_types jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS custom_selectors jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS preview_data jsonb DEFAULT '{}'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN public.scrape_jobs.crawl_mode IS 
  'single_page: scrape only the target URL; smart_crawl: follow pagination/links; full_site: BFS crawl entire site';
COMMENT ON COLUMN public.scrape_jobs.selected_data_types IS 
  'Array of data types user selected: ["tables", "profiles", "articles", etc.]';
COMMENT ON COLUMN public.scrape_jobs.custom_selectors IS 
  'User-provided CSS selectors: {"profiles": ".profile-card", "titles": "h1.title"}';
COMMENT ON COLUMN public.scrape_jobs.preview_data IS 
  'Preview data shown to user before scraping started';
