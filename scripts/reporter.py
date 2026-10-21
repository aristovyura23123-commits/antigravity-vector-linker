"""
Report generators for Vector Semantic Linker: HTML visualizer, CSV export, and JSON graph.
"""

import csv
import json

def generate_html_report(site_domain, articles, categories, commercial_recs, cluster_recs, pr_lift, output_path):
    """
    Renders a standalone interactive HTML dashboard.
    """
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
    .container {{ max-width: 1240px; margin: 0 auto; }}
    header {{
      background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
      color: #ffffff;
      padding: 36px;
      border-radius: 16px;
      margin-bottom: 24px;
      box-shadow: 0 10px 25px -5px rgba(49, 46, 129, 0.3);
    }}
    header h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
    header p {{ color: #c7d2fe; font-size: 15px; max-width: 900px; }}
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .stat-card .val {{ font-size: 30px; font-weight: 800; color: var(--primary); margin-bottom: 4px; }}
    .stat-card.danger .val {{ color: var(--danger); }}
    .stat-card.success .val {{ color: var(--success); }}
    .stat-card .lbl {{ font-size: 13px; color: var(--muted); font-weight: 500; }}
    .section {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 28px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    .section h2 {{ font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #1e1b4b; }}
    .section-desc {{ color: var(--muted); font-size: 14px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 14px 16px; border: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; font-weight: 600; color: #334155; }}
    tr:hover td {{ background: #fdfdfe; }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
    }}
    .badge-sim {{ background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }}
    .badge-high {{ background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
    .context-box {{
      background: #f8fafc;
      border-left: 3px solid #6366f1;
      border-radius: 0 8px 8px 0;
      padding: 10px 14px;
      font-size: 13px;
      color: #334155;
      margin-top: 8px;
    }}
    .anchor-highlight {{
      background: #fef08a;
      color: #854d0e;
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 3px;
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
    footer {{
      text-align: center;
      font-size: 13px;
      color: var(--muted);
      padding: 24px 0;
    }}
  </style>
</head>
<body>

  <div class="container">
    <header>
      <h1>🧬 Vector Semantic Linker | {site_domain}</h1>
      <p>Векторный семантический граф перелинковки контентного блога с коммерческими страницами каталога на основе косинусного сходства (Cosine Similarity) и стемминга русской морфологии.</p>
    </header>

    <div class="stats-bar">
      <div class="stat-card">
        <div class="val">{len(articles)}</div>
        <div class="lbl">Статей блога в выборке</div>
      </div>
      <div class="stat-card">
        <div class="val">{len(categories)}</div>
        <div class="lbl">Целевых категорий каталога</div>
      </div>
      <div class="stat-card">
        <div class="val">{len(commercial_recs)}</div>
        <div class="lbl">Подобранных связей Статья ➔ Каталог</div>
      </div>
      <div class="stat-card success">
        <div class="val">+{pr_lift:.1f}%</div>
        <div class="lbl">Прирост PageRank категорий после внедрения</div>
      </div>
    </div>

    <div class="section">
      <h2>1. Рекомендации по перелинковке: Статья блога ➔ Коммерческий каталог</h2>
      <p class="section-desc">Алгоритм находит статьи с максимальной смысловой близостью к категории каталога, выбирает наиболее релевантное предложение в тексте статьи и выделил место для естественного внедрения анкора.</p>

      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Статья-донор (Блог)</th>
            <th style="width: 22%;">Категория-акцептор (Каталог)</th>
            <th style="width: 10%;">Семантическая близость</th>
            <th style="width: 43%;">Контекст в тексте статьи и рекомендуемый анкор</th>
          </tr>
        </thead>
        <tbody>
    """

    for rec in commercial_recs:
        badge_cls = "badge-high" if rec['similarity'] > 60 else "badge-sim"
        html += f"""
          <tr>
            <td>
              <strong>{rec['article_title']}</strong><br>
              <a href="{rec['article_url']}" target="_blank" style="font-size: 11px; color: var(--primary);">{rec['article_url']}</a>
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

    <div class="section">
      <h2>2. Семантические хабы блога (Статья ➔ Статья)</h2>
      <p class="section-desc">Связи между статьями с максимальным сходством (Topic Clusters). Перелинковка между ними формирует тематический авторитет (Topic Authority) для поисковых систем.</p>

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

    html += f"""
        </tbody>
      </table>
    </div>

    <footer>
      Сгенерировано автоматически плагином Vector Semantic Linker для Antigravity CLI · 2026
    </footer>
  </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def export_csv_report(commercial_recs, output_path):
    """
    Exports CSV file for copywriters and CMS operators.
    """
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Статья URL', 'Заголовок статьи', 'Каталог URL', 'Категория каталога', 'Семантическое сходство (%)', 'Предложение в статье', 'Рекомендуемый анкор'])
        for r in commercial_recs:
            writer.writerow([
                r['article_url'],
                r['article_title'],
                r['target_url'],
                r['target_title'],
                r['similarity'],
                r['sentence_raw'],
                r['suggested_anchor']
            ])

def export_json_graph(nodes, edges, output_path):
    """
    Exports graph JSON for D3.js or graph visualization libraries.
    """
    data = {
        'nodes': [{'id': n['url'], 'title': n['title'], 'type': 'article' if n['is_article'] else 'category'} for n in nodes],
        'edges': [{'source': e['source_url'], 'target': e['target_url'], 'weight': e['similarity']} for e in edges]
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
