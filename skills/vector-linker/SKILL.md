---
name: vector-linker
argument-hint: "<sitemap URL or Screaming Frog CSV files: internal_all.csv, inlinks.csv, target_pages.csv>"
description: >
  Интеллектуальная система анализа внутренней перелинковки ILIS v2.0 (Internal Linking Intelligence System)
  и векторного связывания страниц. Вычисляет процентили ссылочного веса, индексы IE и CR, проводит
  аудит страниц-сирот (Orphan Pages) и анкорной каннибализации, применяет 6-факторный Decision Tree отбор
  доноров и подбирает контекстные анкоры со строгим правилом «1 предложение = 1 ссылка».
  Используйте при запросах: "перелинковка", "векторная перелинковка", "внутренние ссылки",
  "ilis", "ilis v2", "internal linking", "orphan pages", "страницы сироты", "аудит перелинковки",
  "screaming frog перелинковка", "topic clusters", "кросс-линкинг", "распределение pagerank".
---

# ILIS v2.0 & Vector Semantic Linker — Интеллектуальная перелинковка

Этот навык реализует методологию **ILIS (Internal Linking Intelligence System) v2.0** в сочетании с алгоритмами векторного анализа текстов (Russian Snowball Stemmer, TF-IDF 1-2 N-grams, Cosine Similarity, Head Entity Intent Gating).

## 6 Обязательных принципов ILIS
1. **Достоверность**: выводы строятся исключительно на данных краулинга или выгрузки Screaming Frog.
2. **Объяснимость (Evidence)**: каждая рекомендация сопровождается доказательной базой (Link Score, Crawl Depth, Inlinks, IE).
3. **Многофакторность**: решение принимается минимум по 2–3 независимым метрикам.
4. **Разделение фактов и рекомендаций**: факты из данных, аналитический статус (🟡 🟠 🔴 ⏹ ✅) и конкретное действие.
5. **Отсутствие домыслов**: ссылки не ставятся с неиндексируемых или битых страниц; нерелевантные сущности блокируются шлюзом Entity Gate.
6. **Пользовательская ценность**: анкоры сохраняют естественный синтаксис предложения автора (строго 1 ссылка на 1 предложение).

## Режимы работы
- **Режим 1 (Target Pages Boost)**: анализ и приоритетное усиление списка целевых коммерческих страниц (`--target-pages target_pages.csv`).
- **Режим 2 (Full Site Audit)**: полный сквозной аудит ссылочной структуры всего сайта по карте сайта или `internal_all.csv`.

## Как запустить анализ

### 1. По карте сайта (Sitemap XML) — автономный краулинг:
```bash
python3 ~/.gemini/config/plugins/vector-linker/scripts/linker_cli.py \
  --sitemap "https://example.com/sitemap.xml" \
  --articles-pattern "/articles/|/blog/|/news/" \
  --catalog-pattern "/catalog/|/services/|/products/" \
  --output-html "ilis_report.html" \
  --output-csv "ilis_report.csv"
```

### 2. По выгрузкам Screaming Frog / Sitebulb CSV:
```bash
python3 ~/.gemini/config/plugins/vector-linker/scripts/linker_cli.py \
  --internal-all "internal_all.csv" \
  --inlinks "inlinks.csv" \
  --target-pages "target_pages.csv" \
  --output-html "ilis_report.html" \
  --output-csv "ilis_report.csv"
```

### 3. По конкретным спискам URL:
```bash
python3 ~/.gemini/config/plugins/vector-linker/scripts/linker_cli.py \
  --articles-urls "https://example.com/blog/art1,https://example.com/blog/art2" \
  --categories-urls "https://example.com/catalog/cat1,https://example.com/catalog/cat2" \
  --output-html "ilis_report.html"
```

## Алгоритмические модули ILIS v2.0
1. **Процентильная классификация**: оценка Link Score, Inlinks и Crawl Depth относительно распределения конкретного сайта.
2. **Метрики эффективности**: расчет $IE = \text{LinkScore} / \text{Outlinks}$ и коэффициента связанности $CR = \text{Inlinks} / \text{Outlinks}$.
3. **Orphan Pages Audit**: классификация изолированных страниц (*True Orphan*, *Indexed Orphan*, *Potential Orphan*) и план действий.
4. **Anchor Profile & Cannibalization**: обнаружение конфликтов, когда один анкор ссылается на разные URL.
5. **6-факторная модель оценки донора**:
   $$\text{Score} = 0.35 \times \text{Семантика} + 0.25 \times \text{LinkScore} + 0.15 \times \text{Глубина} + 0.10 \times \text{Outlinks} + 0.10 \times \text{SILO} + 0.05 \times \text{Приоритет}$$
6. **Sentence Deduplication**: запрет на пересечение ссылок внутри одного предложения.
7. **Готовые HTML-блоки (CMS виджеты)**: генерация адаптивных блоков ссылок для шаблонов страниц.
