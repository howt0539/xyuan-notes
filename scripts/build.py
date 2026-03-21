#!/usr/bin/env python3
"""
從 content/*.md 自動生成 index.html
usage: python3 scripts/build.py
"""

import os
import re
import glob
import json

CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'index.html')
TOPICS_FILE = os.path.join(CONTENT_DIR, 'topics.json')


def parse_frontmatter(text):
    """Parse YAML-like frontmatter between --- markers."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).strip().split('\n'):
        key, _, val = line.partition(':')
        val = val.strip().strip('"').strip("'")
        if val.isdigit():
            val = int(val)
        meta[key.strip()] = val
    return meta, text[match.end():]


def md_inline(text):
    """Convert inline markdown (bold, links, checkmarks) to HTML."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


def parse_topics(body):
    """Parse markdown body into topics."""
    topics = []
    current_topic = None
    current_subsection = None

    for line in body.split('\n'):
        line = line.rstrip()

        # Topic header: ## 1. ⭐ Title or ## 1. Title
        m = re.match(r'^## (\d+)\.\s*(⭐\s*)?(.+)$', line)
        if m:
            if current_topic:
                topics.append(current_topic)
            current_topic = {
                'number': m.group(1),
                'starred': bool(m.group(2)),
                'title': m.group(3).strip(),
                'subsections': [],
                'items': []
            }
            current_subsection = None
            continue

        # Subsection header: #### Title
        m = re.match(r'^#{3,4}\s+(.+)$', line)
        if m and current_topic is not None:
            current_subsection = {
                'title': m.group(1).strip(),
                'items': []
            }
            current_topic['subsections'].append(current_subsection)
            continue

        # List item (top level): - text
        m = re.match(r'^- (.+)$', line)
        if m and current_topic is not None:
            item = {'text': md_inline(m.group(1)), 'children': []}
            if current_subsection is not None:
                current_subsection['items'].append(item)
            else:
                current_topic['items'].append(item)
            continue

        # Nested list item:   - text
        m = re.match(r'^  - (.+)$', line)
        if m and current_topic is not None:
            child = {'text': md_inline(m.group(1)), 'children': []}
            # Add to last item in current context
            if current_subsection and current_subsection['items']:
                current_subsection['items'][-1]['children'].append(child)
            elif current_topic['items']:
                current_topic['items'][-1]['children'].append(child)
            continue

    if current_topic:
        topics.append(current_topic)

    return topics


def render_items(items, depth=0):
    """Render list items to HTML."""
    if not items:
        return ''
    html = '<ul>\n'
    for item in items:
        html += f'            <li>{item["text"]}'
        if item['children']:
            html += '\n              <ul>\n'
            for child in item['children']:
                html += f'                <li>{child["text"]}</li>\n'
            html += '              </ul>\n            '
        html += '</li>\n'
    html += '          </ul>'
    return html


def render_topic(topic, source_label=None):
    """Render a single topic card."""
    starred_class = ' starred' if topic['starred'] else ''
    star_badge = '<span class="star-badge">⭐ 重點</span>' if topic['starred'] else ''

    body_html = ''

    # If there are subsections, render them with h4 headers
    if topic['subsections']:
        # First render any top-level items
        if topic['items']:
            body_html += render_items(topic['items'])
        for sub in topic['subsections']:
            body_html += f'\n          <h4>{md_inline(sub["title"])}</h4>\n'
            body_html += render_items(sub['items'])
    else:
        body_html = render_items(topic['items'])

    source_html = ''
    if source_label:
        source_html = f'<span class="topic-source">{source_label}</span>'

    return f'''      <div class="topic-card{starred_class}">
        <div class="topic-header" onclick="toggle(this)">
          <span class="topic-number">{topic["number"]}</span>
          <span class="topic-title">{md_inline(topic["title"])}</span>
          {source_html}
          {star_badge}
          <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
        </div>
        <div class="topic-body">
          {body_html}
        </div>
      </div>'''


def render_livestream(meta, topics):
    """Render a full livestream section."""
    num = meta.get('number', '??')
    title = meta.get('title', '')
    duration = meta.get('duration', '?')
    ls_type = meta.get('type', '')

    cards = '\n\n'.join(render_topic(t) for t in topics)

    return f'''    <section class="livestream" id="live{num}">
      <div class="ls-header">
        <span class="ls-number">直播 {num}</span>
        <h2>{title}</h2>
        <div class="ls-meta">
          <span>⏱ 約 {duration} 分鐘</span>
          <span>💬 {ls_type}</span>
        </div>
      </div>

{cards}

    </section>'''


def render_category_sections(all_livestreams, topics_data):
    """Render topics grouped by category."""
    categories = topics_data['categories']
    icons = topics_data.get('category_icons', {})
    topic_map = topics_data['topics']

    # Collect topics per category
    cat_topics = {cat: [] for cat in categories}

    for meta, topics in all_livestreams:
        num = meta.get('number', '??')
        date_key = num  # e.g. "2025-11-24"
        mapping = topic_map.get(date_key, {})
        for topic in topics:
            cat = mapping.get(topic['number'], '裝備與其他')
            # Format short date for source label
            parts = date_key.split('-')
            short = f'{int(parts[1])}/{int(parts[2])}' if len(parts) >= 3 else date_key
            cat_topics[cat].append((topic, short))

    html_parts = []
    for cat in categories:
        items = cat_topics[cat]
        if not items:
            continue
        icon = icons.get(cat, '')
        count = len(items)
        cards = '\n\n'.join(
            render_topic(t, source_label=short) for t, short in items
        )
        cat_id = cat.replace(' ', '_')
        html_parts.append(f'''    <section class="category-section" id="cat-{cat_id}">
      <div class="cat-header">
        <span class="cat-icon">{icon}</span>
        <h2>{cat}</h2>
        <span class="cat-count">{count} 個主題</span>
      </div>

{cards}

    </section>''')

    return '\n\n'.join(html_parts)


def render_category_nav(topics_data):
    """Render category navigation buttons."""
    categories = topics_data['categories']
    icons = topics_data.get('category_icons', {})
    parts = []
    for i, cat in enumerate(categories):
        icon = icons.get(cat, '')
        active = ' active' if i == 0 else ''
        cat_id = cat.replace(' ', '_')
        # Short label for nav
        short_label = cat.replace('與', '/')
        parts.append(
            f'<button class="nav-btn cat-nav-btn{active}" '
            f'onclick="scrollToSection(\'cat-{cat_id}\')" '
            f'title="{cat}">{icon} {short_label}</button>'
        )
    return '\n      '.join(parts)


def build_search_data(all_livestreams, topics_data=None):
    """Build JSON search index."""
    topic_map = topics_data['topics'] if topics_data else {}
    data = []
    for meta, topics in all_livestreams:
        num = meta.get('number', '??')
        mapping = topic_map.get(num, {})
        for topic in topics:
            # Collect all text
            texts = [topic['title']]
            for item in topic['items']:
                texts.append(re.sub(r'<[^>]+>', '', item['text']))
                for child in item['children']:
                    texts.append(re.sub(r'<[^>]+>', '', child['text']))
            for sub in topic.get('subsections', []):
                texts.append(sub['title'])
                for item in sub['items']:
                    texts.append(re.sub(r'<[^>]+>', '', item['text']))
                    for child in item['children']:
                        texts.append(re.sub(r'<[^>]+>', '', child['text']))

            data.append({
                'live': num,
                'num': topic['number'],
                'title': topic['title'],
                'starred': topic['starred'],
                'cat': mapping.get(topic['number'], ''),
                'text': ' '.join(texts),
            })
    return json.dumps(data, ensure_ascii=False)


def generate_html(all_livestreams, topics_data):
    """Generate the complete HTML page."""
    # Date nav buttons
    nav_parts = []
    current_year = None
    for i, (meta, _) in enumerate(all_livestreams):
        num = meta.get('number', '')
        parts = num.split('-')
        year = parts[0] if len(parts) >= 3 else ''
        short_date = f'{int(parts[1])}/{int(parts[2])}' if len(parts) >= 3 else num
        if year != current_year:
            if current_year is not None:
                nav_parts.append('<span class="nav-divider"></span>')
            nav_parts.append(f'<span class="nav-year">{year}</span>')
            current_year = year
        active = ' active' if i == 0 else ''
        nav_parts.append(
            f'<button class="nav-btn date-nav-btn{active}" onclick="scrollToSection(\'live{num}\')" title="直播 {num}">'
            f'{short_date}</button>'
        )
    date_nav_buttons = '\n      '.join(nav_parts)

    # Category nav buttons
    cat_nav_buttons = render_category_nav(topics_data)

    # Date view sections
    date_sections = '\n\n'.join(
        render_livestream(meta, topics)
        for meta, topics in all_livestreams
    )

    # Category view sections
    cat_sections = render_category_sections(all_livestreams, topics_data)

    # Search data
    search_data = build_search_data(all_livestreams, topics_data)

    total = len(all_livestreams)

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>瘋狗 教練直播筆記｜Mouthfill 自由潛水</title>
  <meta name="description" content="瘋狗教練（陳志璿）Mouthfill 自由潛水直播 QA 精華整理">
  <meta property="og:title" content="瘋狗 教練直播筆記｜Mouthfill 自由潛水">
  <meta property="og:description" content="陳志璿教練 Mouthfill 直播 QA 精華整理，含逐字稿摘要與主題索引">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface-hover: #222636;
      --card: #1e2230;
      --border: rgba(255,255,255,0.06);
      --text: #e8e8ed;
      --text-secondary: #9ca3b0;
      --accent: #6c8cff;
      --accent-soft: rgba(108,140,255,0.12);
      --accent-glow: rgba(108,140,255,0.25);
      --star: #fbbf24;
      --tag-bg: rgba(108,140,255,0.1);
      --tag-text: #8aa4ff;
      --green: #34d399;
      --green-bg: rgba(52,211,153,0.1);
      --radius: 16px;
      --radius-sm: 10px;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.75;
      -webkit-font-smoothing: antialiased;
    }}

    .hero {{
      position: relative;
      padding: 80px 24px 60px;
      text-align: center;
      overflow: hidden;
      background: linear-gradient(160deg, #151828 0%, #0f1117 50%, #141825 100%);
    }}
    .hero::before {{
      content: '';
      position: absolute;
      top: -120px; left: 50%; transform: translateX(-50%);
      width: 600px; height: 600px;
      background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
      opacity: 0.4;
      pointer-events: none;
    }}
    .hero h1 {{
      font-size: clamp(1.8rem, 5vw, 2.8rem);
      font-weight: 900;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
      position: relative;
    }}
    .hero h1 .accent {{ color: var(--accent); }}
    .hero .subtitle {{
      font-size: 1.05rem;
      color: var(--text-secondary);
      font-weight: 300;
      margin-bottom: 20px;
      position: relative;
    }}
    .hero .meta-badges {{
      display: flex;
      gap: 10px;
      justify-content: center;
      flex-wrap: wrap;
      position: relative;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 999px;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }}
    .badge a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .badge a:hover {{ text-decoration: underline; }}

    .container {{
      max-width: 820px;
      margin: 0 auto;
      padding: 0 20px;
    }}

    /* Search */
    .search-wrap {{
      padding: 0 20px;
      max-width: 820px;
      margin: -20px auto 0;
      position: relative;
      z-index: 50;
    }}
    .search-box {{
      width: 100%;
      padding: 12px 16px 12px 44px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      color: var(--text);
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-box::placeholder {{ color: var(--text-secondary); opacity: 0.6; }}
    .search-box:focus {{ border-color: var(--accent); }}
    .search-icon {{
      position: absolute;
      left: 34px;
      top: 50%;
      transform: translateY(-50%);
      width: 18px; height: 18px;
      color: var(--text-secondary);
      pointer-events: none;
    }}
    .search-results-info {{
      text-align: center;
      padding: 8px;
      font-size: 0.85rem;
      color: var(--text-secondary);
      display: none;
    }}

    /* View Toggle */
    .view-toggle {{
      display: flex;
      justify-content: center;
      gap: 4px;
      margin-top: 16px;
      padding: 0 20px;
    }}
    .view-toggle-btn {{
      padding: 8px 20px;
      font-size: 0.85rem;
      font-weight: 600;
      font-family: inherit;
      color: var(--text-secondary);
      background: var(--surface);
      border: 1px solid var(--border);
      cursor: pointer;
      transition: all 0.2s;
    }}
    .view-toggle-btn:first-child {{
      border-radius: 999px 0 0 999px;
    }}
    .view-toggle-btn:last-child {{
      border-radius: 0 999px 999px 0;
    }}
    .view-toggle-btn.active {{
      color: var(--accent);
      background: var(--accent-soft);
      border-color: rgba(108,140,255,0.3);
    }}

    /* Nav */
    .section-nav {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(15,17,23,0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      padding: 0 20px;
      margin-top: 8px;
    }}
    .section-nav .nav-inner {{
      max-width: 820px;
      margin: 0 auto;
      display: flex;
      gap: 0;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .section-nav .nav-inner::-webkit-scrollbar {{ display: none; }}
    .nav-year {{
      padding: 14px 8px 14px 4px;
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--text-secondary);
      opacity: 0.5;
      letter-spacing: 0.05em;
      white-space: nowrap;
      align-self: center;
    }}
    .nav-divider {{
      width: 1px;
      background: var(--border);
      margin: 10px 4px;
      flex-shrink: 0;
    }}
    .nav-btn {{
      padding: 14px 14px;
      font-size: 0.9rem;
      font-weight: 500;
      color: var(--text-secondary);
      background: none;
      border: none;
      cursor: pointer;
      white-space: nowrap;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }}
    .nav-btn:hover, .nav-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}
    .cat-nav-btn {{
      font-size: 0.8rem;
      padding: 10px 12px;
    }}
    #catNav .nav-inner {{
      flex-wrap: wrap;
      justify-content: center;
      gap: 0;
      padding: 6px 0;
    }}

    /* Livestream */
    .livestream {{
      padding: 48px 0;
    }}
    .livestream + .livestream {{
      border-top: 1px solid var(--border);
    }}
    .ls-header {{
      margin-bottom: 32px;
    }}
    .ls-number {{
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--accent);
      background: var(--accent-soft);
      padding: 4px 12px;
      border-radius: 999px;
      margin-bottom: 12px;
    }}
    .ls-header h2 {{
      font-size: clamp(1.3rem, 3.5vw, 1.7rem);
      font-weight: 700;
      line-height: 1.4;
      margin-bottom: 12px;
    }}
    .ls-meta {{
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }}
    .ls-meta span {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    /* Category Sections */
    .category-section {{
      padding: 48px 0;
    }}
    .category-section + .category-section {{
      border-top: 1px solid var(--border);
    }}
    .cat-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 32px;
    }}
    .cat-icon {{
      font-size: 1.8rem;
    }}
    .cat-header h2 {{
      font-size: clamp(1.3rem, 3.5vw, 1.7rem);
      font-weight: 700;
      line-height: 1.4;
    }}
    .cat-count {{
      font-size: 0.8rem;
      color: var(--text-secondary);
      background: var(--surface);
      padding: 4px 10px;
      border-radius: 999px;
    }}

    /* Topic source label (shown in category view) */
    .topic-source {{
      flex-shrink: 0;
      font-size: 0.7rem;
      color: var(--text-secondary);
      background: var(--surface);
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 500;
    }}

    /* Topic Cards */
    .topic-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: 16px;
      overflow: hidden;
      transition: border-color 0.2s;
    }}
    .topic-card:hover {{
      border-color: rgba(108,140,255,0.15);
    }}
    .topic-card.starred {{
      border-color: rgba(251,191,36,0.2);
    }}
    .topic-card.starred .topic-header {{
      background: rgba(251,191,36,0.04);
    }}
    .topic-card.search-hidden {{
      display: none;
    }}

    .topic-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }}
    .topic-header:hover {{
      background: var(--surface-hover);
    }}
    .topic-number {{
      flex-shrink: 0;
      width: 30px; height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
    }}
    .topic-card.starred .topic-number {{
      background: rgba(251,191,36,0.12);
      color: var(--star);
    }}
    .topic-title {{
      flex: 1;
      font-size: 1rem;
      font-weight: 600;
    }}
    .star-badge {{
      font-size: 0.7rem;
      color: var(--star);
      background: rgba(251,191,36,0.1);
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 600;
    }}
    .chevron {{
      flex-shrink: 0;
      width: 20px; height: 20px;
      color: var(--text-secondary);
      transition: transform 0.25s;
    }}
    .topic-card.open .chevron {{
      transform: rotate(180deg);
    }}

    .topic-body {{
      display: none;
      padding: 0 20px 20px 62px;
    }}
    .topic-card.open .topic-body {{
      display: block;
    }}
    .topic-body ul {{
      list-style: none;
      padding: 0;
    }}
    .topic-body li {{
      position: relative;
      padding: 4px 0 4px 16px;
      font-size: 0.92rem;
      color: var(--text);
      line-height: 1.7;
    }}
    .topic-body li::before {{
      content: '';
      position: absolute;
      left: 0; top: 13px;
      width: 5px; height: 5px;
      background: var(--accent);
      border-radius: 50%;
      opacity: 0.5;
    }}
    .topic-body li ul {{ margin-top: 2px; }}
    .topic-body li li {{
      padding-left: 16px;
      font-size: 0.87rem;
      color: var(--text-secondary);
    }}
    .topic-body li li::before {{
      width: 4px; height: 4px;
      background: var(--text-secondary);
      opacity: 0.3;
    }}
    .topic-body strong {{
      color: #fff;
      font-weight: 600;
    }}
    .topic-body h4 {{
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--accent);
      margin: 12px 0 6px;
    }}
    .topic-body h4:first-child {{ margin-top: 0; }}
    .topic-body a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .topic-body a:hover {{ text-decoration: underline; }}

    footer {{
      text-align: center;
      padding: 40px 20px;
      border-top: 1px solid var(--border);
      color: var(--text-secondary);
      font-size: 0.8rem;
    }}
    footer a {{
      color: var(--accent);
      text-decoration: none;
    }}

    @media (max-width: 600px) {{
      .hero {{ padding: 60px 20px 40px; }}
      .topic-body {{ padding-left: 20px; }}
      .topic-header {{ padding: 14px 16px; }}
      .nav-btn {{ padding: 12px 14px; font-size: 0.85rem; }}
      .cat-nav-btn {{ font-size: 0.75rem; padding: 12px 8px; }}
    }}

    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 3px; }}

    .topic-card {{ animation: fadeUp 0.4s ease both; }}
    .topic-card:nth-child(2) {{ animation-delay: 0.05s; }}
    .topic-card:nth-child(3) {{ animation-delay: 0.1s; }}
    .topic-card:nth-child(4) {{ animation-delay: 0.15s; }}
    .topic-card:nth-child(5) {{ animation-delay: 0.2s; }}
    .topic-card:nth-child(6) {{ animation-delay: 0.25s; }}
    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    mark {{
      background: rgba(108,140,255,0.25);
      color: inherit;
      padding: 1px 2px;
      border-radius: 3px;
    }}

    /* Hidden view */
    .view-hidden {{ display: none !important; }}
  </style>
</head>
<body>

  <header class="hero">
    <h1>🤿 <span class="accent">瘋狗</span> 教練直播筆記</h1>
    <p class="subtitle">陳志璿｜Mouthfill 自由潛水 QA 精華整理</p>
    <div class="meta-badges">
      <span class="badge">🎙️ {total} 場直播</span>
      <span class="badge">📷 <a href="https://www.instagram.com/xyuannnnn" target="_blank">@xyuannnnn</a></span>
      <span class="badge">✏️ 整理：<a href="https://www.instagram.com/howt0539" target="_blank">@howt0539</a></span>
    </div>
  </header>

  <!-- Search -->
  <div class="search-wrap">
    <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
    <input type="text" class="search-box" placeholder="搜尋主題、關鍵字..." oninput="doSearch(this.value)">
  </div>
  <div class="search-results-info" id="searchInfo"></div>

  <!-- View Toggle -->
  <div class="view-toggle">
    <button class="view-toggle-btn active" onclick="switchView('date')">📅 按日期</button>
    <button class="view-toggle-btn" onclick="switchView('topic')">📂 按主題</button>
  </div>

  <!-- Date Nav -->
  <nav class="section-nav" id="dateNav">
    <div class="nav-inner">
      {date_nav_buttons}
    </div>
  </nav>

  <!-- Category Nav -->
  <nav class="section-nav view-hidden" id="catNav">
    <div class="nav-inner">
      {cat_nav_buttons}
    </div>
  </nav>

  <!-- Date View -->
  <main class="container" id="dateView">

{date_sections}

  </main>

  <!-- Category View -->
  <main class="container view-hidden" id="catView">

{cat_sections}

  </main>

  <footer>
    <p>內容來源：<a href="https://www.instagram.com/xyuannnnn" target="_blank">@xyuannnnn</a> IG 直播 ｜ 整理：<a href="https://www.instagram.com/howt0539" target="_blank">@howt0539</a></p>
  </footer>

  <script>
    // Toggle card
    function toggle(header) {{
      header.parentElement.classList.toggle('open');
    }}

    // Scroll to section
    function scrollToSection(id) {{
      document.getElementById(id).scrollIntoView({{ behavior: 'smooth' }});
      // Update active nav btn
      const activeView = document.getElementById('dateView').classList.contains('view-hidden') ? 'cat' : 'date';
      const navClass = activeView === 'date' ? '.date-nav-btn' : '.cat-nav-btn';
      document.querySelectorAll(navClass).forEach(b => b.classList.remove('active'));
      if (event && event.target) event.target.classList.add('active');
    }}

    // View switching
    let currentView = 'date';
    function switchView(view) {{
      if (view === currentView) return;
      currentView = view;

      const dateView = document.getElementById('dateView');
      const catView = document.getElementById('catView');
      const dateNav = document.getElementById('dateNav');
      const catNav = document.getElementById('catNav');
      const toggleBtns = document.querySelectorAll('.view-toggle-btn');

      if (view === 'date') {{
        dateView.classList.remove('view-hidden');
        catView.classList.add('view-hidden');
        dateNav.classList.remove('view-hidden');
        catNav.classList.add('view-hidden');
        toggleBtns[0].classList.add('active');
        toggleBtns[1].classList.remove('active');
      }} else {{
        dateView.classList.add('view-hidden');
        catView.classList.remove('view-hidden');
        dateNav.classList.add('view-hidden');
        catNav.classList.remove('view-hidden');
        toggleBtns[0].classList.remove('active');
        toggleBtns[1].classList.add('active');
      }}

      // Clear search
      document.querySelector('.search-box').value = '';
      doSearch('');
      window.scrollTo({{ top: 0 }});
    }}

    // Search
    const searchData = {search_data};

    function doSearch(query) {{
      const info = document.getElementById('searchInfo');

      if (!query.trim()) {{
        // Show all cards in both views
        document.querySelectorAll('.topic-card').forEach(c => c.classList.remove('search-hidden'));
        document.querySelectorAll('.livestream, .category-section').forEach(s => s.style.display = '');
        info.style.display = 'none';
        return;
      }}

      const q = query.toLowerCase();
      let count = 0;

      // Hide all cards first
      document.querySelectorAll('.topic-card').forEach(c => c.classList.add('search-hidden'));

      // Date view search
      searchData.forEach((item) => {{
        if (item.text.toLowerCase().includes(q) || item.title.toLowerCase().includes(q)) {{
          count++;
          // Show in date view
          const section = document.getElementById('live' + item.live);
          if (section) {{
            const cards = section.querySelectorAll('.topic-card');
            const card = cards[parseInt(item.num) - 1];
            if (card) card.classList.remove('search-hidden');
          }}
          // Show in category view
          if (item.cat) {{
            const catId = 'cat-' + item.cat.replace(/ /g, '_');
            const catSection = document.getElementById(catId);
            if (catSection) {{
              const catCards = catSection.querySelectorAll('.topic-card');
              catCards.forEach(cc => {{
                const title = cc.querySelector('.topic-title');
                if (title && title.textContent.trim() === item.title) {{
                  cc.classList.remove('search-hidden');
                }}
              }});
            }}
          }}
        }}
      }});

      // Hide empty sections
      document.querySelectorAll('.livestream').forEach(s => {{
        const visible = s.querySelectorAll('.topic-card:not(.search-hidden)');
        s.style.display = visible.length ? '' : 'none';
      }});
      document.querySelectorAll('.category-section').forEach(s => {{
        const visible = s.querySelectorAll('.topic-card:not(.search-hidden)');
        s.style.display = visible.length ? '' : 'none';
      }});

      info.textContent = `找到 ${{count}} 個相關主題`;
      info.style.display = 'block';
    }}

    // Update nav on scroll
    function updateScrollNav() {{
      if (currentView === 'date') {{
        const sections = document.querySelectorAll('.livestream');
        const navBtns = document.querySelectorAll('.date-nav-btn');
        const navInner = document.querySelector('#dateNav .nav-inner');
        let current = '';
        sections.forEach(section => {{
          const top = section.offsetTop - 80;
          if (scrollY >= top) current = section.id;
        }});
        navBtns.forEach(btn => {{
          btn.classList.remove('active');
          const onclick = btn.getAttribute('onclick') || '';
          if (onclick.includes(current) && current) {{
            btn.classList.add('active');
            const navRect = navInner.getBoundingClientRect();
            const btnRect = btn.getBoundingClientRect();
            if (btnRect.left < navRect.left || btnRect.right > navRect.right) {{
              btn.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
            }}
          }}
        }});
      }} else {{
        const sections = document.querySelectorAll('.category-section');
        const navBtns = document.querySelectorAll('.cat-nav-btn');
        const navInner = document.querySelector('#catNav .nav-inner');
        let current = '';
        sections.forEach(section => {{
          const top = section.offsetTop - 80;
          if (scrollY >= top) current = section.id;
        }});
        navBtns.forEach(btn => {{
          btn.classList.remove('active');
          const onclick = btn.getAttribute('onclick') || '';
          if (onclick.includes(current) && current) {{
            btn.classList.add('active');
            const navRect = navInner.getBoundingClientRect();
            const btnRect = btn.getBoundingClientRect();
            if (btnRect.left < navRect.left || btnRect.right > navRect.right) {{
              btn.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
            }}
          }}
        }});
      }}
    }}
    window.addEventListener('scroll', updateScrollNav);
  </script>

</body>
</html>'''


def main():
    # Find all content files
    md_files = sorted(glob.glob(os.path.join(CONTENT_DIR, 'live*.md')))

    if not md_files:
        print('❌ 沒有找到 content/live*.md 檔案')
        return

    # Load topics data
    topics_data = None
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, 'r') as fh:
            topics_data = json.load(fh)
        print(f'📂 載入主題分類：{len(topics_data["categories"])} 個分類')
    else:
        print('⚠️  找不到 topics.json，將不產生主題視角')
        topics_data = {'categories': [], 'category_icons': {}, 'topics': {}}

    all_livestreams = []
    for f in md_files:
        with open(f, 'r') as fh:
            text = fh.read()
        meta, body = parse_frontmatter(text)
        topics = parse_topics(body)
        all_livestreams.append((meta, topics))
        print(f'📄 {os.path.basename(f)}: {len(topics)} 個主題')

    html = generate_html(all_livestreams, topics_data)

    with open(OUTPUT_FILE, 'w') as fh:
        fh.write(html)

    print(f'\n✅ 已生成 {OUTPUT_FILE}')
    print(f'   共 {len(all_livestreams)} 場直播')


if __name__ == '__main__':
    main()
