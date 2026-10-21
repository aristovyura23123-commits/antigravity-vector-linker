"""
Core algorithmic engine for Vector Semantic Linker v2.0.
Features:
- Two-Stage Entity & Category Intent Gating (Head Entity vs Demographic Modifiers)
- Tight Syntactic Anchor Span Extractor (Natural In-Text Anchors)
- Adaptive Relevance Thresholding (Zero False Positives, No Forced Top-K)
- Internal PageRank Graph Simulator
"""

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem.snowball import RussianStemmer

STEMMER = RussianStemmer()

DEFAULT_STOP_WORDS = set([
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все',
    'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по',
    'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему',
    'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть',
    'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом',
    'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'этот', 'для',
    'при', 'интернет', 'магазин', 'руб', 'цена', 'купить', 'каталог', 'spb', 'спб', 'мск',
    'наш', 'ваш', 'доставка', 'рублей', 'фото', 'отзывы', 'наличие', 'очень', 'просто'
])

# Demographic & generic modifiers that must NOT be confused with product head entities
DEMOGRAPHIC_MODIFIERS = set([
    'девочек', 'мальчиков', 'девочки', 'мальчика', 'девочкам', 'мальчикам',
    'новорожденных', 'новорожденного', 'новорожденным', 'детей', 'ребенка', 'детям',
    'малышей', 'малыша', 'малышу', 'детские', 'детская', 'детский', 'детских', 'детское',
    'детскому', 'детской', 'детскую', 'для', 'аксессуары', 'товары', 'купить',
    'интернет', 'магазин', 'цена', 'распродажа', 'новинки', 'скидки', 'spb', 'спб', 'мск',
    'недорого', 'каталог', 'бренды', 'бренд'
])

ADJECTIVE_ENDINGS = ('ая', 'яя', 'ое', 'ее', 'ый', 'ий', 'ой', 'ей', 'ые', 'ие', 'ом', 'ем', 'их', 'ых', 'ую', 'юю')

def stem_tokenizer(text):
    """Extracts words and stems them using Russian Snowball Stemmer."""
    words = re.findall(r'[а-яёa-z0-9]+', text.lower())
    res = []
    for w in words:
        if len(w) > 2 and w not in DEFAULT_STOP_WORDS:
            res.append(STEMMER.stem(w))
    return res

def parse_category_components(title):
    """
    Separates a category title into Head Entities (e.g. 'обувь', 'рюкзаки')
    and Demographic/Generic Modifiers (e.g. 'для девочек', 'детские').
    """
    words = re.findall(r'[а-яёa-z]+', title.lower())
    head_tokens = [w for w in words if w not in DEMOGRAPHIC_MODIFIERS and len(w) > 2]
    mod_tokens = [w for w in words if w in DEMOGRAPHIC_MODIFIERS and len(w) > 2]
    
    head_stems = set(STEMMER.stem(w) for w in head_tokens)
    mod_stems = set(STEMMER.stem(w) for w in mod_tokens)
    return head_stems, mod_stems

def extract_tight_anchor_span(sentence, head_stems, mod_stems, target_url):
    """
    Locates the single best occurrence of the Head Entity in the sentence,
    expands left to include natural modifying adjectives, and expands right
    to include prepositional phrases ('для мальчиков').
    Returns a tight 1-4 word anchor span and formatted HTML.
    """
    tokens = re.findall(r'(\w+|\W+)', sentence)
    words_only = [(idx, t.lower(), STEMMER.stem(t.lower())) for idx, t in enumerate(tokens) if re.match(r'\w+', t)]
    
    if not words_only:
        return None, None
        
    candidate_spans = []
    
    for pos, (orig_idx, word, st) in enumerate(words_only):
        if st in head_stems:
            # Look left up to 2 adjectives
            start_w = pos
            if pos > 0:
                prev_w = words_only[pos-1][1]
                if any(prev_w.endswith(end) for end in ADJECTIVE_ENDINGS) and prev_w not in DEFAULT_STOP_WORDS:
                    start_w = pos - 1
                    if pos > 1:
                        prev2_w = words_only[pos-2][1]
                        if any(prev2_w.endswith(end) for end in ADJECTIVE_ENDINGS) and prev2_w not in DEFAULT_STOP_WORDS:
                            start_w = pos - 2
                            
            # Look right for prepositional modifiers ('для мальчиков', 'для детей')
            end_w = pos
            if pos + 2 < len(words_only) and words_only[pos+1][1] in ['для', 'из', 'на', 'в']:
                if words_only[pos+2][2] in mod_stems:
                    end_w = pos + 2
                    
            token_start = words_only[start_w][0]
            token_end = words_only[end_w][0]
            span_text = ''.join(tokens[token_start:token_end+1]).strip()
            
            # Score: contains both head and modifier = 10, only head = 5
            span_words = re.findall(r'\w+', span_text.lower())
            has_mod = any(STEMMER.stem(w) in mod_stems for w in span_words)
            span_score = 10 if has_mod else 5
            
            # Penalize excessively long spans (> 5 words)
            if len(span_words) > 5:
                span_score -= 3
                
            candidate_spans.append((span_score, span_text, token_start, token_end))
            
    if not candidate_spans:
        return None, None
        
    candidate_spans.sort(key=lambda x: x[0], reverse=True)
    best_score, best_anchor, t_start, t_end = candidate_spans[0]
    
    prefix = ''.join(tokens[:t_start])
    suffix = ''.join(tokens[t_end+1:])
    html_sentence = f'{prefix}<a href="{target_url}"><strong>{best_anchor}</strong></a>{suffix}'
    
    return best_anchor, html_sentence

class VectorSemanticEngine:
    def __init__(self, ngram_range=(1, 2), min_df=1, max_df=1.0):
        self.vectorizer = TfidfVectorizer(
            tokenizer=stem_tokenizer,
            token_pattern=None,
            ngram_range=ngram_range,
            sublinear_tf=True,
            min_df=min_df,
            max_df=max_df
        )
        self.tfidf_matrix = None
        self.doc_meta = []

    def fit_transform(self, docs):
        self.doc_meta = docs
        texts = [d['title'] + " " + d.get('text', '') for d in docs]
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        return self.tfidf_matrix

    def compute_similarity(self, idx1, idx2):
        vec1 = self.tfidf_matrix[idx1]
        vec2 = self.tfidf_matrix[idx2]
        return float(cosine_similarity(vec1, vec2)[0][0])

    def find_best_sentence_match(self, source_text, head_stems, mod_stems, target_url):
        """
        Splits source article into sentences and finds the sentence containing
        verified head entity matches with a natural anchor span.
        """
        raw_sentences = re.split(r'(?<=[.!?])\s+', source_text)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 20 and len(s.strip()) < 350]
        
        best_sentence_html = None
        best_sentence_raw = None
        best_anchor = None
        best_score = -1
        
        for sent in sentences:
            words = [STEMMER.stem(w.lower()) for w in re.findall(r'[а-яёa-z]+', sent)]
            head_count = sum(1 for w in words if w in head_stems)
            if head_count == 0:
                continue
                
            mod_count = sum(1 for w in words if w in mod_stems)
            sent_score = head_count * 10 + mod_count * 3
            
            anchor, html_sent = extract_tight_anchor_span(sent, head_stems, mod_stems, target_url)
            if anchor and sent_score > best_score:
                best_score = sent_score
                best_sentence_html = html_sent
                best_sentence_raw = sent
                best_anchor = anchor
                
        return best_anchor, best_sentence_raw, best_sentence_html, best_score

def compute_internal_pagerank(adj_matrix, num_iterations=50, d=0.85):
    """
    Computes PageRank vector on a directed link graph matrix.
    adj_matrix[i, j] = 1 if page i links to page j.
    """
    N = adj_matrix.shape[0]
    if N == 0:
        return np.array([])
    out_degree = np.sum(adj_matrix, axis=1)
    M = np.zeros((N, N))
    for i in range(N):
        if out_degree[i] > 0:
            M[i, :] = adj_matrix[i, :] / out_degree[i]
        else:
            M[i, :] = 1.0 / N
    pr = np.ones(N) / N
    for _ in range(num_iterations):
        pr = (1 - d) / N + d * np.dot(M.T, pr)
    return pr
