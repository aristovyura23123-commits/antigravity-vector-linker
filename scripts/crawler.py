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

        # Detect article or category content container
        content_container = None
        if is_article:
            content_container = (
                soup.find('div', class_=re.compile(r'news-content|article|content-body|detail-text|post-content', re.I))
                or soup.find('article')
                or soup.find('main')
                or soup.body
            )
        else:
            # Catalog page: isolate category description and SEO text
            # Decompose product cards, item lists, modals, breadcrumbs, filters, and pagination
            for tag in soup.find_all(class_=re.compile(r'breadcrumb|nav-chain|breadcrumbs|chain|filter|sorting|catalog-sort|product-card|catalog-grid|catalog-items|products-list|product-item|cookie|policy|popup|notification|cart-modal|basket|pagin', re.I)):
                tag.decompose()
            for tag in soup(['ol', 'ul']):
                if any('breadcrumb' in str(c).lower() for c in tag.get('class', [])):
                    tag.decompose()
                
            # Prefer explicit description containers if available, otherwise use cleaned body
            content_container = (
                soup.find('div', class_=re.compile(r'category-description|catalog-desc|seo-text|catalog-section-desc|section-description|category-text|catalog-bottom-text|cat-desc|desc', re.I))
                or soup.find('main')
                or soup.body
            )

        in_body_links = []
        if content_container:
            for a in content_container.find_all('a', href=True):
                href = a['href'].split('#')[0].rstrip('/')
                if href and not href.startswith(('javascript:', 'tel:', 'mailto:')):
                    in_body_links.append(urljoin(url, href).rstrip('/'))

            # Extract clean meaningful text
            raw_text = content_container.get_text(separator=' ', strip=True)
            # Remove repeated shopping button noises
            cleaned_text = re.sub(r'\b(\d+\s*руб(\.|лей)?|купить в 1 клик|в корзину|быстрый просмотр|артикул:?\s*\w+)\b', ' ', raw_text, flags=re.I)
            text = ' '.join(cleaned_text.split())
        else:
            text = ' '.join(soup.get_text(separator=' ', strip=True).split())

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

def load_screaming_frog_data(internal_all_path, inlinks_path=None, target_pages_path=None):
    """
    Imports crawl and linking data from Screaming Frog / Sitebulb CSV exports (ILIS v2.0 Section 4).
    Supports internal_all.csv, inlinks.csv, and target_pages.csv.
    """
    import csv

    def read_csv_safe(path):
        for enc in ['utf-8-sig', 'utf-8', 'cp1251', 'latin1']:
            try:
                with open(path, 'r', encoding=enc) as f:
                    sample = f.read(2048)
                    delimiter = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=delimiter)
                    return list(reader)
            except UnicodeDecodeError:
                continue
        return []

    # 1. Target pages
    target_urls = set()
    target_meta = {}
    if target_pages_path:
        rows = read_csv_safe(target_pages_path)
        for r in rows:
            u = (r.get('Address') or r.get('URL') or r.get('url') or '').strip().rstrip('/')
            if u:
                target_urls.add(u)
                target_meta[u] = {
                    'priority': r.get('Приоритет') or r.get('Priority') or 'High',
                    'keyword': r.get('Основной запрос') or r.get('Target Keyword') or '',
                    'page_type': r.get('Тип страницы') or r.get('Type') or ''
                }

    # 2. Internal all pages
    pages = []
    if internal_all_path:
        rows = read_csv_safe(internal_all_path)
        for r in rows:
            u = (r.get('Address') or r.get('URL') or r.get('url') or '').strip().rstrip('/')
            if not u:
                continue

            status_code = int(r.get('Status Code', 200)) if str(r.get('Status Code', '')).isdigit() else 200
            indexability = r.get('Indexability', 'Indexable')
            is_indexable = 'non' not in indexability.lower() and status_code == 200

            title = r.get('Title 1') or r.get('Title') or r.get('title') or u
            h1 = r.get('H1-1') or r.get('H1') or r.get('h1') or title
            ls = float(r.get('Link Score', 0.0)) if r.get('Link Score') else 10.0
            u_in = int(r.get('Unique Inlinks', 0)) if str(r.get('Unique Inlinks', '')).isdigit() else 0
            u_out = int(r.get('Unique Outlinks', 0)) if str(r.get('Unique Outlinks', '')).isdigit() else 0
            depth = int(r.get('Crawl Depth', 1)) if str(r.get('Crawl Depth', '')).isdigit() else 1

            is_art = bool(re.search(r'/articles/|/blog/|/news/|/post/', u, re.I))

            pages.append({
                'url': u,
                'title': title,
                'h1': h1,
                'text': title + ' ' + h1,
                'links': [],
                'link_score': ls,
                'unique_inlinks': u_in,
                'unique_outlinks': u_out,
                'crawl_depth': depth,
                'indexable': is_indexable,
                'status_code': status_code,
                'is_article': is_art,
                'is_target': u in target_urls,
                'target_meta': target_meta.get(u, {})
            })

    # 3. Inlinks
    inlinks = []
    if inlinks_path:
        rows = read_csv_safe(inlinks_path)
        for r in rows:
            src = (r.get('From') or r.get('Source') or '').strip().rstrip('/')
            tgt = (r.get('To') or r.get('Destination') or '').strip().rstrip('/')
            anc = (r.get('Anchor Text') or r.get('Anchor') or r.get('Alt Text') or '').strip()
            follow = (r.get('Follow') or 'true').lower() in ['true', 'follow']
            pos = r.get('Link Position') or r.get('Position') or 'контекст'
            if src and tgt:
                inlinks.append({
                    'from': src,
                    'to': tgt,
                    'anchor': anc,
                    'follow': follow,
                    'position': pos
                })

    return pages, inlinks, target_urls
