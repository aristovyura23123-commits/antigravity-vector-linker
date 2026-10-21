"""
High-performance crawler and main-content extractor for sitemaps and web pages.
"""

import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import re

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AntigravityVectorLinker/1.0'
}

def parse_sitemap(sitemap_url, max_urls=500):
    """
    Parses a sitemap URL or sitemap index recursively and extracts page URLs.
    """
    discovered_urls = []
    visited_sitemaps = set()
    sitemaps_to_crawl = [sitemap_url]

    while sitemaps_to_crawl and len(discovered_urls) < max_urls:
        current_sm = sitemaps_to_crawl.pop(0)
        if current_sm in visited_sitemaps:
            continue
        visited_sitemaps.add(current_sm)

        try:
            req = urllib.request.Request(current_sm, headers=HEADERS)
            with OPENER.open(req, timeout=12) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            
            # Check if it's a sitemapindex
            sub_sitemaps = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if sub_sitemaps:
                for sm in sub_sitemaps:
                    if sm.text and sm.text.strip() not in visited_sitemaps:
                        sitemaps_to_crawl.append(sm.text.strip())
            else:
                # urlset
                urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                for u in urls:
                    if u.text:
                        discovered_urls.append(u.text.strip())
                        if len(discovered_urls) >= max_urls:
                            break
        except Exception as e:
            print(f"Warning: could not parse sitemap {current_sm}: {e}")

    return discovered_urls

def extract_page_data(url, is_article=True):
    """
    Fetches a single page and extracts its title, clean body content, and in-body internal links.
    """
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with OPENER.open(req, timeout=12) as resp:
            raw = resp.read()
            html = raw.decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')

        # Remove noise elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'noscript', 'iframe']):
            tag.decompose()

        h1 = soup.find('h1')
        title = h1.get_text().strip() if h1 else (soup.title.string.strip() if soup.title else url)

        # Detect article body container
        content_container = (
            soup.find('div', class_=re.compile(r'news-content|article|content-body|detail-text|post-content', re.I))
            or soup.find('article')
            or soup.find('main')
            or soup.body
        )

        in_body_links = []
        if content_container:
            for a in content_container.find_all('a', href=True):
                href = a['href'].split('#')[0].rstrip('/')
                if href and not href.startswith(('javascript:', 'tel:', 'mailto:')):
                    in_body_links.append(urljoin(url, href).rstrip('/'))

            text = content_container.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

        return {
            'url': url.rstrip('/'),
            'title': title,
            'text': text,
            'links': in_body_links,
            'is_article': is_article
        }
    except Exception as e:
        return None

def crawl_site_pages(article_urls, category_urls, max_workers=10):
    """
    Fetches articles and categories in parallel using ThreadPoolExecutor.
    """
    tasks = [(u, True) for u in article_urls] + [(u, False) for u in category_urls]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda item: extract_page_data(item[0], item[1]), tasks))
    
    clean_pages = [p for p in results if p is not None and len(p['text']) > 15]
    return clean_pages
