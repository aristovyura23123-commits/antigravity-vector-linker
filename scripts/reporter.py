"""
Report generators for Vector Semantic Linker v2.5 / v3.0:
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
    output_path
):
    """
    Renders an enterprise-grade standalone interactive HTML dashboard.
    """
    total_recs = len(art_to_cat_recs) + len(cat_to_cat_recs) + len(cat_to_art_recs) + len(link_blocks)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vector Semantic Linker | Отчёт перелинковки {site_domain}</title>
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
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    header {{
      background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
      color: #ffffff;
      padding: 36px;
      border-radius: 16px;
      margin-bottom: 24px;
      box-shadow: 0 10px 25px -5px rgba(49, 46, 129, 0.3);
    }}
    header h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
    header p {{ color: #c7d2fe; font-size: 15px; max-width: 950px; line-height: 1.6; }}
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .stat-card .val {{ font-size: 28px; font-weight: 800; color: var(--primary); margin-bottom: 4px; }}
    .stat-card.success .val {{ color: var(--success); }}
    .stat-card.purple .val {{ color: var(--purple); }}
    .stat-card.amber .val {{ color: var(--amber); }}
    .stat-card .lbl {{ font-size: 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
    .nav-tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .nav-tab {{
      padding: 10px 18px;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      color: var(--muted);
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .nav-tab:hover, .nav-tab.active {{
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
    }}
    .section {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 28px;
      margin-bottom: 28px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    .section h2 {{ font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #1e1b4b; display: flex; align-items: center; gap: 8px; }}
    .section-desc {{ color: var(--muted); font-size: 14px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 12px 16px; border: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; font-weight: 600; color: #334155; }}
    tr:hover td {{ background: #fdfdfe; }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
    }}
    .badge-sim {{ background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }}
    .badge-high {{ background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
    .badge-purple {{ background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }}
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
      padding: 14px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      overflow-x: auto;
      margin-top: 8px;
      position: relative;
    }}
    .copy-btn {{
      position: absolute;
      top: 8px;
      right: 8px;
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
      <h1>🧬 Vector Semantic Linker v2.5 | {site_domain}</h1>
      <p>Многонаправленная семантическая перелинковка сайта: контекстные ссылки (Статья ➔ Каталог, Каталог ➔ Каталог, Каталог ➔ Статья), тематические кластеры и готовые HTML-блоки (виджеты) для CMS. Строгая гарантия уникальности: 1 предложение = не более 1 ссылки.</p>
    </header>

    <div class="stats-bar">
      <div class="stat-card">
        <div class="val">{len(articles)}</div>
        <div class="lbl">Статей блога</div>
      </div>
      <div class="stat-card">
        <div class="val">{len(categories)}</div>
        <div class="lbl">Категорий каталога</div>
      </div>
      <div class="stat-card">
        <div class="val">{len(art_to_cat_recs)}</div>
        <div class="lbl">Статья ➔ Каталог (в тексте)</div>
      </div>
      <div class="stat-card purple">
        <div class="val">{len(cat_to_cat_recs)}</div>
        <div class="lbl">Каталог ➔ Каталог (в тексте)</div>
      </div>
      <div class="stat-card amber">
        <div class="val">{len(link_blocks)}</div>
        <div class="lbl">HTML-блоков для CMS</div>
      </div>
      <div class="stat-card success">
        <div class="val">+{pr_lift:.1f}%</div>
        <div class="lbl">Расчетный рост PageRank</div>
      </div>
    </div>

    <!-- Раздел 1: Статья ➔ Каталог -->
    <div class="section" id="sec-art-cat">
      <h2>📝 1. Контекстная перелинковка: Статья блога ➔ Каталог</h2>
      <div class="rule-note">
        🛡 <strong>Гарантия v2.5:</strong> Строго 1 ссылка на 1 предложение. Анкоры выделены прямо из авторского текста без искажения синтаксиса.
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

    html += """
        </tbody>
      </table>
    </div>

    <!-- Раздел 2: Каталог ➔ Каталог -->
    <div class="section" id="sec-cat-cat">
      <h2>🛒 2. Контекстная перелинковка: Каталог ➔ Каталог (Кросс-линкинг)</h2>
      <div class="rule-note">
        🛡 <strong>Связка категорий:</strong> Алгоритм сканирует описания категорий и связывает сопутствующие товарные ветки через естественные анкоры.
      </div>
      <p class="section-desc">Кросс-категорийная перелинковка внутри каталога интернет-магазина. Повышает внутренний PageRank смежных разделов.</p>

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

    html += """
        </tbody>
      </table>
    </div>

    <!-- Раздел 3: Каталог ➔ Статья (E-E-A-T гиды) -->
    <div class="section" id="sec-cat-art">
      <h2>📚 3. Экспертные гиды: Каталог ➔ Статья (E-E-A-T)</h2>
      <p class="section-desc">Ссылки со страниц каталога на полезные статьи и гиды покупателя. Повышают авторитетность магазина и доверие пользователей.</p>

      <table>
        <thead>
          <tr>
            <th style="width: 30%;">Категория каталога</th>
            <th style="width: 35%;">Рекомендуемая статья / Гид</th>
            <th style="width: 15%;">Семантическое сходство</th>
            <th style="width: 20%;">Формат размещения</th>
          </tr>
        </thead>
        <tbody>
    """

    if not cat_to_art_recs:
        html += """<tr><td colspan="4" style="text-align: center; color: var(--muted); padding: 20px;">Не найдено гидов с превышением порога сходства</td></tr>"""
    else:
        for rec in cat_to_art_recs:
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
                <td><span class="badge badge-high">{rec['similarity']}%</span></td>
                <td><span style="font-size: 12px; color: var(--muted);">Блок «Гид покупателя» / Ссылка в описании</span></td>
              </tr>
            """

    html += """
        </tbody>
      </table>
    </div>

    <!-- Раздел 4: Тематические кластеры (Статья ➔ Статья) -->
    <div class="section" id="sec-art-art">
      <h2>🕸 4. Тематические кластеры блога (Статья ➔ Статья)</h2>
      <p class="section-desc">Связи между статьями с максимальным сходством (Topic Clusters). Формируют тематический авторитет (Topic Authority).</p>

      <table>
        <thead>
          <tr>
            <th style="width: 40%;">Статья А</th>
            <th style="width: 40%;">Статья Б</th>
            <th style="width: 20%;">Векторная близость</th>
          </tr>
        </thead>
        <tbody>
    """

    for rec in cluster_recs:
        html += f"""
          <tr>
            <td>
              <strong>{rec['source_title']}</strong><br>
              <span style="font-size: 11px; color: var(--muted);">{rec['source_url']}</span>
            </td>
            <td>
              <strong>{rec['target_title']}</strong><br>
              <span style="font-size: 11px; color: var(--muted);">{rec['target_url']}</span>
            </td>
            <td><span class="badge badge-sim">{rec['similarity']}% сходства</span></td>
          </tr>
        """

    html += """
        </tbody>
      </table>
    </div>

    <!-- Раздел 5: Готовые блоки перелинковки для CMS -->
    <div class="section" id="sec-blocks">
      <h2>📦 5. Готовые блоки перелинковки для CMS (HTML-виджеты)</h2>
      <p class="section-desc">Если у контент-менеджера нет возможности вручную вставлять ссылки в абзацы, используйте эти готовые адаптивные HTML-блоки для вставки в шаблон или в конец страниц.</p>

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
      Сгенерировано автоматически плагином Vector Semantic Linker v2.5 для Antigravity CLI · 2026
    </footer>
  </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def export_csv_report(all_recs, output_path):
    """
    Exports a comprehensive CSV file for copywriters, SEOs, and CMS operators.
    """
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'Тип перелинковки',
            'URL источника',
            'Заголовок источника',
            'Целевой URL',
            'Целевой заголовок',
            'Семантическая близость (%)',
            'Предложение-контекст',
            'Рекомендуемый анкор'
        ])
        for r in all_recs:
            writer.writerow([
                r.get('link_type', 'Статья -> Каталог'),
                r.get('source_url', ''),
                r.get('source_title', ''),
                r.get('target_url', ''),
                r.get('target_title', ''),
                r.get('similarity', 0.0),
                r.get('sentence_raw', ''),
                r.get('suggested_anchor', '')
            ])

def export_json_graph(nodes, edges, output_path):
    """
    Exports graph JSON for D3.js or graph visualization libraries.
    """
    data = {
        'nodes': [{'id': n['url'], 'title': n['title'], 'type': 'article' if n['is_article'] else 'category'} for n in nodes],
        'edges': [{'source': e['source_url'], 'target': e['target_url'], 'weight': e.get('similarity', 1.0), 'type': e.get('link_type', 'commercial')} for e in edges]
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
