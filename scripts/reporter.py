"""
Report generators for Vector Semantic Linker v3.0 (ILIS v2.0 Unified Edition):
Interactive HTML dashboard, Comprehensive CSV export, and Graph JSON.
"""

import csv
import json
import html as html_lib

def generate_html_report(
    site_domain,
    articles,
    categories,
    art_to_cat_recs,
    cat_to_cat_recs,
    cat_to_art_recs,
    cluster_recs,
    link_blocks,
    pr_lift,
    output_path,
    ilis_data=None
):
    """
    Renders an enterprise-grade standalone interactive HTML dashboard based on ILIS v2.0.
    """
    if ilis_data is None:
        ilis_data = {}

    orphans = ilis_data.get('orphans', [])
    anchor_audit = ilis_data.get('anchor_audit', {})
    cannibalization = anchor_audit.get('cannibalization', [])
    generic_warnings = anchor_audit.get('generic_warnings', [])
    ilis_table = ilis_data.get('ilis_table', [])
    summary_stats = ilis_data.get('summary_stats', {})

    total_pages = len(articles) + len(categories)
    mean_inlinks = summary_stats.get('mean_inlinks', 0)
    mean_depth = summary_stats.get('mean_depth', 1.0)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ILIS v2.0 & Vector Linker | Отчёт перелинковки {site_domain}</title>
  <style>
    :root {{
      --primary: #4f46e5;
      --primary-dark: #3730a3;
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --border: #e2e8f0;
      --success: #16a34a;
      --purple: #9333ea;
      --amber: #d97706;
      --danger: #dc2626;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }}
    .container {{ max-width: 1320px; margin: 0 auto; }}
    header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
      color: #ffffff;
      padding: 36px;
      border-radius: 16px;
      margin-bottom: 24px;
      box-shadow: 0 10px 25px -5px rgba(30, 27, 75, 0.4);
    }}
    header h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
    header p {{ color: #cbd5e1; font-size: 14px; max-width: 950px; line-height: 1.6; }}
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .stat-card .val {{ font-size: 26px; font-weight: 800; color: var(--primary); margin-bottom: 4px; }}
    .stat-card.success .val {{ color: var(--success); }}
    .stat-card.danger .val {{ color: var(--danger); }}
    .stat-card.purple .val {{ color: var(--purple); }}
    .stat-card.amber .val {{ color: var(--amber); }}
    .stat-card .lbl {{ font-size: 11px; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
    .section {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 26px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    .section h2 {{ font-size: 19px; font-weight: 700; margin-bottom: 8px; color: #0f172a; display: flex; align-items: center; gap: 8px; }}
    .section-desc {{ color: var(--muted); font-size: 13px; margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 12px 14px; border: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; font-weight: 600; color: #334155; }}
    tr:hover td {{ background: #fdfdfe; }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
    }}
    .badge-sim {{ background: #e0e7ff; color: #3730a3; }}
    .badge-high {{ background: #dcfce7; color: #166534; }}
    .badge-critical {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}
    .badge-medium {{ background: #fef3c7; color: #92400e; }}
    .badge-purple {{ background: #f3e8ff; color: #6b21a8; }}
    .context-box {{
      background: #f8fafc;
      border-left: 3px solid #6366f1;
      border-radius: 0 8px 8px 0;
      padding: 10px 14px;
      font-size: 13px;
      color: #334155;
      margin-top: 6px;
      line-height: 1.5;
    }}
    .context-box a {{
      color: #4f46e5;
      text-decoration: underline;
    }}
    .anchor-cta {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--primary);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .code-box {{
      background: #1e293b;
      color: #f1f5f9;
      border-radius: 8px;
      padding: 12px;
      font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 12px;
      overflow-x: auto;
      margin-top: 6px;
      position: relative;
    }}
    .copy-btn {{
      position: absolute;
      top: 6px;
      right: 6px;
      background: #334155;
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 4px 8px;
      font-size: 11px;
      cursor: pointer;
    }}
    .copy-btn:hover {{ background: #475569; }}
    .rule-note {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      margin-bottom: 12px;
    }}
    .warning-note {{
      background: #fffbeb;
      border: 1px solid #fde68a;
      color: #92400e;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-bottom: 14px;
    }}
    footer {{
      text-align: center;
      font-size: 13px;
      color: var(--muted);
      padding: 24px 0;
    }}
  </style>
  <script>
    function copyCode(id) {{
      const el = document.getElementById(id);
      navigator.clipboard.writeText(el.innerText).then(() => {{
        alert('HTML-код скопирован в буфер обмена!');
      }});
    }}
  </script>
</head>
<body>

  <div class="container">
    <header>
      <h1>🧠 ILIS v2.0 & Vector Semantic Linker | {site_domain}</h1>
      <p>Интеллектуальная система анализа внутренней перелинковки и распределения ссылочного веса. Объединяет методологию ILIS (Internal Linking Intelligence System): процентильную классификацию, Decision Tree, аудит страниц-сирот (Orphans), анкорную каннибализацию, контекстные ссылки и адаптивные виджеты для CMS.</p>
    </header>

    <div class="stats-bar">
      <div class="stat-card">
        <div class="val">{total_pages}</div>
        <div class="lbl">Всего страниц</div>
      </div>
      <div class="stat-card {'danger' if len(orphans) > 0 else 'success'}">
        <div class="val">{len(orphans)}</div>
        <div class="lbl">Страниц-сирот (Orphans)</div>
      </div>
      <div class="stat-card">
        <div class="val">{mean_inlinks}</div>
        <div class="lbl">Среднее число Inlinks</div>
      </div>
      <div class="stat-card">
        <div class="val">{mean_depth:.1f}</div>
        <div class="lbl">Средняя глубина (Depth)</div>
      </div>
      <div class="stat-card purple">
        <div class="val">{len(art_to_cat_recs) + len(cat_to_cat_recs)}</div>
        <div class="lbl">Контекстных связей</div>
      </div>
      <div class="stat-card success">
        <div class="val">+{pr_lift:.1f}%</div>
        <div class="lbl">Рост PageRank категорий</div>
      </div>
    </div>

    <!-- Раздел 1: Аудит страниц-сирот (Orphan Pages Audit) -->
    <div class="section" id="sec-orphans">
      <h2>🚨 1. Orphan Pages Audit (Аудит изолированных страниц)</h2>
      <p class="section-desc">Страницы с нулевой или критически слабой входящей поддержкой. По методологии ILIS, сироты разделяются по типам и не спасаются вслепую, а получают точечный план действий.</p>
    """

    if not orphans:
        html += """<div class="rule-note">✅ Изолированных страниц (True Orphans) в проанализированном графе не обнаружено. Все URL имеют входящую поддержку.</div>"""
    else:
        html += """
        <table>
          <thead>
            <tr>
              <th style="width: 30%;">Страница (URL)</th>
              <th style="width: 15%;">Тип Orphan</th>
              <th style="width: 10%;">Приоритет</th>
              <th style="width: 10%;">Метрики</th>
              <th style="width: 35%;">Рекомендация по действию</th>
            </tr>
          </thead>
          <tbody>
        """
        for o in orphans:
            badge_prio = "badge-critical" if o['priority'] == 'Critical' else "badge-medium"
            html += f"""
            <tr>
              <td>
                <strong>{o['title']}</strong><br>
                <a href="{o['url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{o['url']}</a>
              </td>
              <td><span class="badge badge-purple">{o['orphan_type']}</span></td>
              <td><span class="badge {badge_prio}">{o['priority']}</span></td>
              <td>Inlinks: {o['inlinks']}<br>Depth: {o['crawl_depth']}</td>
              <td>{o['recommendation']}</td>
            </tr>
            """
        html += """</tbody></table>"""

    html += f"""
    </div>

    <!-- Раздел 2: Анкорный аудит и каннибализация -->
    <div class="section" id="sec-anchors">
      <h2>🎯 2. Анкорный аудит и каннибализация (Anchor Risk Audit)</h2>
      <p class="section-desc">Анализ рисков переоптимизации, анкорной каннибализации (одинаковый анкор ведет на разные URL) и общих неинформативных ссылок.</p>
    """

    if cannibalization:
        html += """
        <div class="warning-note">⚠️ <strong>Обнаружена анкорная каннибализация:</strong> один и тот же анкор используется для ссылок на разные целевые страницы, что путает поисковые алгоритмы.</div>
        <table>
          <thead>
            <tr>
              <th style="width: 30%;">Спорный анкор</th>
              <th style="width: 15%;">Количество целей</th>
              <th style="width: 55%;">Конфликтующие целевые URL</th>
            </tr>
          </thead>
          <tbody>
        """
        for c in cannibalization[:10]:
            urls_html = "<br>".join([f'<a href="{u}" target="_blank" style="font-size: 11px; color: var(--primary);">{u}</a>' for u in c['targets']])
            html += f"""
            <tr>
              <td><code>«{c['anchor']}»</code></td>
              <td><span class="badge badge-medium">{c['target_count']} URL</span></td>
              <td>{urls_html}</td>
            </tr>
            """
        html += """</tbody></table>"""
    else:
        html += """<div class="rule-note">✅ Конфликтов анкорной каннибализации не обнаружено. Все анкоры строго разделены между целевыми страницами.</div>"""

    if generic_warnings:
        html += """
        <h3 style="font-size: 15px; margin: 18px 0 8px 0;">Неинформативные пустые анкоры («тут», «здесь», «подробнее»):</h3>
        <table>
          <thead><tr><th>Анкор</th><th>Частота</th><th>Доля от всех ссылок</th><th>Проблема</th></tr></thead>
          <tbody>
        """
        for g in generic_warnings:
            html += f"""<tr><td><code>«{g['anchor']}»</code></td><td>{g['count']}</td><td>{g['pct']}%</td><td>{g['issue']}</td></tr>"""
        html += """</tbody></table>"""

    html += f"""
    </div>

    <!-- Раздел 3: Сводная таблица решений ILIS (Decision Table) -->
    <div class="section" id="sec-decision-table">
      <h2>📋 3. Сводная таблица решений ILIS v2.0 (Decision Engine Table)</h2>
      <div class="rule-note">
        🛡 <strong>Принцип ILIS:</strong> Каждая рекомендация опирается на многофакторные метрики (Link Score, Crawl Depth, Inlinks, IE) и 6-факторную модель отбора доноров.
      </div>
      <p class="section-desc">Единый приоритизированный план действий по внедрению внутренних ссылок с доказательной базой (Evidence).</p>

      <table>
        <thead>
          <tr>
            <th style="width: 20%;">Donor URL (Донор)</th>
            <th style="width: 20%;">Target URL (Цель)</th>
            <th style="width: 10%;">Приоритет</th>
            <th style="width: 15%;">Рекомендуемый анкор</th>
            <th style="width: 35%;">Обоснование на данных (Evidence) & Зачем нужна ссылка</th>
          </tr>
        </thead>
        <tbody>
    """

    for rec in ilis_table[:25]:
        prio_badge = "badge-critical" if rec['priority'] == 'Critical' else ("badge-high" if rec['priority'] == 'High' else "badge-sim")
        html += f"""
          <tr>
            <td>
              <strong>{rec.get('donor_title', 'Донор')}</strong><br>
              <a href="{rec['donor_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['donor_url']}</a>
            </td>
            <td>
              <strong>{rec.get('target_title', 'Целевая')}</strong><br>
              <a href="{rec['target_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['target_url']}</a>
            </td>
            <td><span class="badge {prio_badge}">{rec['priority']}</span><br><span style="font-size: 11px; color: var(--muted);">ILIS: {rec.get('ilis_score', 0)}</span></td>
            <td><code>{rec['suggested_anchor']}</code><br><span style="font-size: 11px; color: var(--muted);">{rec.get('link_position', 'контекст')}</span></td>
            <td>
              <div style="font-size: 12px; margin-bottom: 4px;">{rec['why_needed']}</div>
              <div style="font-size: 11px; color: var(--muted); background: #f8fafc; padding: 4px 6px; border-radius: 4px;">📊 <strong>Метрики:</strong> {rec['evidence']}</div>
            </td>
          </tr>
        """

    html += f"""
        </tbody>
      </table>
    </div>

    <!-- Раздел 4: Контекстная перелинковка: Статья ➔ Каталог -->
    <div class="section" id="sec-art-cat">
      <h2>📝 4. Контекстная перелинковка: Статья блога ➔ Каталог</h2>
      <div class="rule-note">
        🛡 <strong>Гарантия v3.0:</strong> Строго 1 ссылка на 1 уникальное предложение. Анкоры выделены прямо из авторского текста без искажения синтаксиса.
      </div>
      <p class="section-desc">Коммерческая конверсионная перелинковка. Передает ссылочный вес со статей на целевые страницы каталога.</p>

      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Статья-донор (Блог)</th>
            <th style="width: 22%;">Категория-акцептор (Каталог)</th>
            <th style="width: 8%;">Близость</th>
            <th style="width: 45%;">Контекст в тексте статьи и рекомендуемый анкор</th>
          </tr>
        </thead>
        <tbody>
    """

    for rec in art_to_cat_recs:
        badge_cls = "badge-high" if rec['similarity'] > 60 else "badge-sim"
        html += f"""
          <tr>
            <td>
              <strong>{rec['source_title']}</strong><br>
              <a href="{rec['source_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['source_url']}</a>
            </td>
            <td>
              <strong>{rec['target_title']}</strong><br>
              <a href="{rec['target_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['target_url']}</a>
            </td>
            <td><span class="badge {badge_cls}">{rec['similarity']}%</span></td>
            <td>
              <div class="context-box">
                «{rec['sentence_html']}»
              </div>
              <div class="anchor-cta">
                🎯 <strong>Внедрить ссылку с анкором:</strong> <code>{rec['suggested_anchor']}</code>
              </div>
            </td>
          </tr>
        """

    html += f"""
        </tbody>
      </table>
    </div>

    <!-- Раздел 5: Каталог ➔ Каталог -->
    <div class="section" id="sec-cat-cat">
      <h2>🛒 5. Контекстная перелинковка: Каталог ➔ Каталог (Кросс-линкинг)</h2>
      <p class="section-desc">Кросс-категорийная перелинковка внутри описаний разделов каталога. Повышает внутренний PageRank смежных разделов.</p>

      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Категория-донор</th>
            <th style="width: 22%;">Связанная категория-акцептор</th>
            <th style="width: 8%;">Близость</th>
            <th style="width: 45%;">Контекст в описании категории и анкор</th>
          </tr>
        </thead>
        <tbody>
    """

    if not cat_to_cat_recs:
        html += """<tr><td colspan="4" style="text-align: center; color: var(--muted); padding: 20px;">Нет прямых совпадений в кратких описаниях категорий</td></tr>"""
    else:
        for rec in cat_to_cat_recs:
            html += f"""
              <tr>
                <td>
                  <strong>{rec['source_title']}</strong><br>
                  <a href="{rec['source_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['source_url']}</a>
                </td>
                <td>
                  <strong>{rec['target_title']}</strong><br>
                  <a href="{rec['target_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['target_url']}</a>
                </td>
                <td><span class="badge badge-purple">{rec['similarity']}%</span></td>
                <td>
                  <div class="context-box">
                    «{rec['sentence_html']}»
                  </div>
                  <div class="anchor-cta">
                    🎯 <strong>Внедрить ссылку с анкором:</strong> <code>{rec['suggested_anchor']}</code>
                  </div>
                </td>
              </tr>
            """

    html += f"""
        </tbody>
      </table>
    </div>

    <!-- Раздел 6: Готовые блоки перелинковки для CMS -->
    <div class="section" id="sec-blocks">
      <h2>📦 6. Готовые блоки перелинковки для CMS (HTML-виджеты)</h2>
      <p class="section-desc">Адаптивные HTML-блоки со встроенными стилями для быстрой вставки в шаблоны CMS или окончания страниц без ручной редактуры текста.</p>

      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Страница размещения</th>
            <th style="width: 20%;">Тип блока</th>
            <th style="width: 55%;">Готовый HTML-код для вставки в CMS</th>
          </tr>
        </thead>
        <tbody>
    """

    for idx, blk in enumerate(link_blocks):
        code_id = f"block_code_{idx}"
        escaped_html = html_lib.escape(blk['html'])
        html += f"""
          <tr>
            <td>
              <strong>{blk['page_title']}</strong><br>
              <a href="{blk['page_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{blk['page_url']}</a>
            </td>
            <td>
              <span class="badge badge-purple">{blk['type_label']}</span>
            </td>
            <td>
              <div class="code-box">
                <button class="copy-btn" onclick="copyCode('{code_id}')">Копировать HTML</button>
                <pre id="{code_id}"><code>{escaped_html}</code></pre>
              </div>
            </td>
          </tr>
        """

    html += f"""
        </tbody>
      </table>
    </div>

    <footer>
      Сгенерировано автоматически системой ILIS v2.0 & Vector Semantic Linker для Antigravity CLI · 2026
    </footer>
  </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def export_csv_report(all_recs, output_path):
    """
    Exports a comprehensive CSV file conforming to ILIS v2.0 schema (Section 15.2).
    """
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'Приоритет (Priority)',
            'Тип перелинковки (Link Type)',
            'URL источника (Donor URL)',
            'Заголовок источника (Donor Title)',
            'Целевой URL (Target URL)',
            'Целевой заголовок (Target Title)',
            'Семантическая близость (%)',
            'ILIS Score',
            'Рекомендуемый анкор (Anchor)',
            'Позиция ссылки (Link Position)',
            'Обоснование из данных (Evidence)',
            'Зачем нужна ссылка (Why Needed)',
            'Предложение в тексте (Sentence Context)'
        ])
        for r in all_recs:
            writer.writerow([
                r.get('priority', 'Medium'),
                r.get('link_type', 'Контекстная ссылка'),
                r.get('donor_url') or r.get('source_url', ''),
                r.get('donor_title') or r.get('source_title', ''),
                r.get('target_url', ''),
                r.get('target_title', ''),
                r.get('similarity', 50.0),
                r.get('ilis_score', 50.0),
                r.get('suggested_anchor', ''),
                r.get('link_position', 'контекст'),
                r.get('evidence', ''),
                r.get('why_needed', ''),
                r.get('sentence_raw', '')
            ])

def export_json_graph(nodes, edges, output_path):
    """
    Exports graph JSON for D3.js or graph visualization libraries.
    """
    data = {
        'nodes': [{'id': n['url'], 'title': n['title'], 'type': 'article' if n.get('is_article', False) else 'category', 'status': n.get('status', ''), 'link_score': n.get('link_score', 0)} for n in nodes],
        'edges': [{'source': e.get('source_url') or e.get('donor_url'), 'target': e['target_url'], 'weight': e.get('similarity', 1.0), 'type': e.get('link_type', 'commercial')} for e in edges]
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
