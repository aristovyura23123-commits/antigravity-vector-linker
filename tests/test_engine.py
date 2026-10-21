"""
Unit tests for Vector Semantic Linker v2.0 engine.
"""

import unittest
import numpy as np
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.abspath(os.path.join(current_dir, '..', 'scripts'))
sys.path.insert(0, scripts_dir)

from engine import (
    stem_tokenizer,
    parse_category_components,
    extract_tight_anchor_span,
    VectorSemanticEngine,
    compute_internal_pagerank
)

class TestVectorLinkerEngineV2(unittest.TestCase):

    def test_stem_tokenizer(self):
        tokens = stem_tokenizer("Как правильно выбрать детские ботинки для мальчика?")
        self.assertIn("ботинк", tokens)
        self.assertIn("мальчик", tokens)
        self.assertNotIn("как", tokens)
        self.assertNotIn("для", tokens)

    def test_parse_category_components(self):
        head, mod = parse_category_components("Обувь для мальчиков")
        self.assertIn("обув", head)
        self.assertIn("мальчик", mod)
        self.assertNotIn("мальчик", head)

        head2, mod2 = parse_category_components("Аксессуары для детских колясок и автокресел")
        self.assertIn("колясок", head2)
        self.assertIn("автокресел", head2)
        self.assertNotIn("детск", head2)

    def test_tight_anchor_span_extraction(self):
        sentence = "Разнообразные модели детской весенней обуви для мальчиков и девочек предоставляют бренды."
        head_stems = {"обув"}
        mod_stems = {"мальчик", "для"}
        target_url = "/catalog/obuv-dlya-malchikov/"
        
        anchor, html_sent = extract_tight_anchor_span(sentence, head_stems, mod_stems, target_url)
        self.assertIsNotNone(anchor)
        self.assertIn("обуви для мальчиков", anchor.lower())
        self.assertIn(f'<a href="{target_url}"><strong>{anchor}</strong></a>', html_sent)

    def test_entity_gate_blocks_irrelevant_category(self):
        engine = VectorSemanticEngine()
        shoe_article = "Свежий воздух и сырая погода. Выбираем качественные демисезонные ботинки и обувь для ребенка."
        
        stroller_head = {"колясок", "автокресел"}
        stroller_mod = {"детск", "для"}
        
        anchor, raw_sent, html_sent, score = engine.find_best_sentence_match(shoe_article, stroller_head, stroller_mod, "/catalog/kolyaski/")
        # MUST BE NONE! Stroller has 0 head matches in a shoe article!
        self.assertIsNone(anchor)
        self.assertIsNone(raw_sent)
        self.assertIsNone(html_sent)

    def test_pagerank_computation(self):
        adj = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 0]
        ])
        pr = compute_internal_pagerank(adj)
        self.assertEqual(len(pr), 3)
        self.assertAlmostEqual(float(np.sum(pr)), 1.0, places=4)

if __name__ == '__main__':
    unittest.main()
