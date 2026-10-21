"""
Unit tests for Vector Semantic Linker v2.5 engine.
Covers:
- Russian Snowball tokenization & stemming
- Category component parsing (Head Entity vs Demographic Modifiers)
- In-text anchor span extraction
- Entity Gate blocking irrelevant categories
- Strict Sentence Deduplication: 1 sentence = at most 1 link
- Alternative sentence allocation across distinct sentences
- HTML Link Block Generator (CMS widgets)
- Internal PageRank calculation
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
    generate_html_link_block,
    VectorSemanticEngine,
    compute_internal_pagerank
)

class TestVectorLinkerEngineV25(unittest.TestCase):

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
        self.assertIsNone(anchor)
        self.assertIsNone(raw_sent)
        self.assertIsNone(html_sent)

    def test_strict_sentence_deduplication(self):
        """
        If an article has only ONE matching sentence, only ONE category can be linked.
        The second candidate cannot reuse or overlap on the same sentence.
        """
        engine = VectorSemanticEngine()
        text = "Демисезонная обувь для детей обязательно имеет утепление и мягкую прокладку для комфорта малыша."
        
        cat1 = {
            'url': '/catalog/obuv-novorozhdennye/',
            'title': 'Обувь для новорожденных',
            'head_stems': {'обув'},
            'mod_stems': {'новорожден'},
            'score': 20
        }
        cat2 = {
            'url': '/catalog/obuv-devochki/',
            'title': 'Обувь для девочек',
            'head_stems': {'обув'},
            'mod_stems': {'девочек'},
            'score': 18
        }
        
        allocated = engine.allocate_page_in_text_links(
            '/articles/boots/', 'Как выбрать обувь', text, [cat1, cat2], max_links=2
        )
        # Must be exactly 1 because there is only 1 sentence!
        self.assertEqual(len(allocated), 1)
        self.assertEqual(allocated[0]['target_url'], '/catalog/obuv-novorozhdennye/')

    def test_alternative_sentence_allocation(self):
        """
        If an article has TWO distinct sentences matching different categories,
        each category gets its own distinct sentence without collision.
        """
        engine = VectorSemanticEngine()
        text = (
            "Демисезонная обувь для детей обязательно имеет утепление и мягкую подкладку. "
            "А теплая мембранная куртка защитит от ветра и дождя в любую погоду."
        )
        
        cat_shoe = {
            'url': '/catalog/obuv/',
            'title': 'Обувь для детей',
            'head_stems': {'обув'},
            'mod_stems': {'детей'},
            'score': 20
        }
        cat_jacket = {
            'url': '/catalog/kurtki/',
            'title': 'Куртки для детей',
            'head_stems': {'куртк'},
            'mod_stems': {'детей'},
            'score': 18
        }
        
        allocated = engine.allocate_page_in_text_links(
            '/articles/spring/', 'Весенний гардероб', text, [cat_shoe, cat_jacket], max_links=2
        )
        self.assertEqual(len(allocated), 2)
        # Verify sentences are completely distinct!
        self.assertNotEqual(allocated[0]['sentence_raw'], allocated[1]['sentence_raw'])
        self.assertIn("обувь", allocated[0]['sentence_raw'].lower())
        self.assertIn("куртка", allocated[1]['sentence_raw'].lower())

    def test_link_block_generator(self):
        links = [
            {'url': '/catalog/obuv/', 'title': 'Детская обувь'},
            {'url': '/catalog/kurtki/', 'title': 'Детские куртки'}
        ]
        block_html = generate_html_link_block('catalog_for_article', 'Рекомендуемые разделы', links)
        self.assertIn('seo-block-catalog_for_article', block_html)
        self.assertIn('Рекомендуемые разделы', block_html)
        self.assertIn('href="/catalog/obuv/"', block_html)
        self.assertIn('Детская обувь', block_html)

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
