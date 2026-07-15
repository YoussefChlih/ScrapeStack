"""
ScrapeStack Worker — FastAPI application.

Receives scrape job requests from the Next.js app and processes them
asynchronously using Playwright + BeautifulSoup.
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

# Fix Windows asyncio subprocess event loop issue (e.g. Playwright NotImplementedError)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.scraper import crawl_site

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scrapestack.worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Install Playwright browsers on startup if not present."""
    logger.info("ScrapeStack Worker starting up...")
    yield
    logger.info("ScrapeStack Worker shutting down...")


app = FastAPI(
    title="ScrapeStack Worker",
    description="Async web scraping worker for ScrapeStack",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    job_id: str


def verify_webhook_secret(x_webhook_secret: str | None = Header(None)):
    """Verify the webhook secret matches."""
    expected = os.environ.get("WEBHOOK_SECRET", "")
    if not expected:
        logger.warning("WEBHOOK_SECRET not set — skipping verification")
        return
    if x_webhook_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "scrapestack-worker"}


@app.post("/scrape")
async def start_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    x_webhook_secret: str | None = Header(None),
):
    """
    Start a scrape job. The actual crawling runs as a background task
    so this endpoint returns immediately.
    """
    verify_webhook_secret(x_webhook_secret)
    
    logger.info(f"Received scrape request for job_id={request.job_id}")
    
    # Run the crawl in a separate background thread to resolve Windows asyncio subprocess issues
    import threading
    
    def run_scraper_thread():
        if sys.platform == 'win32':
            loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
        else:
            loop = asyncio.new_event_loop()
            
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(crawl_site(request.job_id))
        finally:
            loop.close()

    threading.Thread(target=run_scraper_thread, daemon=True).start()

    return {
        "status": "accepted",
        "job_id": request.job_id,
        "message": "Scrape job started in background thread",
    }
