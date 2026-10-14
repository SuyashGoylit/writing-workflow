#!/usr/bin/env python3
"""Extract clean text and figures from a Cloud4C case study PDF and its existing LP.

Usage:
    python3 sourcetext.py --pdf case.pdf --lp lp_source.md --out sources/
    python3 sourcetext.py --pdf case.pdf --out sources/      # PDF only

--lp accepts the saved page as .html, the web-fetched text as .md/.txt, or an
https:// URL (only works where the sandbox can reach cloud4c.com).

Writes pdf.txt, lp.txt and facts.json into --out and prints a short report.
Standard library plus pdftotext (poppler); falls back to pypdf or pdfplumber.
Exit code: 0 = ok, 1 = extracted with warnings (unmapped glyphs, client names),
2 = could not read the input.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIENT_NAMES = HERE / "client_names.txt"

# The case study PDFs are Adobe XD exports whose font maps some symbols to
# private-use code points. Left as-is, "24/7" reads as "247" and "60+ TB" as
# "60 TB". Mapping confirmed against the matching LP text for all 50 PDFs.
GLYPHS = {
    "": "/", "": "+", "": ">", "": "<",
    "": "-", "": "-", "": "(", "": ")", "": ":",
}
PUNCT = {
    "ʼ": "'", "’": "'", "‘": "'", "“": '"', "”": '"',
    " ": " ", "­": "", "​": "", " ": " ", " ": " ",
}
PUA_RE = re.compile(r"[-]")

# Heading words that open and close the results block in the PDF and LP.
RESULTS_START = re.compile(
    r"^(?:the\s+)?(?:key\s+)?(?:results?|impact|business\s+impact|outcomes?|benefits|"
    r"numbers\s+that\s+tell|key\s+results|the\s+impact|value\s+delivered|what\s+changed)\b", re.I)
RESULTS_END = re.compile(
    r"^(?:road\s+ahead|future[\s-]+forward|looking\s+ahead|the\s+way\s+forward|what'?s\s+next|"
    r"next\s+steps?|the\s+road\s+ahead)|www\.cloud4c\.com", re.I)

LP_STOP = re.compile(r"^\s*(?:#+\s*)?(?:\d{4}\s+)?(?:Cloud4C All Rights Reserved|Get in touch)\b", re.I)
LP_DROP = re.compile(r"^\s*(?:#+\s*)?(?:Fill-IN to Download Case Study|\[?Download full Case Study)", re.I)


# ---------- normalising ----------

def clean_chars(text, report=None):
    """Map private-use glyphs and odd punctuation, then NFKC (ligatures)."""
    for k, v in GLYPHS.items():
        text = text.replace(k, v)
    for k, v in PUNCT.items():
        text = text.replace(k, v)
    if report is not None:
        for m in PUA_RE.finditer(text):
            report.append({"char": f"U+{ord(m.group()):04X}",
                           "context": text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")})
    return unicodedata.normalize("NFKC", text)


SMALL_WORDS = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "at", "by",
               "from", "into", "via", "as", "vs", "its", "it", "is", "&"}


def _is_title_line(line):
    """Sub-headings in the PDFs are Title Case and do not end like a sentence."""
    if re.search(r"[.;,]$", line) or len(line) > 110:
        return False
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", line) if w.lower() not in SMALL_WORDS]
    if not words:
        return False
    return sum(w[0].isupper() for w in words) / len(words) >= 0.75


# ---------- PDF ----------
# The PDFs are single, very tall pages laid out in Adobe XD: full-width sections,
# two-column solution blocks and 4-column result grids. pdftotext's own reading
# order interleaves the columns line by line, so we take every line with its
# box (-bbox-layout) and rebuild the reading order with a recursive XY-cut.

Line = tuple  # (x0, y0, x1, y1, text)

H_GAP = 12    # min vertical whitespace (pt) that separates two blocks
V_GAP = 24    # min horizontal whitespace (pt) that separates two columns


def _lines_pdftotext(path):
    from xml.etree import ElementTree
    r = subprocess.run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
                       capture_output=True, text=True)
    if r.returncode != 0 or "<word" not in r.stdout:
        return None
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", r.stdout).replace('xmlns="http://www.w3.org/1999/xhtml"', "")
    root = ElementTree.fromstring(xml)
    pages = []
    for page in root.iter("page"):
        out = []
        for ln in page.iter("line"):
            words = [w.text or "" for w in ln.iter("word")]
            out.append((float(ln.get("xMin")), float(ln.get("yMin")), float(ln.get("xMax")),
                        float(ln.get("yMax")), " ".join(words)))
        pages.append(out)
    return pages


def _lines_pdfplumber(path):
    try:
        import pdfplumber  # noqa: WPS433
    except ImportError:
        return None
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            if not hasattr(page, "extract_text_lines"):
                return None
            pages.append([(l["x0"], l["top"], l["x1"], l["bottom"], l["text"])
                          for l in page.extract_text_lines()])
    return pages


def _gaps(intervals, min_gap):
    """Whitespace gaps between merged 1-D intervals: [(gap_size, cut_position)]."""
    iv = sorted(intervals)
    out, end = [], iv[0][1]
    for a, b in iv[1:]:
        if a - end >= min_gap:
            out.append((a - end, (a + end) / 2))
        end = max(end, b)
    return out


def _row_gaps(lines):
    """Vertical whitespace between rows. Large type has more leading, so the gap
    must also exceed 60% of the smaller neighbouring line height."""
    rows = sorted(lines, key=lambda l: l[1])
    out, end, end_h = [], rows[0][3], rows[0][3] - rows[0][1]
    for l in rows[1:]:
        gap = l[1] - end
        if gap >= max(H_GAP, 0.6 * min(end_h, l[3] - l[1])):
            out.append((gap, (l[1] + end) / 2))
        if l[3] > end:
            end, end_h = l[3], l[3] - l[1]
    return out


def _xy_cut(lines):
    """Recursively split on the single widest whitespace gap, vertical or horizontal."""
    if len(lines) <= 1:
        return [lines]
    v = max(_gaps([(l[0], l[2]) for l in lines], V_GAP), default=None)
    h = max(_row_gaps(lines), default=None)
    if v is None and h is None:
        return [sorted(lines, key=lambda l: (round(l[1]), l[0]))]
    if v is not None and (h is None or v[0] >= h[0]):
        cut, mid = v[1], (lambda l: (l[0] + l[2]) / 2)
    else:
        cut, mid = h[1], (lambda l: (l[1] + l[3]) / 2)
    first = [l for l in lines if mid(l) <= cut]
    rest = [l for l in lines if mid(l) > cut]
    if not first or not rest:
        return [sorted(lines, key=lambda l: (round(l[1]), l[0]))]
    return _xy_cut(first) + _xy_cut(rest)


def _join_lines(texts, vocab):
    text = texts[0]
    for nxt in texts[1:]:
        m = re.search(r"([A-Za-z]+)-$", text)
        n = re.match(r"([a-z]+)", nxt)
        if m and n:
            a, b = m.group(1).lower(), n.group(1)
            # join words split by the layout (stabiliza-tion, imple-mented); keep
            # compounds whose first part is a word (on-prem, next-gen, decision-making)
            if (a + b.lower()) in vocab or a not in vocab:
                text = text[:-1] + nxt
            else:
                text += nxt
        else:
            text += " " + nxt
    return re.sub(r"\s+", " ", text).strip()


def _vocab(all_lines):
    vocab = set()
    texts = [l[4] for l in all_lines]
    for i, t in enumerate(texts):
        toks = re.findall(r"[A-Za-z]+", t)
        if t.rstrip().endswith("-") and toks:
            toks = toks[:-1]           # fragment before a line-end hyphen
        if i and texts[i - 1].rstrip().endswith("-") and toks:
            toks = toks[1:]            # fragment after it
        vocab.update(w.lower() for w in toks)
    return vocab


def _blocks_to_paras(blocks, vocab):
    heights = sorted(l[3] - l[1] for b in blocks for l in b)
    body_h = heights[len(heights) // 2] if heights else 0
    paras = []
    for b in blocks:
        texts = [l[4] for l in b if l[4].strip()]
        if not texts:
            continue
        text = _join_lines(texts, vocab)
        avg_h = sum(l[3] - l[1] for l in b) / len(b)
        is_head = avg_h > body_h * 1.15 or (len(texts) <= 3 and all(_is_title_line(t) for t in texts))
        paras.append(f"## {text}" if is_head else text)
    return paras


def _pdf_paragraphs(path):
    for engine, fn in (("pdftotext", _lines_pdftotext if shutil.which("pdftotext") else None),
                       ("pdfplumber", _lines_pdfplumber)):
        if fn is None:
            continue
        pages = fn(path)
        if pages and any(pages):
            paras = []
            vocab = _vocab([l for p in pages for l in p])
            for page in pages:
                if page:
                    paras += _blocks_to_paras(_xy_cut(page), vocab)
            return paras, engine
    try:
        import pypdf  # noqa: WPS433
        reader = pypdf.PdfReader(str(path))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        if text.strip():
            # no geometry: one paragraph per line, columns may interleave
            return [l.strip() for l in text.splitlines() if l.strip()], "pypdf (no layout)"
    except ImportError:
        pass
    raise RuntimeError("no PDF text extractor worked (need pdftotext, pdfplumber or pypdf), "
                       "or the PDF has no text layer")


def pdf_text(path):
    """Return (paragraphs, info) for a case study PDF. Headings start with '## '."""
    paras, engine = _pdf_paragraphs(path)
    glyphs = []
    joined = clean_chars("\n\n".join(paras), glyphs)
    paras = [p for p in joined.split("\n\n") if p.strip()]
    # Result grids come out one fragment per block; merge runs of short
    # non-heading fragments that do not end a sentence into their neighbours.
    merged = []
    for p in paras:
        if (merged and not p.startswith("## ") and not merged[-1].startswith("## ")
                and len(merged[-1].split()) <= 6 and not re.search(r"[.!?:]$", merged[-1])
                and re.match(r"[a-z0-9]", p)):
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return merged, {"engine": engine, "unmapped_glyphs": glyphs}


# ---------- LP ----------

class _LPParser(HTMLParser):
    """Pull the readable parts of a cloud4c.com /wb/case-study/ page."""
    SKIP_CLASSES = ("show-in-mobile", "section_form", "pageload", "image-section")
    BLOCK = {"h1", "h2", "h3", "h4", "p", "li"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, skipping)
        self.blocks = []         # (tag, text)
        self.cur = None
        self.done = False
        self.crumbs = []
        self.in_crumb = False

    def handle_starttag(self, tag, attrs):
        if self.done or tag in ("br", "img", "meta", "link", "input", "hr"):
            if tag == "br" and self.cur is not None:
                self.cur[1].append(" ")
            return
        cls = dict(attrs).get("class", "") or ""
        skipping = (self.stack and self.stack[-1][1]) or any(c in cls.split() for c in self.SKIP_CLASSES)
        if "banner_head6" in cls:
            self.done = True
            return
        if tag in ("script", "style", "form"):
            skipping = True
        if tag == "ol" and "breadcrumb" in cls:
            self.in_crumb = True
        self.stack.append((tag, skipping))
        if tag in self.BLOCK and not skipping:
            self.cur = [tag, []]

    def handle_endtag(self, tag):
        if self.done:
            return
        if tag == "ol":
            self.in_crumb = False
        while self.stack:
            t, _ = self.stack.pop()
            if t == tag:
                break
        if self.cur is not None and tag == self.cur[0]:
            text = re.sub(r"\s+", " ", "".join(self.cur[1])).strip()
            if text:
                if self.in_crumb and tag == "li":
                    self.crumbs.append(text)
                else:
                    self.blocks.append((tag, text))
            self.cur = None

    def handle_data(self, data):
        if self.done or self.cur is None:
            return
        if self.stack and self.stack[-1][1]:
            return
        self.cur[1].append(data)


def _dedupe(blocks):
    """The LP repeats the Solution block (mobile + desktop). Keep first copies."""
    seen, out = set(), []
    for tag, text in blocks:
        key = (tag in ("h1", "h2", "h3", "h4"), text.lower())
        if tag in ("p", "li") and key in seen:
            continue
        if tag in ("h2", "h3", "h4") and key in seen:
            continue
        seen.add(key)
        out.append((tag, text))
    return out


def lp_from_html(source):
    p = _LPParser()
    p.feed(source)
    blocks = [(t, x) for t, x in p.blocks if not LP_DROP.match(x)]
    blocks = _dedupe(blocks)
    crumbs = [c for c in p.crumbs if c.lower() != "case study"]
    lines = []
    in_results = False
    for tag, text in blocks:
        if tag == "h1":
            lines.append(f"# {text}")
            if crumbs:
                lines.append(f"Breadcrumb: {' | '.join(crumbs)}")
        elif tag in ("h2", "h3", "h4"):
            in_results = bool(RESULTS_START.match(text))
            lines.append(f"## {text}")
        elif in_results or tag == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines), crumbs


def lp_from_text(source):
    """Clean web-fetched LP text (Markdown-ish) into the same shape as lp_from_html."""
    lines = [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"!\[[^\]]*\]\([^)]*\)", "", l)).strip()
             for l in source.splitlines()]
    # Header: the H1 (often wrapped over several lines) and the breadcrumb before the first "##".
    first_h2 = next((i for i, l in enumerate(lines) if re.match(r"^#{2,6}\s", l)), len(lines))
    title, crumbs, in_title = [], [], False
    for l in lines[:first_h2]:
        if l.startswith("# "):
            title, in_title = [l[2:].strip()], True
            continue
        if not l:
            in_title = False
            continue
        if in_title:
            title.append(l)
            continue
        item = re.sub(r"^(?:\d+\.|[-*>])\s*", "", l).strip(" >/")
        if title and item and len(item.split()) <= 6 and not LP_DROP.match(item) \
                and item.lower() not in ("case study", "case studies"):
            crumbs.append(item)
    out = [f"# {' '.join(title)}"] if title else []
    if crumbs:
        out.append(f"Breadcrumb: {' | '.join(crumbs)}")

    seen, para = set(), []
    in_results = False

    def flush():
        if para:
            text = re.sub(r"\s+", " ", " ".join(para)).strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(f"- {text}" if in_results else text)
            para.clear()

    for line in lines[first_h2:]:
        if LP_STOP.match(line):
            break
        if not line or LP_DROP.match(line):
            flush()
            continue
        m = re.match(r"^(#{1,6})\s*(.+)$", line)
        if m:
            flush()
            text = m.group(2).strip(" #")
            if f"h:{text.lower()}" in seen:
                in_results = False   # repeated (mobile) Solution heading
                continue
            seen.add(f"h:{text.lower()}")
            in_results = bool(RESULTS_START.match(text))
            out.append(f"## {text}")
            continue
        para.append(line)
        if in_results:
            flush()
    flush()
    return "\n\n".join(out), crumbs


def lp_text(arg):
    """Return (text, crumbs) from an LP .html/.md/.txt path or URL."""
    if re.match(r"https?://", arg):
        import urllib.request
        req = urllib.request.Request(arg, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
            src = r.read().decode("utf-8", "ignore")
    else:
        src = Path(arg).read_text(encoding="utf-8", errors="ignore")
    src = clean_chars(src)
    if re.search(r"<(html|body|div|h1)\b", src, re.I):
        return lp_from_html(src)
    return lp_from_text(src)


# ---------- figures ----------

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
WORDNUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "hundred": 100,
}
UNITS = [
    ("%", r"%|percent\b|per\s+cent\b"),
    ("x", r"x\b(?![\d×x])|times\b(?=\s+(?:faster|more|higher|lower|less|greater|quicker))"),
    ("TB", r"TB\b|terabytes?\b"), ("GB", r"GB\b|gigabytes?\b"), ("PB", r"PB\b|petabytes?\b"),
    ("MB", r"MB\b|megabytes?\b"), ("Gbps", r"Gbps\b"), ("Mbps", r"Mbps\b"),
    ("ms", r"ms\b|milliseconds?\b"), ("second", r"seconds?\b|secs?\b"),
    ("minute", r"minutes?\b|mins?\b"), ("hour", r"hours?\b|hrs?\b"), ("day", r"days?\b"),
    ("week", r"weeks?\b"), ("month", r"months?\b"), ("year", r"years?\b|yrs?\b"),
    ("K", r"K\b|thousand\b"), ("M", r"M\b|Mn\b|million\b"), ("B", r"Bn\b|billion\b"),
    ("lakh", r"lakhs?\b"), ("crore", r"crores?\b"),
]
UNIT_RE = "|".join(f"(?P<u_{i}>{rx})" for i, (_, rx) in enumerate(UNITS))
UNIT_ANY = "|".join(rx for _, rx in UNITS)
CURRENCY = r"US\$|\$|USD|AED|SAR|QAR|OMR|KWD|BHD|INR|Rs\.?|₹|€|EUR|£|GBP|MYR|RM|SGD|CAD|THB|KHR|IDR|PHP"
QUALS = [
    ("plus", r"over|more\s+than|upwards\s+of|in\s+excess\s+of|at\s+least|exceeding|greater\s+than|>|≥"),
    ("approx", r"approximately|approx\.?|around|about|nearly|almost|close\s+to|roughly|~|an\s+estimated|estimated"),
    ("max", r"up\s+to|upto|under|less\s+than|below|within|<|≤"),
]
QUAL_RE = "|".join(f"(?P<q_{n}>{rx})" for n, rx in QUALS)

FIG_RE = re.compile(
    rf"(?:(?:{QUAL_RE})\s*)?"
    rf"(?P<cur>{CURRENCY})?\s?"
    rf"(?<![\w/.])(?P<num>{NUM})(?:\s*(?:-|to)\s*(?P<num2>{NUM})(?=\s*-?\s*(?:{UNIT_ANY})))?"
    rf"(?P<plus>\+)?"
    rf"(?:\s*-?\s*(?:{UNIT_RE}))?"
    rf"(?P<plus2>\+)?"
    rf"(?![A-Za-z0-9])", re.I)
TWENTYFOUR_SEVEN = re.compile(r"\b24\s*(?:/|x|×|\*)\s*7(?:\s*(?:/|x|×|\*)\s*365)?\b", re.I)
WORDNUM_RE = re.compile(
    rf"\b(?P<w>{'|'.join(WORDNUM)})(?:[\s-]+)(?=(?:{UNIT_ANY}))", re.I)


def _unit_of(m):
    for i, (name, _) in enumerate(UNITS):
        if m.group(f"u_{i}"):
            return name
    return ""


def _qual_of(m):
    for n, _ in QUALS:
        if m.group(f"q_{n}"):
            return n
    return "plus" if m.group("plus") else "exact"


def norm_value(v):
    v = v.replace(",", "")
    if "." in v:
        v = v.rstrip("0").rstrip(".")
    return v


def figures(text, origin="", section_of=None):
    """Every figure in text: value, unit, qualifier, raw match and a context snippet."""
    found = []
    text_n = WORDNUM_RE.sub(lambda m: f"{WORDNUM[m.group('w').lower()]} ", text)
    for m in TWENTYFOUR_SEVEN.finditer(text_n):
        found.append({"value": "24/7", "unit": "", "qual": "exact", "raw": m.group(),
                      "key": "24/7", "origin": origin, "start": m.start(),
                      "context": _ctx(text_n, m.start(), m.end())})
    spans = [(f["start"], f["start"] + len(f["raw"])) for f in found]
    for m in FIG_RE.finditer(text_n):
        if any(a <= m.start("num") < b for a, b in spans):
            continue
        value = norm_value(m.group("num"))
        if m.group("num2"):
            value += "-" + norm_value(m.group("num2"))
        unit = _unit_of(m)
        cur = (m.group("cur") or "").replace("US$", "$").replace("USD", "$")
        qual = _qual_of(m)
        if (m.group("plus") or m.group("plus2")) and qual == "exact":
            qual = "plus"
        key = f"{cur}{value}{(' ' + unit) if unit else ''}"
        found.append({"value": value, "unit": unit, "cur": cur, "qual": qual,
                      "raw": m.group().strip(), "key": key, "origin": origin,
                      "start": m.start(), "context": _ctx(text_n, m.start(), m.end())})
    if section_of:
        for f in found:
            f["section"] = section_of(f["start"])
    return found


def _ctx(text, a, b, pad=60):
    return re.sub(r"\s+", " ", text[max(0, a - pad):b + pad]).strip()


# ---------- results sections ----------

def results_paragraphs(paras):
    """Paragraphs between the PDF's results heading and its road-ahead heading."""
    start = None
    for i, p in enumerate(paras):
        head = p[3:] if p.startswith("## ") else None
        if start is None and head and RESULTS_START.match(head):
            start = i + 1
        elif start is not None and (RESULTS_END.match(head or "") or RESULTS_END.search(p)):
            return paras[start:i]
    return paras[start:] if start is not None else []


def lp_results(lp):
    out, on = [], False
    for line in lp.splitlines():
        if line.startswith("## "):
            on = bool(RESULTS_START.match(line[3:]))
        elif on and line.startswith("- "):
            out.append(line[2:])
    return out


# ---------- client names ----------

def load_client_names(extra=""):
    names = []
    if CLIENT_NAMES.exists():
        names = [l.strip() for l in CLIENT_NAMES.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
    names += [n.strip() for n in re.split(r"[;\n]", extra or "") if n.strip()]
    return names


def find_names(text, names):
    hits = []
    for n in names:
        for m in re.finditer(rf"\b{re.escape(n)}\b", text, re.I):
            hits.append({"name": n, "context": _ctx(text, m.start(), m.end())})
    return hits


# ---------- facts ----------

def build_facts(pdf_paras, lp, crumbs, glyphs, names):
    pdf = "\n\n".join(pdf_paras)
    pdf_figs = figures(pdf, "pdf")
    lp_figs = figures(lp, "lp") if lp else []
    res_pdf = figures("\n\n".join(results_paragraphs(pdf_paras)), "pdf-results")
    # the title and the subtitle under it carry the case study's lead figure
    top = [p for p in pdf_paras[:3] if not p.startswith("www.")][:2]
    res_pdf += figures("\n\n".join(top), "pdf-title")
    res_lp = figures("\n\n".join(lp_results(lp)), "lp-results") if lp else []

    pdf_by_key = {}
    for f in pdf_figs:
        pdf_by_key.setdefault(f["key"], set()).add(f["qual"])
    conflicts, lp_only = [], []
    for f in lp_figs:
        if f["key"] not in pdf_by_key:
            if not any(x["key"] == f["key"] for x in lp_only):
                lp_only.append({"key": f["key"], "qual": f["qual"], "context": f["context"]})
        elif f["qual"] not in pdf_by_key[f["key"]]:
            conflicts.append({"key": f["key"], "lp_qual": f["qual"],
                              "pdf_quals": sorted(pdf_by_key[f["key"]]), "lp_context": f["context"],
                              "pdf_context": next(x["context"] for x in pdf_figs if x["key"] == f["key"])})
    strip = lambda fs: [{k: v for k, v in f.items() if k != "start"} for f in fs]  # noqa: E731
    return {
        "title": next((p[3:] for p in pdf_paras if p.startswith("## ")), ""),
        "breadcrumb": crumbs,
        "figures": {"pdf": strip(pdf_figs), "lp": strip(lp_figs)},
        "headline_figures": sorted({f["key"] for f in res_pdf + res_lp}),
        "conflicts": conflicts,
        "lp_only_figures": lp_only,
        "unmapped_glyphs": glyphs,
        "client_names_found": find_names(pdf + "\n" + lp, names),
    }


def extract(pdf_path, lp_arg=None, out_dir=None, extra_names=""):
    lp, crumbs = ("", [])
    if lp_arg:
        lp, crumbs = lp_text(lp_arg)
    paras, info = pdf_text(pdf_path)
    facts = build_facts(paras, lp, crumbs, info["unmapped_glyphs"], load_client_names(extra_names))
    facts["engine"] = info["engine"]
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "pdf.txt").write_text("\n\n".join(paras) + "\n", encoding="utf-8")
        (out / "lp.txt").write_text(lp + "\n", encoding="utf-8")
        (out / "facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
    return paras, lp, facts


def report(facts, out_dir):
    lines = [f"Extracted with {facts['engine']} → {out_dir}/pdf.txt, lp.txt, facts.json"]
    lines.append(f"Title: {facts['title']}")
    if facts["breadcrumb"]:
        lines.append(f"Breadcrumb: {' | '.join(facts['breadcrumb'])}")
    lines.append(f"Figures: {len(facts['figures']['pdf'])} in PDF, {len(facts['figures']['lp'])} in LP; "
                 f"headline: {', '.join(facts['headline_figures']) or 'none found'}")
    if facts["conflicts"]:
        lines.append("LP vs PDF qualifier conflicts (PDF wins):")
        lines += [f"  - {c['key']}: LP '{c['lp_qual']}' vs PDF {c['pdf_quals']} | LP: …{c['lp_context']}…"
                  for c in facts["conflicts"]]
    if facts["lp_only_figures"]:
        lines.append("Figures only in the LP (usable, flag to the writer):")
        lines += [f"  - {c['key']} | …{c['context']}…" for c in facts["lp_only_figures"]]
    if facts["unmapped_glyphs"]:
        lines.append("UNMAPPED GLYPHS (symbols may be missing nearby; check the PDF visually):")
        lines += [f"  - {g['char']}: …{g['context']}…" for g in facts["unmapped_glyphs"][:20]]
    if facts["client_names_found"]:
        lines.append("REAL CLIENT NAME IN SOURCE (never repeat it):")
        lines += [f"  - {h['name']}: …{h['context']}…" for h in facts["client_names_found"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--lp", help="existing LP: .html, .md/.txt or URL")
    ap.add_argument("--out", default="sources")
    ap.add_argument("--client-names", default="", help="extra real names to flag, separated by ';'")
    a = ap.parse_args()
    try:
        _, _, facts = extract(a.pdf, a.lp, a.out, a.client_names)
    except (OSError, RuntimeError) as e:
        print(f"Could not read sources: {e}", file=sys.stderr)
        sys.exit(2)
    print(report(facts, a.out))
    sys.exit(1 if facts["unmapped_glyphs"] or facts["client_names_found"] else 0)


if __name__ == "__main__":
    main()
