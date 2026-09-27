#!/usr/bin/env python3
"""Audit a blog draft against the Cloud4C blog style rules.

Usage:
    python audit.py draft.md --keywords "kw one; kw two" [--secondary "a; b"]
                    [--min 1200] [--max 1500] [--json]

Accepts .md, .txt or .docx. Standard library only.
Exit code: 0 = no FAIL, 1 = at least one FAIL, 2 = bad input.
"""
import argparse
import json
import re
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BANNED = SKILL_DIR / "banned_phrases.txt"
DEFAULT_COMPETITORS = SKILL_DIR / "competitors.txt"

PRONOUN_RES = [
    re.compile(r"\b(you|your|yours|yourself|yourselves|we|our|ours|ourselves|let's)\b", re.IGNORECASE),
    # case-sensitive so "US" (country/region) and "I/O" are not flagged
    re.compile(r"(?<![/\-])\b(I|[Mm]e|[Mm]y|[Mm]ine|[Uu]s)\b(?![/\-])"),
]
DASH_RE = re.compile(r"[—–]|(?<=\w) - (?=\w)|(?<=\w) -- (?=\w)")
STOPWORDS = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "is", "are", "vs"}


# ---------- loading ----------

def read_docx(path):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    lines = []
    for p in root.iter(f"{{{ns['w']}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t")).strip()
        if not text:
            continue
        style = p.find("w:pPr/w:pStyle", ns)
        level = 0
        if style is not None:
            m = re.search(r"(?:Heading|Title)\s*(\d*)", style.get(f"{{{ns['w']}}}val", ""), re.I)
            if m:
                level = int(m.group(1)) if m.group(1) else 1
        lines.append(("#" * level + " " + text) if level else text)
        lines.append("")
    return "\n".join(lines)


def load_text(path):
    p = Path(path)
    if p.suffix.lower() == ".docx":
        return read_docx(p)
    return p.read_text(encoding="utf-8")


def normalise(text):
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def load_phrase_file(path):
    sections = {"ban": [], "watch": [], "ban-regex": [], "watch-regex": []}
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"\[(.+)\]", line)
        if m:
            current = m.group(1).lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def load_list(path):
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def split_keywords(value):
    return [k.strip() for k in re.split(r"[;\n]", value or "") if k.strip()]


# ---------- parsing ----------

def strip_md(line):
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"[*_`]{1,3}", "", line)
    line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)
    line = re.sub(r"^\s*>\s?", "", line)
    return line.strip()


def parse(text):
    """Return list of blocks: {'type': 'heading'|'para', 'level', 'text', 'line', 'section'}."""
    blocks, para, para_line = [], [], None
    section = ""  # current H2 text
    lines = text.splitlines()
    # Drop writer notes after a trailing '---' separator (notes section).
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() in ("---", "***", "___"):
            if i > len(lines) * 0.5:
                lines = lines[:i]
            break
    # Drop a trailing "Sources:" / "References:" list (URLs are not prose).
    for i in range(len(lines) - 1, int(len(lines) * 0.6), -1):
        if re.match(r"^\s*(?:#+\s*)?\**(sources|references)\s*:?\**\s*$", lines[i], re.I):
            lines = lines[:i]
            break

    def flush():
        nonlocal para, para_line
        if para:
            blocks.append({"type": "para", "text": " ".join(para), "line": para_line, "section": section})
        para, para_line = [], None

    for n, raw in enumerate(lines, 1):
        m = re.match(r"^\s*(#{1,6})\s+(.*)$", raw)
        if m:
            flush()
            level, htext = len(m.group(1)), strip_md(m.group(2))
            if level == 2:
                section = htext
            blocks.append({"type": "heading", "level": level, "text": htext, "line": n, "section": section})
            continue
        clean = strip_md(raw)
        if not clean:
            flush()
            continue
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", raw):
            # each list item is its own paragraph-ish block
            flush()
            blocks.append({"type": "para", "text": clean, "line": n, "section": section, "list": True})
            continue
        if para_line is None:
            para_line = n
        para.append(clean)
    flush()
    return blocks


def sentences(text):
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9\"'(])", text)
    return [s.strip() for s in parts if len(s.strip().split()) >= 2]


def words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-/.%]*", text)


def snippet(text, start, end, pad=40):
    a, b = max(0, start - pad), min(len(text), end + pad)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


# ---------- checks ----------

class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, check, detail, hits=None):
        self.rows.append({"status": status, "check": check, "detail": detail, "hits": hits or []})

    @property
    def failed(self):
        return any(r["status"] == "FAIL" for r in self.rows)


def run(text, keywords, secondary, wmin, wmax, banned, competitors):
    text = normalise(text)
    blocks = parse(text)
    rep = Report()
    headings = [b for b in blocks if b["type"] == "heading"]
    paras = [b for b in blocks if b["type"] == "para"]
    h2s = [h for h in headings if h["level"] == 2]
    all_items = headings + paras  # things that carry text, with line numbers
    faq_re = re.compile(r"\b(faqs?|frequently asked)\b", re.I)

    def is_faq(block):
        return bool(faq_re.search(block.get("section", "")))

    # The Cloud4C pitch is the last H2 that isn't an FAQ (an FAQ may follow the pitch).
    content_h2s = [h for h in h2s if not faq_re.search(h["text"])]
    pitch_h2 = content_h2s[-1] if content_h2s else None

    def in_pitch(block):
        return bool(pitch_h2) and block.get("section") == pitch_h2["text"]

    # 1. Word count (FAQ and Sources are extra, on top of the target)
    total_words = sum(len(words(b["text"])) for b in all_items)
    faq_words = sum(len(words(b["text"])) for b in all_items if is_faq(b))
    main_words = total_words - faq_words
    status = "PASS" if wmin <= main_words <= wmax else "FAIL"
    rep.add(status, "Word count", f"{main_words} words excluding FAQ (target {wmin}-{wmax}); {total_words} incl. FAQ")

    # 2. Dashes
    hits = []
    for b in all_items:
        for m in DASH_RE.finditer(b["text"]):
            hits.append(f"L{b['line']}: {snippet(b['text'], m.start(), m.end())}")
    rep.add("FAIL" if hits else "PASS", "Em/en dashes", f"{len(hits)} found", hits)

    # 3. Banned phrases
    def scan(patterns, is_regex):
        found = []
        for pat in patterns:
            rx = re.compile(pat if is_regex else r"(?<![\w-])" + re.escape(pat) + r"(?![\w-])", re.I)
            for b in all_items:
                if is_regex and is_faq(b) and b["type"] == "heading":
                    continue
                for m in rx.finditer(b["text"]):
                    found.append((pat, f"L{b['line']}: {snippet(b['text'], m.start(), m.end())}"))
        return found

    ban_hits = scan(banned.get("ban", []), False) + scan(banned.get("ban-regex", []), True)
    rep.add("FAIL" if ban_hits else "PASS", "Banned phrases / constructions",
            f"{len(ban_hits)} found", [f"[{p}] {s}" for p, s in ban_hits])

    watch_hits = scan(banned.get("watch", []), False) + scan(banned.get("watch-regex", []), True)
    counts = Counter(p.lower() for p, _ in watch_hits)
    status = "WARN" if len(watch_hits) > 5 or any(c > 2 for c in counts.values()) else "PASS"
    rep.add(status, "Watch-list words (use sparingly)",
            ", ".join(f"{k}×{v}" for k, v in counts.most_common()) or "none",
            [f"[{p}] {s}" for p, s in watch_hits] if status == "WARN" else [])

    # 4. Pronouns
    hits, pitch_we = [], []
    for b in all_items:
        quoted = [q.span() for q in re.finditer(r'"[^"]{1,100}"', b["text"])]
        for rx in PRONOUN_RES:
            for m in rx.finditer(b["text"]):
                if any(a <= m.start() < z for a, z in quoted):
                    continue  # quoted speech, e.g. "we support compliance"
                hit = f"L{b['line']}: '{m.group(0)}' in {snippet(b['text'], m.start(), m.end())}"
                if in_pitch(b) and m.group(0).lower() in ("we", "our", "ours", "us"):
                    pitch_we.append(hit)
                else:
                    hits.append(hit)
    rep.add("FAIL" if hits else "PASS", "First/second person (you/I/we)", f"{len(hits)} found", hits)
    rep.add("WARN" if pitch_we else "PASS", "Cloud4C 'we/our' in pitch",
            f"{len(pitch_we)} found (published posts use it; the brief says third person, so confirm)"
            if pitch_we else "none", pitch_we)

    # 5. Competitors
    hits = []
    for name in competitors:
        rx = re.compile(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])")
        for b in all_items:
            for m in rx.finditer(b["text"]):
                hits.append(f"L{b['line']}: '{name}' in {snippet(b['text'], m.start(), m.end())}")
    rep.add("FAIL" if hits else "PASS", "Competitor names", f"{len(hits)} found (review each)", hits)

    # 6. Rhetorical questions in body (not headings, not FAQ)
    hits = []
    for b in paras:
        if is_faq(b):
            continue
        for s in sentences(b["text"]):
            if s.rstrip("\"')").endswith("?"):
                hits.append(f"L{b['line']}: {s[:120]}")
    rep.add("FAIL" if hits else "PASS", "Rhetorical questions in body", f"{len(hits)} found", hits)

    # 7. Conclusion heading / pitch
    concl = [h for h in headings if re.search(r"\b(conclusion|final thoughts|wrapping up|key takeaways)\b", h["text"], re.I)]
    rep.add("FAIL" if concl else "PASS", "No 'Conclusion' section",
            "found: " + "; ".join(h["text"] for h in concl) if concl else "none")
    last_h2 = pitch_h2
    pitch_paras = [p for p in paras if in_pitch(p)
                   and not (len(words(p["text"])) <= 30 and re.search(r"\b(contact|talk to|connect with|reach out|get in touch)\b", p["text"], re.I))]
    pitch_ok = bool(last_h2) and "cloud4c" in (last_h2["text"] + " ".join(p["text"] for p in pitch_paras)).lower()
    detail = (f"'{last_h2['text']}' has {len(pitch_paras)} paragraph(s)" if last_h2 else "no H2s found")
    status = "PASS" if pitch_ok and len(pitch_paras) == 2 else "WARN" if pitch_ok else "FAIL"
    rep.add(status, "Closing Cloud4C pitch (2 paragraphs + optional CTA line)", detail)

    faq_h = [h for h in h2s if faq_re.search(h["text"])]
    faq_qs = [p for p in paras if is_faq(p) and p["text"].rstrip().endswith("?")]
    faq_qs += [h for h in headings if h["level"] >= 3 and is_faq(h) and h["text"].rstrip().endswith("?")]
    rep.add("PASS" if faq_h and 4 <= len(faq_qs) <= 6 else "WARN", "FAQ section (5 questions after pitch)",
            f"{len(faq_qs)} question(s)" if faq_h else "no FAQ section")

    # 8. Headings structure
    body_heads = [h for h in headings if h["level"] in (2, 3) and not is_faq(h) and not faq_re.search(h["text"])
                  and h is not pitch_h2 and not in_pitch(h)]
    n_h3 = sum(1 for h in body_heads if h["level"] == 3)
    status = "PASS" if len(body_heads) >= 5 and len(content_h2s) >= 2 else "WARN"
    rep.add(status, "Heading structure",
            f"{len(h2s)} H2s, {n_h3} H3s; {len(body_heads)} body sections (target 5+ H2/H3 sections plus the pitch H2)")

    # 9. Keywords
    body_lower = _kw_norm(" ".join(b["text"] for b in all_items))
    kw_rows, missing, stuffed = [], [], []
    for kw in keywords:
        c = len(re.findall(r"(?<!\w)" + re.escape(_kw_norm(kw)) + r"(?!\w)", body_lower))
        kw_rows.append(f"'{kw}': {c}")
        if c == 0:
            missing.append(kw)
        elif c > 4:
            stuffed.append(kw)
    if keywords:
        status = "FAIL" if missing else "WARN" if stuffed else "PASS"
        detail = f"{len(keywords) - len(missing)}/{len(keywords)} primary keywords used"
        if missing:
            detail += "; missing: " + ", ".join(missing)
        if stuffed:
            detail += "; possibly overused (>4): " + ", ".join(stuffed)
        rep.add(status, "Primary keywords", detail, kw_rows)
        title = next((h for h in headings if h["level"] == 1), None)
        intro_text = " ".join(p["text"] for p in paras if not p["section"])
        intro_first100 = _kw_norm(" ".join(words(intro_text)[:100]))
        checks = []
        if title and not any(_kw_match(k, title["text"]) for k in keywords):
            checks.append("title has no primary keyword")
        if not any(_kw_norm(k) in intro_first100 for k in keywords):
            checks.append("no exact primary keyword in first 100 words")
        rep.add("WARN" if checks else "PASS", "Title & intro keyword placement", "; ".join(checks) or "ok")
    else:
        rep.add("WARN", "Primary keywords", "no --keywords given; keyword checks skipped")

    all_kw = keywords + secondary
    if all_kw and body_heads:
        with_kw = [h for h in body_heads if any(_kw_match(k, h["text"]) for k in all_kw)]
        ratio = len(with_kw) / len(body_heads)
        rep.add("PASS" if ratio >= 0.4 else "WARN", "Keywords in headings",
                f"{len(with_kw)}/{len(body_heads)} body H2/H3s contain a primary/secondary keyword",
                [f"no keyword: {h['text']}" for h in body_heads if h not in with_kw])

    # 10. Sentence rhythm
    sents = [s for b in paras for s in sentences(b["text"]) if not b.get("list")]
    lengths = [len(words(s)) for s in sents]
    if len(lengths) >= 10:
        mean, sd = statistics.mean(lengths), statistics.pstdev(lengths)
        cv = sd / mean if mean else 0
        short = sum(1 for l in lengths if l <= 8)
        long_ = [s for s, l in zip(sents, lengths) if l > 35]
        runs, run = 0, 1
        for a, b in zip(lengths, lengths[1:]):
            run = run + 1 if abs(a - b) <= 3 else 1
            if run == 4:
                runs += 1
        issues = []
        if cv < 0.40:
            issues.append(f"low variation (CV {cv:.2f} < 0.40)")
        if short / len(lengths) < 0.10:
            issues.append(f"few short sentences ({short}/{len(lengths)} ≤8 words)")
        if runs:
            issues.append(f"{runs} run(s) of 4+ similar-length sentences")
        if long_:
            issues.append(f"{len(long_)} sentence(s) over 35 words")
        rep.add("WARN" if issues else "PASS", "Sentence-length variety",
                f"{len(lengths)} sentences, mean {mean:.1f}, sd {sd:.1f}, CV {cv:.2f}"
                + ("; " + "; ".join(issues) if issues else ""),
                [s[:140] for s in long_])

        # 11. Openers
        openers = [re.sub(r"[^a-z']", "", s.split()[0].lower()) for s in sents]
        oc = Counter(openers)
        heavy = [f"'{w}'×{c}" for w, c in oc.most_common()
                 if c >= 4 and c / len(openers) > 0.07 and w not in ("the", "a", "an")]
        consec = [f"'{a}' twice in a row near: {sents[i + 1][:60]}" for i, (a, b) in enumerate(zip(openers, openers[1:]))
                  if a == b and a not in ("",)]
        rep.add("WARN" if heavy or consec else "PASS", "Sentence openers",
                ("overused: " + ", ".join(heavy) if heavy else "no overused openers")
                + (f"; {len(consec)} consecutive repeat(s)" if consec else ""), consec)

    # 12. Paragraph length
    long_paras = [f"L{p['line']}: {len(words(p['text']))} words" for p in paras if len(words(p["text"])) > 100]
    rep.add("WARN" if long_paras else "PASS", "Paragraph length", f"{len(long_paras)} paragraph(s) over 100 words", long_paras)

    return rep


def _kw_norm(text):
    """Lowercase and treat hyphens as spaces, so 'AI-powered' matches 'ai powered'."""
    return re.sub(r"\s+", " ", text.lower().replace("-", " "))


def _kw_match(kw, text):
    """True if heading contains the keyword phrase, or all its meaningful words."""
    t = _kw_norm(text)
    if _kw_norm(kw) in t:
        return True
    toks = [w for w in re.findall(r"[a-z0-9]+", kw.lower()) if w not in STOPWORDS]
    ht = set(re.findall(r"[a-z0-9]+", t))
    return len(toks) >= 2 and all(w in ht or w.rstrip("s") in ht or w + "s" in ht for w in toks)


# ---------- output ----------

def render(rep):
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    out = ["| Status | Check | Result |", "|---|---|---|"]
    for r in rep.rows:
        out.append(f"| {icon[r['status']]} {r['status']} | {r['check']} | {r['detail'].replace('|', '/')} |")
    details = [r for r in rep.rows if r["hits"] and r["status"] != "PASS"]
    if details:
        out.append("\n## Details")
        for r in details:
            out.append(f"\n### {r['check']}")
            out.extend(f"- {h}" for h in r["hits"][:40])
            if len(r["hits"]) > 40:
                out.append(f"- …and {len(r['hits']) - 40} more")
    fails = sum(r["status"] == "FAIL" for r in rep.rows)
    warns = sum(r["status"] == "WARN" for r in rep.rows)
    out.append(f"\n**Summary:** {fails} fail, {warns} warn, {len(rep.rows) - fails - warns} pass")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--keywords", default="", help="primary keywords, separated by ';'")
    ap.add_argument("--secondary", default="", help="secondary keywords, separated by ';'")
    ap.add_argument("--min", type=int, default=1200)
    ap.add_argument("--max", type=int, default=1500)
    ap.add_argument("--banned", default=str(DEFAULT_BANNED))
    ap.add_argument("--competitors", default=str(DEFAULT_COMPETITORS))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        text = load_text(a.file)
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        print(f"Could not read {a.file}: {e}", file=sys.stderr)
        sys.exit(2)
    rep = run(text, split_keywords(a.keywords), split_keywords(a.secondary), a.min, a.max,
              load_phrase_file(a.banned), load_list(a.competitors))
    print(json.dumps(rep.rows, indent=2, ensure_ascii=False) if a.json else render(rep))
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
