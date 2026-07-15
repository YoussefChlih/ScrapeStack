// TypeScript types matching the Supabase database schema

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  plan: 'free' | 'pro' | 'enterprise';
  created_at: string;
  updated_at: string;
}

export interface ScrapeJob {
  id: string;
  user_id: string;
  target_url: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  pages_total: number;
  pages_scraped: number;
  max_pages: number;
  same_domain_only: boolean;
  respect_robots: boolean;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ScrapedPage {
  id: string;
  job_id: string;
  url: string;
  status_code: number | null;
  title: string | null;
  meta_description: string | null;
  word_count: number | null;
  links_found: number | null;
  content_text: string | null;
  content_html_storage_path: string | null;
  scraped_at: string;
}

export interface ScrapedDataItem {
  id: string;
  page_id: string;
  job_id: string;
  data_type: 'text' | 'image' | 'link' | 'table' | 'meta' | 'heading' | 'custom';
  data: Record<string, unknown>;
  created_at: string;
}

export interface Recommendation {
  id: string;
  job_id: string;
  category: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
}

export interface Export {
  id: string;
  job_id: string;
  user_id: string;
  format: 'json' | 'csv' | 'xlsx';
  file_url: string;
  created_at: string;
}

// Supabase Database type for type-safe queries
export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: Profile;
        Insert: Omit<Profile, 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Profile, 'id' | 'created_at'>>;
      };
      scrape_jobs: {
        Row: ScrapeJob;
        Insert: Omit<ScrapeJob, 'id' | 'created_at' | 'pages_total' | 'pages_scraped'> & {
          id?: string;
          pages_total?: number;
          pages_scraped?: number;
          same_domain_only?: boolean;
          respect_robots?: boolean;
        };
        Update: Partial<Omit<ScrapeJob, 'id' | 'created_at'>>;
      };
      scraped_pages: {
        Row: ScrapedPage;
        Insert: Omit<ScrapedPage, 'id' | 'scraped_at'>;
        Update: Partial<Omit<ScrapedPage, 'id'>>;
      };
      scraped_data: {
        Row: ScrapedDataItem;
        Insert: Omit<ScrapedDataItem, 'id' | 'created_at'>;
        Update: Partial<Omit<ScrapedDataItem, 'id'>>;
      };
      recommendations: {
        Row: Recommendation;
        Insert: Omit<Recommendation, 'id' | 'created_at'>;
        Update: Partial<Omit<Recommendation, 'id'>>;
      };
      exports: {
        Row: Export;
        Insert: Omit<Export, 'id' | 'created_at'>;
        Update: Partial<Omit<Export, 'id'>>;
      };
    };
  };
}
