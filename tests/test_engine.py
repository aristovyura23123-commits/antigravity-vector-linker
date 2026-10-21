"""
Unit tests for Vector Semantic Linker engine.
"""

import unittest
import numpy as np
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.abspath(os.path.join(current_dir, '..', 'scripts'))
sys.path.insert(0, scripts_dir)

from engine import stem_tokenizer, VectorSemanticEngine, compute_internal_pagerank

class TestVectorLinkerEngine(unittest.TestCase):

    def test_stem_tokenizer(self):
        tokens = stem_tokenizer("Как правильно выбрать детские ботинки для мальчика?")
        self.assertIn("ботинк", tokens)
        self.assertIn("мальчик", tokens)
        self.assertNotIn("как", tokens)
        self.assertNotIn("для", tokens)

    def test_cosine_similarity(self):
        engine = VectorSemanticEngine()
        docs = [
            {'title': 'Детская обувь и сапоги', 'text': 'Как выбрать зимние ботинки и обувь для ребенка'},
            {'title': 'Зимние ботинки для мальчиков', 'text': 'Каталог качественной детской обуви и сапог'},
            {'title': 'Школьный ранец и пенал', 'text': 'Купить ранец с ортопедической спинкой для школы'}
        ]
        engine.fit_transform(docs)
        sim_related = engine.compute_similarity(0, 1)
        sim_unrelated = engine.compute_similarity(0, 2)
        self.assertGreater(sim_related, sim_unrelated)

    def test_pagerank_computation(self):
        adj = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 0]
        ])
        pr = compute_internal_pagerank(adj)
        self.assertEqual(len(pr), 3)
        self.assertAlmostEqual(float(np.sum(pr)), 1.0, places=4)

    def test_anchor_sentence_finder(self):
        engine = VectorSemanticEngine()
        doc = {'title': 'Тест', 'text': 'Первое предложение. Мы продаем качественные ботинки для детей. Третье предложение о погоде.'}
        engine.fit_transform([doc, {'title': 'Ботинки для детей', 'text': ''}])
        best_sent, score, html = engine.find_best_sentence_anchor(doc['text'], 'Ботинки для детей', engine.tfidf_matrix[1])
        self.assertIn("ботинки", best_sent.lower())
        self.assertGreater(score, 0.0)

if __name__ == '__main__':
    unittest.main()
