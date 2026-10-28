#!/usr/bin/env python3
"""Build the hix tools writing site into docs/ for GitHub Pages."""

from __future__ import annotations

import html
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
SITE_URL = "https://hix-pro.github.io/blog"
SITE_TITLE = "hix tools — writing"
SITE_DESCRIPTION = (
    "Seven practical deep dives into the checks that normally depend on "
    "someone remembering: env drift, dangerous migrations, contract breaks, "
    "workflow risk, Compose red flags, agent remote control, and star velocity "
    "— plus the hix runner that ties the CLI tools together."
)
PUBLISHED = datetime(2026, 10, 28, tzinfo=timezone.utc)

# Reading order for the site: browser tools first, then the CLIs.
ORDER = ["04", "05", "01", "02", "03", "07", "06"]

TOOLS = {
    "01": ("EnvAudit", "#3fb950"),
    "02": ("Migration Guard", "#d29922"),
    "03": ("API Watch", "#f0883e"),
    "04": ("ActionLens", "#58a6ff"),
    "05": ("ComposeMap", "#39c5cf"),
    "06": ("OpenCode Telegram", "#2aabee"),
    "07": ("RepoRace", "#bc8cff"),
}

COVERS = {
    "01": "01-envaudit.png",
    "02": "02-migration-guard.png",
    "03": "03-api-watch.png",
    "04": "04-actionlens.png",
    "05": "05-composemap.png",
    "06": "06-opencode-telegram.png",
    "07": "07-reporace.png",
}

MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'


def parse_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path.name}: missing front matter")
    meta = yaml.safe_load(match.group(1))
    body = match.group(2).strip()
    prefix = path.name[:2]
    tool, accent = TOOLS[prefix]
    tags = [tag.strip() for tag in str(meta.get("tags", "")).split(",") if tag.strip()]
    words = len(re.findall(r"\w+", re.sub(r"```.*?```", "", body, flags=re.DOTALL)))
    return {
        "file": path.name,
        "slug": path.stem,
        "title": meta["title"],
        "description": meta["description"],
        "tags": tags,
        "tool": tool,
        "accent": accent,
        "cover": COVERS[prefix],
        "body": body,
        "minutes": max(1, math.ceil(words / 200)),
        "words": words,
    }


def render_markdown(body: str) -> str:
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "codehilite", "sane_lists"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False}
        },
    )
    return md.convert(body)


def page(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    prefix: str,
    og_image: str,
    og_type: str = "website",
) -> str:
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <meta name="description" content="{safe_description}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{prefix}assets/style.css">
  <link rel="alternate" type="application/rss+xml" title="{SITE_TITLE}" href="{prefix}feed.xml">
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{SITE_TITLE}">
  <meta property="og:title" content="{safe_title}">
  <meta property="og:description" content="{safe_description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{og_image}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{safe_title}">
  <meta name="twitter:description" content="{safe_description}">
  <meta name="twitter:image" content="{og_image}">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header">
    <a class="brand" href="{prefix}index.html"><span class="prompt">&gt;_</span> hix tools</a>
    <nav aria-label="Site">
      <a href="{prefix}index.html">Writing</a>
      <a href="https://github.com/hix-pro">Tools</a>
      <a href="https://github.com/hix-pro/hix">hix</a>
      <a href="https://github.com/hix-pro/blog">GitHub</a>
      <a href="{prefix}feed.xml">RSS</a>
    </nav>
  </header>
  {body}
  <footer class="site-footer">
    <p><strong>hix tools</strong> — local-first developer tools that catch what CI misses.</p>
    <p><a href="https://github.com/hix-pro">GitHub</a> · <a href="https://github.com/topics/hix-tools">All tools</a> · <a href="https://github.com/hix-pro/blog">Source</a> · <a href="{prefix}feed.xml">RSS</a></p>
  </footer>
</body>
</html>
"""


def card(post: dict, prefix: str, featured: bool = False) -> str:
    cover = f"{prefix}covers/{post['cover']}"
    classes = "card featured" if featured else "card"
    loading = "eager" if featured else "lazy"
    return f"""<a class="{classes}" href="{prefix}posts/{post["slug"]}.html" style="--accent: {post["accent"]}">
  <div class="card-cover"><img src="{cover}" alt="Cover for {html.escape(post["title"])}" loading="{loading}" width="2400" height="1260"></div>
  <div class="card-body">
    <p class="card-kicker">{html.escape(post["tool"])}</p>
    <h3>{html.escape(post["title"])}</h3>
    <p>{html.escape(post["description"])}</p>
    <p class="card-meta">{post["minutes"]} min read · {html.escape(", ".join(post["tags"]))}</p>
  </div>
</a>"""


def build_index(posts: list[dict]) -> str:
    featured = posts[0]
    rest = posts[1:]
    og = f"{SITE_URL}/covers/{featured['cover']}"
    body = f"""<main id="main">
  <section class="hero">
    <p class="eyebrow">Writing</p>
    <h1>Notes on what CI misses.</h1>
    <p class="lede">{SITE_DESCRIPTION} Every tool is local-first, and every post ends with what it will not do.</p>
    <div class="hero-actions">
      <a class="button" href="#series">Read the series</a>
      <a class="button ghost" href="https://hix-pro.github.io/action-lens/">Try ActionLens</a>
    </div>
  </section>

  <section id="series" aria-labelledby="series-title">
    <div class="section-head">
      <h2 id="series-title">The series</h2>
      <span>7 posts · 2026</span>
    </div>
    <div class="grid">
      {card(featured, "", featured=True)}
      {"".join(card(post, "") for post in rest)}
    </div>
  </section>
</main>
"""
    return page(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        canonical=f"{SITE_URL}/",
        body=body,
        prefix="",
        og_image=og,
    )


def build_post(post: dict, previous: dict | None, following: dict | None) -> str:
    article = render_markdown(post["body"])
    canonical = f"{SITE_URL}/posts/{post['slug']}.html"
    nav = []
    if previous:
        nav.append(
            f'<a href="{previous["slug"]}.html"><span class="label">Previous</span>{html.escape(previous["title"])}</a>'
        )
    if following:
        nav.append(
            f'<a class="next" href="{following["slug"]}.html"><span class="label">Next</span>{html.escape(following["title"])}</a>'
        )
    nav_html = (
        f'<nav class="post-nav" aria-label="Posts">{"".join(nav)}</nav>' if nav else ""
    )
    body = f"""<main id="main" class="post">
  <a class="back" href="../index.html">← All writing</a>
  <div class="post-cover" style="--accent: {post["accent"]}">
    <img src="../covers/{post["cover"]}" alt="Cover for {html.escape(post["title"])}" width="2400" height="1260">
  </div>
  <header class="post-header">
    <p class="eyebrow">{html.escape(post["tool"])} · hix tools</p>
    <h1>{html.escape(post["title"])}</h1>
    <p class="lede">{html.escape(post["description"])}</p>
    <p class="post-meta">{post["minutes"]} min read · {html.escape(", ".join(post["tags"]))}</p>
  </header>
  <article class="prose">
    {article}
  </article>
  {nav_html}
</main>
"""
    return page(
        title=f"{post['title']} — {SITE_TITLE}",
        description=post["description"],
        canonical=canonical,
        body=body,
        prefix="../",
        og_image=f"{SITE_URL}/covers/{post['cover']}",
        og_type="article",
    )


def build_feed(posts: list[dict]) -> str:
    items = []
    for post in posts:
        link = f"{SITE_URL}/posts/{post['slug']}.html"
        items.append(
            f"""    <item>
      <title>{html.escape(post["title"])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{html.escape(post["description"])}</description>
      <category>{html.escape(post["tool"])}</category>
      <pubDate>{PUBLISHED.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_TITLE}</title>
    <link>{SITE_URL}/</link>
    <description>{html.escape(SITE_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>{PUBLISHED.strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""


def build_sitemap(posts: list[dict]) -> str:
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/posts/{p['slug']}.html" for p in posts]
    body = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>2026-10-28</lastmod></url>" for url in urls
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def build_404() -> str:
    body = """<main id="main" class="not-found">
  <p class="eyebrow">404</p>
  <h1>That page isn't here.</h1>
  <p class="lede">The writing is still at the index, and the tools are on GitHub.</p>
  <div class="hero-actions">
    <a class="button" href="./index.html">All writing</a>
    <a class="button ghost" href="https://github.com/hix-pro">Tools</a>
  </div>
</main>
"""
    return page(
        title=f"Not found — {SITE_TITLE}",
        description="Page not found.",
        canonical=f"{SITE_URL}/404.html",
        body=body,
        prefix="",
        og_image=f"{SITE_URL}/covers/04-actionlens.png",
    )


def build_css() -> str:
    pygments = HtmlFormatter(style="github-dark").get_style_defs(".highlight")
    return f"""/* hix tools writing — generated by scripts/build_site.py */
:root {{
  --bg: #0d1117;
  --bg-soft: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #3fb950;
  --radius: 12px;
  --max: 1080px;
  --mono: {MONO};
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 17px/1.7 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(700px 320px at 12% -8%, rgba(63,185,80,.10), transparent 70%),
    radial-gradient(600px 280px at 88% -6%, rgba(88,166,255,.07), transparent 70%);
}}
a {{ color: var(--green); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
:focus-visible {{ outline: 2px solid var(--green); outline-offset: 3px; }}
.skip {{
  position: absolute; left: -999px; top: 12px; z-index: 10;
  background: var(--green); color: #0d1117; padding: 8px 14px; border-radius: 6px;
}}
.skip:focus {{ left: 12px; }}
.site-header {{
  max-width: var(--max);
  margin: 0 auto;
  padding: 26px 24px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}
.brand {{
  font-family: var(--mono);
  font-weight: 700;
  font-size: 16px;
  color: var(--text);
  letter-spacing: -0.02em;
}}
.brand:hover {{ text-decoration: none; }}
.brand .prompt {{ color: var(--green); margin-right: 6px; }}
nav {{ display: flex; gap: 20px; flex-wrap: wrap; }}
nav a {{ color: var(--muted); font-size: 14px; }}
nav a:hover {{ color: var(--text); text-decoration: none; }}
main {{
  position: relative;
  max-width: var(--max);
  margin: 0 auto;
  padding: 48px 24px 88px;
}}
.hero {{
  padding: 44px 0 44px;
  border-bottom: 1px solid var(--border);
}}
.eyebrow {{
  margin: 0;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--green);
}}
h1 {{
  margin: 14px 0 18px;
  font-size: clamp(38px, 6vw, 64px);
  line-height: 1.05;
  letter-spacing: -0.035em;
  max-width: 820px;
}}
.lede {{
  margin: 0;
  max-width: 740px;
  color: var(--muted);
  font-size: 19px;
  line-height: 1.65;
}}
.hero-actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }}
.button {{
  display: inline-block;
  padding: 10px 18px;
  border-radius: 8px;
  background: var(--green);
  color: #07110a;
  font-size: 14px;
  font-weight: 700;
}}
.button:hover {{ text-decoration: none; filter: brightness(1.08); }}
.button.ghost {{
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
}}
.button.ghost:hover {{ border-color: var(--muted); filter: none; }}
.section-head {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin: 52px 0 22px;
}}
.section-head h2 {{ margin: 0; font-size: 26px; letter-spacing: -0.02em; }}
.section-head span {{ color: var(--muted); font-family: var(--mono); font-size: 12px; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }}
.card {{
  display: flex;
  flex-direction: column;
  color: var(--text);
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent, var(--green));
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform .15s ease, border-color .15s ease;
}}
.card:hover {{
  transform: translateY(-2px);
  border-color: var(--accent, var(--green));
  text-decoration: none;
}}
.card-cover {{ aspect-ratio: 2400 / 1260; overflow: hidden; background: #000; }}
.card-cover img {{ display: block; width: 100%; height: 100%; object-fit: cover; }}
.card-body {{ display: flex; flex-direction: column; gap: 8px; padding: 18px 20px 22px; }}
.card-kicker {{
  margin: 0;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--accent, var(--green));
}}
.card h3 {{ margin: 0; font-size: 20px; line-height: 1.28; letter-spacing: -0.015em; }}
.card p {{ margin: 0; color: var(--muted); font-size: 14.5px; line-height: 1.6; }}
.card .card-meta {{
  margin-top: auto;
  padding-top: 12px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}}
.card.featured {{ grid-column: 1 / -1; display: grid; grid-template-columns: 1.05fr 1fr; }}
.card.featured .card-cover {{ height: 100%; aspect-ratio: auto; }}
.card.featured .card-body {{ justify-content: center; padding: 30px 34px; }}
.card.featured h3 {{ font-size: clamp(24px, 3vw, 34px); }}
.card.featured p {{ font-size: 16px; }}
.post {{ max-width: 800px; }}
.back {{ font-family: var(--mono); font-size: 13px; color: var(--muted); }}
.back:hover {{ color: var(--text); }}
.post-cover {{
  margin: 24px 0 34px;
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent, var(--green));
  border-radius: var(--radius);
  overflow: hidden;
}}
.post-cover img {{ display: block; width: 100%; height: auto; }}
.post-header h1 {{ font-size: clamp(32px, 5vw, 50px); margin-top: 10px; }}
.post-meta {{
  margin: 18px 0 0;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
}}
.prose {{ margin-top: 40px; }}
.prose h2 {{ margin: 52px 0 16px; font-size: 27px; line-height: 1.25; letter-spacing: -0.02em; }}
.prose h3 {{ margin: 34px 0 12px; font-size: 20px; }}
.prose p, .prose ul, .prose ol {{ margin: 0 0 18px; }}
.prose ul, .prose ol {{ padding-left: 24px; }}
.prose li {{ margin: 7px 0; }}
.prose strong {{ color: #f0f6fc; }}
.prose code {{
  font-family: var(--mono);
  font-size: .87em;
  background: #1f2630;
  border: 1px solid #2a323d;
  padding: 1px 5px;
  border-radius: 4px;
}}
.prose pre {{
  margin: 22px 0;
  padding: 16px 18px;
  overflow-x: auto;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13.5px;
  line-height: 1.6;
}}
.prose pre code {{ background: none; border: 0; padding: 0; font-size: inherit; }}
.prose pre {{ scrollbar-width: thin; scrollbar-color: var(--border) var(--bg-soft); }}
.prose pre::-webkit-scrollbar {{ height: 8px; }}
.prose pre::-webkit-scrollbar-track {{ background: var(--bg-soft); }}
.prose pre::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 8px; }}
.prose blockquote {{
  margin: 24px 0;
  padding: 4px 0 4px 18px;
  border-left: 3px solid var(--green);
  color: var(--muted);
}}
.prose table {{ width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 14px; }}
.prose th, .prose td {{ padding: 9px 12px; border: 1px solid var(--border); text-align: left; vertical-align: top; }}
.prose th {{ background: var(--bg-soft); }}
.prose img {{ max-width: 100%; height: auto; }}
.prose hr {{ border: 0; border-top: 1px solid var(--border); margin: 42px 0; }}
.prose a {{ text-decoration: underline; text-underline-offset: 3px; text-decoration-color: rgba(63,185,80,.35); }}
.prose a:hover {{ text-decoration-color: var(--green); }}
.post-nav {{
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 56px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}}
.post-nav a {{ max-width: 48%; color: var(--text); font-size: 15px; }}
.post-nav a:hover {{ color: var(--green); text-decoration: none; }}
.post-nav .next {{ margin-left: auto; text-align: right; }}
.post-nav .label {{
  display: block;
  margin-bottom: 4px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--muted);
}}
.site-footer {{
  max-width: var(--max);
  margin: 0 auto;
  padding: 28px 24px 48px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 14px;
}}
.site-footer p {{ margin: 6px 0; }}
.site-footer strong {{ color: var(--text); }}
.site-footer a {{ color: var(--muted); }}
.site-footer a:hover {{ color: var(--green); }}
.not-found {{ padding-top: 96px; padding-bottom: 120px; }}
@media (max-width: 760px) {{
  .site-header {{ flex-direction: column; align-items: flex-start; }}
  nav {{ gap: 14px; }}
  main {{ padding-top: 32px; }}
  .hero {{ padding-top: 24px; }}
  .grid {{ grid-template-columns: 1fr; }}
  .card.featured {{ grid-template-columns: 1fr; }}
  .card.featured .card-cover {{ aspect-ratio: 2400 / 1260; }}
  .card.featured .card-body {{ padding: 22px 22px 26px; }}
  .post-nav {{ flex-direction: column; }}
  .post-nav a, .post-nav .next {{ max-width: 100%; text-align: left; }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  .card {{ transition: none; }}
}}

/* Pygments (github-dark) */
{pygments}
"""


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    (OUT / "assets").mkdir(parents=True)
    (OUT / "covers").mkdir(parents=True)

    posts = []
    for prefix in ORDER:
        matches = sorted(ROOT.glob(f"{prefix}-*.md"))
        if len(matches) != 1:
            raise SystemExit(f"expected one post for {prefix}, found {len(matches)}")
        posts.append(parse_post(matches[0]))

    for cover in sorted((ROOT / "covers").glob("*.png")):
        shutil.copy2(cover, OUT / "covers" / cover.name)

    (OUT / "index.html").write_text(build_index(posts), encoding="utf-8")
    for i, post in enumerate(posts):
        previous = posts[i - 1] if i > 0 else None
        following = posts[i + 1] if i + 1 < len(posts) else None
        (OUT / "posts" / f"{post['slug']}.html").write_text(
            build_post(post, previous, following), encoding="utf-8"
        )

    (OUT / "feed.xml").write_text(build_feed(posts), encoding="utf-8")
    (OUT / "sitemap.xml").write_text(build_sitemap(posts), encoding="utf-8")
    (OUT / "404.html").write_text(build_404(), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )
    (OUT / "assets" / "style.css").write_text(build_css(), encoding="utf-8")
    (OUT / "assets" / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#0d1117"/>'
        '<text x="9" y="44" font-family="monospace" font-size="30" font-weight="700" fill="#3fb950">&gt;_</text>'
        "</svg>\n",
        encoding="utf-8",
    )
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"built {len(posts)} posts into {OUT}")


if __name__ == "__main__":
    main()
