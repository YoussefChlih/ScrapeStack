"""
Smart Data Extractor - Extracts specific data based on user selection.
"""

import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from urllib.parse import urljoin

logger = logging.getLogger("scrapestack.extractor")


def extract_table_data(soup: BeautifulSoup, selector: str) -> List[Dict[str, Any]]:
    """Extract data from a specific table."""
    if selector.startswith("table:nth-of-type"):
        # Extract nth-of-type number
        nth = int(selector.split("(")[1].split(")")[0])
        tables = soup.find_all("table")
        if nth <= len(tables):
            table = tables[nth - 1]
        else:
            return []
    else:
        table = soup.select_one(selector)
    
    if not table:
        return []
    
    # Extract headers
    headers = []
    header_row = table.find("thead")
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
    else:
        first_row = table.find("tr")
        if first_row:
            headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
    
    # Extract data rows
    rows_data = []
    data_rows = table.find_all("tr")
    
    # Skip header row if we used it
    start_idx = 1 if headers else 0
    
    for row in data_rows[start_idx:]:
        cells = row.find_all("td")
        if not cells:
            continue
        
        row_data = {}
        for idx, cell in enumerate(cells):
            header = headers[idx] if idx < len(headers) else f"column_{idx + 1}"
            row_data[header] = cell.get_text(strip=True)
        
        if row_data:
            rows_data.append(row_data)
    
    return rows_data


def extract_linkedin_profiles(soup: BeautifulSoup, page_url: str) -> List[Dict[str, Any]]:
    """Extract LinkedIn profile cards from search results."""
    profiles = []
    
    # Try different selectors for LinkedIn
    profile_cards = soup.find_all("li", class_=lambda x: x and "reusable-search__result-container" in x)
    if not profile_cards:
        profile_cards = soup.find_all("div", class_=lambda x: x and "entity-result" in x)
    
    for card in profile_cards:
        profile_data = {}
        
        # Extract name
        name_elem = card.find(["span", "div"], class_=lambda x: x and "entity-result__title" in x if x else False)
        if not name_elem:
            name_elem = card.find(["h3", "h4", "span"], class_=lambda x: x and "name" in x.lower() if x else False)
        
        profile_data["name"] = name_elem.get_text(strip=True) if name_elem else "N/A"
        
        # Extract title/headline
        title_elem = card.find(["div", "span"], class_=lambda x: x and "entity-result__primary-subtitle" in x if x else False)
        if not title_elem:
            title_elem = card.find(["div", "p"], class_=lambda x: x and "headline" in x.lower() if x else False)
        
        profile_data["title"] = title_elem.get_text(strip=True) if title_elem else "N/A"
        
        # Extract company
        company_elem = card.find(["div", "span"], class_=lambda x: x and "entity-result__secondary-subtitle" in x if x else False)
        profile_data["company"] = company_elem.get_text(strip=True) if company_elem else "N/A"
        
        # Extract location
        location_elem = card.find(["div", "span"], class_=lambda x: x and "entity-result__tertiary-subtitle" in x if x else False)
        if not location_elem:
            location_elem = card.find(text=lambda x: x and any(keyword in x.lower() for keyword in ["area", "location"]))
        
        profile_data["location"] = location_elem.get_text(strip=True) if location_elem else "N/A"
        
        # Extract profile URL
        link_elem = card.find("a", href=True)
        if link_elem:
            profile_data["profile_url"] = urljoin(page_url, link_elem["href"])
        else:
            profile_data["profile_url"] = "N/A"
        
        if profile_data["name"] != "N/A":
            profiles.append(profile_data)
    
    return profiles


def extract_wikipedia_article(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract Wikipedia article content."""
    article_data = {
        "title": "",
        "summary": "",
        "sections": [],
        "infobox": {},
    }
    
    # Get title
    title_elem = soup.find("h1", id="firstHeading")
    if title_elem:
        article_data["title"] = title_elem.get_text(strip=True)
    
    # Get main content
    content = soup.find("div", id="mw-content-text")
    if not content:
        return article_data
    
    # Get summary (first few paragraphs before first heading)
    paragraphs = []
    for elem in content.children:
        if elem.name == "p":
            text = elem.get_text(strip=True)
            if text and len(text) > 50:
                paragraphs.append(text)
        elif elem.name in ["h2", "h3"]:
            break
        
        if len(paragraphs) >= 3:
            break
    
    article_data["summary"] = " ".join(paragraphs)
    
    # Get sections
    sections = []
    current_section = None
    
    for elem in content.find_all(["h2", "h3", "p"]):
        if elem.name in ["h2", "h3"]:
            if current_section:
                sections.append(current_section)
            
            heading_text = elem.get_text(strip=True)
            # Remove edit links
            heading_text = heading_text.replace("[edit]", "").strip()
            
            current_section = {
                "heading": heading_text,
                "level": int(elem.name[1]),
                "content": [],
            }
        elif elem.name == "p" and current_section:
            text = elem.get_text(strip=True)
            if text and len(text) > 30:
                current_section["content"].append(text)
    
    if current_section:
        sections.append(current_section)
    
    article_data["sections"] = sections[:10]  # Limit to 10 sections
    
    # Extract infobox
    infobox = soup.find("table", class_="infobox")
    if infobox:
        infobox_data = {}
        rows = infobox.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    infobox_data[key] = value
        
        article_data["infobox"] = infobox_data
    
    return article_data


def extract_generic_cards(soup: BeautifulSoup, selector: str) -> List[Dict[str, Any]]:
    """Extract generic card/profile elements."""
    cards_data = []
    
    if selector == "auto-detected":
        elements = []
        for class_name in ["card", "profile", "member", "team-member", "person", "user", "item"]:
            found = soup.find_all(class_=lambda x: x and class_name in x.lower() if x else False)
            if len(found) >= 3:
                elements.extend(found)
                break
    else:
        elements = soup.select(selector)
    
    for elem in elements:
        card_data = {}
        
        heading = elem.find(["h1", "h2", "h3", "h4", "h5"])
        if heading:
            card_data["title"] = heading.get_text(strip=True)
        
        link = elem.find("a", href=True)
        if link:
            card_data["url"] = link["href"]
        
        card_data["content"] = elem.get_text(strip=True)[:500]
        
        if card_data.get("title") or card_data.get("content"):
            cards_data.append(card_data)
    
    return cards_data


def extract_portfolio_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract content from portfolio/personal websites."""
    portfolio_data = {
        "name": "",
        "title": "",
        "about": "",
        "skills": [],
        "projects": [],
        "experience": [],
        "education": [],
        "contact": {},
        "social_links": [],
    }
    
    # Try JSON-LD Person/Profile structured data first
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, dict):
                if data.get("@type") in ["Person", "Profile"]:
                    portfolio_data["name"] = data.get("name", "")
                    portfolio_data["title"] = data.get("jobTitle", "")
                    portfolio_data["about"] = data.get("description", "")
                    break
        except Exception:
            pass
    
    # Extract name from common selectors if not found in JSON-LD
    if not portfolio_data["name"]:
        name_selectors = ["h1", ".name", "#name", ".profile-name"]
        for selector in name_selectors:
            elem = soup.find(selector) if selector.startswith(".") or selector.startswith("#") else soup.find(selector)
            if elem:
                portfolio_data["name"] = elem.get_text(strip=True)
                break
    
    # Extract about section
    about_selectors = [".about", "#about", ".bio", "#bio", ".about-me"]
    for selector in about_selectors:
        elem = soup.find(class_=lambda x: x and selector[1:] in x.split()) if selector.startswith(".") else soup.find(id=selector[1:]) if selector.startswith("#") else None
        if elem:
            portfolio_data["about"] = elem.get_text(strip=True)[:1000]
            break
    
    # Extract skills
    skill_keywords = ["skill", "expertise", "technology", "tech stack", "tools"]
    for keyword in skill_keywords:
        skill_sections = soup.find_all(class_=lambda x: x and keyword in x.lower() if x else False)
        for section in skill_sections:
            items = section.find_all(["li", "span", "a", "div"])
            skills = [item.get_text(strip=True) for item in items if len(item.get_text(strip=True)) > 1 and len(item.get_text(strip=True)) < 50]
            if skills:
                portfolio_data["skills"].extend(skills[:20])
        if portfolio_data["skills"]:
            break
    
    # Extract projects
    project_keywords = ["project", "portfolio", "work", "case-study"]
    for keyword in project_keywords:
        project_sections = soup.find_all(class_=lambda x: x and keyword in x.lower() if x else False)
        for section in project_sections[:5]:
            title = section.find(["h2", "h3", "h4", ".title", ".name"])
            desc = section.find(["p", ".description", ".desc"])
            link = section.find("a", href=True)
            project = {}
            if title:
                project["title"] = title.get_text(strip=True)
            if desc:
                project["description"] = desc.get_text(strip=True)[:200]
            if link:
                project["url"] = link["href"]
            if project:
                portfolio_data["projects"].append(project)
        if portfolio_data["projects"]:
            break
    
    # Extract experience
    exp_keywords = ["experience", "employment", "work-history"]
    for keyword in exp_keywords:
        exp_sections = soup.find_all(class_=lambda x: x and keyword in x.lower() if x else False)
        for section in exp_sections[:5]:
            items = section.find_all(["li", ".item", ".job"])
            for item in items:
                text = item.get_text(strip=True)
                if text and len(text) > 10:
                    portfolio_data["experience"].append(text[:200])
        if portfolio_data["experience"]:
            break
    
    # Extract contact info
    contact_section = soup.find(class_=lambda x: x and "contact" in x.lower() if x else False)
    if contact_section:
        portfolio_data["contact"]["text"] = contact_section.get_text(strip=True)[:500]
    
    # Extract social links
    social_domains = ["github.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com"]
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        for domain in social_domains:
            if domain in href:
                portfolio_data["social_links"].append({
                    "platform": domain.split(".")[0],
                    "url": href,
                })
                break
    
    return portfolio_data


def extract_article_content(soup: BeautifulSoup, selector: str = None) -> Dict[str, Any]:
    """Extract article/main content."""
    if selector:
        article = soup.select_one(selector)
    else:
        article = soup.find("article") or soup.find("main")
    
    if not article:
        return {}
    
    article_data = {
        "title": "",
        "headings": [],
        "paragraphs": [],
        "content": "",
    }
    
    title_elem = article.find(["h1", "h2"])
    if title_elem:
        article_data["title"] = title_elem.get_text(strip=True)
    
    headings = article.find_all(["h1", "h2", "h3", "h4"])
    article_data["headings"] = [h.get_text(strip=True) for h in headings]
    
    paragraphs = article.find_all("p")
    article_data["paragraphs"] = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
    
    article_data["content"] = article.get_text(strip=True)
    
    return article_data


def extract_list_items(soup: BeautifulSoup, selector: str) -> List[str]:
    """Extract list items."""
    if selector.startswith(("ul", "ol")):
        # Handle nth-of-type selector
        if ":nth-of-type" in selector:
            tag = selector.split(":")[0]
            nth = int(selector.split("(")[1].split(")")[0])
            lists = soup.find_all(tag)
            if nth <= len(lists):
                list_elem = lists[nth - 1]
            else:
                return []
        else:
            list_elem = soup.find(selector.split(":")[0])
    else:
        list_elem = soup.select_one(selector)
    
    if not list_elem:
        return []
    
    items = list_elem.find_all("li", recursive=False)
    return [item.get_text(strip=True) for item in items]


def extract_selected_data(html: str, page_url: str, selected_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract data based on user's selection from preview.
    
    Args:
        html: Page HTML
        page_url: Current page URL
        selected_data: List of data items user selected (from preview)
    
    Returns:
        Extracted data organized by type
    """
    soup = BeautifulSoup(html, "lxml")
    
    extracted = {
        "url": page_url,
        "data": {},
    }
    
    for item in selected_data:
        data_type = item.get("type")
        data_id = item.get("id")
        selector = item.get("selector", "")
        
        try:
            if data_type == "table":
                extracted["data"][data_id] = extract_table_data(soup, selector)
            
            elif data_type == "profiles" and data_id == "linkedin_profiles":
                extracted["data"][data_id] = extract_linkedin_profiles(soup, page_url)
            
            elif data_type == "article" and data_id == "wikipedia_article":
                extracted["data"][data_id] = extract_wikipedia_article(soup)
            
            elif data_type == "infobox" and data_id == "wikipedia_infobox":
                result = extract_wikipedia_article(soup)
                extracted["data"][data_id] = result.get("infobox", {})
            
            elif data_type == "cards":
                extracted["data"][data_id] = extract_generic_cards(soup, selector)
            
            elif data_type == "article":
                extracted["data"][data_id] = extract_article_content(soup, selector)
            
            elif data_type == "list":
                extracted["data"][data_id] = extract_list_items(soup, selector)
            
            elif data_type == "portfolio":
                extracted["data"][data_id] = extract_portfolio_content(soup)
            
            else:
                logger.warning(f"Unknown data type: {data_type}")
        
        except Exception as e:
            logger.error(f"Error extracting {data_type} ({data_id}): {e}")
            extracted["data"][data_id] = {"error": str(e)}
    
    return extracted
