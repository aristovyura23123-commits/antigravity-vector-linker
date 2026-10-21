"""
Core algorithmic engine for Vector Semantic Linker.
Calculates semantic cosine similarity, internal PageRank, and sentence-level anchor matching.
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

def stem_tokenizer(text):
    """Extracts words and stems them using Russian Snowball Stemmer."""
    words = re.findall(r'[а-яёa-z0-9]+', text.lower())
    res = []
    for w in words:
        if len(w) > 2 and w not in DEFAULT_STOP_WORDS:
            res.append(STEMMER.stem(w))
    return res

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
        """Fits TF-IDF model on document corpus and returns normalized matrix."""
        self.doc_meta = docs
        texts = [d['title'] + " " + d.get('text', '') for d in docs]
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        return self.tfidf_matrix

    def compute_similarity(self, idx1, idx2):
        """Cosine similarity between two document indices."""
        vec1 = self.tfidf_matrix[idx1]
        vec2 = self.tfidf_matrix[idx2]
        return float(cosine_similarity(vec1, vec2)[0][0])

    def find_best_sentence_anchor(self, source_text, target_title, target_vec):
        """
        Splits source article into sentences and finds the sentence with
        the highest semantic affinity to the target page.
        """
        raw_sentences = re.split(r'(?<=[.!?])\s+', source_text)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 25 and len(s.strip()) < 400]
        if not sentences:
            return "", 0.0, ""

        sent_vecs = self.vectorizer.transform(sentences)
        sent_sims = cosine_similarity(sent_vecs, target_vec).flatten()
        best_idx = int(np.argmax(sent_sims))
        best_sent = sentences[best_idx]
        best_score = float(sent_sims[best_idx])

        # Highlight target matching tokens
        target_stems = set(stem_tokenizer(target_title))
        words = re.findall(r'(\w+|\W+)', best_sent)
        highlighted = []
        for token in words:
            if re.match(r'\w+', token):
                stem = STEMMER.stem(token.lower())
                if stem in target_stems and len(token) > 2:
                    highlighted.append(f'<span class="anchor-highlight">{token}</span>')
                    continue
            highlighted.append(token)

        return best_sent, best_score, ''.join(highlighted)

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
