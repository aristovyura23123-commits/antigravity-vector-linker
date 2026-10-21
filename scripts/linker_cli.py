#!/usr/bin/env python3
"""
CLI entrypoint for Antigravity Vector Semantic Linker v2.5 / v3.0.
Features:
- Strict Sentence Deduplication: 1 sentence = at most 1 link
- In-Text Contextual Links (Article -> Catalog, Catalog -> Catalog, Catalog -> Article)
- Topic Clusters (Article -> Article)
- Dedicated Link Blocks / HTML Widgets for CMS
- Internal PageRank Graph Simulation
"""

import argparse
import sys
import os
import re
from urllib.parse import urlparse
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from crawler import parse_sitemap, crawl_site_pages
from engine import (
    VectorSemanticEngine,
    parse_category_components,
    generate_html_link_block,
    compute_internal_pagerank
)
from reporter import generate_html_report, export_csv_report, export_json_graph

def main():
    parser = argparse.ArgumentParser(description="Vector Semantic Linker v2.5 for Antigravity CLI")
    parser.add_argument("--sitemap", type=str, help="URL of sitemap.xml or sitemap index")
    parser.add_argument("--articles-urls", type=str, help="Comma-separated article URLs or path to file")
    parser.add_argument("--categories-urls", type=str, help="Comma-separated category URLs or path to file")
    parser.add_argument("--articles-pattern", type=str, default=r"/articles/|/blog/|/news/|/post/", help="Regex pattern to filter article URLs from sitemap")
    parser.add_argument("--catalog-pattern", type=str, default=r"/catalog/|/category/|/services/|/uslugi/", help="Regex pattern to filter money/catalog URLs from sitemap")
    parser.add_argument("--max-articles", type=int, default=30, help="Maximum number of articles to analyze")
    parser.add_argument("--max-categories", type=int, default=30, help="Maximum number of categories to analyze")
    parser.add_argument("--max-links-per-page", type=int, default=2, help="Maximum contextual in-text links per page")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent crawler workers")
    parser.add_argument("--output-html", type=str, default="vector_linker_report.html", help="Path to output HTML report")
    parser.add_argument("--output-csv", type=str, default="vector_linker_report.csv", help="Path to output CSV report")
    parser.add_argument("--output-json", type=str, default="vector_linker_graph.json", help="Path to output JSON graph")

    args = parser.parse_args()

    article_urls = []
    category_urls = []

    if args.sitemap:
        print(f"🔍 Парсинг sitemap: {args.sitemap}...")
        all_urls = parse_sitemap(args.sitemap)
        print(f"Найдено URL в карте сайта: {len(all_urls)}")
        
        art_re = re.compile(args.articles_pattern, re.I)
        cat_re = re.compile(args.catalog_pattern, re.I)

        for u in all_urls:
            if art_re.search(u) and len(article_urls) < args.max_articles:
                article_urls.append(u)
            elif cat_re.search(u) and len(category_urls) < args.max_categories:
                category_urls.append(u)

    if args.articles_urls:
        if os.path.exists(args.articles_urls):
            with open(args.articles_urls, 'r', encoding='utf-8') as f:
                article_urls.extend([line.strip() for line in f if line.strip()])
        else:
            article_urls.extend([u.strip() for u in args.articles_urls.split(',') if u.strip()])

    if args.categories_urls:
        if os.path.exists(args.categories_urls):
            with open(args.categories_urls, 'r', encoding='utf-8') as f:
                category_urls.extend([line.strip() for line in f if line.strip()])
        else:
            category_urls.extend([u.strip() for u in args.categories_urls.split(',') if u.strip()])

    article_urls = list(dict.fromkeys(article_urls))[:args.max_articles]
    category_urls = list(dict.fromkeys(category_urls))[:args.max_categories]

    if not article_urls and not category_urls:
        print("Ошибка: не указаны URL для анализа. Укажите --sitemap или --articles-urls / --categories-urls.")
        sys.exit(1)

    print(f"📥 Сканирование: {len(article_urls)} статей и {len(category_urls)} категорий (потоков: {args.workers})...")
    pages = crawl_site_pages(article_urls, category_urls, max_workers=args.workers)

    articles = [p for p in pages if p['is_article']]
    categories = [p for p in pages if not p['is_article']]

    print(f"🧠 Семантическая векторизация {len(pages)} страниц...")
    engine = VectorSemanticEngine()
    engine.fit_transform(pages)

    art_count = len(articles)
    cat_count = len(categories)

    # Matrix slice for articles and categories
    art_matrix = engine.tfidf_matrix[:art_count] if art_count > 0 else None
    sim_art_art = cosine_similarity(art_matrix, art_matrix) if art_matrix is not None and art_count > 1 else np.zeros((art_count, art_count))

    # Parse Category Components (Head Entity vs Modifiers)
    cat_components = []
    for c in categories:
        h, m = parse_category_components(c['title'])
        cat_components.append({
            'url': c['url'],
            'title': c['title'],
            'head_stems': h,
            'mod_stems': m
        })

    # =========================================================================
    # PHASE 1: Article -> Catalog In-Text Links (Strict Sentence Deduplication)
    # =========================================================================
    print("🛡 Фаза 1: Контекстная перелинковка Статья ➔ Каталог (1 предложение = 1 ссылка)...")
    art_to_cat_recs = []

    for i, art in enumerate(articles):
        existing_links = set(art.get('links', []))
        candidate_targets = []

        for cat in cat_components:
            clean_cat_url = cat['url'].rstrip('/')
            if any(clean_cat_url in l for l in existing_links):
                continue
                
            # Quick score estimation
            matches = engine.find_all_sentence_matches(
                art['text'], cat['head_stems'], cat['mod_stems'], cat['url']
            )
            if matches:
                top_match_score = matches[0][0]
                candidate_targets.append({
                    'url': cat['url'],
                    'title': cat['title'],
                    'head_stems': cat['head_stems'],
                    'mod_stems': cat['mod_stems'],
                    'score': top_match_score
                })

        # Allocate links with strict sentence deduplication
        allocated = engine.allocate_page_in_text_links(
            art['url'], art['title'], art['text'], candidate_targets, max_links=args.max_links_per_page
        )
        for al in allocated:
            al['link_type'] = 'Статья -> Каталог [текст]'
            art_to_cat_recs.append(al)

    # =========================================================================
    # PHASE 2: Catalog -> Catalog In-Text Links (Category Cross-Linking)
    # =========================================================================
    print("🛒 Фаза 2: Контекстная перелинковка Каталог ➔ Каталог (Кросс-линкинг описаний)...")
    cat_to_cat_recs = []

    for i, cat_src in enumerate(categories):
        existing_links = set(cat_src.get('links', []))
        candidate_targets = []

        for cat_tgt in cat_components:
            if cat_tgt['url'] == cat_src['url']:
                continue
            clean_tgt_url = cat_tgt['url'].rstrip('/')
            if any(clean_tgt_url in l for l in existing_links):
                continue

            matches = engine.find_all_sentence_matches(
                cat_src['text'], cat_tgt['head_stems'], cat_tgt['mod_stems'], cat_tgt['url']
            )
            if matches:
                top_match_score = matches[0][0]
                candidate_targets.append({
                    'url': cat_tgt['url'],
                    'title': cat_tgt['title'],
                    'head_stems': cat_tgt['head_stems'],
                    'mod_stems': cat_tgt['mod_stems'],
                    'score': top_match_score
                })

        allocated = engine.allocate_page_in_text_links(
            cat_src['url'], cat_src['title'], cat_src['text'], candidate_targets, max_links=args.max_links_per_page
        )
        for al in allocated:
            al['link_type'] = 'Каталог -> Каталог [текст]'
            cat_to_cat_recs.append(al)

    # =========================================================================
    # PHASE 3: Catalog -> Article (Buying Guides / E-E-A-T Links)
    # =========================================================================
    print("📚 Фаза 3: Экспертные гиды Каталог ➔ Статья (E-E-A-T)...")
    cat_to_art_recs = []

    for cat in categories:
        cat_h, cat_m = parse_category_components(cat['title'])
        for art in articles:
            art_h, art_m = parse_category_components(art['title'])
            # Check overlap between category head entities and article title
            overlap = cat_h.intersection(art_h)
            if overlap:
                cat_to_art_recs.append({
                    'link_type': 'Каталог -> Статья [гид]',
                    'source_url': cat['url'],
                    'source_title': cat['title'],
                    'target_url': art['url'],
                    'target_title': art['title'],
                    'similarity': 95.0,
                    'suggested_anchor': art['title']
                })
                break

    # =========================================================================
    # PHASE 4: Article -> Article (Topic Clusters)
    # =========================================================================
    print("🕸 Фаза 4: Тематические кластеры Статья ➔ Статья...")
    cluster_recs = []
    if art_count > 1:
        for i, art in enumerate(articles):
            top_arts = np.argsort(sim_art_art[i])[::-1]
            for peer_idx in top_arts:
                if peer_idx == i:
                    continue
                peer_score = sim_art_art[i][peer_idx]
                peer_art = articles[peer_idx]

                if peer_score > 0.02:
                    sim_pct = min(98.0, round(float(peer_score) * 250, 1))
                    cluster_recs.append({
                        'link_type': 'Статья -> Статья [кластер]',
                        'source_title': art['title'],
                        'source_url': art['url'],
                        'target_title': peer_art['title'],
                        'target_url': peer_art['url'],
                        'similarity': sim_pct,
                        'suggested_anchor': peer_art['title']
                    })
                    break

    # =========================================================================
    # PHASE 5: Dedicated Link Blocks for CMS (HTML Widgets)
    # =========================================================================
    print("📦 Фаза 5: Генерация готовых блоков перелинковки для CMS...")
    link_blocks = []

    # 1. Blocks for articles (Related categories & Related articles)
    for art in articles:
        # Match top 2-3 categories based on title/text similarity
        matched_cats = [r for r in art_to_cat_recs if r['source_url'] == art['url']]
        if not matched_cats:
            # Fallback to general category matching
            for cat in cat_components:
                h, m = cat['head_stems'], cat['mod_stems']
                if any(w in art['text'].lower() for w in h):
                    matched_cats.append({'target_url': cat['url'], 'target_title': cat['title']})
                    if len(matched_cats) >= 3:
                        break

        if matched_cats:
            cat_links = [{'url': m['target_url'], 'title': m['target_title']} for m in matched_cats[:3]]
            html_block = generate_html_link_block(
                'catalog_for_article',
                'Рекомендуемые разделы каталога по теме',
                cat_links
            )
            link_blocks.append({
                'page_url': art['url'],
                'page_title': art['title'],
                'type_label': 'Статья: Блок каталога',
                'html': html_block
            })

        # Match peer articles in cluster
        matched_peers = [c for c in cluster_recs if c['source_url'] == art['url']]
        if matched_peers:
            peer_links = [{'url': p['target_url'], 'title': p['target_title']} for p in matched_peers[:3]]
            cluster_html = generate_html_link_block(
                'cluster_for_article',
                'Похожие статьи и публикации',
                peer_links
            )
            link_blocks.append({
                'page_url': art['url'],
                'page_title': art['title'],
                'type_label': 'Статья: Блок кластера',
                'html': cluster_html
            })

    # 2. Blocks for catalog categories (Related categories & Buying guides)
    for cat in categories:
        matched_cross = [r for r in cat_to_cat_recs if r['source_url'] == cat['url']]
        if matched_cross:
            cross_links = [{'url': m['target_url'], 'title': m['target_title']} for m in matched_cross[:3]]
            cross_html = generate_html_link_block(
                'cross_catalog',
                'Сопутствующие категории товаров',
                cross_links
            )
            link_blocks.append({
                'page_url': cat['url'],
                'page_title': cat['title'],
                'type_label': 'Каталог: Блок сопутствующих категорий',
                'html': cross_html
            })

        matched_guides = [g for g in cat_to_art_recs if g['source_url'] == cat['url']]
        if matched_guides:
            guide_links = [{'url': g['target_url'], 'title': g['target_title']} for g in matched_guides[:2]]
            guide_html = generate_html_link_block(
                'guides_for_catalog',
                'Полезные гиды и советы экспертов',
                guide_links
            )
            link_blocks.append({
                'page_url': cat['url'],
                'page_title': cat['title'],
                'type_label': 'Каталог: Блок гидов покупателя',
                'html': guide_html
            })

    # =========================================================================
    # PageRank Simulation Across Entire Graph
    # =========================================================================
    total_nodes = art_count + cat_count
    adj_current = np.zeros((total_nodes, total_nodes))
    pr_before = compute_internal_pagerank(adj_current)

    adj_after = np.copy(adj_current)
    # Add Article -> Catalog
    for rec in art_to_cat_recs:
        try:
            art_idx = [a['url'] for a in articles].index(rec['source_url'])
            cat_idx = [c['url'] for c in categories].index(rec['target_url']) + art_count
            adj_after[art_idx, cat_idx] = 1.0
        except ValueError:
            pass

    # Add Catalog -> Catalog
    for rec in cat_to_cat_recs:
        try:
            src_idx = [c['url'] for c in categories].index(rec['source_url']) + art_count
            tgt_idx = [c['url'] for c in categories].index(rec['target_url']) + art_count
            adj_after[src_idx, tgt_idx] = 1.0
        except ValueError:
            pass

    # Add Catalog -> Article
    for rec in cat_to_art_recs:
        try:
            cat_idx = [c['url'] for c in categories].index(rec['source_url']) + art_count
            art_idx = [a['url'] for a in articles].index(rec['target_url'])
            adj_after[cat_idx, art_idx] = 1.0
        except ValueError:
            pass

    pr_after = compute_internal_pagerank(adj_after)
    cat_pr_before = np.mean(pr_before[art_count:]) if cat_count > 0 else 0
    cat_pr_after = np.mean(pr_after[art_count:]) if cat_count > 0 else 0
    pr_lift = ((cat_pr_after - cat_pr_before) / cat_pr_before) * 100 if cat_pr_before > 0 else 0

    domain = urlparse(pages[0]['url']).netloc if pages else "website"

    print("📊 Сохранение отчётов...")
    if args.output_html:
        generate_html_report(
            domain,
            articles,
            categories,
            art_to_cat_recs,
            cat_to_cat_recs,
            cat_to_art_recs,
            cluster_recs,
            link_blocks,
            pr_lift,
            args.output_html
        )
        print(f"  ➜ HTML дашборд: {args.output_html}")

    all_csv_records = art_to_cat_recs + cat_to_cat_recs + cat_to_art_recs + cluster_recs
    if args.output_csv:
        export_csv_report(all_csv_records, args.output_csv)
        print(f"  ➜ CSV выгрузка: {args.output_csv}")

    if args.output_json:
        nodes = articles + categories
        edges = [{'source_url': r['source_url'], 'target_url': r['target_url'], 'similarity': r.get('similarity', 50.0), 'link_type': r.get('link_type', '')} for r in all_csv_records]
        export_json_graph(nodes, edges, args.output_json)
        print(f"  ➜ JSON граф: {args.output_json}")

    print(f"\n🎉 Анализ завершен!")
    print(f"  • Статья ➔ Каталог (в тексте): {len(art_to_cat_recs)} связей")
    print(f"  • Каталог ➔ Каталог (в тексте): {len(cat_to_cat_recs)} связей")
    print(f"  • Каталог ➔ Статья (E-E-A-T гиды): {len(cat_to_art_recs)} связей")
    print(f"  • Тематические кластеры: {len(cluster_recs)} связей")
    print(f"  • Готовых блоков для CMS: {len(link_blocks)} шт.")
    print(f"  • Расчётный прирост PageRank: +{pr_lift:.1f}%\n")

if __name__ == '__main__':
    main()
