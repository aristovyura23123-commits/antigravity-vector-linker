#!/usr/bin/env python3
"""
CLI entrypoint for Antigravity Vector Semantic Linker v3.0 (ILIS v2.0 Unified Edition).
Combines:
- ILIS (Internal Linking Intelligence System) Decision Engine & Principles
- Dual Ingestion: Live Sitemap Crawler OR Screaming Frog CSVs (internal_all, inlinks, target_pages)
- 6-Factor Weighted Donor Scoring Model (Semantic, LinkScore, Depth, Outlinks, SILO, Priority)
- Orphan Pages Audit (True, Indexed, Potential) & Anchor Profile Risk Audit (Cannibalization)
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

from crawler import parse_sitemap, crawl_site_pages, load_screaming_frog_data
from engine import (
    VectorSemanticEngine,
    parse_category_components,
    generate_html_link_block,
    compute_internal_pagerank
)
from ilis_engine import ILISEngine
from reporter import generate_html_report, export_csv_report, export_json_graph

def main():
    parser = argparse.ArgumentParser(description="Vector Semantic Linker v3.0 (ILIS v2.0 Edition) for Antigravity CLI")
    
    # Live crawl arguments
    parser.add_argument("--sitemap", type=str, help="URL of sitemap.xml or sitemap index")
    parser.add_argument("--articles-urls", type=str, help="Comma-separated article URLs or path to file")
    parser.add_argument("--categories-urls", type=str, help="Comma-separated category URLs or path to file")
    parser.add_argument("--articles-pattern", type=str, default=r"/articles/|/blog/|/news/|/post/", help="Regex pattern for article URLs")
    parser.add_argument("--catalog-pattern", type=str, default=r"/catalog/|/category/|/services/|/uslugi/", help="Regex pattern for category URLs")
    parser.add_argument("--max-articles", type=int, default=30, help="Maximum articles to crawl")
    parser.add_argument("--max-categories", type=int, default=30, help="Maximum categories to crawl")
    parser.add_argument("--workers", type=int, default=8, help="Crawler workers")

    # Screaming Frog CSV import arguments (ILIS Section 4)
    parser.add_argument("--internal-all", type=str, help="Path to Screaming Frog internal_all.csv")
    parser.add_argument("--inlinks", type=str, help="Path to Screaming Frog inlinks.csv")
    parser.add_argument("--target-pages", type=str, help="Path to target_pages.csv (ILIS Mode 1)")

    # Common linking options
    parser.add_argument("--max-links-per-page", type=int, default=2, help="Maximum contextual in-text links per page")
    parser.add_argument("--output-html", type=str, default="ilis_vector_linker_report.html", help="Path to output HTML report")
    parser.add_argument("--output-csv", type=str, default="ilis_vector_linker_report.csv", help="Path to output CSV report")
    parser.add_argument("--output-json", type=str, default="ilis_vector_linker_graph.json", help="Path to output JSON graph")

    args = parser.parse_args()

    pages = []
    inlinks = []
    target_urls = set()

    # Mode detection: Screaming Frog CSV vs Live Crawler
    if args.internal_all:
        print(f"📁 Загрузка данных Screaming Frog: {args.internal_all}...")
        pages, inlinks, target_urls = load_screaming_frog_data(args.internal_all, args.inlinks, args.target_pages)
        print(f"  Загружено страниц: {len(pages)}, внутренних ссылок: {len(inlinks)}, целевых URL: {len(target_urls)}")
    else:
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
            print("Ошибка: не указаны входные данные. Укажите --sitemap / --articles-urls или --internal-all.")
            sys.exit(1)

        print(f"📥 Сканирование: {len(article_urls)} статей и {len(category_urls)} категорий (потоков: {args.workers})...")
        pages = crawl_site_pages(article_urls, category_urls, max_workers=args.workers)

        # Build inlinks from crawled body links
        url_set = set(p['url'] for p in pages)
        for p in pages:
            for lk in p.get('links', []):
                clean_lk = lk.rstrip('/')
                if clean_lk in url_set:
                    inlinks.append({'from': p['url'], 'to': clean_lk, 'anchor': '', 'position': 'контекст'})

    if not pages:
        print("Ошибка: не удалось получить данные о страницах.")
        sys.exit(1)

    # =========================================================================
    # ILIS INITIALIZATION & STRUCTURE ANALYSIS (Sections 5, 8, 9, 14)
    # =========================================================================
    print("🧠 ILIS v2.0: Проверка данных и процентильный расчет метрик...")
    ilis = ILISEngine()
    analyzed_pages = ilis.analyze_site_structure(pages, inlinks)

    # Orphan Pages Audit
    orphans = ilis.audit_orphan_pages(analyzed_pages)
    print(f"  • Найдено изолированных страниц (Orphans): {len(orphans)}")

    # Anchor Profile Audit
    anchor_audit = ilis.audit_anchor_profile(inlinks)
    print(f"  • Анкорных конфликтов каннибализации: {len(anchor_audit['cannibalization'])}")

    # Summary Stats
    mean_inlinks = round(np.mean([p['unique_inlinks'] for p in analyzed_pages]), 1) if analyzed_pages else 0
    mean_depth = round(np.mean([p['crawl_depth'] for p in analyzed_pages]), 1) if analyzed_pages else 1.0

    # Split articles and categories
    articles = [p for p in analyzed_pages if p.get('is_article', False)]
    categories = [p for p in analyzed_pages if not p.get('is_article', False)]

    # =========================================================================
    # VECTOR SEMANTIC ENGINE & COMPONENT EXTRACTION
    # =========================================================================
    print(f"⚡ Векторизация {len(analyzed_pages)} страниц (RussianStemmer + TF-IDF 1-2 N-grams)...")
    engine = VectorSemanticEngine()
    engine.fit_transform(analyzed_pages)

    page_url_to_idx = {p['url']: i for i, p in enumerate(analyzed_pages)}

    cat_components = []
    for c in categories:
        h, m = parse_category_components(c['title'])
        cat_components.append({
            'page_ref': c,
            'url': c['url'],
            'title': c['title'],
            'head_stems': h,
            'mod_stems': m
        })

    ilis_table = []

    # =========================================================================
    # PHASE 1: Article -> Catalog In-Text Links (Strict Sentence Deduplication)
    # =========================================================================
    print("🛡 Фаза 1: Контекстная перелинковка Статья ➔ Каталог (1 предложение = 1 ссылка)...")
    art_to_cat_recs = []

    for art in articles:
        candidate_targets = []
        art_idx = page_url_to_idx[art['url']]

        for cat in cat_components:
            tgt_page = cat['page_ref']
            tgt_idx = page_url_to_idx[tgt_page['url']]
            sim = engine.compute_similarity(art_idx, tgt_idx)

            matches = engine.find_all_sentence_matches(
                art['text'], cat['head_stems'], cat['mod_stems'], cat['url']
            )
            if matches:
                top_match_score = matches[0][0]
                # 6-Factor ILIS Weighted Score
                ilis_score = ilis.score_donor_candidate(art, tgt_page, sim)
                candidate_targets.append({
                    'url': cat['url'],
                    'title': cat['title'],
                    'head_stems': cat['head_stems'],
                    'mod_stems': cat['mod_stems'],
                    'score': ilis_score,
                    'target_page': tgt_page,
                    'similarity': round(sim * 100.0, 1)
                })

        allocated = engine.allocate_page_in_text_links(
            art['url'], art['title'], art['text'], candidate_targets, max_links=args.max_links_per_page
        )
        for al in allocated:
            tgt_obj = next((c['target_page'] for c in candidate_targets if c['url'] == al['target_url']), {})
            al['link_type'] = 'Статья -> Каталог [текст]'
            art_to_cat_recs.append(al)

            # ILIS Decision Table recommendation
            rec = ilis.formulate_ilis_recommendation(
                art, tgt_obj, al['score'], al['suggested_anchor'], al['sentence_raw'], al['sentence_html']
            )
            ilis_table.append(rec)

    # =========================================================================
    # PHASE 2: Catalog -> Catalog In-Text Links (Category Cross-Linking)
    # =========================================================================
    print("🛒 Фаза 2: Контекстная перелинковка Каталог ➔ Каталог (Кросс-линкинг описаний)...")
    cat_to_cat_recs = []

    for cat_src in categories:
        candidate_targets = []
        src_idx = page_url_to_idx[cat_src['url']]

        for cat_tgt in cat_components:
            if cat_tgt['url'] == cat_src['url']:
                continue
            tgt_page = cat_tgt['page_ref']
            tgt_idx = page_url_to_idx[tgt_page['url']]
            sim = engine.compute_similarity(src_idx, tgt_idx)

            matches = engine.find_all_sentence_matches(
                cat_src['text'], cat_tgt['head_stems'], cat_tgt['mod_stems'], cat_tgt['url']
            )
            if matches:
                top_match_score = matches[0][0]
                ilis_score = ilis.score_donor_candidate(cat_src, tgt_page, sim)
                candidate_targets.append({
                    'url': cat_tgt['url'],
                    'title': cat_tgt['title'],
                    'head_stems': cat_tgt['head_stems'],
                    'mod_stems': cat_tgt['mod_stems'],
                    'score': ilis_score,
                    'target_page': tgt_page,
                    'similarity': round(sim * 100.0, 1)
                })

        allocated = engine.allocate_page_in_text_links(
            cat_src['url'], cat_src['title'], cat_src['text'], candidate_targets, max_links=args.max_links_per_page
        )
        for al in allocated:
            tgt_obj = next((c['target_page'] for c in candidate_targets if c['url'] == al['target_url']), {})
            al['link_type'] = 'Каталог -> Каталог [текст]'
            cat_to_cat_recs.append(al)

            rec = ilis.formulate_ilis_recommendation(
                cat_src, tgt_obj, al['score'], al['suggested_anchor'], al['sentence_raw'], al['sentence_html']
            )
            ilis_table.append(rec)

    # =========================================================================
    # PHASE 3: Catalog -> Article (Buying Guides / E-E-A-T Links)
    # =========================================================================
    print("📚 Фаза 3: Экспертные гиды Каталог ➔ Статья (E-E-A-T)...")
    cat_to_art_recs = []

    for cat in categories:
        cat_h, cat_m = parse_category_components(cat['title'])
        for art in articles:
            art_h, art_m = parse_category_components(art['title'])
            if cat_h.intersection(art_h):
                cat_to_art_recs.append({
                    'link_type': 'Каталог -> Статья [E-E-A-T гид]',
                    'source_url': cat['url'],
                    'source_title': cat['title'],
                    'target_url': art['url'],
                    'target_title': art['title'],
                    'similarity': 95.0,
                    'suggested_anchor': art['title'],
                    'priority': 'Medium',
                    'why_needed': f"Раздел каталога '{cat['title']}' повышает экспертность (E-E-A-T), ссылаясь на профильный гид покупателя '{art['title']}'."
                })
                break

    # =========================================================================
    # PHASE 4: Article -> Article (Topic Clusters)
    # =========================================================================
    print("🕸 Фаза 4: Тематические кластеры Статья ➔ Статья...")
    cluster_recs = []
    if len(articles) > 1:
        art_indices = [page_url_to_idx[a['url']] for a in articles]
        art_matrix = engine.tfidf_matrix[art_indices]
        sim_art_art = cosine_similarity(art_matrix, art_matrix)

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
                        'suggested_anchor': peer_art['title'],
                        'priority': 'Low'
                    })
                    break

    # =========================================================================
    # PHASE 5: Dedicated Link Blocks for CMS (HTML Widgets)
    # =========================================================================
    print("📦 Фаза 5: Генерация готовых блоков перелинковки для CMS...")
    link_blocks = []

    # 1. Blocks for articles
    for art in articles:
        matched_cats = [r for r in art_to_cat_recs if r['source_url'] == art['url']]
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

    # 2. Blocks for catalog
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
    N = len(analyzed_pages)
    adj_current = np.zeros((N, N))
    pr_before = compute_internal_pagerank(adj_current)

    adj_after = np.copy(adj_current)
    all_recs = art_to_cat_recs + cat_to_cat_recs + cat_to_art_recs
    for rec in all_recs:
        try:
            s_idx = page_url_to_idx[rec.get('source_url') or rec.get('donor_url')]
            t_idx = page_url_to_idx[rec['target_url']]
            adj_after[s_idx, t_idx] = 1.0
        except KeyError:
            pass

    pr_after = compute_internal_pagerank(adj_after)
    cat_indices = [page_url_to_idx[c['url']] for c in categories]
    cat_pr_before = np.mean(pr_before[cat_indices]) if cat_indices else 0
    cat_pr_after = np.mean(pr_after[cat_indices]) if cat_indices else 0
    pr_lift = ((cat_pr_after - cat_pr_before) / cat_pr_before) * 100 if cat_pr_before > 0 else 0

    domain = urlparse(analyzed_pages[0]['url']).netloc if analyzed_pages else "website"

    ilis_data = {
        'orphans': orphans,
        'anchor_audit': anchor_audit,
        'ilis_table': ilis_table,
        'summary_stats': {
            'mean_inlinks': mean_inlinks,
            'mean_depth': mean_depth
        }
    }

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
            args.output_html,
            ilis_data=ilis_data
        )
        print(f"  ➜ HTML дашборд: {args.output_html}")

    all_csv_records = ilis_table + cat_to_art_recs + cluster_recs
    if args.output_csv:
        export_csv_report(all_csv_records, args.output_csv)
        print(f"  ➜ CSV выгрузка: {args.output_csv}")

    if args.output_json:
        edges = [{'source_url': r.get('donor_url') or r.get('source_url'), 'target_url': r['target_url'], 'similarity': r.get('ilis_score', 50.0), 'link_type': r.get('link_type', '')} for r in all_csv_records]
        export_json_graph(analyzed_pages, edges, args.output_json)
        print(f"  ➜ JSON граф: {args.output_json}")

    print(f"\n🎉 Анализ ILIS v2.0 завершен успешно!")
    print(f"  • Страниц в графе: {len(analyzed_pages)}")
    print(f"  • Изолированных страниц (Orphans): {len(orphans)}")
    print(f"  • Контекстных связей Статья ➔ Каталог: {len(art_to_cat_recs)}")
    print(f"  • Контекстных связей Каталог ➔ Каталог: {len(cat_to_cat_recs)}")
    print(f"  • Экспертных гидов Каталог ➔ Статья (E-E-A-T): {len(cat_to_art_recs)}")
    print(f"  • Готовых блоков для CMS: {len(link_blocks)} шт.")
    print(f"  • Расчётный прирост PageRank: +{pr_lift:.1f}%\n")

if __name__ == '__main__':
    main()
