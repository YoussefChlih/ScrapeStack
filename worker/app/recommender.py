"""
AI Recommendation generator — sends a condensed summary of scraped data
to an LLM and stores categorized recommendations.
"""

import json
import logging
import os

from openai import OpenAI
from app.supabase_client import get_supabase

logger = logging.getLogger("scrapestack.recommender")

SYSTEM_PROMPT = """You are a web analysis expert. Given a summary of a website crawl, generate 5-10 actionable recommendations.

Each recommendation must have:
- category: one of "SEO", "Content", "Accessibility", "Structure", "Performance", "Data Quality"
- title: a short, clear title (max 80 chars)
- description: 1-3 sentences explaining the issue and what to do about it
- priority: "low", "medium", or "high"

Focus on:
- Missing or duplicate page titles
- Missing meta descriptions
- Pages with very low word count (thin content)
- Missing image alt text (accessibility)
- Broken links (4xx/5xx status codes)
- Heading structure issues (missing H1s, heading hierarchy)
- Internal/external link balance
- Content gaps or opportunities

Return ONLY a JSON array of recommendation objects. No markdown, no explanation."""


def build_summary(job_id: str) -> str:
    """Build a condensed text summary of the crawl results for the LLM."""
    sb = get_supabase()

    # Fetch pages
    pages_resp = (
        sb.table("scraped_pages")
        .select("url, title, meta_description, word_count, status_code, links_found")
        .eq("job_id", job_id)
        .execute()
    )
    pages = pages_resp.data or []

    if not pages:
        return ""

    total_pages = len(pages)
    total_words = sum(p.get("word_count", 0) or 0 for p in pages)
    avg_words = total_words // total_pages if total_pages else 0

    # Broken links (4xx/5xx)
    broken_pages = [p for p in pages if p.get("status_code", 200) >= 400]

    # Missing titles
    missing_titles = [p for p in pages if not p.get("title")]

    # Duplicate titles
    titles = [p["title"] for p in pages if p.get("title")]
    seen_titles = {}
    duplicate_titles = []
    for t in titles:
        seen_titles[t] = seen_titles.get(t, 0) + 1
    duplicate_titles = [t for t, count in seen_titles.items() if count > 1]

    # Missing meta descriptions
    missing_meta = [p for p in pages if not p.get("meta_description")]

    # Thin content pages (< 100 words)
    thin_pages = [p for p in pages if (p.get("word_count") or 0) < 100]

    # Fetch image data for alt-text analysis
    images_resp = (
        sb.table("scraped_data")
        .select("data")
        .eq("job_id", job_id)
        .eq("data_type", "image")
        .execute()
    )
    
    total_images = 0
    missing_alt = 0
    for row in (images_resp.data or []):
        items = row.get("data", {}).get("items", [])
        total_images += len(items)
        missing_alt += sum(1 for img in items if not img.get("has_alt", True))

    # Fetch link data
    links_resp = (
        sb.table("scraped_data")
        .select("data")
        .eq("job_id", job_id)
        .eq("data_type", "link")
        .execute()
    )
    
    total_internal = 0
    total_external = 0
    for row in (links_resp.data or []):
        d = row.get("data", {})
        total_internal += d.get("internal_count", 0)
        total_external += d.get("external_count", 0)

    # Fetch heading data
    headings_resp = (
        sb.table("scraped_data")
        .select("data")
        .eq("job_id", job_id)
        .eq("data_type", "heading")
        .execute()
    )
    
    pages_without_h1 = 0
    all_headings = []
    for row in (headings_resp.data or []):
        items = row.get("data", {}).get("items", [])
        h1s = [h for h in items if h.get("level") == 1]
        if not h1s:
            pages_without_h1 += 1
        all_headings.extend(items)

    summary = f"""Website Crawl Summary:
- Total pages crawled: {total_pages}
- Total word count: {total_words:,}
- Average words per page: {avg_words}
- Broken pages (4xx/5xx): {len(broken_pages)}
- Pages missing title: {len(missing_titles)} / {total_pages}
- Duplicate titles found: {len(duplicate_titles)}
- Pages missing meta description: {len(missing_meta)} / {total_pages}
- Thin content pages (<100 words): {len(thin_pages)} / {total_pages}
- Total images: {total_images}
- Images missing alt text: {missing_alt} / {total_images}
- Internal links: {total_internal}
- External links: {total_external}
- Pages without H1 heading: {pages_without_h1} / {total_pages}

Sample page titles: {', '.join(titles[:10])}

Thin content pages: {', '.join(p['url'] for p in thin_pages[:5])}

Broken pages: {', '.join(p['url'] for p in broken_pages[:5])}

Duplicate titles: {', '.join(duplicate_titles[:5])}"""

    return summary


async def generate_recommendations(job_id: str):
    """Generate AI recommendations from crawl data and store in Supabase."""
    sb = get_supabase()

    summary = build_summary(job_id)
    if not summary:
        logger.warning(f"No summary data available for job {job_id}")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — skipping recommendations")
        return

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": summary},
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        
        # Parse the JSON response
        parsed = json.loads(content)
        
        # Handle both {"recommendations": [...]} and direct array
        if isinstance(parsed, dict):
            recs = parsed.get("recommendations", parsed.get("items", []))
        elif isinstance(parsed, list):
            recs = parsed
        else:
            logger.error(f"Unexpected LLM response format: {type(parsed)}")
            return

        # Validate and insert
        valid_categories = {"SEO", "Content", "Accessibility", "Structure", "Performance", "Data Quality"}
        valid_priorities = {"low", "medium", "high"}

        rows = []
        for rec in recs:
            category = rec.get("category", "Content")
            if category not in valid_categories:
                category = "Content"
            
            priority = rec.get("priority", "medium")
            if priority not in valid_priorities:
                priority = "medium"

            rows.append({
                "job_id": job_id,
                "category": category,
                "title": str(rec.get("title", ""))[:200],
                "description": str(rec.get("description", ""))[:1000],
                "priority": priority,
            })

        if rows:
            sb.table("recommendations").insert(rows).execute()
            logger.info(f"Inserted {len(rows)} recommendations for job {job_id}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        logger.error(f"LLM recommendation failed: {e}", exc_info=True)
