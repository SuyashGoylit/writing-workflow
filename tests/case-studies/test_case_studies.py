"""Tests for the case study LP skills. Standard library only.

    python3 -m unittest discover -s tests/case-studies -v

Fixtures:
- sources/middle-east-petroleum-company/: sourcetext.py output for the template's own case study
- template_as_is.md: the client's template document converted to Markdown, as delivered before the
  client's feedback (copies PDF wording, British spelling, drops the + from "3 TB+", changes the
  meaning of several sentences, no source links, no compare help lines)
- bad_example.md: an older example.md with one injected defect per check (its narrative still has
  the meaning drift the client flagged)
- european_aviation_good.md + sources/european-aviation-services/: a dry run of the skill

Set CASE_STUDY_PDF_DIR to a folder of downloaded <slug>.pdf / <slug>.html files to also run
the extraction tests against the real PDFs.
"""
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SHARED = ROOT / "skills" / "_shared"
VERIFY = ROOT / "skills" / "case-study-verify" / "scripts" / "verify_lp.py"
BUILD = ROOT / "skills" / "case-study-lp" / "scripts" / "build_docx.py"
EXAMPLE = ROOT / "skills" / "case-study-lp" / "example.md"
SOURCES = HERE / "sources" / "middle-east-petroleum-company"
PDF_URL = "https://www.cloud4c.com/wb/case-study/middle-east-petroleum-company/middle-east-petroleum-company.pdf"
LP_URL = "https://www.cloud4c.com/wb/case-study/middle-east-petroleum-company/"
sys.path.insert(0, str(SHARED))
import lpformat as L  # noqa: E402
import sourcetext as S  # noqa: E402


def verify(path, sources=SOURCES, pdf_url=PDF_URL, lp_url=LP_URL, extra=()):
    out = subprocess.run([sys.executable, str(VERIFY), str(path), "--sources", str(sources),
                          "--pdf-url", pdf_url, "--lp-url", lp_url, "--json", *extra],
                         capture_output=True, text=True)
    import json
    rows = json.loads(out.stdout)
    return out.returncode, {r["check"]: r for r in rows}


class Glyphs(unittest.TestCase):
    def test_private_use_glyphs_map_back(self):
        raw = "247 ops, 60 TB, 99%, 30 minutes, 3545%, RTO, RISE x"
        self.assertEqual(S.clean_chars(raw), "24/7 ops, 60+ TB, >99%, <30 minutes, 35-45%, (RTO), RISE: x")

    def test_unmapped_glyph_is_reported(self):
        report = []
        S.clean_chars("value  here", report)
        self.assertEqual(report[0]["char"], "U+E0FF")


class Figures(unittest.TestCase):
    CASES = {
        "a 3 TB+ HANA database": ("3 TB", "plus"),
        "60+ TB": ("60 TB", "plus"),
        "over 3,500 servers": ("3500", "plus"),
        "approximately 40% reduction": ("40 %", "approx"),
        ">99% success": ("99 %", "plus"),
        "<30 minutes": ("30 minute", "max"),
        "35-45% faster": ("35-45 %", "exact"),
        "24x7x365 support": ("24/7", "exact"),
        "a 4-Hour RTO": ("4 hour", "exact"),
        "over three years": ("3 year", "plus"),
        "up to 99.99% uptime": ("99.99 %", "max"),
    }

    def test_figures(self):
        for text, want in self.CASES.items():
            got = [(f["key"], f["qual"]) for f in S.figures(text)]
            self.assertEqual(got, [want], text)

    def test_names_with_digits_are_not_figures(self):
        self.assertEqual(S.figures("Cloud4C runs S/4HANA and HL7 FHIR"), [])


class Verify(unittest.TestCase):
    def test_example_passes(self):
        code, rows = verify(EXAMPLE)
        self.assertEqual(code, 0, [r for r in rows.values() if r["status"] == "FAIL"])

    def test_dry_run_lp_passes(self):
        # written by following case-study-lp/SKILL.md on a case with 5 challenges, ~40% figures
        # and a real client name in the PDF
        src = HERE / "sources" / "european-aviation-services"
        code, rows = verify(HERE / "european_aviation_good.md", src,
                            "https://www.cloud4c.com/wb/case-study/european-aviation-services/european-aviation-services.pdf",
                            "https://www.cloud4c.com/wb/case-study/european-aviation-services/")
        self.assertEqual(code, 0, [r for r in rows.values() if r["status"] == "FAIL"])
        self.assertIn("correctly leaves it out", "\n".join(rows["Client anonymity"]["hits"]))

    def test_template_as_is_fails_on_the_client_feedback(self):
        code, rows = verify(HERE / "template_as_is.md")
        fails = {k for k, r in rows.items() if r["status"] == "FAIL"}
        self.assertEqual(fails, {"Not copied from PDF/LP", "US spelling", "Figures match sources",
                                 "Source links at top", "Compare questions"})
        self.assertIn("'3 TB' drops the source's qualifier", "\n".join(rows["Figures match sources"]["hits"]))
        self.assertIn("no italic help line", "\n".join(rows["Compare questions"]["hits"]))
        self.assertEqual(rows["Fixed template copy"]["status"], "PASS")
        # the sentences the client said changed the meaning
        watch = rows["Meaning watch"]
        self.assertEqual(watch["status"], "WARN")
        hits = "\n".join(watch["hits"])
        for needle in ("adds 'first'; drops 'specifically'",  # "starting with the DR workloads"
                       "adds 'all/entire'",                   # "every other system"
                       "adds 'must'",                         # "had to be dependable at all times"
                       "adds 'not'"):                         # "does not run in parallel"
            self.assertIn(needle, hits)

    def test_example_has_no_drift_on_the_flagged_sentences(self):
        _, rows = verify(EXAMPLE)
        hits = "\n".join(rows["Meaning watch"]["hits"])
        for needle in ("starting with", "every other", "at all times", "does not run"):
            self.assertNotIn(needle, hits)

    def test_source_links_must_match(self):
        _, rows = verify(EXAMPLE, lp_url="https://www.cloud4c.com/wb/case-study/some-other-case/")
        self.assertEqual(rows["Source links at top"]["status"], "FAIL")
        self.assertIn("≠ the link given", "\n".join(rows["Source links at top"]["hits"]))

    def test_align_table_written(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "align.md"
            verify(EXAMPLE, extra=("--align", str(out)))
            text = out.read_text(encoding="utf-8")
        self.assertIn("| LP line | Section | LP sentence | Closest source | Match | Watch |", text)
        self.assertIn("PDF: Cloud4C used its Factory approach", text)

    def test_lp_only_point_reported_as_not_used(self):
        md = (HERE / "european_aviation_good.md").read_text(encoding="utf-8").replace(
            "It also needed a stable platform that could scale for order tracking and efficient inventory management, but recurring",
            "Recurring")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lp.md"
            p.write_text(md, encoding="utf-8")
            _, rows = verify(p, HERE / "sources" / "european-aviation-services")
        self.assertIn("LP point not used: \"Mission-critical aviation operations", "\n".join(rows["Source coverage"]["hits"]))

    def test_bad_example_fails_every_injected_defect(self):
        code, rows = verify(HERE / "bad_example.md")
        self.assertEqual(code, 1)
        for check in ("Source links at top", "Challenge", "Compare questions", "Figures match sources", "Names and technologies",
                      "Client anonymity", "Not copied from PDF/LP", "Dashes", "US spelling"):
            self.assertEqual(rows[check]["status"], "FAIL", check)
        hits = "\n".join(rows["Figures match sources"]["hits"])
        for needle in ("'90+' NOT IN SOURCES", "24/7", "'up to 40%' NOT IN SOURCES"):
            self.assertIn(needle, hits)
        self.assertIn("AWS", "\n".join(rows["Names and technologies"]["hits"]))
        hits = "\n".join(rows["Meaning watch"]["hits"])
        for needle in ("adds 'not'", "adds 'all/entire'", "adds 'unacceptable'"):
            self.assertIn(needle, hits)


class BuildDocx(unittest.TestCase):
    def test_round_trip_and_read_time(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "lp.docx"
            r = subprocess.run([sys.executable, str(BUILD), str(EXAMPLE), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("3-minute read", r.stdout)
            code, rows = verify(out)
            self.assertEqual(code, 0, [r for r in rows.values() if r["status"] == "FAIL"])
            md = L.docx_to_md(out)
            with zipfile.ZipFile(out) as z:
                rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
            self.assertIn(f'Target="{LP_URL}" TargetMode="External"', rels)
            self.assertTrue(md.startswith(f"**Original LP:** {LP_URL}"))
            self.assertIn("*Scheduled DR tests show that failover works", md)
            self.assertIn("## How does your project compare?", md)
            self.assertIn("| Cloud4C role |", md)

    def test_template_matches_client_document(self):
        client = ROOT / "Case Study 2_ Revamp_ Middle East Petrochemical Data Centre.docx"
        if not client.exists():
            self.skipTest("client template not in repo root")
        a = L.parse_md(L.docx_to_md(client))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "t.docx"
            subprocess.run([sys.executable, str(BUILD), str(HERE / "template_as_is.md"), "--out", str(out)], check=True)
            b = L.parse_md(L.docx_to_md(out))
        self.assertEqual([(x["kind"], L.norm(x["text"])) for x in a], [(x["kind"], L.norm(x["text"])) for x in b])


@unittest.skipUnless(os.environ.get("CASE_STUDY_PDF_DIR"), "set CASE_STUDY_PDF_DIR to run against real PDFs")
class RealPDFs(unittest.TestCase):
    DIR = Path(os.environ.get("CASE_STUDY_PDF_DIR", "."))

    def text(self, slug):
        paras, info = S.pdf_text(self.DIR / f"{slug}.pdf")
        self.assertEqual(info["unmapped_glyphs"], [])
        return "\n\n".join(paras)

    def test_known_figures(self):
        self.assertIn("24/7 monitoring", self.text("gulf-ministry-of-health"))
        t = self.text("healthcare-and-wellness-major")
        for s in (">99%", "<30 minutes", "35-45%"):
            self.assertIn(s, t)
        self.assertIn("60+ TB", self.text("indian-automotive-giant"))

    def test_columns_are_not_interleaved(self):
        t = self.text("middle-east-petroleum-company")
        self.assertIn("Cloud4C used its Factory approach to transition the client's entire DR landscape", t)

    def test_client_name_leak_flagged(self):
        _, _, facts = S.extract(self.DIR / "european-aviation-services.pdf")
        self.assertTrue(facts["client_names_found"])


if __name__ == "__main__":
    unittest.main()
