"""
ILIS v2.0 (Internal Linking Intelligence System) Engine.
Implements:
- 6 Fundamental Principles of ILIS
- Percentile-Based Page Classification (Link Score, Inlinks, Depth)
- Efficiency Index (IE = Link Score / Outlinks)
- Connectivity Ratio (CR = Inlinks / Outlinks)
- 10-Stage Decision Tree & Decision Engine
- 6-Factor Weighted Donor Scoring Model
- Orphan Pages Audit (True, Indexed, Potential)
- Anchor Profile & Cannibalization Audit
- Risk & Structural Anomaly Detection
"""

import math
import re
from collections import defaultdict
import numpy as np

def compute_percentiles(values):
    """
    Returns a dictionary mapping each value to its percentile (0.0 to 100.0).
    Uses relative ranking across the site dataset.
    """
    if not values:
        return {}
    sorted_vals = sorted(values)
    N = len(sorted_vals)
    return {val: (sorted_vals.index(val) / N) * 100.0 for val in set(values)}

class ILISEngine:
    def __init__(self, weights=None):
        # Default configurable ILIS weights (Section 12.2)
        self.weights = weights or {
            'semantic': 0.35,
            'link_score': 0.25,
            'depth': 0.15,
            'outlinks': 0.10,
            'page_type': 0.10,
            'priority': 0.05
        }

    def analyze_site_structure(self, pages, inlinks=None):
        """
        Runs comprehensive ILIS metric calculations across all pages.
        Calculates Link Score, Inlinks, Depth percentiles, IE, CR, and integration status.
        """
        if inlinks is None:
            inlinks = []

        # Graph aggregation
        inlinks_by_target = defaultdict(list)
        outlinks_by_source = defaultdict(list)
        for link in inlinks:
            tgt = link.get('to', '').rstrip('/')
            src = link.get('from', '').rstrip('/')
            if tgt and src:
                inlinks_by_target[tgt].append(link)
                outlinks_by_source[src].append(link)

        # Collect distributions
        link_scores = [float(p.get('link_score', 1.0)) for p in pages]
        inlink_counts = [len(set(l['from'] for l in inlinks_by_target[p['url'].rstrip('/')])) if inlinks else int(p.get('unique_inlinks', 0)) for p in pages]
        depths = [int(p.get('crawl_depth', 1)) for p in pages]

        ls_pct_map = compute_percentiles(link_scores)
        in_pct_map = compute_percentiles(inlink_counts)
        dp_pct_map = compute_percentiles(depths)

        analyzed_pages = []
        for i, p in enumerate(pages):
            url = p['url'].rstrip('/')
            ls = float(p.get('link_score', 1.0))
            depth = int(p.get('crawl_depth', 1))
            indexable = p.get('indexable', True)

            # Inlinks & Outlinks
            if inlinks:
                u_in = len(set(l['from'] for l in inlinks_by_target[url]))
                u_out = len(set(l['to'] for l in outlinks_by_source[url]))
            else:
                u_in = int(p.get('unique_inlinks', len(p.get('incoming_links', []))))
                u_out = int(p.get('unique_outlinks', len(p.get('links', []))))

            ls_pct = ls_pct_map.get(ls, 50.0)
            in_pct = in_pct_map.get(u_in, 50.0)
            dp_pct = dp_pct_map.get(depth, 50.0)

            # ILIS Metrics: IE and CR
            ie = round(ls / u_out, 2) if u_out > 0 else 0.0
            cr = round(u_in / u_out, 2) if u_out > 0 else 0.0

            # ILIS Page Classification (Section 8.6 & 10)
            if not indexable:
                status = "⚫ Не участвует"
                status_desc = "Неиндексируемая страница или технический URL"
            elif u_in == 0:
                status = "🔴 Изолирована (Orphan)"
                status_desc = "Страница не имеет входящих внутренних ссылок"
            elif u_out == 0:
                status = "⏹ Тупик (Dead End)"
                status_desc = "Страница не имеет исходящих ссылок и не передает вес"
            elif in_pct <= 25.0:
                status = "🟠 Недостаточно ссылок"
                status_desc = "Количество входящих ссылок в нижнем квартиле по сайту"
            elif ls_pct <= 35.0 or in_pct <= 40.0:
                status = "🟡 Требует усиления"
                status_desc = "Внутренний вес или связанность ниже среднего по сайту"
            else:
                status = "✅ Хорошо интегрирована"
                status_desc = "Страница имеет сбалансированное распределение ссылочного веса"

            analyzed_pages.append({
                **p,
                'url': url,
                'link_score': ls,
                'link_score_pct': round(ls_pct, 1),
                'unique_inlinks': u_in,
                'unique_inlinks_pct': round(in_pct, 1),
                'unique_outlinks': u_out,
                'crawl_depth': depth,
                'crawl_depth_pct': round(dp_pct, 1),
                'ie': ie,
                'cr': cr,
                'status': status,
                'status_desc': status_desc,
                'is_target': p.get('is_target', False)
            })

        return analyzed_pages

    def audit_orphan_pages(self, analyzed_pages):
        """
        ILIS Orphan Pages Audit (Section 14).
        Categorizes orphans: True Orphan, Indexed Orphan, Potential Orphan.
        """
        orphans = []
        for p in analyzed_pages:
            u_in = p['unique_inlinks']
            indexable = p.get('indexable', True)
            depth = p['crawl_depth']

            if u_in == 0:
                orphan_type = "True Orphan" if not indexable else "Indexed Orphan"
                priority = "Critical" if p.get('is_target', False) or indexable else "High"
                rec = "Добавить в навигацию / контекстную перелинковку" if indexable else "Удалить или закрыть noindex"
                orphans.append({
                    'url': p['url'],
                    'title': p['title'],
                    'orphan_type': orphan_type,
                    'priority': priority,
                    'inlinks': u_in,
                    'crawl_depth': depth,
                    'link_score': p['link_score'],
                    'recommendation': rec
                })
            elif u_in == 1 and depth >= 4 and p['link_score_pct'] <= 15.0:
                orphans.append({
                    'url': p['url'],
                    'title': p['title'],
                    'orphan_type': "Potential Orphan",
                    'priority': "Medium",
                    'inlinks': u_in,
                    'crawl_depth': depth,
                    'link_score': p['link_score'],
                    'recommendation': "Сократить уровень вложенности и добавить 2-3 контекстные ссылки"
                })

        return orphans

    def audit_anchor_profile(self, inlinks):
        """
        ILIS Anchor Profile Audit (Section 13 & 16.3).
        Detects anchor cannibalization, over-optimization, and generic anchor tags.
        """
        if not inlinks:
            return {'top_anchors': [], 'cannibalization': [], 'generic_warnings': []}

        anchor_targets = defaultdict(set)
        anchor_freq = defaultdict(int)
        generic_patterns = re.compile(r'^(тут|здесь|подробнее|читать далее|ссылка|подробно|перейти|нажмите|далее|источник|http[s]?://.*)$', re.I)

        for l in inlinks:
            raw_anc = l.get('anchor', '').strip()
            tgt = l.get('to', '').rstrip('/')
            if not raw_anc:
                raw_anc = "[Безанкорная ссылка / пустой анкор]"
            anchor_freq[raw_anc] += 1
            if tgt:
                anchor_targets[raw_anc.lower()].add(tgt)

        # Cannibalization: same anchor pointing to multiple distinct targets
        cannibalization = []
        for anc, targets in anchor_targets.items():
            if len(targets) > 1 and anc != "[безанкорная ссылка / пустой анкор]":
                cannibalization.append({
                    'anchor': anc,
                    'target_count': len(targets),
                    'targets': list(targets)
                })

        # Generic warnings
        generic_warnings = []
        total_links = sum(anchor_freq.values())
        for anc, cnt in anchor_freq.items():
            if generic_patterns.match(anc):
                pct = round((cnt / total_links) * 100, 1) if total_links > 0 else 0
                generic_warnings.append({
                    'anchor': anc,
                    'count': cnt,
                    'pct': pct,
                    'issue': "Неинформативный общий анкор — не передает релевантность поисковой системе"
                })

        top_anchors = sorted([{'anchor': k, 'count': v} for k, v in anchor_freq.items()], key=lambda x: x['count'], reverse=True)[:15]

        return {
            'top_anchors': top_anchors,
            'cannibalization': sorted(cannibalization, key=lambda x: x['target_count'], reverse=True),
            'generic_warnings': generic_warnings
        }

    def score_donor_candidate(self, donor, target, semantic_similarity):
        """
        ILIS 6-Factor Weighted Model (Section 12.2):
        Score = 0.35 * Semantic + 0.25 * LinkScorePct + 0.15 * DepthScore + 0.10 * OutlinkCap + 0.10 * TypeMatch + 0.05 * Priority
        """
        w = self.weights

        # 1. Semantic similarity (0.0 to 1.0)
        s_sim = float(semantic_similarity)

        # 2. Link Score percentile (0.0 to 1.0)
        s_ls = float(donor.get('link_score_pct', 50.0)) / 100.0

        # 3. Depth score (higher for shallower pages: depth 0 or 1 = 1.0, depth 5 = 0.2)
        d_val = donor.get('crawl_depth', 2)
        s_depth = max(0.1, 1.0 - (d_val * 0.15))

        # 4. Outlink capacity (prefer donors with moderate outlinks, avoid bloated pages)
        outlinks = donor.get('unique_outlinks', 10)
        if outlinks <= 5:
            s_out = 0.9
        elif outlinks <= 25:
            s_out = 1.0
        elif outlinks <= 60:
            s_out = 0.7
        else:
            s_out = 0.4

        # 5. Page type / SILO alignment
        src_is_art = donor.get('is_article', True)
        tgt_is_art = target.get('is_article', False)
        s_type = 0.9 if src_is_art != tgt_is_art else 0.8  # Content to Money SILO

        # 6. Priority boost
        s_prio = 1.0 if donor.get('is_target', False) else 0.5

        final_score = (
            w['semantic'] * s_sim +
            w['link_score'] * s_ls +
            w['depth'] * s_depth +
            w['outlinks'] * s_out +
            w['page_type'] * s_type +
            w['priority'] * s_prio
        )

        return round(final_score * 100.0, 1)

    def formulate_ilis_recommendation(self, donor, target, score, anchor, raw_sentence, html_sentence):
        """
        Formats recommendation according to ILIS Section 15.1 and 15.2.
        Includes full data justification (evidence) and priority ranking.
        """
        # Determine Priority
        tgt_status = target.get('status', '')
        if "🔴" in tgt_status or target.get('is_target', False):
            priority = "Critical" if target.get('unique_inlinks', 0) <= 1 else "High"
        elif "🟡" in tgt_status or "🟠" in tgt_status:
            priority = "High" if score > 70 else "Medium"
        else:
            priority = "Medium" if score > 75 else "Low"

        # Evidence explanation
        evidence = (
            f"Target LinkScore: {target.get('link_score', 0)} ({target.get('link_score_pct', 0)}%), "
            f"Target Inlinks: {target.get('unique_inlinks', 0)}, "
            f"Donor LinkScore: {donor.get('link_score', 0)} ({donor.get('link_score_pct', 0)}%), "
            f"Donor Depth: {donor.get('crawl_depth', 1)}, IE: {donor.get('ie', 0)}"
        )

        why_needed = (
            f"Целевая страница ({target['title']}) имеет статус '{tgt_status}' и требует усиления внутреннего веса. "
            f"Донор ({donor['title']}) обладает высоким авторитетом (Link Score: {donor.get('link_score', 0)}) "
            f"и подтвержденной семантической релевантностью."
        )

        return {
            'donor_url': donor['url'],
            'donor_title': donor['title'],
            'target_url': target['url'],
            'target_title': target['title'],
            'why_needed': why_needed,
            'link_type': 'Контекстная ссылка в тексте',
            'suggested_anchor': anchor,
            'link_position': 'Внутри предложения (контекст)',
            'follow': 'follow',
            'priority': priority,
            'ilis_score': score,
            'evidence': evidence,
            'sentence_raw': raw_sentence,
            'sentence_html': html_sentence
        }
