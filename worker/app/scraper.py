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
from app.extractor import extract_selected_data

logger = logging.getLogger("scrapestack.scraper")

# Delay between page requests (seconds)
CRAWL_DELAY = 1.5

# User-Agent string
USER_AGENT = "ScrapeStack/1.0 (+https://scrapestack.dev)"


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to the same domain (including subdomains)."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True
    hostname = hostname.lower()
    
    # Normalize base_domain to strip port if present
    base_domain_clean = base_domain
    if "://" not in base_domain_clean:
        base_domain_clean = f"http://{base_domain_clean}"
    parsed_base = urlparse(base_domain_clean)
    base_host = (parsed_base.hostname or base_domain).lower()
    
    return hostname == base_host or hostname.endswith("." + base_host)


def normalize_url(url: str) -> str:
    """Normalize a URL by lowercasing scheme/host/path, removing fragments and trailing slashes."""
    url_stripped = url.strip()
    parsed = urlparse(url_stripped)
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.lower(),
        fragment=""
    )
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

    # OpenGraph & Canonical
    canonical_tag = soup.find("link", rel="canonical")
    canonical_url = canonical_tag.get("href", "") if canonical_tag else None

    og_meta = {}
    for meta in soup.find_all("meta", property=True):
        prop = meta["property"].lower()
        if prop.startswith("og:"):
            og_meta[prop] = meta.get("content", "")

    # Fallback to OG if missing
    if not title and "og:title" in og_meta:
        title = og_meta["og:title"]
    if not meta_description and "og:description" in og_meta:
        meta_description = og_meta["og:description"]

    # Structured data (JSON-LD)
    structured_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            structured_data.append(json.loads(script.string))
        except Exception:
            pass

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

    if canonical_url:
        meta_tags.append({"name": "canonical", "content": canonical_url})
    for k, v in og_meta.items():
        meta_tags.append({"name": k, "content": v})

    # Extract meaningful content text
    content_text = extract_meaningful_text(soup, page_url)

    word_count = len(content_text.split()) if content_text else 0

    return {
        "title": title,
        "meta_description": meta_description,
        "body_text": content_text[:50000],
        "word_count": word_count,
        "headings": headings,
        "links": links,
        "links_found": len(links),
        "internal_links": internal_count,
        "external_links": external_count,
        "images": images,
        "tables": tables,
        "meta_tags": meta_tags,
        "structured_data": structured_data,
    }


def extract_meaningful_text(soup: BeautifulSoup, page_url: str) -> str:
    """
    Extract meaningful text content from a page, prioritizing actual content
    over navigation, footer, sidebar, and other boilerplate.
    """
    import re
    
    # Remove boilerplate tags
    boilerplate_tags = [
        "script", "style", "noscript", "nav", "footer", "header", 
        "aside", "form", "svg", "iframe", "canvas", "modal"
    ]
    for tag in boilerplate_tags:
        for elem in soup.find_all(tag):
            elem.decompose()

    # Remove elements with hidden styles
    for elem in soup.find_all(True):
        if hasattr(elem, "attrs") and elem.attrs is not None:
            style = elem.get("style", "")
            if style:
                style_lower = style.lower().replace(" ", "")
                if "display:none" in style_lower or "visibility:hidden" in style_lower:
                    elem.decompose()
                    continue
            if elem.get("aria-hidden") == "true":
                elem.decompose()
                continue

    # Try to find the main content area
    main_content = None
    
    # Priority order for content extraction
    content_selectors = [
        "article",
        "main",
        "[role='main']",
        ".post-content",
        ".entry-content",
        ".article-content",
        ".blog-content",
        ".content-body",
        "#content",
        ".content",
    ]
    
    for selector in content_selectors:
        try:
            if selector.startswith("["):
                main_content = soup.select_one(selector)
            elif selector.startswith("."):
                main_content = soup.find(class_=lambda x: x and selector[1:] in x.split())
            elif selector.startswith("#"):
                main_content = soup.find(id=selector[1:])
            else:
                main_content = soup.find(selector)
            
            if main_content:
                text = main_content.get_text(separator=" ", strip=True)
                if len(text.split()) > 50:
                    break
                main_content = None
        except Exception:
            continue

    if not main_content:
        # Fallback: use body but try to exclude common noise
        body = soup.find("body") or soup
        
        # Remove common noise elements
        noise_selectors = [
            ".sidebar", "#sidebar", ".widget", "#widget",
            ".menu", "#menu", ".nav", "#nav",
            ".breadcrumb", "#breadcrumb",
            ".cookie", "#cookie", ".consent", "#consent",
            ".social", "#social", ".share", "#share",
            ".related", "#related", ".comments", "#comments",
        ]
        for selector in noise_selectors:
            if selector.startswith("."):
                for elem in body.find_all(class_=lambda x: x and selector[1:] in x.split()):
                    elem.decompose()
            elif selector.startswith("#"):
                elem = body.find(id=selector[1:])
                if elem:
                    elem.decompose()
        
        main_content = body

    text = main_content.get_text(separator=" ", strip=True)
    
    # Clean whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    return text


async def scrape_with_smart_extraction(job_id: str):
    """
    Smart scrape based on user-selected data types.
    Supports single-page, smart-crawl, and full-site modes.
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
        crawl_mode = job.get("crawl_mode", "full_site")
        selected_data_types = job.get("selected_data_types", [])
        max_pages = job.get("max_pages", 100)
        
        logger.info(f"Starting smart scrape: job={job_id}, url={target_url}, mode={crawl_mode}, data_types={selected_data_types}")

        # Update job status to running
        sb.table("scrape_jobs").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 720},
            )
            page: Page = await context.new_page()

            pages_to_scrape = [target_url]
            visited = set()
            pages_scraped = 0

            if crawl_mode == "single_page":
                # Only scrape the target URL
                max_pages = 1
            elif crawl_mode == "smart_crawl":
                # Will detect pagination and follow it
                pass
            # else: full_site uses existing BFS logic

            while pages_to_scrape and pages_scraped < max_pages:
                current_url = pages_to_scrape.pop(0)
                
                if current_url in visited:
                    continue
                visited.add(current_url)

                logger.info(f"Scraping [{pages_scraped + 1}/{max_pages}]: {current_url}")

                status_code = 200
                try:
                    response = await page.goto(
                        current_url,
                        wait_until="networkidle",
                        timeout=45000,
                    )
                    if response:
                        status_code = response.status

                    html = await page.content()

                except Exception as e:
                    logger.warning(f"Error loading {current_url}: {e}")
                    status_code = 0
                    html = ""

                if html and selected_data_types:
                    # Use smart extraction
                    extracted = extract_selected_data(html, current_url, selected_data_types)
                    
                    # Store extracted data
                    page_id = str(uuid.uuid4())
                    
                    # Get page title
                    soup_temp = BeautifulSoup(html, "lxml")
                    title_tag = soup_temp.find("title")
                    page_title = title_tag.get_text(strip=True) if title_tag else None
                    
                    sb.table("scraped_pages").insert({
                        "id": page_id,
                        "job_id": job_id,
                        "url": current_url,
                        "status_code": status_code,
                        "title": page_title,
                        "meta_description": None,
                        "word_count": 0,
                        "links_found": 0,
                        "content_text": str(extracted)[:5000],  # Store summary
                    }).execute()

                    # Store extracted data as custom type
                    sb.table("scraped_data").insert({
                        "page_id": page_id,
                        "job_id": job_id,
                        "data_type": "custom",
                        "data": extracted,
                    }).execute()

                    # For smart_crawl, detect pagination
                    if crawl_mode == "smart_crawl" and pages_scraped < max_pages - 1:
                        # Look for "next" page links
                        soup = BeautifulSoup(html, "lxml")
                        next_link = soup.find("a", text=lambda x: x and any(keyword in x.lower() for keyword in ["next", "→", "›", "»"]))
                        if next_link and next_link.get("href"):
                            next_url = urljoin(current_url, next_link["href"])
                            if next_url not in visited:
                                pages_to_scrape.append(next_url)
                
                else:
                    # Fallback to generic extraction (backwards compatibility)
                    parsed_base = urlparse(target_url)
                    base_domain = parsed_base.netloc
                    data = extract_page_data(html, current_url, base_domain)
                    
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

                pages_scraped += 1
                
                # Update progress
                sb.table("scrape_jobs").update({
                    "pages_scraped": pages_scraped,
                    "pages_total": pages_scraped,
                }).eq("id", job_id).execute()

                # Shorter delay for single page mode
                if crawl_mode == "single_page":
                    await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(CRAWL_DELAY)

            await browser.close()

        # Job completed
        sb.table("scrape_jobs").update({
            "status": "completed",
            "pages_total": pages_scraped,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        logger.info(f"Smart scrape completed: job={job_id}, pages={pages_scraped}")

        # Generate exports
        try:
            await generate_exports(job_id)
        except Exception as e:
            logger.error(f"Export generation failed: {e}")

        # Generate recommendations
        try:
            await generate_recommendations(job_id)
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")

    except Exception as e:
        logger.error(f"Smart scrape failed for job={job_id}: {e}", exc_info=True)
        try:
            sb.table("scrape_jobs").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
        except Exception:
            pass


async def crawl_site(job_id: str):
    """
    Main BFS crawl function.
    
    Routes to smart extraction if selected_data_types is set,
    otherwise uses traditional full-site crawl.
    """
    sb = get_supabase()
    
    try:
        # Fetch the job to check mode
        job_resp = sb.table("scrape_jobs").select("*").eq("id", job_id).single().execute()
        job = job_resp.data
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Check if smart extraction is requested
        selected_data_types = job.get("selected_data_types", [])
        crawl_mode = job.get("crawl_mode", "full_site")
        
        if selected_data_types or crawl_mode != "full_site":
            # Use smart extraction
            await scrape_with_smart_extraction(job_id)
            return
        
        # Otherwise continue with traditional full-site crawl
        target_url = job["target_url"]
        max_pages = job.get("max_pages", 100)
        same_domain_only = job.get("same_domain_only", True)
        respect_robots = job.get("respect_robots", True)
        
        logger.info(f"Starting crawl: job={job_id}, url={target_url}, max_pages={max_pages}, same_domain_only={same_domain_only}, respect_robots={respect_robots}")

        # Update job status to running
        sb.table("scrape_jobs").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        # Parse base domain
        parsed_base = urlparse(target_url)
        base_domain = parsed_base.netloc

        # Parse robots.txt
        robot_parser = None
        if respect_robots:
            robot_parser = parse_robots_txt(target_url)
            if not can_fetch(robot_parser, target_url):
                logger.info(f"Start URL blocked by robots.txt: {target_url}")
                sb.table("scrape_jobs").update({
                    "status": "failed",
                    "error_message": "Crawling blocked: The target URL is disallowed by the website's robots.txt policy.",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", job_id).execute()
                return

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
                if respect_robots and robot_parser:
                    if not can_fetch(robot_parser, current_url):
                        logger.info(f"Skipping (robots.txt): {current_url}")
                        continue

                logger.info(f"Crawling [{pages_scraped + 1}/{max_pages}]: {current_url}")

                status_code = 200
                try:
                    response = await page.goto(
                        current_url,
                        wait_until="networkidle",
                        timeout=45000,
                    )
                    if response:
                        status_code = response.status

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

                # Add internal/external links to queue
                for link in data["links"]:
                    if link["is_internal"] or not same_domain_only:
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
