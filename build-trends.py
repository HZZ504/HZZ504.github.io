#!/usr/bin/env python3
"""
AI Trends 构建脚本
将 ai-trends/ai-trends-YYYY-MM-DD.md 文件转换为:
1. ai-trends/YYYY-MM-DD.html  — 独立详情页
2. ai-trends/index.html       — 全部日报列表页
3. 更新 index.html 首页的 #trendsGrid 卡片（最近5篇）
"""

import os
import re
import glob
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
TRENDS_DIR = BASE_DIR / "ai-trends"
INDEX_HTML = BASE_DIR / "index.html"

# ─── Markdown → HTML 转换（轻量级，不依赖外部库）───────────────

def md_to_html(md_text):
    """简单 Markdown → HTML 转换"""
    lines = md_text.split('\n')
    html_lines = []
    in_table = False
    in_code = False
    in_ul = False

    for line in lines:
        # 代码块
        if line.strip().startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                html_lines.append('<pre><code>')
                in_code = True
            continue
        if in_code:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # 空行
        if not line.strip():
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            html_lines.append('')
            continue

        # 分隔线
        if line.strip() == '---':
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            html_lines.append('<hr>')
            continue

        # 表格分隔行（|---|---|）
        if re.match(r'^\s*\|[\s\-:|]+\|\s*$', line):
            continue

        # 表格
        if line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not in_table:
                in_table = True
                html_lines.append('<div class="table-wrap"><table><thead><tr>')
                for c in cells:
                    html_lines.append(f'<th>{inline_md(c)}</th>')
                html_lines.append('</tr></thead><tbody>')
            else:
                html_lines.append('<tr>')
                for c in cells:
                    html_lines.append(f'<td>{inline_md(c)}</td>')
                html_lines.append('</tr>')
            continue

        # 标题
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            level = len(m.group(1))
            text = inline_md(m.group(2))
            html_lines.append(f'<h{level}>{text}</h{level}>')
            continue

        # 列表
        m = re.match(r'^[-*]\s+(.+)$', line.strip())
        if m:
            if not in_ul:
                html_lines.append('<ul>')
                in_ul = True
            html_lines.append(f'<li>{inline_md(m.group(1))}</li>')
            continue

        # 普通段落
        if in_ul:
            html_lines.append('</ul>')
            in_ul = False
        html_lines.append(f'<p>{inline_md(line)}</p>')

    if in_ul:
        html_lines.append('</ul>')
    if in_table:
        html_lines.append('</tbody></table></div>')
    if in_code:
        html_lines.append('</code></pre>')

    return '\n'.join(html_lines)


def inline_md(text):
    """处理行内 Markdown：加粗、斜体、行内代码、链接、emoji"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code class="inline">\1</code>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


# ─── 解析日报文件 ──────────────────────────────────────────────

def parse_trends_file(filepath):
    """解析日报 md 文件，提取元信息"""
    text = filepath.read_text(encoding='utf-8')

    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filepath.name)
    date_str = date_match.group(1) if date_match else 'unknown'

    # 提取标题（第一行 #）
    title_match = re.match(r'^#\s+(.+)$', text, re.MULTILINE)
    title = title_match.group(1) if title_match else f'AI 动态日报 — {date_str}'

    # 提取所有 Level/章节标题
    sections = re.findall(r'^###?\s+(.+)$', text, re.MULTILINE)

    # 统计来源数
    sources = len(re.findall(r'来源[：:]', text))

    # 统计技巧数
    tips_count = len(re.findall(r'^\s*\|\s*\d+\s*\|', text, re.MULTILINE))

    # 统计 YouTube 视频数
    yt_count = len(re.findall(r'YouTube|视频标题', text))

    # 提取 tags（从 Level 标题提取关键词）
    tags = []
    for s in sections:
        if 'Skill' in s: tags.append('Skills')
        if '定时' in s or 'Schedule' in s: tags.append('Scheduled Tasks')
        if 'MCP' in s or 'Connector' in s: tags.append('MCP')
        if 'Hook' in s: tags.append('Hooks')
        if '子代理' in s or 'Sub-Agent' in s: tags.append('Sub-Agents')
        if 'CLAUDE.md' in s or '基础' in s: tags.append('CLAUDE.md')
        if '专家' in s or '工作流' in s: tags.append('Workflows')
    tags = list(dict.fromkeys(tags))[:5]  # dedupe, max 5

    if not tags:
        tags = ['Claude Code', 'Cowork']

    # 生成摘要（取趋势总结的第一段）
    summary_match = re.search(r'\*\*1\.\s*(.+?)\*\*\n(.+?)(?:\n\n|\n\*\*)', text, re.DOTALL)
    if summary_match:
        desc = summary_match.group(1) + ' — ' + summary_match.group(2).strip()
    else:
        desc = f'{date_str} Claude Code / Cowork 社区最新动态、高级用法和实战技巧汇总'

    # 限制描述长度
    if len(desc) > 100:
        desc = desc[:97] + '...'

    return {
        'date': date_str,
        'title': title,
        'desc': desc,
        'tags': tags,
        'tips_count': tips_count,
        'sources': sources,
        'yt_count': yt_count,
        'md_text': text,
        'filepath': filepath,
    }


# ─── 生成详情页 HTML ───────────────────────────────────────────

def generate_detail_page(info):
    """生成单篇日报详情页"""
    content_html = md_to_html(info['md_text'])
    date_str = info['date']
    title = info['title']

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | 张翰之</title>
<meta name="description" content="{info['desc']}">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0a0a0f;--bg2:#12121a;--bg3:#1a1a28;
  --text:#e0e0e8;--text-dim:#8888a0;--text-bright:#ffffff;
  --accent:#00d4aa;--accent2:#00a8ff;--accent3:#7c5cfc;
  --mono:'SF Mono','Fira Code','Cascadia Code',monospace;
  --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --max-w:900px;
}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.8;overflow-x:hidden}}
a{{color:var(--accent);text-decoration:none}}a:hover{{color:var(--accent2)}}
::selection{{background:var(--accent);color:var(--bg)}}
::-webkit-scrollbar{{width:6px}}::-webkit-scrollbar-track{{background:var(--bg)}}::-webkit-scrollbar-thumb{{background:var(--accent);border-radius:3px}}

body::before{{
  content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(0,212,170,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,170,.03) 1px,transparent 1px);
  background-size:60px 60px;pointer-events:none;z-index:0;
}}

.container{{max-width:var(--max-w);margin:0 auto;padding:0 24px;position:relative;z-index:1}}

/* Nav */
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(10,10,15,.85);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.05)}}
nav .inner{{max-width:var(--max-w);margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:60px}}
nav .logo{{font-family:var(--mono);font-weight:700;font-size:1.1rem;color:var(--text-bright);display:flex;align-items:center;gap:8px}}
nav .logo span{{color:var(--accent)}}
nav .logo svg{{width:28px;height:28px}}
nav .back{{font-size:.85rem;color:var(--text-dim);display:flex;align-items:center;gap:6px}}
nav .back:hover{{color:var(--accent)}}

/* Article */
article{{padding:100px 0 60px}}
.article-meta{{display:flex;align-items:center;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.article-date{{font-family:var(--mono);font-size:.8rem;color:var(--accent);padding:4px 12px;border:1px solid rgba(0,212,170,.3);border-radius:4px}}
.article-tag{{font-family:var(--mono);font-size:.65rem;color:var(--accent2);padding:2px 8px;background:rgba(0,168,255,.08);border:1px solid rgba(0,168,255,.15);border-radius:4px}}

article h1{{font-size:1.8rem;font-weight:700;color:var(--text-bright);margin-bottom:32px;line-height:1.3}}
article h2{{font-size:1.35rem;font-weight:600;color:var(--accent);margin:40px 0 16px;padding-bottom:8px;border-bottom:1px solid rgba(0,212,170,.15)}}
article h3{{font-size:1.1rem;font-weight:600;color:var(--accent2);margin:28px 0 12px}}
article h4{{font-size:.95rem;font-weight:600;color:var(--accent3);margin:20px 0 8px}}
article p{{margin-bottom:12px;color:var(--text)}}
article ul{{margin:0 0 16px 20px}}
article li{{margin-bottom:8px;color:var(--text)}}
article li strong{{color:var(--accent)}}
article hr{{border:none;border-top:1px solid rgba(255,255,255,.08);margin:32px 0}}
article code.inline{{font-family:var(--mono);font-size:.85em;background:rgba(0,212,170,.1);color:var(--accent);padding:2px 6px;border-radius:4px}}
article pre{{background:var(--bg2);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px;overflow-x:auto;margin:16px 0}}
article pre code{{font-family:var(--mono);font-size:.85rem;color:var(--text)}}

/* Tables */
.table-wrap{{overflow-x:auto;margin:16px 0}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th{{font-family:var(--mono);font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--accent);text-align:left;padding:10px 12px;border-bottom:2px solid rgba(0,212,170,.2);white-space:nowrap}}
td{{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.05);color:var(--text)}}
tr:hover td{{background:rgba(0,212,170,.03)}}

/* Footer */
.article-footer{{padding:40px 0;border-top:1px solid rgba(255,255,255,.06);margin-top:60px;text-align:center}}
.article-footer a{{font-family:var(--mono);font-size:.85rem}}
</style>
</head>
<body>
<nav>
  <div class="inner">
    <a href="../" class="logo"><svg viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="6" fill="url(#lg)"/><path d="M7 8h3v12H7V8zm4 5h6v3h-6v-3zm7-5h3v12h-3V8z" fill="#0a0a0f"/><defs><linearGradient id="lg" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#00d4aa"/><stop offset="1" stop-color="#00a8ff"/></linearGradient></defs></svg><span>&lt;</span>HZ<span>/&gt;</span></a>
    <a href="../#ai-trends" class="back"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/></svg> 返回日报列表</a>
  </div>
</nav>
<article>
  <div class="container">
    <div class="article-meta">
      <span class="article-date">{date_str}</span>
      {' '.join(f'<span class="article-tag">{t}</span>' for t in info['tags'])}
    </div>
    <h1>{title}</h1>
    {content_html}
  </div>
</article>
<div class="article-footer">
  <div class="container">
    <a href="../#ai-trends">← 返回首页</a>
  </div>
</div>
</body>
</html>'''


# ─── 生成列表页 ────────────────────────────────────────────────

def generate_list_page(all_info):
    """生成 ai-trends/index.html 全部日报列表"""
    cards_html = ''
    for info in all_info:
        tags_html = ''.join(f'<span class="t-tag">{t}</span>' for t in info['tags'])
        cards_html += f'''
    <a href="{info['date']}.html" class="t-card">
      <div class="t-card-head">
        <span class="t-date">{info['date']}</span>
        <div class="t-tags">{tags_html}</div>
      </div>
      <h3>{info['title']}</h3>
      <p>{info['desc']}</p>
      <div class="t-stats">
        <span>📋 {info['tips_count']} 技巧</span>
        <span>📺 {info['yt_count']} 视频</span>
        <span>📡 {info['sources']} 来源</span>
      </div>
    </a>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 动态日报 | 张翰之</title>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0a0a0f;--bg2:#12121a;--bg3:#1a1a28;
  --text:#e0e0e8;--text-dim:#8888a0;--text-bright:#ffffff;
  --accent:#00d4aa;--accent2:#00a8ff;--accent3:#7c5cfc;
  --mono:'SF Mono','Fira Code','Cascadia Code',monospace;
  --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --max-w:900px;
}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.7;overflow-x:hidden}}
a{{color:var(--accent);text-decoration:none}}a:hover{{color:var(--accent2)}}
::selection{{background:var(--accent);color:var(--bg)}}
::-webkit-scrollbar{{width:6px}}::-webkit-scrollbar-track{{background:var(--bg)}}::-webkit-scrollbar-thumb{{background:var(--accent);border-radius:3px}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,170,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,170,.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}}
.container{{max-width:var(--max-w);margin:0 auto;padding:0 24px;position:relative;z-index:1}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(10,10,15,.85);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.05)}}
nav .inner{{max-width:var(--max-w);margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:60px}}
nav .logo{{font-family:var(--mono);font-weight:700;font-size:1.1rem;color:var(--text-bright);display:flex;align-items:center;gap:8px}}
nav .logo span{{color:var(--accent)}}
nav .logo svg{{width:28px;height:28px}}
nav .back{{font-size:.85rem;color:var(--text-dim);display:flex;align-items:center;gap:6px}}
nav .back:hover{{color:var(--accent)}}

.page-header{{padding:100px 0 40px}}
.page-header h1{{font-size:2rem;font-weight:700;color:var(--text-bright);margin-bottom:8px}}
.page-header p{{color:var(--text-dim);font-size:.9rem}}
.live-badge{{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:.75rem;color:var(--accent);padding:4px 12px;border:1px solid rgba(0,212,170,.3);border-radius:20px;background:rgba(0,212,170,.06);margin-top:12px}}
.live-badge::before{{content:'';width:6px;height:6px;border-radius:50%;background:var(--accent);animation:pd 2s infinite}}
@keyframes pd{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}

.t-list{{display:flex;flex-direction:column;gap:16px;padding-bottom:80px}}
.t-card{{display:block;padding:24px;background:var(--bg2);border:1px solid rgba(255,255,255,.06);border-radius:12px;transition:all .3s;color:inherit}}
.t-card:hover{{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,212,170,.08)}}
.t-card-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}}
.t-date{{font-family:var(--mono);font-size:.75rem;color:var(--accent);padding:3px 8px;border:1px solid rgba(0,212,170,.25);border-radius:4px}}
.t-tags{{display:flex;flex-wrap:wrap;gap:4px}}
.t-tag{{font-family:var(--mono);font-size:.6rem;color:var(--accent2);padding:2px 6px;background:rgba(0,168,255,.08);border:1px solid rgba(0,168,255,.15);border-radius:3px}}
.t-card h3{{font-size:1rem;color:var(--text-bright);margin-bottom:6px}}
.t-card p{{font-size:.82rem;color:var(--text-dim)}}
.t-stats{{display:flex;gap:14px;margin-top:12px;font-family:var(--mono);font-size:.7rem;color:var(--text-dim)}}
</style>
</head>
<body>
<nav>
  <div class="inner">
    <a href="../" class="logo"><svg viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="6" fill="url(#lg)"/><path d="M7 8h3v12H7V8zm4 5h6v3h-6v-3zm7-5h3v12h-3V8z" fill="#0a0a0f"/><defs><linearGradient id="lg" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#00d4aa"/><stop offset="1" stop-color="#00a8ff"/></linearGradient></defs></svg><span>&lt;</span>HZ<span>/&gt;</span></a>
    <a href="../" class="back"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/></svg> 返回首页</a>
  </div>
</nav>
<div class="page-header">
  <div class="container">
    <h1>每日 AI 动态追踪</h1>
    <p>Claude Code / Cowork 社区高级用法、实战技巧与趋势分析</p>
    <span class="live-badge">由 Claude Cowork 自动生成</span>
  </div>
</div>
<div class="container">
  <div class="t-list">{cards_html}
  </div>
</div>
</body>
</html>'''


# ─── 更新首页 #trendsGrid ──────────────────────────────────────

def update_index_trends(all_info, max_cards=5):
    """更新首页 index.html 中 #trendsGrid 的内容"""
    index_text = INDEX_HTML.read_text(encoding='utf-8')

    cards = all_info[:max_cards]
    cards_html = ''
    for info in cards:
        tags_html = ''.join(f'<span class="trends-tag">{t}</span>' for t in info['tags'])
        cards_html += f'''
      <a href="ai-trends/{info['date']}.html" class="trends-card fade-up" style="text-decoration:none;color:inherit">
        <div class="trends-card-top">
          <div>
            <h3>{info['title']}</h3>
            <p class="trends-card-desc">{info['desc']}</p>
          </div>
          <span class="trends-card-date">{info['date']}</span>
        </div>
        <div class="trends-tags">{tags_html}</div>
        <div class="trends-stats">
          <span class="trends-stat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="ts-num">{info['tips_count']}</span> 技巧</span>
          <span class="trends-stat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg><span class="ts-num">{info['yt_count']}</span> 视频</span>
          <span class="trends-stat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg><span class="ts-num">{info['sources']}</span> 来源</span>
        </div>
      </a>'''

    # 替换 trendsGrid 内容
    pattern = r'(<div class="trends-grid" id="trendsGrid">).*?(</div>\s*<a href="ai-trends/")'
    replacement = f'\\1{cards_html}\n    \\2'
    new_text = re.sub(pattern, replacement, index_text, flags=re.DOTALL)

    INDEX_HTML.write_text(new_text, encoding='utf-8')
    print(f"  ✅ 首页更新: {len(cards)} 张卡片")


# ─── 主函数 ────────────────────────────────────────────────────

def main():
    print("🔄 构建 AI Trends 页面...\n")

    # 扫描所有 md 文件
    md_files = sorted(TRENDS_DIR.glob("ai-trends-*.md"), reverse=True)

    if not md_files:
        print("⚠️  没有找到 ai-trends-*.md 文件")
        return

    print(f"📄 找到 {len(md_files)} 篇日报\n")

    all_info = []
    for f in md_files:
        info = parse_trends_file(f)
        all_info.append(info)

        # 生成详情页
        detail_html = generate_detail_page(info)
        out_path = TRENDS_DIR / f"{info['date']}.html"
        out_path.write_text(detail_html, encoding='utf-8')
        print(f"  📝 {out_path.name} ({len(info['md_text'])} chars)")

    # 生成列表页
    list_html = generate_list_page(all_info)
    list_path = TRENDS_DIR / "index.html"
    list_path.write_text(list_html, encoding='utf-8')
    print(f"\n  📋 列表页: {list_path.name}")

    # 更新首页
    update_index_trends(all_info)

    print(f"\n✨ 构建完成! 共处理 {len(all_info)} 篇日报")


if __name__ == '__main__':
    main()
