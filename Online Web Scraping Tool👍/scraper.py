"""
Scraper logic: check robots.txt and extract content using requests + BeautifulSoup.

Public functions:
- allowed_to_scrape(url) -> bool
- scrape_url(url, timeout=10) -> dict (structured data)
"""
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Any, List
import time

USER_AGENT = 'FlaskScraperBot/1.0 (+https://example.com/contact)'

def allowed_to_scrape(url: str, timeout: int = 5) -> bool:
    """
    Check robots.txt for the domain to see if scraping is allowed.
    Returns True if allowed or robots.txt not found; False if disallowed.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme or 'http'
    netloc = parsed.netloc
    robots_url = f"{scheme}://{netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        # RobotFileParser.set_url + read fetches robots.txt
        rp.set_url(robots_url)
        rp.read()
        can = rp.can_fetch(USER_AGENT, url)
        return can
    except Exception:
        # If robots.txt is unreachable, be conservative and allow (common practice),
        # but a stricter implementation could deny by default.
        return True

def _parse_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    tables_out = []
    for table in soup.find_all('table'):
        headers = []
        # try header row
        thead = table.find('thead')
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all('th')]
        else:
            # look in first row for th or td
            first_row = table.find('tr')
            if first_row:
                headers = [cell.get_text(strip=True) for cell in first_row.find_all(['th', 'td'])]
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(cells)
        tables_out.append({'headers': headers, 'rows': rows})
    return tables_out

def scrape_url(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Scrape the given URL and return structured data. Raises exceptions on errors.
    """
    if not allowed_to_scrape(url):
        raise Exception('Scraping disallowed by robots.txt for this URL.')

    headers = {'User-Agent': USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise Exception(f'Network error: {str(e)}')

    if resp.status_code == 429:
        raise Exception('Remote server rate-limited us (HTTP 429). Try later or lower request frequency.')
    if resp.status_code >= 400:
        raise Exception(f'HTTP error: {resp.status_code}')

    content = resp.text
    soup = BeautifulSoup(content, 'html.parser')

    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else ''

    meta_desc = ''
    desc = soup.find('meta', attrs={'name':'description'})
    if desc and desc.get('content'):
        meta_desc = desc.get('content').strip()
    else:
        # sometimes meta name is 'og:description'
        og = soup.find('meta', attrs={'property':'og:description'})
        if og and og.get('content'):
            meta_desc = og.get('content').strip()

    headings = []
    for level in range(1,7):
        tag = f'h{level}'
        for h in soup.find_all(tag):
            headings.append({'tag': tag, 'text': h.get_text(strip=True)})

    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

    links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href').strip()
        # resolve relative URLs
        href = urljoin(resp.url, href)
        text = a.get_text(strip=True)
        links.append({'href': href, 'text': text})

    tables = _parse_tables(soup)

    summary = {
        'num_links': len(links),
        'num_paragraphs': len(paragraphs),
        'num_headings': len(headings),
        'num_tables': len(tables)
    }

    result = {
        'url': resp.url,
        'title': title,
        'meta_description': meta_desc,
        'headings': headings,
        'paragraphs': paragraphs,
        'links': links,
        'tables': tables,
        'summary': summary,
        'fetched_at': datetime.utcnow().isoformat()
    }
    # polite short delay — minimal (only when used in loops); here we do not block but note best practice
    time.sleep(0.1)
    return result
