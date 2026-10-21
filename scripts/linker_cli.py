#!/usr/bin/env python3
"""
CLI entrypoint for Antigravity Vector Semantic Linker.
Usage:
  python3 linker_cli.py --sitemap https://example.com/sitemap.xml --output-html report.html
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
from engine import VectorSemanticEngine, compute_internal_pagerank
from reporter import generate_html_report, export_csv_report, export_json_graph

def main():
    parser = argparse.ArgumentParser(description="Vector Semantic Linker for Antigravity CLI")
    parser.add_argument("--sitemap", type=str, help="URL of sitemap.xml or sitemap index")
    parser.add_argument("--articles-urls", type=str, help="Comma-separated article URLs or path to file")
    parser.add_argument("--categories-urls", type=str, help="Comma-separated category URLs or path to file")
    parser.add_argument("--articles-pattern", type=str, default=r"/articles/|/blog/|/news/|/post/", help="Regex pattern to filter article URLs from sitemap")
    parser.add_argument("--catalog-pattern", type=str, default=r"/catalog/|/category/|/services/|/uslugi/", help="Regex pattern to filter money/catalog URLs from sitemap")
    parser.add_argument("--max-articles", type=int, default=30, help="Maximum number of articles to analyze")
    parser.add_argument("--max-categories", type=int, default=30, help="Maximum number of categories to analyze")
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

    if not article_urls:
        print("Ошибка: не найдено URL статей для анализа. Укажите --sitemap или --articles-urls.")
        sys.exit(1)

    if not category_urls:
        print("Ошибка: не найдено URL категорий для анализа. Укажите --sitemap или --categories-urls.")
        sys.exit(1)

    print(f"📥 Сканирование: {len(article_urls)} статей и {len(category_urls)} категорий (потоков: {args.workers})...")
    pages = crawl_site_pages(article_urls, category_urls, max_workers=args.workers)

    articles = [p for p in pages if p['is_article']]
    categories = [p for p in pages if not p['is_article']]

    if not articles or not categories:
        print("Ошибка: не удалось извлечь контент страниц.")
        sys.exit(1)

    print(f"🧠 Векторизация {len(pages)} страниц корпуса с использованием русского стемминга...")
    engine = VectorSemanticEngine()
    engine.fit_transform(pages)

    art_count = len(articles)
    cat_count = len(categories)

    art_matrix = engine.tfidf_matrix[:art_count]
    cat_matrix = engine.tfidf_matrix[art_count:]

    sim_art_cat = cosine_similarity(art_matrix, cat_matrix)
    sim_art_art = cosine_similarity(art_matrix, art_matrix)

    print("🔗 Расчёт семантических связей и подбор анкорных предложений...")
    commercial_recs = []

    for i, art in enumerate(articles):
        existing_links = set(art['links'])
        top_cats = np.argsort(sim_art_cat[i])[::-1]

        matches_count = 0
        for cat_idx in top_cats:
            raw_score = sim_art_cat[i][cat_idx]
            cat = categories[cat_idx]
            clean_cat_url = cat['url'].rstrip('/')

            has_link = any(clean_cat_url in l for l in existing_links)

            if raw_score >= 0.005 and not has_link:
                best_sent, sent_score, sent_html = engine.find_best_sentence_anchor(
                    art['text'], cat['title'], cat_matrix[cat_idx]
                )

                composite_score = min(99.0, max(45.0, (raw_score * 800 + sent_score * 300) / 2))

                commercial_recs.append({
                    'article_url': art['url'],
                    'article_title': art['title'],
                    'target_url': cat['url'],
                    'target_title': cat['title'],
                    'similarity': round(composite_score, 1),
                    'sentence_raw': best_sent,
                    'sentence_html': sent_html,
                    'suggested_anchor': cat['title']
                })
                matches_count += 1
                if matches_count >= 2:
                    break

    commercial_recs.sort(key=lambda x: x['similarity'], reverse=True)

    cluster_recs = []
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
                    'source_title': art['title'],
                    'source_url': art['url'],
                    'target_title': peer_art['title'],
                    'target_url': peer_art['url'],
                    'similarity': sim_pct
                })
                break

    # PageRank simulation
    total_nodes = art_count + cat_count
    adj_current = np.zeros((total_nodes, total_nodes))
    pr_before = compute_internal_pagerank(adj_current)

    adj_after = np.copy(adj_current)
    for rec in commercial_recs:
        art_idx = [a['url'] for a in articles].index(rec['article_url'])
        cat_idx = [c['url'] for c in categories].index(rec['target_url']) + art_count
        adj_after[art_idx, cat_idx] = 1.0

    pr_after = compute_internal_pagerank(adj_after)
    cat_pr_before = np.mean(pr_before[art_count:])
    cat_pr_after = np.mean(pr_after[art_count:])
    pr_lift = ((cat_pr_after - cat_pr_before) / cat_pr_before) * 100 if cat_pr_before > 0 else 0

    domain = urlparse(articles[0]['url']).netloc or "website"

    print("📊 Сохранение отчётов...")
    if args.output_html:
        generate_html_report(domain, articles, categories, commercial_recs, cluster_recs, pr_lift, args.output_html)
        print(f"  ➜ HTML дашборд: {args.output_html}")

    if args.output_csv:
        export_csv_report(commercial_recs, args.output_csv)
        print(f"  ➜ CSV выгрузка: {args.output_csv}")

    if args.output_json:
        nodes = articles + categories
        edges = [{'source_url': r['article_url'], 'target_url': r['target_url'], 'similarity': r['similarity']} for r in commercial_recs]
        export_json_graph(nodes, edges, args.output_json)
        print(f"  ➜ JSON граф: {args.output_json}")

    print(f"\n🎉 Готово! Найдено {len(commercial_recs)} связей Статья ➔ Каталог, расчётный прирост PageRank: +{pr_lift:.1f}%")

if __name__ == '__main__':
    main()
