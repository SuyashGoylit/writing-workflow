#!/usr/bin/env python3
"""Verify a Cloud4C case study LP against its sources and the LP template.

Usage:
    python3 verify_lp.py lp.md --sources sources/ [--lp-url URL] [--pdf-url URL] [--align align.md] [--json]
    python3 verify_lp.py "LP Revamp.docx" --pdf case.pdf --lp lp_source.md [--pdf-url URL]

--sources is the folder sourcetext.py wrote (pdf.txt, lp.txt, facts.json). Without it,
pass --pdf (and --lp) and the sources are extracted on the fly.

Checks: template structure and fixed copy, the source links at the top, every figure against
the sources (value and qualifier), headline figures used, names and technologies that are not
in the sources, real client names, meaning drift against the closest source sentence, source
points left out, wording copied from the PDF or LP, dashes, banned phrases, US spelling.
--align writes each LP sentence next to its closest source sentence, for the claim audit.
Standard library only. Exit code: 0 = no FAIL, 1 = at least one FAIL, 2 = bad input.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parents[1] / "_shared"))  # repo layout; the zip has these in scripts/
import lpformat as L  # noqa: E402
import sourcetext as S  # noqa: E402


def _first(*paths):
    return next((p for p in paths if p.exists()), paths[0])


TEMPLATE = _first(HERE.parent / "template.md", HERE.parents[1] / "case-study-lp" / "template.md")
BANNED = _first(HERE.parent / "banned_phrases.txt", HERE.parents[1] / "blog-audit" / "banned_phrases.txt")

COUNT_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
REGION_CODES = {"MEA", "APAC", "Europe", "Americas", "India"}
ALLOW_STRONG = {"cloud4c", "pdf", "mea", "apac", "emea", "latam", "it", "lp"}
NEVER = ["Capgemini"]
DASH_RE = re.compile(r"[—–]|(?<=\w) - (?=\w)|(?<=\w) -- (?=\w)")
BRIT_RE = re.compile(
    r"\b\w*(?:organis|optimis|modernis|digitis|standardis|prioritis|minimis|maximis|utilis|customis|"
    r"authoris|realis|recognis|centralis|virtualis|containeris|monetis|operationalis|synchronis|"
    r"visualis|mobilis|finalis|summaris|categoris|harmonis|normalis|stabilis|rationalis|localis|"
    r"personalis|specialis|industrialis|initialis|emphasis)(?:e|ed|es|ing|ation|ations|er|ers)\b"
    r"|\b\w*centres?\b|\b\w*metres?\b|\banalys(?:e|ed|es|ing)\b|\b(?:colour|behaviour|favour|labour|"
    r"honour|endeavour)\w*|\bprogrammes?\b|\bcatalogues?\b|\blicences?\b|\b(?:defence|offence)s?\b|"
    r"\btravell(?:ed|ing|er)\b|\bmodell(?:ed|ing)\b|\bcancell(?:ed|ing)\b|\bageing\b|\bwhilst\b|"
    r"\bamongst\b|\bjudgement\b", re.I)

QUAL_RANK = {"max": 0, "approx": 1, "exact": 2, "plus": 3}
QUAL_WORD = {"max": "up to / under", "approx": "approximately", "exact": "exact", "plus": "over / +"}


class Report:
    def __init__(self):
        self.rows = []

    def add(self, check, status, detail, hits=None):
        self.rows.append({"check": check, "status": status, "detail": detail, "hits": hits or []})

    @property
    def failed(self):
        return any(r["status"] == "FAIL" for r in self.rows)


def worst(*statuses):
    return "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"


# ---------- loading ----------

def load_sources(a):
    if a.sources:
        d = Path(a.sources)
        pdf = (d / "pdf.txt").read_text(encoding="utf-8")
        lp = (d / "lp.txt").read_text(encoding="utf-8") if (d / "lp.txt").exists() else ""
        facts = json.loads((d / "facts.json").read_text(encoding="utf-8")) if (d / "facts.json").exists() else None
        if facts is None:
            paras = [p for p in pdf.split("\n\n") if p.strip()]
            facts = S.build_facts(paras, lp, [], [], S.load_client_names(a.client_names))
        return pdf, lp, facts
    if not a.pdf:
        raise ValueError("give --sources DIR, or --pdf (and --lp)")
    paras, lp, facts = S.extract(a.pdf, a.lp, None, a.client_names)
    return "\n\n".join(paras), lp, facts


def fixed_blocks():
    """Every template line without a {{slot}}: (section, normalised text)."""
    out = []
    for b in L.parse_md(TEMPLATE.read_text(encoding="utf-8")):
        if "{{" in b["md"] or b["kind"] in ("h1", "table"):
            continue
        if b["kind"] == "h2":
            continue  # section order is checked separately
        out.append((b["section"], b["kind"], L.norm(b["text"])))
    return out


# ---------- structure ----------

def check_structure(rep, blocks, a, md_text):
    secs = L.sections(blocks)

    # Section order
    h2s = [b["text"] for b in blocks if b["kind"] == "h2"]
    got = [L.norm(h).lower() for h in h2s]
    want = [h.lower() for h in L.H2_ORDER]
    missing = [h for h in L.H2_ORDER if h.lower() not in got]
    extra = [h for h in h2s if L.norm(h).lower() not in want]
    order_ok = [g for g in got if g in want] == [w for w in want if w in got]
    hits = [f"missing: {h}" for h in missing] + [f"extra H2: {h}" for h in extra]
    if not order_ok:
        hits.append("sections out of order: " + " → ".join(h2s))
    rep.add("Template sections", "FAIL" if missing or not order_ok else "WARN" if extra else "PASS",
            f"{len(h2s)} H2 sections" + (f", {len(missing)} missing" if missing else ""), hits)

    # Fixed copy
    miss = []
    for sec, kind, text in fixed_blocks():
        if not any(L.norm(b["text"]) == text for b in secs.get(sec, [])):
            near = [b for b in secs.get(sec, []) if b["kind"] == kind]
            miss.append(f"[{sec}] missing or changed: \"{text}\"" + (f" (line {near[0]['line']} has a {kind})" if near else ""))
    rep.add("Fixed template copy", "FAIL" if miss else "PASS",
            f"{len(miss)} fixed lines missing or reworded" if miss else "all fixed UI copy present and verbatim", miss)

    # Unfilled slots / leftover comments
    slots = [f"line {i}: {l.strip()[:80]}" for i, l in enumerate(md_text.splitlines(), 1) if "{{" in l or "}}" in l]
    rep.add("Unfilled slots", "FAIL" if slots else "PASS", f"{len(slots)} unfilled" if slots else "none", slots)

    # Source links at the top
    st, hits = [], []
    links = L.source_links(blocks)
    first = next((b for b in blocks), None)
    for name, given in (("LP", a.lp_url), ("PDF", a.pdf_url)):
        url = links.get(name)
        if not url:
            st.append("FAIL"); hits.append(f"no '**Original {name}:** <link>' line at the top")
        elif not url.startswith("http"):
            st.append("FAIL"); hits.append(f"Original {name} is not a link: {url}")
        elif given and url.rstrip("/") != given.strip().rstrip("/"):
            st.append("FAIL"); hits.append(f"Original {name} {url} ≠ the link given {given}")
        elif "cloud4c.com" not in url:
            st.append("WARN"); hits.append(f"Original {name} is not on cloud4c.com: {url}")
    if links.get("PDF", "").startswith("http") and not links["PDF"].lower().endswith(".pdf"):
        st.append("FAIL"); hits.append(f"Original PDF does not end in .pdf: {links['PDF']}")
    if links and first is not None and first["kind"] != "source":
        st.append("WARN"); hits.append("the source links should be the first lines of the document")
    rep.add("Source links at top", worst(*st),
            " / ".join(f"{k}: {v}" for k, v in sorted(links.items())) or "missing", hits)

    hero = secs.get("hero", [])
    st, hits = [], []
    h1 = [b for b in hero if b["kind"] == "h1"]
    if len(h1) != 1:
        st.append("FAIL"); hits.append(f"expected one H1, found {len(h1)}")
    elif not 50 <= len(h1[0]["text"]) <= 100:
        st.append("WARN"); hits.append(f"H1 is {len(h1[0]['text'])} characters (aim for 60-90)")
    lede = [b for b in hero if b.get("role") == "lede"]
    if not lede:
        st.append("FAIL"); hits.append("no lede paragraph directly under the H1")
    else:
        n_w = len(L.words(lede[0]["text"]))
        n_s = len(re.findall(r"[.!?](?:\s|$)", lede[0]["text"]))
        if n_w > 45 or n_s > 2:
            st.append("WARN"); hits.append(f"lede is {n_w} words / {n_s} sentences (max 45 / 2)")
    tags = [b for b in hero if b["kind"] == "tags"]
    if not tags:
        st.append("FAIL"); hits.append("no bold tag line 'Case study  |  Industry  |  Service  |  Region'")
    else:
        parts = [p.strip() for p in tags[0]["text"].split("|")]
        if len(parts) != 4 or not all(parts):
            st.append("FAIL"); hits.append(f"tag line needs 4 parts, has {len(parts)}: {tags[0]['text']}")
        elif parts[3] not in REGION_CODES:
            st.append("WARN"); hits.append(f"region code '{parts[3]}' is not one of {sorted(REGION_CODES)}")
        if "&" in tags[0]["text"]:
            st.append("WARN"); hits.append("write the industry in words ('Oil and Gas', not 'Oil & Gas')")
    read = [b for b in hero if b["kind"] == "note" and re.fullmatch(r"\d+-minute read", b["text"])]
    minutes, n = L.read_minutes(blocks)
    if not read:
        st.append("FAIL"); hits.append("no '*N-minute read*' line")
    elif read[0]["text"] != f"{minutes}-minute read":
        st.append("WARN"); hits.append(f"says '{read[0]['text']}', the story is {n} words ≈ {minutes} minutes (build_docx.py fixes this)")
    tables = [b for b in hero if b["kind"] == "table"]
    want_rows = ["Client", "Sector", "Region", "Technology", "Cloud4C role"]
    if not tables:
        st.append("FAIL"); hits.append("no fact table")
    else:
        rows = tables[0]["rows"]
        labels = [r[0] for r in rows[1:]]
        if labels != want_rows:
            st.append("FAIL"); hits.append(f"fact table rows should be {want_rows}, found {labels}")
        empty = [r[0] for r in rows[1:] if len(r) < 2 or not r[1].strip()]
        if empty:
            st.append("FAIL"); hits.append(f"empty fact table cells: {empty}")
    rep.add("Hero and fact table", worst(*st), "OK" if not hits else f"{len(hits)} issue(s)", hits)

    # Story cards
    story = secs.get("story", [])
    st, hits = [], []
    labels_at = [i for i, b in enumerate(story) if b["kind"] == "card_label"]
    if len(labels_at) != 3:
        st.append("FAIL"); hits.append(f"expected 3 story cards, found {len(labels_at)}")
    for j, i in enumerate(labels_at):
        end = labels_at[j + 1] if j + 1 < len(labels_at) else len(story)
        card = story[i + 1:end]
        head = [b for b in card if b["kind"] == "bold"]
        bullets = [b for b in card if b["kind"] == "bullet"]
        name = story[i]["text"]
        if not head:
            st.append("FAIL"); hits.append(f"{name}: no bold headline")
        elif len(L.words(head[0]["text"])) > 14:
            st.append("WARN"); hits.append(f"{name}: headline is {len(L.words(head[0]['text']))} words (max 14)")
        if len(bullets) != 3:
            st.append("FAIL"); hits.append(f"{name}: {len(bullets)} bullets (need exactly 3)")
        for bl in bullets:
            if len(L.words(bl["text"])) > 15:
                st.append("WARN"); hits.append(f"{name}: bullet over 15 words: {bl['text'][:70]}")
    rep.add("Story cards", worst(*st), "3 cards × headline + 3 bullets" if not hits else f"{len(hits)} issue(s)", hits)

    # About
    about = [b for b in secs.get("about", []) if b["kind"] == "para"]
    st, hits = [], []
    if len(about) < 2:
        st.append("FAIL"); hits.append(f"{len(about)} paragraph(s), need 2")
    elif len(about) > 2:
        st.append("WARN"); hits.append(f"{len(about)} paragraphs, template has 2")
    for b in about:
        n_w = len(L.words(b["text"]))
        if not 35 <= n_w <= 80:
            st.append("WARN"); hits.append(f"line {b['line']}: {n_w} words (aim for 35-80)")
    rep.add("About the client", worst(*st), f"{len(about)} paragraphs", hits)

    # Challenge
    ch = secs.get("challenge", [])
    st, hits = [], []
    boxes = [i for i, b in enumerate(ch) if b["kind"] == "checkbox"]
    n_items = len(boxes)
    lead = next((b for b in ch if b["kind"] == "bold"), None)
    if not lead:
        st.append("FAIL"); hits.append("no bold lead sentence with the number of challenges")
    else:
        first = L.words(lead["text"])[0].lower() if L.words(lead["text"]) else ""
        count = COUNT_WORDS.get(first) or (int(first) if first.isdigit() else None)
        if count is None:
            st.append("FAIL"); hits.append(f"lead should open with the count ('{_num_word(n_items)} …'): {lead['text'][:70]}")
        elif count != n_items:
            st.append("FAIL"); hits.append(f"lead says {first} but there are {n_items} ☐ items")
    if not 3 <= n_items <= 6:
        st.append("WARN" if n_items >= 2 else "FAIL"); hits.append(f"{n_items} challenge items (usually 3-6)")
    for i in boxes:
        title = re.sub(r"^☐\s*", "", ch[i]["text"])
        if not title.endswith("."):
            st.append("WARN"); hits.append(f"line {ch[i]['line']}: challenge title should end with a full stop")
        nxt = ch[i + 1] if i + 1 < len(ch) else None
        if not nxt or nxt.get("role") != "challenge_text":
            st.append("FAIL"); hits.append(f"line {ch[i]['line']}: no paragraph under '{title[:50]}'")
        else:
            n_w = len(L.words(nxt["text"]))
            if not 20 <= n_w <= 80:
                st.append("WARN"); hits.append(f"line {nxt['line']}: challenge paragraph is {n_w} words (aim for 30-70)")
    ticked = next((b for b in ch if b["kind"] == "labelled" and b["text"].startswith("Once ticked:")), None)
    if not ticked:
        st.append("FAIL"); hits.append("no 'Once ticked:' line")
    else:
        m = re.search(r"(\d+) of (\d+) sound familiar\. Talk to someone who has solved them\.", L.norm(ticked["text"]))
        if not m:
            st.append("FAIL"); hits.append(f"'Once ticked' copy changed: {ticked['text']}")
        elif int(m.group(2)) != n_items:
            st.append("FAIL"); hits.append(f"'Once ticked' says {m.group(1)} of {m.group(2)}, but there are {n_items} items")
    rep.add("Challenge", worst(*st), f"{n_items} challenge items", hits)

    # Solution
    so = secs.get("solution", [])
    st, hits = [], []
    if not so[1:2] or so[1]["kind"] != "bold":
        st.append("FAIL"); hits.append("the section should open with one bold lead sentence")
    h3 = [i for i, b in enumerate(so) if b["kind"] == "h3"]
    if len(h3) < 2:
        st.append("FAIL"); hits.append(f"{len(h3)} solution steps (need 4-6 H3s)")
    elif not 4 <= len(h3) <= 6:
        st.append("WARN"); hits.append(f"{len(h3)} solution steps (template uses 4-6)")
    for i in h3:
        if not so[i]["text"].endswith("."):
            st.append("WARN"); hits.append(f"line {so[i]['line']}: H3 should end with a full stop")
        nxt = so[i + 1] if i + 1 < len(so) else None
        if not nxt or nxt["kind"] != "para":
            st.append("FAIL"); hits.append(f"line {so[i]['line']}: no paragraph under '{so[i]['text'][:50]}'")
        elif not 20 <= len(L.words(nxt["text"])) <= 70:
            st.append("WARN"); hits.append(f"line {nxt['line']}: {len(L.words(nxt['text']))} words (aim for 25-60)")
    cta = [b for b in so if b.get("role") == "cta"]
    if not cta or not cta[0]["text"].startswith("How ready is your"):
        st.append("FAIL"); hits.append("no bold readiness line 'How ready is your … for …?'")
    rep.add("Solution", worst(*st), f"{len(h3)} solution steps", hits)

    # Results
    rs = secs.get("results", [])
    st, hits = [], []
    bullets = [b for b in rs if b["kind"] == "bullet"]
    if len(bullets) < 3:
        st.append("FAIL"); hits.append(f"{len(bullets)} results (need 4-8)")
    elif not 4 <= len(bullets) <= 8:
        st.append("WARN"); hits.append(f"{len(bullets)} results (template uses 4-8)")
    for b in bullets:
        if not re.match(r"^\*\*[^*]+\.\*\*\s+\S", b["md"]):
            st.append("FAIL"); hits.append(f"line {b['line']}: needs '**Label.** sentence': {b['md'][:60]}")
    la = [b for b in rs if b.get("role") == "looking_ahead"]
    if not la:
        st.append("FAIL"); hits.append("no '**Looking ahead.**' paragraph")
    elif not 40 <= len(L.words(la[0]["text"])) <= 100:
        st.append("WARN"); hits.append(f"Looking ahead is {len(L.words(la[0]['text']))} words (aim for 50-90)")
    rep.add("Results and looking ahead", worst(*st), f"{len(bullets)} results", hits)

    # Compare
    cp = secs.get("compare", [])
    st, hits = [], []
    line = next((b for b in cp if b["kind"] == "para"), None)
    if not line or not line["text"].startswith("Five quick questions to see how ready your"):
        st.append("FAIL"); hits.append("supporting line should start 'Five quick questions to see how ready your …'")
    qs = [i for i, b in enumerate(cp) if b.get("role") == "question"]
    if len(qs) != 5:
        st.append("FAIL"); hits.append(f"{len(qs)} questions (need exactly 5)")
    for i in qs:
        q = cp[i]
        n_w = len(L.words(q["text"]))
        if not L.whole(q["md"], "**") or not q["text"].endswith("?"):
            st.append("FAIL"); hits.append(f"line {q['line']}: question must be bold and end with '?'")
        if n_w > 14:
            st.append("FAIL"); hits.append(f"line {q['line']}: {n_w} words (max 10)")
        elif n_w > 10:
            st.append("WARN"); hits.append(f"line {q['line']}: {n_w} words (max 10)")
        nxt = cp[i + 1] if i + 1 < len(cp) else None
        if nxt and nxt.get("role") == "question_help":
            help_ = nxt
            n_h = len(L.words(help_["text"]))
            if not 8 <= n_h <= 20:
                st.append("WARN"); hits.append(f"line {help_['line']}: help line is {n_h} words (aim for 8-20)")
            if help_["text"].rstrip().endswith("?") or not help_["text"].rstrip().endswith("."):
                st.append("WARN"); hits.append(f"line {help_['line']}: help line should be a statement ending with a full stop")
            qw = {w.lower() for w in L.words(q["text"])}
            hw = [w.lower() for w in L.words(help_["text"])]
            if hw and sum(w in qw for w in hw) / len(hw) > 0.7:
                st.append("WARN"); hits.append(f"line {help_['line']}: help line mostly repeats the question")
            nxt = cp[i + 2] if i + 2 < len(cp) else None
        else:
            st.append("FAIL"); hits.append(f"line {q['line']}: no italic help line under the question")
        if not nxt or nxt["kind"] != "toggle":
            st.append("FAIL"); hits.append(f"line {q['line']}: no 'Not started | In progress | In place' line after it")
    rep.add("Compare questions", worst(*st), f"{len(qs)} questions with help lines", hits)

    # Similar + next step
    st, hits = [], []
    sim = secs.get("similar", [])
    if len([b for b in sim if b["kind"] not in ("h2",)]) > 2:
        st.append("WARN"); hits.append("Similar case studies should only hold the dev-team note and the button")
    nx = secs.get("next", [])
    urls = [b for b in nx if b["kind"] == "url"]
    if not urls:
        st.append("FAIL"); hits.append("no PDF URL under 'The full case study'")
    else:
        u = urls[0]["text"]
        if not u.lower().endswith(".pdf"):
            st.append("FAIL"); hits.append(f"PDF URL does not end in .pdf: {u}")
        if a.pdf_url and u.strip() != a.pdf_url.strip():
            st.append("FAIL"); hits.append(f"PDF URL {u} ≠ the case study's PDF {a.pdf_url}")
        if "cloud4c.com" not in u:
            st.append("WARN"); hits.append(f"PDF URL is not on cloud4c.com: {u}")
    more = [b for b in nx if b["kind"] == "h3" and re.fullmatch(r"More stories in .+\.", b["text"])]
    if not more:
        st.append("FAIL"); hits.append("no 'More stories in <industry>.' heading")
    rep.add("Next step and links", worst(*st), urls[0]["text"] if urls else "no PDF link", hits)


def _num_word(n):
    return next((w.capitalize() for w, v in COUNT_WORDS.items() if v == n), str(n))


# ---------- content scope ----------

FIXED_TEXTS = None


def variable_blocks(blocks, include_compare=False):
    """Blocks written for this case study (not fixed UI copy)."""
    global FIXED_TEXTS
    if FIXED_TEXTS is None:
        FIXED_TEXTS = {t for _, _, t in fixed_blocks()}
    keep_secs = {"hero", "story", "about", "challenge", "solution", "results"}
    if include_compare:
        keep_secs.add("compare")
    out = []
    for b in blocks:
        if b["section"] not in keep_secs or b["kind"] in ("h2", "button", "card_label", "toggle", "url", "source"):
            continue
        if L.norm(b["text"]) in FIXED_TEXTS or b["kind"] in ("labelled",):
            continue
        if b["kind"] == "note":
            continue
        if b["section"] == "compare" and b["kind"] == "h3":
            continue
        out.append(b)
    return out


def scope_text(blk):
    return "\n".join(b["text"] for b in blk)


# ---------- figures ----------

def check_figures(rep, blocks, pdf, lp, facts):
    scope = variable_blocks(blocks)
    pdf_figs = S.figures(pdf, "pdf")
    lp_figs = S.figures(lp, "lp") if lp else []
    by_pdf, by_lp = {}, {}
    for f in pdf_figs:
        by_pdf.setdefault(f["key"], []).append(f)
    for f in lp_figs:
        by_lp.setdefault(f["key"], []).append(f)
    values_pdf = {}
    for f in pdf_figs + lp_figs:
        values_pdf.setdefault(f["value"], set()).add(f["key"])

    hits, statuses, used = [], [], set()
    for b in scope:
        for f in S.figures(b["text"], "lp-draft"):
            key, q = f["key"], f["qual"]
            if key == "247" and "247" not in pdf + lp:
                continue  # reported below as a lost 24/7 slash
            used.add(key)
            where = f"line {b['line']}"
            src_p, src_l = by_pdf.get(key, []), by_lp.get(key, [])
            if not src_p and not src_l:
                other = sorted(values_pdf.get(f["value"], set()) - {key})
                if other and not f["unit"]:
                    statuses.append("WARN")
                    hits.append(f"{where}: '{f['raw']}' has no unit; sources say {other} | …{f['context']}…")
                else:
                    statuses.append("FAIL")
                    hint = f" (sources have {other})" if other else ""
                    hits.append(f"{where}: '{f['raw']}' NOT IN SOURCES{hint} | …{f['context']}…")
                continue
            quals_p = {x["qual"] for x in src_p}
            quals_l = {x["qual"] for x in src_l}
            if q in quals_p or (not src_p and q in quals_l):
                if not src_p:
                    hits.append(f"{where}: '{f['raw']}' matches the LP only (not in the PDF); fine, but tell the writer")
                continue
            ref = quals_p or quals_l
            src = src_p[0] if src_p else src_l[0]
            best = max(ref, key=lambda x: QUAL_RANK[x])
            lp_note = f" (the LP says '{QUAL_WORD[q]}', but the PDF wins)" if q in quals_l else ""
            if q == "max" and "max" not in ref:
                statuses.append("FAIL")
                hits.append(f"{where}: '{f['raw']}' adds 'up to / under', which changes the source ('{QUAL_WORD[best]}') | source: …{src['context']}…")
            elif q == "exact" and best == "approx":
                statuses.append("FAIL")
                hits.append(f"{where}: '{f['raw']}' drops 'approximately'{lp_note} | source: …{src['context']}…")
            elif QUAL_RANK[q] > QUAL_RANK[best]:
                statuses.append("FAIL")
                hits.append(f"{where}: '{f['raw']}' overstates the source ('{QUAL_WORD[best]}'){lp_note} | source: …{src['context']}…")
            else:
                statuses.append("FAIL")
                hits.append(f"{where}: '{f['raw']}' drops the source's qualifier ('{QUAL_WORD[best]}'), which changes the claim{lp_note} | source: …{src['context']}…")
    for b in scope:
        for m in re.finditer(r"\b247\b", b["text"]):
            if "247" not in pdf + lp:
                statuses.append("FAIL")
                hits.append(f"line {b['line']}: '247' looks like '24/7' with the slash lost in PDF extraction")
    n_figs = len(used)
    rep.add("Figures match sources", worst(*statuses),
            f"{n_figs} distinct figures checked" + (f", {statuses.count('FAIL')} fail" if "FAIL" in statuses else ""), hits)

    headline = set(facts.get("headline_figures") or [])
    missing = sorted(k for k in headline if k not in used)
    unused = sorted({f["key"] for f in pdf_figs + lp_figs} - used - headline)
    hits = [f"headline figure not used: {k} | …{_ctx_for(k, pdf_figs + lp_figs)}…" for k in missing]
    if unused:
        hits.append(f"(info) other source figures not used: {', '.join(unused[:25])}")
    rep.add("Headline figures used", "FAIL" if missing else "PASS",
            f"{len(headline) - len(missing)}/{len(headline)} headline figures used"
            + (f"; {len(unused)} other source figures left out" if unused else ""), hits)


def _ctx_for(key, figs):
    return next((f["context"] for f in figs if f["key"] == key), "")


# ---------- names and technologies ----------

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[/&.+-][A-Za-z0-9]+)*")


def check_entities(rep, blocks, pdf, lp, names):
    src = L.norm(pdf + "\n" + lp).lower()
    scope = variable_blocks(blocks, include_compare=True)
    strong, weak = {}, {}
    for b in scope:
        text = L.norm(b["text"])
        skip_weak = b["kind"] in ("h1", "h3", "tags", "table", "bold") or b["section"] == "compare"
        for m in TOKEN_RE.finditer(text):
            tok = m.group().rstrip(".")
            low = tok.lower()
            caps = sum(c.isupper() for c in tok)
            is_strong = caps >= 2 or (re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok)) \
                or re.search(r"[a-z][A-Z]", tok)
            if is_strong:
                if low in ALLOW_STRONG or _in_source(low, src):
                    continue
                strong.setdefault(tok, b["line"])
                continue
            if skip_weak or not tok[0].isupper():
                continue
            before = re.sub(r"[\s\"'*(☐]+$", "", text[:m.start()])
            if not before or before[-1] in ".!?:;|":
                continue  # sentence start
            if _in_source(low, src) or all(_in_source(part, src) for part in low.split("-")):
                continue
            weak.setdefault(tok, b["line"])
    hits = [f"line {ln}: '{t}' is not in the PDF or LP (invented product, acronym or name?)" for t, ln in strong.items()]
    hits += [f"line {ln}: '{t}' (capitalised) is not in the sources; check it" for t, ln in weak.items()]
    rep.add("Names and technologies", "FAIL" if strong else "WARN" if weak else "PASS",
            f"{len(strong)} unsupported terms, {len(weak)} to check" if strong or weak else
            "every product, acronym and name appears in the sources", hits)

    found = S.find_names("\n".join(b["text"] for b in blocks), names + NEVER)
    hits = [f"'{h['name']}' in the LP | …{h['context']}…" for h in found]
    src_found = S.find_names(pdf + "\n" + lp, names)
    if src_found and not found:
        hits.append(f"(info) the sources name the real client ({src_found[0]['name']}); the LP correctly leaves it out")
    rep.add("Client anonymity", "FAIL" if found else "PASS",
            "real client name or Capgemini in the LP" if found else "no real client names", hits)


def _in_source(low, src):
    """Whole-word match, allowing a plural 's' and hyphen/space variants."""
    variants = {low, low.replace("-", " "), low.replace("-", "")}
    if low.endswith("s"):
        variants.add(low[:-1])
    return any(re.search(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9])", src) for v in variants)


# ---------- duplication ----------

def _tokens(text):
    text = L.norm(text).lower().replace("'s ", " ")
    return re.findall(r"[a-z0-9]+", text)


def _source_tokens(text):
    lines = [re.sub(r"^(?:#+\s*|-\s+|Breadcrumb:\s*)", "", l) for l in text.splitlines()]
    return _tokens("\n".join(lines))


def common_runs(d, s, min_len=7):
    pos = {}
    for j, t in enumerate(s):
        pos.setdefault(t, []).append(j)
    runs, i = [], 0
    while i < len(d):
        best = 0
        for j in pos.get(d[i], []):
            k = 0
            while i + k < len(d) and j + k < len(s) and d[i + k] == s[j + k]:
                k += 1
            best = max(best, k)
        if best >= min_len:
            runs.append((best, " ".join(d[i:i + best])))
            i += best
        else:
            i += 1
    return runs


def overlap(d, s, n=8):
    dg = {tuple(d[i:i + n]) for i in range(len(d) - n + 1)}
    sg = {tuple(s[i:i + n]) for i in range(len(s) - n + 1)}
    return len(dg & sg) / len(dg) if dg else 0.0


def check_duplication(rep, blocks, pdf, lp):
    secs = L.sections(blocks)
    parts = {
        "About": [b for b in secs.get("about", []) if b["kind"] == "para"],
        "Challenge": [b for b in secs.get("challenge", []) if b["kind"] in ("bold", "checkbox") or b.get("role") == "challenge_text"],
        "Solution": [b for b in secs.get("solution", []) if b["kind"] in ("bold", "h3", "para") and b.get("role") != "cta"],
        "Looking ahead": [b for b in secs.get("results", []) if b.get("role") == "looking_ahead"],
    }
    sources = {"PDF": _source_tokens(pdf), "LP": _source_tokens(lp)} if lp else {"PDF": _source_tokens(pdf)}
    statuses, hits, summary = [], [], []
    for name, blk in parts.items():
        # runs are found per block, so a heading and the paragraph under it never join up
        per_block = [_tokens(re.sub(r"^Looking ahead\.\s*", "", b["text"])) for b in blk]
        d = [t for toks in per_block for t in toks]
        if not d:
            continue
        worst_run, worst_ov = 0, 0.0
        for sname, s in sources.items():
            runs = [r for toks in per_block for r in common_runs(toks, s)]
            ov = overlap(d, s)
            longest = max((r[0] for r in runs), default=0)
            worst_run, worst_ov = max(worst_run, longest), max(worst_ov, ov)
            for ln, txt in runs:
                level = "FAIL" if ln >= 10 else "WARN"
                statuses.append(level)
                hits.append(f"{name} vs {sname}: {ln}-word run copied: \"{txt}\"")
            if ov > 0.10:
                statuses.append("FAIL"); hits.append(f"{name} vs {sname}: {ov:.0%} of 8-word phrases also in the {sname} (max 10%)")
            elif ov > 0.05:
                statuses.append("WARN"); hits.append(f"{name} vs {sname}: {ov:.0%} of 8-word phrases also in the {sname}")
        summary.append(f"{name} {worst_run}w/{worst_ov:.0%}")
    rep.add("Not copied from PDF/LP", worst(*statuses),
            "longest copied run / 8-gram overlap: " + ", ".join(summary), hits)


# ---------- meaning ----------
# The script can't read meaning, but it can point at the words that usually carry it. Each LP
# sentence is paired with its closest source sentence, and words that set scope, certainty,
# obligation, time or cause are compared. Every hit is a place for the claim audit to look.

MEANING_WORDS = [  # (class, canonical, pattern); the canonical form is what gets compared
    ("scope", "all/entire", r"all|entire(?:ly)?|every(?:thing)?|full(?:y)?|complete(?:ly)?|whole|end[ -]to[ -]end"),
    ("scope", "only", r"only|solely"), ("scope", "specifically", r"specific(?:ally)?"),
    ("scope", "core", r"core"), ("scope", "some", r"some"), ("scope", "most", r"most(?:ly)?"),
    ("scope", "rest", r"(?:the )?rest of"), ("scope", "partial", r"partial(?:ly)?"),
    ("hedge", "approximately", r"approximately|approx\.?|roughly"), ("hedge", "nearly", r"near(?:ly)?|almost"),
    ("hedge", "over", r"(?:over|more than|upwards of) (?=\d)"), ("hedge", "up to", r"(?:up to|less than|under) (?=\d)"),
    ("hedge", "significantly", r"significant(?:ly)?|substantial(?:ly)?"),
    ("modality", "need", r"need(?:s|ed|ing)?|requir(?:e|es|ed|ing)"), ("modality", "want", r"want(?:s|ed)?|sought"),
    ("modality", "must", r"must|had to|has to|have to"),
    ("modality", "will", r"will|would|plan(?:s|ned)? to"), ("modality", "may", r"may|might"),
    ("negation", "not", r"not|no longer|[a-z]+n't|cannot"), ("negation", "no", r"no|none|nothing"),
    ("negation", "never", r"never"),
    ("absolute", "zero", r"zero"), ("absolute", "always", r"always|at all times|without fail"),
    ("absolute", "eliminate", r"eliminat(?:e|es|ed|ing)|clear(?:s|ed|ing)?|remov(?:e|es|ed|ing)|solv(?:e|es|ed|ing)"), ("absolute", "guarantee", r"guarantee(?:s|d)?"),
    ("absolute", "unacceptable", r"unacceptable"),
    ("time", "earlier", r"earlier|previously|years ago|years earlier"),
    ("time", "periodic", r"periodic(?:ally)?|regular(?:ly)?|ongoing|routine(?:ly)?"),
    ("time", "first", r"first|starting with|initial(?:ly)?|to begin with"), ("time", "later", r"later|next phase|eventually"),
    ("time", "already", r"already"), ("time", "until", r"until|till"),
    ("cause", "because", r"because|due to|given|so|therefore|thus|hence|led to|leads? to|leading to"
                         r"|result(?:s|ed|ing)? in|enabl(?:e|es|ed|ing)|allow(?:s|ed|ing)?|ensur(?:e|es|ed|ing)"),
]
MEANING_RE = [(c, k, re.compile(rf"(?<![a-z0-9])(?:{p})(?![a-z0-9])")) for c, k, p in MEANING_WORDS]
# Dropping one of these narrows or flips the claim; dropping others (like "core") is usually
# just the LP sentence covering part of a longer source sentence.
DROP_MATTERS = {"approximately", "nearly", "over", "up to", "only", "specifically", "not", "never", "earlier"}
STOP = set("""a an the and or of to in on for with by at from as is are was were be been being it its this
that these those their them they he she his her our your we you i into onto than then there which who whom
whose what when where while across through over under up out about also more less has have had do does did
not no so such each other any all both very can could will would may might must""".split())


def _sentences(text, headings=True):
    if not headings:
        text = re.sub(r"^#+\s.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:#+\s*|[-*]\s+|\d+[.)]\s+)", "", text, flags=re.M)
    out = []
    for para in re.split(r"\n\s*\n|\n(?=\S)", text):
        para = L.norm(para)
        if not para or para.lower().startswith(("breadcrumb:", "www.")):
            continue
        out += [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9☐\"“])", para) if x.strip()]
    return out


def _stem(w):
    for suf in ("ing", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def _content(text):
    return {_stem(t) for t in _tokens(text) if t not in STOP and len(t) > 2}


def _meaning(text):
    low = " " + L.norm(text).lower().replace("’", "'") + " "
    return {(c, k) for c, k, rx in MEANING_RE if rx.search(low)}


def source_sentences(pdf, lp):
    out = []
    for name, text in (("PDF", pdf), ("LP", lp)):
        body = set(_sentences(text or "", headings=False))
        for sent in _sentences(text or ""):
            c = _content(sent)
            if len(c) >= 3:
                out.append({"src": name, "text": sent, "content": c, "meaning": _meaning(sent),
                            "heading": sent not in body})
    return out


def lp_sentences(blocks):
    out = []
    for b in variable_blocks(blocks):
        if b["kind"] not in ("para", "bold", "bullet", "checkbox", "h3"):
            continue
        text = re.sub(r"^☐\s*", "", b["text"])
        for sent in _sentences(text):
            c = _content(sent)
            if len(c) >= 3:
                out.append({"line": b["line"], "section": b["section"], "text": sent,
                            "content": c, "meaning": _meaning(sent)})
    return out


def align(lp_sents, src_sents):
    """Pair each LP sentence with its two closest source sentences (by shared content words)."""
    for s in lp_sents:
        scored = sorted(((len(s["content"] & x["content"]) / len(s["content"]), i)
                         for i, x in enumerate(src_sents)), reverse=True)
        s["matches"] = [(round(sc, 2), src_sents[i]) for sc, i in scored[:2] if sc > 0]
    return lp_sents


def check_meaning(rep, blocks, pdf, lp, facts, align_path=None):
    src = source_sentences(pdf, lp)
    sents = align(lp_sentences(blocks), src)
    hits, n_flagged, rows = [], 0, []
    for s in sents:
        flags = []
        if not s["matches"] or s["matches"][0][0] < 0.3:
            flags.append("no close source sentence: check that the claim is in the sources")
        else:
            best = s["matches"][0][1]
            # a runner-up counts only when it fits almost as well (the sentence merges two sources)
            near = set().union(*(m[1]["meaning"] for m in s["matches"] if m[0] >= s["matches"][0][0] * 0.8))
            added = sorted(k for c, k in s["meaning"] - near)
            dropped = sorted(k for c, k in best["meaning"] - s["meaning"]
                             if k in DROP_MATTERS and s["matches"][0][0] >= 0.4)
            if added:
                flags.append("adds " + ", ".join(f"'{k}'" for k in added))
            if dropped:
                flags.append("drops " + ", ".join(f"'{k}'" for k in dropped))
        if flags:
            n_flagged += 1
            m = s["matches"][0] if s["matches"] else (0, {"src": "-", "text": "(none)"})
            hits.append(f"line {s['line']}: {'; '.join(flags)} | LP: \"{s['text']}\" | "
                        f"{m[1]['src']}: \"{m[1]['text']}\"")
        rows.append((s, flags))
    rep.add("Meaning watch", "WARN" if hits else "PASS",
            f"{n_flagged} of {len(sents)} sentences to audit for changed meaning" if hits
            else f"{len(sents)} sentences, no scope, qualifier, modality, time or cause words changed", hits)

    # Coverage: source points (LP ones especially) that no LP sentence draws on
    lp_content = [s["content"] for s in sents]
    missed = {"PDF": [], "LP": []}
    for x in src:
        if x["heading"] or len(x["content"]) < 5:
            continue  # headings and fragments
        # a source sentence is often spread over a few LP sentences: use the best three together
        top = sorted(lp_content, key=lambda c: len(x["content"] & c), reverse=True)[:3]
        cover = len(x["content"] & set().union(*top)) / len(x["content"]) if top else 0
        if cover < 0.4:
            missed[x["src"]].append(x["text"])
    hits = [f"LP point not used: \"{t}\"" for t in missed["LP"]]
    hits += [f"PDF point not used: \"{t}\"" for t in missed["PDF"]]
    unused_lp_figs = [f for f in (facts.get("lp_only_figures") or [])
                      if not any(f in s["text"] for s in sents)]
    hits += [f"LP-only figure not used: {f}" for f in unused_lp_figs]
    rep.add("Source coverage", "WARN" if hits else "PASS",
            f"{len(missed['LP'])} LP and {len(missed['PDF'])} PDF points not used" if hits
            else "every substantial PDF and LP point is used", hits)

    if align_path:
        out = ["# LP sentences and their closest source sentences", "",
               "Audit each row: same actor, strength, scope, qualifier, modality, time and cause?", "",
               "| LP line | Section | LP sentence | Closest source | Match | Watch |", "|---|---|---|---|---|---|"]
        cell = lambda t: t.replace("|", "/")
        for s, flags in rows:
            srcs = "<br>".join(f"{m[1]['src']}: {cell(m[1]['text'])}" for m in s["matches"]) or "(none)"
            score = s["matches"][0][0] if s["matches"] else 0
            out.append(f"| {s['line']} | {s['section']} | {cell(s['text'])} | {srcs} | {score:.0%} | {cell('; '.join(flags))} |")
        Path(align_path).write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------- style ----------

def load_phrases(path):
    out = {"ban": [], "watch": [], "ban-regex": [], "watch-regex": []}
    cur = None
    if not Path(path).exists():
        return out
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"\[(.+)\]", line)
        if m:
            cur = m.group(1).lower()
            out.setdefault(cur, [])
        elif cur:
            out[cur].append(line)
    return out


def check_style(rep, blocks, pdf, lp, banned_path):
    scope = variable_blocks(blocks, include_compare=True)
    hits = []
    for b in scope:
        for m in DASH_RE.finditer(b["text"]):
            hits.append(f"line {b['line']}: dash '{m.group().strip()}' | …{b['text'][max(0, m.start() - 40):m.end() + 40]}…")
    rep.add("Dashes", "FAIL" if hits else "PASS", f"{len(hits)} found" if hits else "none", hits)

    ph = load_phrases(banned_path)
    fails, warns = [], []
    for b in scope:
        low = L.norm(b["text"]).lower()
        for p in ph["ban"]:
            if re.search(rf"\b{re.escape(p.lower())}\b", low):
                fails.append(f"line {b['line']}: banned '{p}'")
        for p in ph["ban-regex"]:
            if p.strip() == r"\blet's\b":
                continue
            if re.search(p, low):
                fails.append(f"line {b['line']}: banned pattern /{p}/")
        for p in ph["watch"]:
            if re.search(rf"\b{re.escape(p.lower())}\b", low):
                warns.append(f"line {b['line']}: watch-list '{p}'")
    rep.add("Banned phrases", "FAIL" if fails else "WARN" if warns else "PASS",
            f"{len(fails)} banned, {len(warns)} watch-list" if fails or warns else "none", fails + warns)

    src = (pdf + " " + lp).lower()
    hits, st = [], []
    for b in scope:
        for m in BRIT_RE.finditer(b["text"]):
            w = m.group()
            in_src = w.lower() in src
            st.append("WARN" if in_src else "FAIL")
            hits.append(f"line {b['line']}: '{w}' is British spelling" + (" (the source uses it, maybe a name)" if in_src else ""))
    rep.add("US spelling", worst(*st), f"{len(hits)} British spellings" if hits else "US English", hits)


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


def run(md_text, pdf, lp, facts, a):
    blocks = L.parse_md(md_text)
    rep = Report()
    check_structure(rep, blocks, a, md_text)
    check_figures(rep, blocks, pdf, lp, facts)
    check_entities(rep, blocks, pdf, lp, S.load_client_names(a.client_names))
    check_meaning(rep, blocks, pdf, lp, facts, a.align)
    check_duplication(rep, blocks, pdf, lp)
    check_style(rep, blocks, pdf, lp, a.banned)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="lp.md or the LP .docx")
    ap.add_argument("--sources", help="folder written by sourcetext.py")
    ap.add_argument("--pdf", help="case study PDF (if no --sources)")
    ap.add_argument("--lp", help="existing LP: .html, .md/.txt or URL (if no --sources)")
    ap.add_argument("--pdf-url", default="", help="the case study's PDF link, to check the top and next-step links")
    ap.add_argument("--lp-url", default="", help="the existing LP link, to check the 'Original LP' line")
    ap.add_argument("--align", help="write the LP sentence / closest source sentence table here (Markdown)")
    ap.add_argument("--client-names", default="", help="extra real names to forbid, separated by ';'")
    ap.add_argument("--banned", default=str(BANNED))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        md_text = L.load_lp(a.file)
        pdf, lp, facts = load_sources(a)
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        print(f"Could not read input: {e}", file=sys.stderr)
        sys.exit(2)
    rep = run(md_text, pdf, lp, facts, a)
    print(json.dumps(rep.rows, indent=2, ensure_ascii=False) if a.json else render(rep))
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
