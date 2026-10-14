"""Shared reader for case study LP files (lp.md or the built .docx).

Both build_docx.py and verify_lp.py use this module, so the Markdown conventions in
case-study-lp/template.md are defined in one place. Standard library only.
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TOGGLE = "Not started | In progress | In place"
H2_ORDER = [
    "The story in 30 seconds", "About the client", "The challenge", "The solution",
    "The results", "How does your project compare?", "Similar case studies",
    "Take the next step", "Talk to the team that built it",
]
SECTION_KEYS = {  # H2 text (normalised) -> short key
    "the story in 30 seconds": "story", "about the client": "about", "the challenge": "challenge",
    "the solution": "solution", "the results": "results", "how does your project compare?": "compare",
    "similar case studies": "similar", "take the next step": "next", "talk to the team that built it": "talk",
}
LABELS = ("Top navigation", "Tick bar", "Once ticked", "Confirmation")
BUTTON_RE = re.compile(r"^(?:\[ [^\[\]]+ \]\s*)+$")
CARD_RE = re.compile(r"^([123]) of 3: The (challenge|solution|result)$")
SOURCE_RE = re.compile(r"^\*\*Original (LP|PDF):\*\*\s*(\S*)\s*$")  # source links at the top
INLINE_RE = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|(?<![*\w])\*(?![\s*]).+?(?<![\s*])\*(?![*\w]))")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


# ---------- text helpers ----------

def norm(text):
    """Straight quotes, single spaces: for comparing fixed copy."""
    text = (text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace(" ", " "))
    return re.sub(r"\s+", " ", text).strip()


def plain(md):
    """Markdown inline -> plain text."""
    return re.sub(r"\*{1,3}([^*]+?)\*{1,3}", r"\1", md).replace("**", "").strip()


def runs(md):
    """Split inline Markdown into [(text, bold, italic)]."""
    out, pos = [], 0
    for m in INLINE_RE.finditer(md):
        if m.start() > pos:
            out.append((md[pos:m.start()], False, False))
        tok = m.group()
        if tok.startswith("***"):
            out.append((tok[3:-3], True, True))
        elif tok.startswith("**"):
            out.append((tok[2:-2], True, False))
        else:
            out.append((tok[1:-1], False, True))
        pos = m.end()
    if pos < len(md):
        out.append((md[pos:], False, False))
    return [r for r in out if r[0]]


def whole(md, marker):
    """True if the whole line is wrapped in one bold (**) or italic (*) span."""
    r = runs(md)
    if len(r) != 1:
        return False
    return r[0][1] if marker == "**" else (r[0][2] and not r[0][1])


def words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'+%./-]*", text)


# ---------- Markdown -> blocks ----------

def parse_md(text):
    """Return blocks: {kind, md, text, line, section}.

    kinds: h1 h2 h3 table bullet numbered button toggle checkbox card_label labelled
           source note url tags bold para
    """
    text = COMMENT_RE.sub("", text)
    lines = text.splitlines()
    # writer notes after a final '---' are not part of the LP
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() in ("---", "***", "___") and i > len(lines) * 0.5:
            lines = lines[:i]
            break
    blocks, section, i = [], "hero", 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        n = i + 1
        i += 1
        if not s:
            continue
        if s.startswith("|"):
            rows = [s]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[plain(c.strip()) for c in r.strip("|").split("|")] for r in rows
                     if not re.fullmatch(r"\|?[\s:|-]+\|?", r)]
            blocks.append({"kind": "table", "rows": cells, "md": "\n".join(rows),
                           "text": "\n".join(" | ".join(c) for c in cells), "line": n, "section": section})
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            htext = plain(re.sub(r"^<H\d>", "", m.group(2), flags=re.I))
            if level == 2:
                section = SECTION_KEYS.get(norm(htext).lower(), "other")
            blocks.append({"kind": f"h{level}", "md": m.group(2), "text": htext, "line": n, "section": section})
            continue
        b = re.match(r"^[-*+]\s+(.*)$", s) if not re.match(r"^\*[^\s*]", s) else None
        if b:
            blocks.append(_block("bullet", b.group(1), n, section))
            continue
        num = re.match(r"^\d+[.)]\s+(.*)$", s)
        if num:
            blocks.append(_block("numbered", num.group(1), n, section))
            continue
        blocks.append(_block(classify(s, section), s, n, section))
    _mark_context(blocks)
    return blocks


def _block(kind, md, line, section):
    return {"kind": kind, "md": md, "text": plain(md), "line": line, "section": section}


def classify(md, section=""):
    t = plain(md)
    if norm(t) == TOGGLE:
        return "toggle"
    if BUTTON_RE.match(t):
        return "button"
    if t.startswith("☐"):
        return "checkbox"
    if CARD_RE.match(t):
        return "card_label"
    if SOURCE_RE.match(md):
        return "source"
    if any(md.startswith(f"**{lab}:**") for lab in LABELS):
        return "labelled"
    if re.match(r"^https?://\S+$", t):
        return "url"
    if norm(t).startswith("Case study |") and whole(md, "**"):
        return "tags"
    if whole(md, "*"):
        return "note"
    if whole(md, "**"):
        return "bold"
    return "para"


def _mark_context(blocks):
    """Flags the builder and verifier both need: lede, indented challenge text, CTA, question help."""
    for i, b in enumerate(blocks):
        prev = blocks[i - 1] if i else None
        if b["kind"] == "para" and prev and prev["kind"] == "h1":
            b["role"] = "lede"
        elif b["kind"] == "para" and prev and prev["kind"] == "checkbox":
            b["role"] = "challenge_text"
        elif b["kind"] == "bold" and b["section"] == "solution" and b["text"].rstrip().endswith("?"):
            b["role"] = "cta"
        elif b["kind"] == "para" and b["md"].startswith("**Looking ahead.**"):
            b["role"] = "looking_ahead"
        elif b["kind"] == "numbered" and b["section"] == "compare":
            b["role"] = "question"
        elif b["kind"] == "note" and prev and prev.get("role") == "question":
            b["role"] = "question_help"


def source_links(blocks):
    """{'LP': url, 'PDF': url} from the '**Original LP:** url' lines at the top."""
    out = {}
    for b in blocks:
        m = SOURCE_RE.match(b["md"]) if b["kind"] == "source" else None
        if m:
            out.setdefault(m.group(1), m.group(2))
    return out


def sections(blocks):
    out = {}
    for b in blocks:
        out.setdefault(b["section"], []).append(b)
    return out


# ---------- .docx -> Markdown ----------

def _num_formats(z):
    try:
        root = ElementTree.fromstring(z.read("word/numbering.xml"))
    except KeyError:
        return {}
    abstract = {}
    for an in root.iter(f"{W}abstractNum"):
        lvl = an.find(f"{W}lvl")
        fmt = lvl.find(f"{W}numFmt") if lvl is not None else None
        abstract[an.get(f"{W}abstractNumId")] = fmt.get(f"{W}val") if fmt is not None else "bullet"
    out = {}
    for num in root.iter(f"{W}num"):
        a = num.find(f"{W}abstractNumId")
        out[num.get(f"{W}numId")] = abstract.get(a.get(f"{W}val") if a is not None else "", "bullet")
    return out


def _runs_md(p):
    parts = []
    for r in p.iter(f"{W}r"):
        t = "".join((x.text or "") for x in r.iter(f"{W}t"))
        if not t:
            continue
        rpr = r.find(f"{W}rPr")
        bold = rpr is not None and rpr.find(f"{W}b") is not None and rpr.find(f"{W}b").get(f"{W}val") not in ("0", "false")
        ital = rpr is not None and rpr.find(f"{W}i") is not None and rpr.find(f"{W}i").get(f"{W}val") not in ("0", "false")
        if parts and (parts[-1][1:] == [bold, ital] or not t.strip()):
            parts[-1][0] += t  # whitespace-only runs take their neighbour's format
        else:
            parts.append([t, bold, ital])
    out = []
    for t, bold, ital in parts:
        core = t.strip()
        if not core or not (bold or ital):
            out.append(t)
            continue
        mark = "***" if bold and ital else "**" if bold else "*"
        lead = t[:len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        out.append(f"{lead}{mark}{core}{mark}{trail}")
    return "".join(out).strip()


def docx_to_md(path):
    """Rebuild lp.md-style Markdown from an LP .docx (the built file or a hand-edited one)."""
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
        fmts = _num_formats(z)
    body = root.find(f"{W}body")
    out = []
    for el in body:
        if el.tag == f"{W}tbl":
            rows = []
            for tr in el.iter(f"{W}tr"):
                cells = ["".join(x.text or "" for x in tc.iter(f"{W}t")).strip() for tc in tr.iter(f"{W}tc")]
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                rows.insert(1, "|" + "---|" * (rows[0].count("|") - 1))
            out.append("\n".join(rows))
            continue
        if el.tag != f"{W}p":
            continue
        text = "".join(x.text or "" for x in el.iter(f"{W}t")).strip()
        if not text:
            continue
        ppr = el.find(f"{W}pPr")
        style = ""
        if ppr is not None and ppr.find(f"{W}pStyle") is not None:
            style = ppr.find(f"{W}pStyle").get(f"{W}val", "")
        md = _runs_md(el)
        tag = re.match(r"^\**<H(\d)>", md, re.I)
        hm = re.match(r"(?:Heading|Title)\s*(\d*)", style, re.I)
        level = int(tag.group(1)) if tag else (int(hm.group(1) or 1) if hm else 0)
        if level and not tag and level == 3 and "**" not in md and len(text) > 120:
            level = 0  # body text accidentally styled as a heading
        if level:
            out.append("#" * level + " " + plain(re.sub(r"<H\d>", "", md, flags=re.I)))
            continue
        num = ppr.find(f"{W}numPr") if ppr is not None else None
        if num is not None and num.find(f"{W}numId") is not None:
            fmt = fmts.get(num.find(f"{W}numId").get(f"{W}val"), "bullet")
            out.append(("- " if fmt == "bullet" else "1. ") + md)
            continue
        out.append(md)
    return "\n\n".join(out) + "\n"


def load_lp(path):
    """Read lp.md / .txt / .docx and return its Markdown text."""
    p = Path(path)
    if p.suffix.lower() == ".docx":
        return docx_to_md(p)
    return p.read_text(encoding="utf-8")


# ---------- reading time ----------

READ_SECTIONS = ("hero", "about", "challenge", "solution", "results")
READ_KINDS = ("h1", "para", "bold", "bullet", "checkbox", "h3")


def read_minutes(blocks, wpm=230):
    """Minutes to read the story itself (hero lede to Looking ahead), rounded up."""
    n = sum(len(words(b["text"])) for b in blocks
            if b["section"] in READ_SECTIONS and b["kind"] in READ_KINDS)
    return max(1, -(-n // wpm)), n
