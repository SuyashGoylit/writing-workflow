#!/usr/bin/env python3
"""Build the case study LP Word document from lp.md, in the client template's styles.

Usage:
    python3 build_docx.py lp.md --out "Case Study - LP Revamp.docx"
    python3 build_docx.py --strip-template original.docx   # (maintainer) refresh assets/lp-template.docx

Reads lp.md (see ../template.md for the conventions), recalculates the "N-minute read"
line, and writes a .docx that reuses assets/lp-template.docx's styles, numbering and page
setup. Standard library only. Exit code: 0 = ok, 2 = bad input.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parents[1] / "_shared"))  # repo layout; the zip has it in scripts/
import lpformat as L  # noqa: E402

TEMPLATE = HERE.parent / "assets" / "lp-template.docx"

# Paragraph and run properties copied from the client's template (Case Study 2 docx).
SP_BODY = '<w:spacing w:after="120" w:line="276" w:lineRule="auto"/>'
SP_BUTTON = '<w:spacing w:before="80" w:after="160"/>'
GRAY, BLUE, DARK = "595959", "1F4E79", "262626"

PPR = {
    "body": SP_BODY,
    "button": SP_BUTTON,
    "h1": '<w:pStyle w:val="Heading1"/><w:spacing w:before="120" w:after="160"/>',
    "h2": ('<w:pStyle w:val="Heading2"/><w:keepNext/><w:pBdr><w:bottom w:val="single" w:sz="6" '
           'w:space="4" w:color="1F4E79"/></w:pBdr><w:spacing w:before="360" w:after="120"/>'),
    "h3": '<w:pStyle w:val="Heading3"/><w:keepNext/><w:spacing w:before="200" w:after="80"/>',
    "h3_plain": '<w:pStyle w:val="Heading3"/>',
    "card_label": '<w:keepNext/><w:spacing w:before="160" w:after="80"/>',
    "bullet": ('<w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/>'
               '</w:numPr>' + SP_BODY.replace('after="120"', 'after="80"')),
    "question": ('<w:pStyle w:val="ListParagraph"/><w:keepNext/><w:numPr><w:ilvl w:val="0"/>'
                 '<w:numId w:val="3"/></w:numPr><w:spacing w:after="60"/>'),
    "step": ('<w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="4"/>'
             '</w:numPr><w:spacing w:after="60"/>'),
    "toggle": '<w:spacing w:after="160"/><w:ind w:left="360"/>',
    "checkbox": '<w:keepNext/><w:spacing w:before="140" w:after="60"/>',
    "challenge_text": SP_BODY + '<w:ind w:left="440"/>',
    "tick_bar": '<w:spacing w:before="200" w:after="60"/>',
    "cta": '<w:spacing w:before="240" w:after="80"/>',
    "looking_ahead": '<w:spacing w:before="200" w:after="120"/>',
    "keep": '<w:keepNext/>' + SP_BODY,
    "source": ('<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="1F4E79"/></w:pBdr>'
               '<w:shd w:val="clear" w:color="auto" w:fill="EAF1F8"/><w:spacing w:after="0"/>'
               '<w:ind w:left="160"/>'),
    "question_help": '<w:keepNext/><w:spacing w:after="40"/><w:ind w:left="360"/>',
}
HYPERLINK_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"


def rpr(bold=False, italic=False, color=None, size=None, caps=False, shade=None):
    parts = []
    if bold:
        parts.append("<w:b/><w:bCs/>")
    if italic:
        parts.append("<w:i/><w:iCs/>")
    if caps:
        parts.append("<w:caps/>")
    if color:
        parts.append(f'<w:color w:val="{color}"/>')
    if size:
        parts.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    if shade:
        parts.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    return f"<w:rPr>{''.join(parts)}</w:rPr>" if parts else ""


def run(text, **fmt):
    return f'<w:r>{rpr(**fmt)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(ppr, runs_xml):
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs_xml}</w:p>"


def inline(md, **base):
    """Inline Markdown -> runs; bold/italic add to the base format."""
    out = []
    for text, b, i in L.runs(md):
        fmt = dict(base)
        fmt["bold"] = fmt.get("bold", False) or b
        fmt["italic"] = fmt.get("italic", False) or i
        out.append(run(text, **fmt))
    return "".join(out)


def buttons(text):
    out = []
    for i, label in enumerate(re.findall(r"\[ [^\[\]]+ \]", text)):
        if i:
            out.append(run("   "))
        out.append(run(label, bold=True, color=BLUE, shade="EAF1F8"))
    return "".join(out)


def table(rows):
    border = ('<w:tcBorders>' + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
                                        for s in ("top", "left", "bottom", "right")) + '</w:tcBorders>')
    mar = ('<w:tcMar><w:top w:w="90" w:type="dxa"/><w:left w:w="140" w:type="dxa"/>'
           '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>')

    def cell(text, width, fill=None, **fmt):
        shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
        return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{border}{shd}{mar}</w:tcPr>'
                f'<w:p>{run(text, **fmt)}</w:p></w:tc>')

    out = ['<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>'
           + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
                     for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + '</w:tblBorders><w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/>'
           '</w:tblCellMar><w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" '
           'w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="2200"/><w:gridCol w:w="7160"/></w:tblGrid>']
    for i, r in enumerate(rows):
        r = (r + ["", ""])[:2]
        if i == 0:
            out.append("<w:tr>" + cell(r[0], 2200, BLUE, bold=True, color="FFFFFF")
                       + cell(r[1], 7160, BLUE, bold=True, color="FFFFFF") + "</w:tr>")
        else:
            out.append("<w:tr>" + cell(r[0], 2200, "EAF1F8", bold=True) + cell(r[1], 7160) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def hyperlink(url, links):
    """A clickable run; the relationship is added to document.xml.rels by build()."""
    rid = f"rIdSrc{len(links) + 1}"
    links.append((rid, url))
    return (f'<w:hyperlink r:id="{rid}" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/>'
            f'<w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(url)}</w:t></w:r></w:hyperlink>')


def render(b, links):
    k, md, text, role = b["kind"], b["md"], b["text"], b.get("role")
    if k == "h1":
        return para(PPR["h1"], run(text, bold=True, color=BLUE, size=40))
    if k == "h2":
        return para(PPR["h2"], run(text, bold=True, color=BLUE, size=30))
    if k == "h3":
        if text == "FORM FIELDS":
            return para(PPR["h3_plain"], run(text))
        return para(PPR["h3"], run(text, bold=True, color=DARK))
    if k == "table":
        return table(b["rows"])
    if k == "button":
        return para(PPR["button"], buttons(text))
    if k == "toggle":
        return para(PPR["toggle"], run("Not started   |   In progress   |   In place", color=GRAY))
    if k == "card_label":
        return para(PPR["card_label"], run(text, bold=True, caps=True, color=GRAY, size=20))
    if k == "checkbox":
        rest = re.sub(r"^☐\s*", "", md)
        return para(PPR["checkbox"], run("☐  ", size=26) + inline(rest))
    if k == "labelled":
        m = re.match(r"^\*\*([^*]+:)\*\*\s*(.*)$", md)
        label, rest = m.group(1), m.group(2)
        ppr = PPR["tick_bar"] if label == "Tick bar:" else PPR["body"]
        rest_fmt = {"color": GRAY} if label == "Top navigation:" else {}
        return para(ppr, run(label + " ", bold=True, color=GRAY) + inline(rest, **rest_fmt))
    if k == "source":
        m = L.SOURCE_RE.match(md)
        url = run(m.group(2), color=GRAY) if not m.group(2).startswith("http") else hyperlink(m.group(2), links)
        return para(PPR["source"], run(f"Original {m.group(1)}: ", bold=True, color=BLUE) + url)
    if role == "question_help":
        return para(PPR["question_help"], run(text, italic=True, color=GRAY, size=20))
    if k == "note":
        return para(PPR["body"], run(text, italic=True, color=GRAY))
    if k == "url":
        return para(PPR["body"], run(text, color=GRAY, size=18))
    if k == "tags":
        return para(PPR["body"], run(text, bold=True, color=BLUE))
    if k == "bullet":
        return para(PPR["bullet"], inline(md))
    if k == "numbered":
        return para(PPR["question" if role == "question" else "step"], inline(md))
    if role == "lede":
        return para(PPR["body"], inline(md, size=24))
    if role == "challenge_text":
        return para(PPR["challenge_text"], inline(md))
    if role == "cta":
        return para(PPR["cta"], run(text, bold=True, color=BLUE))
    if role == "looking_ahead":
        return para(PPR["looking_ahead"], inline(md))
    if text.endswith("(field)"):
        return para(PPR["keep"], run(text, color=GRAY))
    if b["section"] == "compare" and k == "para" and text.startswith("Five quick questions"):
        return para(PPR["keep"], inline(md))
    return para(PPR["body"], inline(md))


def set_read_time(blocks):
    minutes, n = L.read_minutes(blocks)
    for b in blocks:
        if b["kind"] == "note" and re.fullmatch(r"\d+-minute read", b["text"]):
            b["text"] = b["md"] = f"{minutes}-minute read"
    return minutes, n


def build(md_text, out_path, template=TEMPLATE):
    blocks = L.parse_md(md_text)
    if not any(b["kind"] == "h1" for b in blocks):
        raise ValueError("lp.md has no '# ' title; is this the right file?")
    leftover = [b["line"] for b in blocks if "{{" in b["md"]]
    minutes, n = set_read_time(blocks)
    title = next(b["text"] for b in blocks if b["kind"] == "h1")
    with zipfile.ZipFile(template) as zin:
        doc = zin.read("word/document.xml").decode("utf-8")
        head = doc[:doc.index("<w:body>") + len("<w:body>")]
        sect = re.search(r"<w:sectPr\b.*?</w:sectPr>", doc, re.S).group()
        links, parts = [], []
        for i, b in enumerate(blocks):
            parts.append(render(b, links))
            if b["kind"] == "source" and (i + 1 == len(blocks) or blocks[i + 1]["kind"] != "source"):
                parts.append(para(PPR["body"], ""))  # space between the sources box and the page
        body = "".join(parts)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = (head + body + sect + "</w:body></w:document>").encode("utf-8")
                elif item.filename == "docProps/core.xml":
                    data = re.sub(rb"<dc:title>.*?</dc:title>",
                                  f"<dc:title>{escape(title)}</dc:title>".encode("utf-8"), data)
                elif item.filename == "word/_rels/document.xml.rels" and links:
                    rels = "".join(f'<Relationship Id="{rid}" Type="{HYPERLINK_REL}" Target="{escape(url, {chr(34): "&quot;"})}" '
                                   f'TargetMode="External"/>' for rid, url in links)
                    data = data.replace(b"</Relationships>", rels.encode("utf-8") + b"</Relationships>")
                zout.writestr(item, data)
    return {"blocks": len(blocks), "minutes": minutes, "words": n, "leftover_slots": leftover}


def strip_template(src, dst=TEMPLATE):
    """Maintainer helper: keep the client template's styles and numbering, drop its content."""
    with zipfile.ZipFile(src) as zin:
        doc = zin.read("word/document.xml").decode("utf-8")
        head = doc[:doc.index("<w:body>") + len("<w:body>")]
        sect = re.search(r"<w:sectPr\b.*?</w:sectPr>", doc, re.S).group()
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = (head + "<w:p/>" + sect + "</w:body></w:document>").encode("utf-8")
                elif item.filename == "docProps/core.xml":
                    data = re.sub(rb"<dc:title>.*?</dc:title>", b"<dc:title>Case Study LP</dc:title>", data)
                    data = re.sub(rb"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", b"", data)
                zout.writestr(item, data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("md", nargs="?", help="lp.md")
    ap.add_argument("--out", help="output .docx path")
    ap.add_argument("--strip-template", metavar="DOCX", help="refresh assets/lp-template.docx from DOCX")
    a = ap.parse_args()
    if a.strip_template:
        strip_template(a.strip_template)
        print(f"wrote {TEMPLATE}")
        return
    if not a.md:
        ap.error("lp.md is required")
    out = a.out or str(Path(a.md).with_suffix(".docx"))
    try:
        info = build(Path(a.md).read_text(encoding="utf-8"), out)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f"Could not build: {e}", file=sys.stderr)
        sys.exit(2)
    print(f"wrote {out} ({info['blocks']} blocks, {info['words']} story words, "
          f"{info['minutes']}-minute read)")
    if info["leftover_slots"]:
        print(f"WARNING: unfilled {{{{slots}}}} on lines {info['leftover_slots']}")


if __name__ == "__main__":
    main()
