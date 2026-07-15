"""
Smart Data Detector - Analyzes a webpage and detects extractable data structures.
"""

import logging
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Any

logger = logging.getLogger("scrapestack.detector")


def detect_site_type(url: str, soup: BeautifulSoup) -> str:
    """Detect the type of website for specialized extraction."""
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower()
    
    if "linkedin.com" in hostname:
        return "linkedin"
    elif "wikipedia.org" in hostname:
        return "wikipedia"
    elif any(keyword in hostname for keyword in ["github.com", "gitlab.com"]):
        return "code_repository"
    elif any(keyword in soup.get_text().lower()[:500] for keyword in ["portfolio", "projects", "about me"]):
        return "portfolio"
    else:
        return "generic"


def detect_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Detect and preview HTML tables."""
    tables_data = []
    
    for idx, table in enumerate(soup.find_all("table"), 1):
        # Extract headers
        headers = []
        header_row = table.find("thead")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        else:
            # Try first row as headers
            first_row = table.find("tr")
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
        
        # Count rows
        rows = table.find_all("tr")
        row_count = len(rows)
        
        # Get first 3 data rows as preview
        preview_rows = []
        data_rows = [r for r in rows[1:] if r.find_all("td")][:3]
        for row in data_rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if cells:
                preview_rows.append(cells)
        
        # Skip tiny tables
        if row_count < 2 or len(headers) < 2:
            continue
            
        tables_data.append({
            "id": f"table_{idx}",
            "type": "table",
            "name": f"Table {idx}",
            "headers": headers[:10],  # Limit to 10 columns for preview
            "row_count": row_count,
            "column_count": len(headers),
            "preview": preview_rows,
            "selector": f"table:nth-of-type({idx})",
        })
    
    return tables_data


def detect_profile_cards(soup: BeautifulSoup, site_type: str) -> List[Dict[str, Any]]:
    """Detect profile/people cards (LinkedIn, team pages, etc.)."""
    cards = []
    
    if site_type == "linkedin":
        # LinkedIn search results
        profile_cards = soup.find_all("li", class_=lambda x: x and "reusable-search__result-container" in x)
        if not profile_cards:
            profile_cards = soup.find_all("div", class_=lambda x: x and "entity-result" in x)
        
        if profile_cards:
            previews = []
            for card in profile_cards[:3]:
                name_elem = card.find(["span", "div"], class_=lambda x: x and "entity-result__title" in x if x else False)
                title_elem = card.find(["div", "span"], class_=lambda x: x and "entity-result__primary-subtitle" in x if x else False)
                
                name = name_elem.get_text(strip=True) if name_elem else "N/A"
                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                
                previews.append({
                    "name": name,
                    "title": title,
                })
            
            cards.append({
                "id": "linkedin_profiles",
                "type": "profiles",
                "name": "LinkedIn Profile Cards",
                "count": len(profile_cards),
                "preview": previews,
                "fields": ["name", "title", "company", "location"],
                "selector": "li.reusable-search__result-container, div.entity-result",
            })
    else:
        # Generic profile/card detection
        potential_cards = []
        
        # Look for repeating card-like structures
        for class_name in ["card", "profile", "member", "team-member", "person", "user"]:
            elements = soup.find_all(class_=lambda x: x and class_name in x.lower() if x else False)
            if len(elements) >= 3:  # At least 3 similar elements
                potential_cards.extend(elements)
        
        if potential_cards:
            previews = []
            for card in potential_cards[:3]:
                # Try to find name/title
                heading = card.find(["h1", "h2", "h3", "h4"])
                text = heading.get_text(strip=True) if heading else card.get_text(strip=True)[:100]
                previews.append({"text": text})
            
            cards.append({
                "id": "generic_cards",
                "type": "cards",
                "name": f"Card Elements ({len(potential_cards)} found)",
                "count": len(potential_cards),
                "preview": previews,
                "selector": "auto-detected",
            })
    
    return cards


def detect_articles(soup: BeautifulSoup, site_type: str) -> List[Dict[str, Any]]:
    """Detect article/content areas."""
    articles = []
    
    if site_type == "wikipedia":
        # Wikipedia article content
        content = soup.find("div", id="mw-content-text")
        if content:
            headings = content.find_all(["h2", "h3"])
            paragraphs = content.find_all("p", recursive=False)
            
            articles.append({
                "id": "wikipedia_article",
                "type": "article",
                "name": "Wikipedia Article Content",
                "sections": len(headings),
                "paragraphs": len(paragraphs),
                "preview": paragraphs[0].get_text(strip=True)[:200] if paragraphs else "",
                "selector": "#mw-content-text",
            })
        
        # Wikipedia infobox
        infobox = soup.find("table", class_="infobox")
        if infobox:
            rows = infobox.find_all("tr")
            preview_data = []
            for row in rows[:5]:
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    preview_data.append({key: value})
            
            articles.append({
                "id": "wikipedia_infobox",
                "type": "infobox",
                "name": "Wikipedia Infobox",
                "fields": len(rows),
                "preview": preview_data,
                "selector": "table.infobox",
            })
    else:
        # Generic article detection
        article_elem = soup.find("article") or soup.find("main") or soup.find("div", class_=lambda x: x and "content" in x.lower() if x else False)
        
        if article_elem:
            headings = article_elem.find_all(["h1", "h2", "h3"])
            paragraphs = article_elem.find_all("p")
            
            preview_text = ""
            if paragraphs:
                preview_text = paragraphs[0].get_text(strip=True)[:200]
            
            articles.append({
                "id": "main_content",
                "type": "article",
                "name": "Main Content Area",
                "headings": len(headings),
                "paragraphs": len(paragraphs),
                "preview": preview_text,
                "selector": "article, main",
            })
    
    return articles


def detect_lists(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Detect structured lists (products, items, posts, etc.)."""
    lists_data = []
    
    # Look for <ul> or <ol> with multiple items
    for idx, list_elem in enumerate(soup.find_all(["ul", "ol"]), 1):
        items = list_elem.find_all("li", recursive=False)
        
        # Skip navigation menus (short items)
        if len(items) < 3:
            continue
        
        # Check if items have substantial content
        avg_length = sum(len(item.get_text(strip=True)) for item in items) / len(items)
        if avg_length < 20:  # Skip menus
            continue
        
        preview_items = []
        for item in items[:3]:
            text = item.get_text(strip=True)[:100]
            if text:
                preview_items.append(text)
        
        lists_data.append({
            "id": f"list_{idx}",
            "type": "list",
            "name": f"List {idx} ({list_elem.name.upper()})",
            "item_count": len(items),
            "preview": preview_items,
            "selector": f"{list_elem.name}:nth-of-type({idx})",
        })
    
    return lists_data


def detect_pagination(soup: BeautifulSoup) -> Dict[str, Any]:
    """Detect pagination links."""
    pagination_data = {
        "has_pagination": False,
        "pages_found": 0,
        "next_page": None,
        "pattern": None,
    }
    
    # Look for pagination elements
    pagination = soup.find(["nav", "div"], class_=lambda x: x and any(p in x.lower() for p in ["pagination", "pager", "page-nav"]) if x else False)
    
    if pagination:
        links = pagination.find_all("a", href=True)
        pagination_data["has_pagination"] = True
        pagination_data["pages_found"] = len(links)
        
        # Find "next" link
        for link in links:
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in ["next", "→", "›", "»"]):
                pagination_data["next_page"] = link["href"]
                break
    
    return pagination_data


def detect_page_data(html: str, url: str) -> Dict[str, Any]:
    """
    Main function: Detect all extractable data structures on a page.
    
    Returns a preview of what can be scraped.
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Detect site type
    site_type = detect_site_type(url, soup)
    
    # Get page title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    
    # Detect all data structures
    detected_data = {
        "url": url,
        "site_type": site_type,
        "page_title": page_title,
        "available_data": [],
    }
    
    # Detect tables
    tables = detect_tables(soup)
    detected_data["available_data"].extend(tables)
    
    # Detect profile cards
    profiles = detect_profile_cards(soup, site_type)
    detected_data["available_data"].extend(profiles)
    
    # Detect articles/content
    articles = detect_articles(soup, site_type)
    detected_data["available_data"].extend(articles)
    
    # Detect lists
    lists = detect_lists(soup)
    detected_data["available_data"].extend(lists)
    
    # Detect pagination
    pagination = detect_pagination(soup)
    detected_data["pagination"] = pagination
    
    return detected_data
