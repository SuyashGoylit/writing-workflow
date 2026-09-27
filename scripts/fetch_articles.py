#!/usr/bin/env python3
"""Download published Cloud4C blog posts as Markdown for the Project knowledge.

Usage:
    python3 scripts/fetch_articles.py                 # every URL in past-articles/sources.txt
    python3 scripts/fetch_articles.py URL [URL ...]   # specific posts (also appended to sources.txt)

Needs: beautifulsoup4, html2text  (pip install beautifulsoup4 html2text)
"""
import re
import sys
import urllib.request
from pathlib import Path

import html2text
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "project" / "knowledge" / "past-articles"
SOURCES = OUT_DIR / "sources.txt"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def extract(html):
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)) if h1 else "Untitled"
    date = ""
    header = soup.select_one(".hed-date")
    if header:
        m = re.search(r"\d{1,2} \w{3},? \d{4}", header.get_text(" ", strip=True))
        date = m.group(0) if m else ""

    article = soup.select_one(".blog_content_details article") or soup.find("article")
    if article is None:
        raise ValueError("article body not found (page layout may have changed)")

    for tag in article(["script", "style", "noscript", "iframe", "form", "button", "svg"]):
        tag.decompose()
    # Table of contents: the "Table of Contents" label followed by a list of anchor links.
    label = article.find(string=re.compile(r"Table of Contents", re.I))
    if label:
        toc = label.find_next(["ul", "ol"])
        if toc is not None and all(a.get("href", "").startswith("#") for a in toc.find_all("a")):
            toc.decompose()
        holder = label.parent
        if len(holder.get_text(strip=True)) <= len("Table of Contents") + 5:
            holder.decompose()
        else:
            label.extract()
    # Inline "related post" promo cards are not part of the article.
    for card in article.select("div.bg-gray.text-center"):
        card.decompose()
    # Promo images/banners add noise.
    for img in article.find_all("img"):
        img.decompose()

    conv = html2text.HTML2Text()
    conv.body_width = 0
    conv.ignore_images = True
    conv.ignore_emphasis = False
    md = conv.handle(str(article))
    md = re.sub(r"\n\s*-\s*\n", "\n", md)          # stray "-" separators in FAQ accordions
    md = re.sub(r"^\**Table of Contents\**\s*$", "", md, flags=re.I | re.M)
    md = re.sub(r"^(#+ \d+)\\\.", r"\1.", md, flags=re.M)  # "### 1\." -> "### 1."
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return title, date, md


def slug(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def main():
    urls = sys.argv[1:]
    known = [l.strip() for l in SOURCES.read_text().splitlines() if l.strip() and not l.startswith("#")] \
        if SOURCES.exists() else []
    if urls:
        with SOURCES.open("a") as f:
            for u in urls:
                if u not in known:
                    f.write(u + "\n")
    else:
        urls = known
    if not urls:
        sys.exit("No URLs given and sources.txt is empty.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for url in urls:
        try:
            title, date, body = extract(fetch(url))
        except Exception as e:  # keep going with the rest
            print(f"FAILED {url}: {e}", file=sys.stderr)
            continue
        path = OUT_DIR / f"{slug(url)}.md"
        meta = f"<!-- source: {url} | published: {date or 'unknown'} -->\n\n"
        path.write_text(meta + f"# {title}\n\n{body}\n", encoding="utf-8")
        print(f"saved {path.relative_to(ROOT)}  ({len(body.split())} words)")


if __name__ == "__main__":
    main()
