"""
Unit tests for ILIS v2.0 Engine & Screaming Frog CSV Loader.
"""

import unittest
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.abspath(os.path.join(current_dir, '..', 'scripts'))
sys.path.insert(0, scripts_dir)

from ilis_engine import ILISEngine, compute_percentiles

class TestILISEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ILISEngine()

    def test_percentile_computation(self):
        values = [10, 20, 30, 40, 50]
        pct = compute_percentiles(values)
        self.assertEqual(pct[10], 0.0)
        self.assertEqual(pct[50], 80.0)

    def test_site_structure_and_metrics(self):
        pages = [
            {'url': 'https://example.com/', 'title': 'Главная', 'link_score': 85.0, 'unique_inlinks': 100, 'unique_outlinks': 20, 'crawl_depth': 0, 'indexable': True},
            {'url': 'https://example.com/cat1', 'title': 'Каталог 1', 'link_score': 45.0, 'unique_inlinks': 10, 'unique_outlinks': 15, 'crawl_depth': 1, 'indexable': True},
            {'url': 'https://example.com/orphan', 'title': 'Сирота', 'link_score': 5.0, 'unique_inlinks': 0, 'unique_outlinks': 2, 'crawl_depth': 4, 'indexable': True},
            {'url': 'https://example.com/deadend', 'title': 'Тупик', 'link_score': 10.0, 'unique_inlinks': 5, 'unique_outlinks': 0, 'crawl_depth': 2, 'indexable': True}
        ]
        analyzed = self.engine.analyze_site_structure(pages)
        self.assertEqual(len(analyzed), 4)

        # Check IE & CR on home
        home = next(p for p in analyzed if p['url'] == 'https://example.com')
        self.assertEqual(home['ie'], 4.25)
        self.assertEqual(home['cr'], 5.0)
        self.assertIn("✅", home['status'])

        # Check orphan
        orphan = next(p for p in analyzed if p['url'] == 'https://example.com/orphan')
        self.assertIn("🔴", orphan['status'])

        # Check dead end
        deadend = next(p for p in analyzed if p['url'] == 'https://example.com/deadend')
        self.assertIn("⏹", deadend['status'])

    def test_orphan_audit(self):
        pages = [
            {'url': 'https://example.com/p1', 'title': 'P1', 'link_score': 5.0, 'link_score_pct': 10.0, 'unique_inlinks': 0, 'unique_outlinks': 2, 'crawl_depth': 2, 'indexable': True},
            {'url': 'https://example.com/p2', 'title': 'P2', 'link_score': 2.0, 'link_score_pct': 5.0, 'unique_inlinks': 1, 'unique_outlinks': 5, 'crawl_depth': 5, 'indexable': True}
        ]
        orphans = self.engine.audit_orphan_pages(pages)
        self.assertEqual(len(orphans), 2)
        self.assertEqual(orphans[0]['orphan_type'], "Indexed Orphan")
        self.assertEqual(orphans[1]['orphan_type'], "Potential Orphan")

    def test_anchor_cannibalization_and_generic(self):
        inlinks = [
            {'from': 'https://example.com/a', 'to': 'https://example.com/shoes', 'anchor': 'детская обувь'},
            {'from': 'https://example.com/b', 'to': 'https://example.com/boots', 'anchor': 'детская обувь'},  # Cannibalization!
            {'from': 'https://example.com/c', 'to': 'https://example.com/jackets', 'anchor': 'тут'},           # Generic!
        ]
        audit = self.engine.audit_anchor_profile(inlinks)
        self.assertEqual(len(audit['cannibalization']), 1)
        self.assertEqual(audit['cannibalization'][0]['anchor'], 'детская обувь')
        self.assertEqual(audit['cannibalization'][0]['target_count'], 2)

        self.assertEqual(len(audit['generic_warnings']), 1)
        self.assertEqual(audit['generic_warnings'][0]['anchor'], 'тут')

    def test_6_factor_donor_scoring(self):
        donor = {
            'url': 'https://example.com/blog/boots',
            'title': 'Гид по выбору ботинок',
            'link_score_pct': 85.0,
            'crawl_depth': 1,
            'unique_outlinks': 12,
            'is_article': True,
            'is_target': False
        }
        target = {
            'url': 'https://example.com/catalog/boots',
            'title': 'Ботинки детские',
            'is_article': False,
            'is_target': True
        }
        score = self.engine.score_donor_candidate(donor, target, semantic_similarity=0.9)
        self.assertGreater(score, 75.0)

if __name__ == '__main__':
    unittest.main()
