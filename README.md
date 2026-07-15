# ScrapeStack

A production-grade SaaS web application that lets authenticated users submit a website URL, crawl it page by page, extract structured content, view results in a smart analytics dashboard, and receive AI-generated recommendations.

## Architecture

```
User Browser
   │
   ▼
Next.js App (Vercel)         →  Auth, dashboard, job management
   │
   ▼
Python FastAPI Worker         →  Crawls websites with Playwright + BS4
   │
   ▼
Supabase                      →  Auth, Postgres, Storage, Realtime
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS v4 |
| Auth & DB | Supabase (Auth + Postgres + RLS + Realtime) |
| Scraping | Python FastAPI + Playwright + BeautifulSoup |
| Charts | Recharts |
| AI | OpenAI GPT-4o-mini |
| Exports | pandas + openpyxl (JSON/CSV/XLSX) |

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- A [Supabase](https://supabase.com) project
- An [OpenAI](https://platform.openai.com) API key (for AI recommendations)

## Setup

### 1. Database

1. Go to your Supabase project's SQL Editor
2. Run the contents of `supabase/schema.sql`
3. Enable Realtime for the `scrape_jobs` table (the schema does this automatically)

### 2. Next.js App (web/)

```bash
cd web
cp .env.example .env.local
# Edit .env.local with your Supabase URL, anon key, service role key, and worker URL
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

### 3. Python Worker (worker/)

```bash
cd worker
cp .env.example .env
# Edit .env with your Supabase URL, service role key, webhook secret, and OpenAI key

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

uvicorn app.main:app --reload --port 8000
```

The worker will be available at `http://localhost:8000`.

### 4. Environment Variables

**web/.env.local:**
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anon (public) key |
| `SUPABASE_SERVICE_ROLE_KEY` | Your Supabase service role key |
| `WORKER_URL` | URL of the Python worker (default: `http://localhost:8000`) |
| `WORKER_WEBHOOK_SECRET` | Shared secret for worker authentication |

**worker/.env:**
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Your Supabase service role key |
| `WEBHOOK_SECRET` | Must match `WORKER_WEBHOOK_SECRET` above |
| `OPENAI_API_KEY` | Your OpenAI API key |

## Deployment

### Next.js → Vercel

```bash
cd web
npx vercel --prod
```

Set all environment variables in the Vercel dashboard.

### Python Worker → Railway

```bash
cd worker
# Push to a GitHub repo, then:
# 1. Create a new Railway project
# 2. Connect to your repo
# 3. Set the root directory to /worker
# 4. Add all environment variables
# 5. Deploy
```

Or use the Docker image directly:
```bash
docker build -t scrapestack-worker .
docker run -p 8000:8000 --env-file .env scrapestack-worker
```

## Features

- **Page-by-page crawling** with BFS link discovery
- **Live progress** via Supabase Realtime
- **Smart dashboard** with Recharts visualizations
- **AI recommendations** (SEO, accessibility, content quality)
- **Export** to JSON, CSV, XLSX
- **Auth** with email/password and Google OAuth
- **Responsive** design — works on mobile, tablet, and desktop
