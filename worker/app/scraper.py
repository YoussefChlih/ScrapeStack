"""
BFS Web Crawler using Playwright + BeautifulSoup.

Crawls a website page-by-page, extracts structured content, and writes
results to Supabase incrementally.
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser

from app.supabase_client import get_supabase
from app.exporter import generate_exports
from app.recommender import generate_recommendations

logger = logging.getLogger("scrapestack.scraper")

# Delay between page requests (seconds)
CRAWL_DELAY = 1.5

# User-Agent string
USER_AGENT = "ScrapeStack/1.0 (+https://scrapestack.dev)"


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to the same domain."""
    parsed = urlparse(url)
    return parsed.netloc == base_domain or parsed.netloc == ""


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and trailing slashes."""
    parsed = urlparse(url)
    # Remove fragment, normalize path
    normalized = parsed._replace(fragment="")
    result = normalized.geturl().rstrip("/")
    return result


def can_fetch(robot_parser: RobotFileParser | None, url: str) -> bool:
    """Check if robots.txt allows fetching this URL."""
    if robot_parser is None:
        return True
    try:
        return robot_parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def parse_robots_txt(base_url: str) -> RobotFileParser | None:
    """Parse robots.txt for the given base URL."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp
    except Exception as e:
        logger.warning(f"Could not parse robots.txt: {e}")
        return None


def extract_page_data(html: str, page_url: str, base_domain: str) -> dict:
    """
    Extract structured data from a page's HTML.
    
    Returns a dict with page-level metadata and lists of extracted items.
    """
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Meta description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content", "") if meta_desc_tag else None

    # Body text
    # Remove script and style elements
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    body = soup.find("body")
    body_text = body.get_text(separator=" ", strip=True) if body else ""
    word_count = len(body_text.split()) if body_text else 0

    # Headings (h1-h6)
    headings = []
    for level in range(1, 7):
        for heading in soup.find_all(f"h{level}"):
            text = heading.get_text(strip=True)
            if text:
                headings.append({"level": level, "text": text})

    # Links
    links = []
    internal_count = 0
    external_count = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        absolute_url = urljoin(page_url, href)
        link_text = a_tag.get_text(strip=True)
        is_internal = is_same_domain(absolute_url, base_domain)
        
        links.append({
            "url": absolute_url,
            "text": link_text,
            "is_internal": is_internal,
        })
        
        if is_internal:
            internal_count += 1
        else:
            external_count += 1

    # Images
    images = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src:
            absolute_src = urljoin(page_url, src)
            images.append({
                "src": absolute_src,
                "alt": img.get("alt", ""),
                "has_alt": bool(img.get("alt", "").strip()),
            })

    # Tables
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append({"rows": rows, "row_count": len(rows)})

    # Meta tags
    meta_tags = []
    for meta in soup.find_all("meta"):
        name = meta.get("name", meta.get("property", ""))
        content = meta.get("content", "")
        if name and content:
            meta_tags.append({"name": name, "content": content})

    return {
        "title": title,
        "meta_description": meta_description,
        "body_text": body_text[:50000],  # Cap at 50k chars
        "word_count": word_count,
        "headings": headings,
        "links": links,
        "links_found": len(links),
        "internal_links": internal_count,
        "external_links": external_count,
        "images": images,
        "tables": tables,
        "meta_tags": meta_tags,
    }


async def crawl_site(job_id: str):
    """
    Main BFS crawl function.
    
    Fetches the job from Supabase, crawls the target site page-by-page,
    extracts structured data, and writes results back to Supabase.
    """
    sb = get_supabase()
    
    try:
        # Fetch the job
        job_resp = sb.table("scrape_jobs").select("*").eq("id", job_id).single().execute()
        job = job_resp.data
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        target_url = job["target_url"]
        max_pages = job.get("max_pages", 100)
        
        logger.info(f"Starting crawl: job={job_id}, url={target_url}, max_pages={max_pages}")

        # Update job status to running
        sb.table("scrape_jobs").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        # Parse base domain
        parsed_base = urlparse(target_url)
        base_domain = parsed_base.netloc

        # Parse robots.txt
        robot_parser = parse_robots_txt(target_url)

        # BFS queue
        queue: deque[str] = deque([normalize_url(target_url)])
        visited: set[str] = set()
        pages_scraped = 0

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 720},
            )
            page: Page = await context.new_page()

            while queue and pages_scraped < max_pages:
                current_url = queue.popleft()
                normalized = normalize_url(current_url)

                # Skip if already visited
                if normalized in visited:
                    continue
                visited.add(normalized)

                # Check robots.txt
                if not can_fetch(robot_parser, current_url):
                    logger.info(f"Skipping (robots.txt): {current_url}")
                    continue

                logger.info(f"Crawling [{pages_scraped + 1}/{max_pages}]: {current_url}")

                status_code = 200
                try:
                    response = await page.goto(
                        current_url,
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    if response:
                        status_code = response.status

                    # Wait a moment for dynamic content
                    await page.wait_for_timeout(1000)

                    # Get rendered HTML
                    html = await page.content()

                except Exception as e:
                    logger.warning(f"Error loading {current_url}: {e}")
                    status_code = 0
                    html = ""

                # Extract data
                data = extract_page_data(html, current_url, base_domain)

                # Insert scraped_pages row
                page_id = str(uuid.uuid4())
                sb.table("scraped_pages").insert({
                    "id": page_id,
                    "job_id": job_id,
                    "url": current_url,
                    "status_code": status_code,
                    "title": data["title"],
                    "meta_description": data["meta_description"],
                    "word_count": data["word_count"],
                    "links_found": data["links_found"],
                    "content_text": data["body_text"],
                }).execute()

                # Insert scraped_data rows for each data type
                data_rows = []

                # Headings
                if data["headings"]:
                    data_rows.append({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "heading",
                        "data": {"items": data["headings"]},
                    })

                # Links
                if data["links"]:
                    data_rows.append({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "link",
                        "data": {
                            "items": data["links"][:500],  # Cap at 500 links
                            "internal_count": data["internal_links"],
                            "external_count": data["external_links"],
                        },
                    })

                # Images
                if data["images"]:
                    data_rows.append({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "image",
                        "data": {"items": data["images"]},
                    })

                # Tables
                if data["tables"]:
                    data_rows.append({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "table",
                        "data": {"items": data["tables"]},
                    })

                # Meta tags
                if data["meta_tags"]:
                    data_rows.append({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "meta",
                        "data": {"items": data["meta_tags"]},
                    })

                # Text summary
                data_rows.append({
                    "page_id": page_id,
                    "job_id": job_id,
                    "data_type": "text",
                    "data": {
                        "word_count": data["word_count"],
                        "preview": data["body_text"][:500],
                    },
                })

                if data_rows:
                    sb.table("scraped_data").insert(data_rows).execute()

                # Update job progress
                pages_scraped += 1
                sb.table("scrape_jobs").update({
                    "pages_scraped": pages_scraped,
                    "pages_total": min(len(visited) + len(queue), max_pages),
                }).eq("id", job_id).execute()

                # Add internal links to queue
                for link in data["links"]:
                    if link["is_internal"]:
                        link_url = normalize_url(link["url"])
                        # Only add HTML-like URLs
                        parsed = urlparse(link_url)
                        path = parsed.path.lower()
                        # Skip files that aren't pages
                        skip_extensions = (
                            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
                            ".css", ".js", ".zip", ".tar", ".gz", ".mp4",
                            ".mp3", ".ico", ".woff", ".woff2", ".ttf",
                        )
                        if not any(path.endswith(ext) for ext in skip_extensions):
                            if link_url not in visited:
                                queue.append(link_url)

                # Delay between requests
                await asyncio.sleep(CRAWL_DELAY)

            await browser.close()

        # Job completed successfully
        sb.table("scrape_jobs").update({
            "status": "completed",
            "pages_total": pages_scraped,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        logger.info(f"Crawl completed: job={job_id}, pages={pages_scraped}")

        # Generate exports
        try:
            await generate_exports(job_id)
            logger.info(f"Exports generated for job={job_id}")
        except Exception as e:
            logger.error(f"Export generation failed for job={job_id}: {e}")

        # Generate AI recommendations
        try:
            await generate_recommendations(job_id)
            logger.info(f"Recommendations generated for job={job_id}")
        except Exception as e:
            logger.error(f"Recommendation generation failed for job={job_id}: {e}")

    except Exception as e:
        logger.error(f"Crawl failed for job={job_id}: {e}", exc_info=True)
        try:
            sb.table("scrape_jobs").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
        except Exception:
            pass
