---
name: case-study-verify
description: Fact-check a revamped Cloud4C case study LP against its sources (the existing LP page and the case study PDF). A script checks the template structure, the source links, every figure and qualifier, headline figures, unsupported names, real client names, meaning drift, source points left out, copied wording, dashes, banned phrases and US spelling. Claude then audits every sentence's meaning against its quoted source sentence. Use after case-study-lp writes an LP, or when the user says "verify", "fact-check", "check the figures", "is this accurate", or uploads or pastes a finished case study LP (.docx or text) to check.
---

# Case Study LP Verification

Prove that every sentence in a new case study LP says what its sources say (no more, no less, nothing different), that both sources were used, and that the LP follows the template.

## 1. Get the LP into a file
- If case-study-lp just wrote it, use that `lp.md`.
- If the user uploaded a `.docx` (the built file or one edited by hand), pass it directly. The script reads Word headings, lists, bold and the fact table.
- If the LP was pasted, write it to `lp.md` exactly as given. Leave out any writer notes after a final `---`.

## 2. Get the sources
- If this chat already ran `sourcetext.py`, reuse its `sources/` folder.
- Otherwise ask for the existing LP link and the PDF (upload preferred). Fetch the LP with web fetch, save it unedited as `lp_source.md`, then run:
  ```bash
  python3 <skill-dir>/scripts/sourcetext.py --pdf case.pdf --lp lp_source.md --out sources/
  ```
  Only the PDF is treated as authoritative on conflicts. Never verify against a web-fetch text version of the PDF: it drops `+ / < >` from figures.

## 3. Run the script
```bash
python3 <skill-dir>/scripts/verify_lp.py lp.md --sources sources/ --lp-url "<LP link>" --pdf-url "<PDF link>" --align align.md
```
Exit code 1 means at least one FAIL. What it checks:
- **Source links**: `**Original LP:**` and `**Original PDF:**` lines at the top, matching `--lp-url` and `--pdf-url`.
- **Template**: section order, every fixed UI line verbatim (taken from `template.md`), no unfilled `{{slots}}`, the hero and fact table, 3 story cards × 3 bullets, 2 About paragraphs, the challenge count word = ☐ items = "2 of N", 4–6 solution H3s, the readiness line, 4–8 `**Label.**` results, Looking ahead, 5 questions each followed by an italic help line and the toggle line, and the PDF link.
- **Figures**: every number in the narrative must exist in the PDF or LP with the same unit, and the qualifier must not overstate the source. Any qualifier change is a FAIL: "40%" where the source says "approximately 40%", an added "+", an added "up to", and also a dropped one ("3 TB" for "3 TB+", "80" for "80+"). "247" is flagged as a lost "24/7". Headline figures (title, subtitle, results block) must all appear.
- **Names and technologies**: acronyms, product names and CamelCase terms in the LP that don't appear in the sources are a FAIL. Capitalised words not in the sources are a WARN.
- **Client anonymity**: any name in `client_names.txt`, or Capgemini, is a FAIL.
- **Meaning watch** (WARN, input to step 4): each LP sentence is paired with its closest source sentence, and the script lists words that were added or dropped in scope (entire, every, only, specifically, core, the rest of), hedges (approximately, over, up to), modality (needed, wanted, had to, would), negation, absolutes (zero, eliminated, without fail), time (earlier, periodic, starting with) and cause (so, because, enabling). It also flags sentences with no close source sentence. `--align` writes the full pairing to `align.md`.
- **Source coverage** (WARN): substantial PDF and LP sentences that no LP sentence draws on, plus LP-only figures not used. Each one should be in the LP or deliberately left out.
- **Not copied from PDF/LP**: About, Challenge, Solution and Looking ahead are compared with both sources. A shared run of 10+ words or more than 10% of shared 8-word phrases is a FAIL. A run of 7–9 words is a WARN.
- **Style**: dashes, banned phrases (`banned_phrases.txt`) and British spellings.

## 4. Audit the meaning of every sentence (Claude, not the script)
The script can only point at suspicious words. You decide whether the meaning changed. Work from `align.md` and go through the whole narrative (lede, fact table, story cards, About, Challenge, Solution, Results, Looking ahead, readiness line, compare help lines) **sentence by sentence, not paragraph by paragraph**. For each sentence:
1. Quote the LP sentence and the source sentence(s) it restates (`sources/pdf.txt` or `sources/lp.txt`). If `align.md` paired it with the wrong one, search for the right one.
2. Ask the seven questions. Is it the same **actor** (who did it)? The same **strength** (reduced vs eliminated, supported vs matters)? The same **scope** (core vs entire, specifically vs starting with, the rest vs every)? The same **figure and qualifier**? The same **modality** (wanted vs needed vs had to)? The same **time or sequence**? The same **cause** (does the source link these two things)?
3. Give a verdict:

| Verdict | Meaning |
|---|---|
| Supported | Same claim, reworded (all seven answers are yes) |
| Meaning changed | Same topic, but the sentence now says something the source doesn't: a new actor, a swapped requirement, a scope word that implies something else, a new cause and effect, a result recast as a challenge |
| Overstated | Broader, stronger or more certain than the source ("every system" where the source says "the rest of the environment"; "eliminated" where it says "reduced") |
| Understated | Narrower or weaker than the source (a dropped "+", "some" for "did not consistently") |
| Unsupported | Not in either source: an invented cause, benefit, detail, timeline, scope or technology |
| Contradicted | The source says otherwise |
| Source conflict | The PDF and LP disagree; the LP must follow the PDF |

Rules:
- Every **Meaning watch** hit must get a row with a verdict, even if the verdict is Supported.
- Write the full table, every sentence, to `audit.md`. Don't skip sentences that look fine. The client's complaints came from sentences that looked fine. In a test run on steel-manufacturing-corporation the script passed every sentence, yet the audit found five changes: "no analytics" for "no reliable analytics", "cleared" for "addressed", "until" for "without resolving", a new cause and effect, and an invented future claim in Looking ahead.
- Check that each challenge title restates a real source challenge, and each compare question relates to something the case study covers. Help lines must not state case study facts.
- Check **Source coverage**: each LP or PDF point listed there is either in the LP or deliberately left out (rhetoric, repetition). A missing substantive point (a scale figure, a reason, an outcome) is a finding.
- Skip only the fixed UI copy.

## 5. Report
1. The script's summary table.
2. The claim table, showing only the rows that are not Supported (all rows if the user asks): `| LP line | LP sentence | Source quote (PDF/LP) | Verdict | What changed | Fix |`. The "What changed" column names the drift: actor, strength, scope, qualifier, modality, time or cause.
3. Source points left out that should be in the LP.
4. 2-4 bullets on what matters most.

Don't paste the script's full details unless asked.

## 6. Fix
If case-study-lp called this skill, or the user asks for fixes:
- **Figure FAIL**: copy the source's value, unit and qualifier exactly.
- **Not in sources**: remove the claim or replace it with what the source says.
- **Unsupported name**: remove it, or use the sources' term.
- **Copied run**: rebuild the sentence from the facts, with a new structure and order. Keep the technical nouns.
- **Structure FAIL**: restore the template line or count (`template.md` is the reference). For missing source links, add `**Original LP:** <link>` and `**Original PDF:** <link>` as the first two lines. For a missing help line, add one italic line under the question.
- **Meaning changed, Overstated or Understated**: restore the source's locked words (the actor, scope word, qualifier, modality or cause it changed). If the only way to keep the meaning is to stay close to the source wording, do that. A short shared run is a WARN, a changed meaning is not acceptable.
- **Unsupported claim**: remove it, or replace it with what the source says.
- **Missing source point**: add it where it fits (About, Challenge, Results), reworded, with its locked words.

Edit only the affected sentences, rebuild the .docx if one exists (case-study-lp's `build_docx.py`), re-run the script, and re-audit the sentences you changed. Stop after 2 passes and list anything that still flags.

## Notes
- A real client name found in the sources (for example, the european-aviation-services PDF names its client) is reported by `sourcetext.py`. To block a newly found name, add it to `client_names.txt` in both case study skills and re-upload them.
- Meaning watch WARNs need judgement: "drops 'core'" is often just a long source sentence split across two LP sentences. Coverage WARNs for rhetorical LP lines ("Leadership knew the fix wasn't a patch job") can be left out.
- Other WARNs need judgement. Watch-list words like "landscape" are normal in DR and infrastructure copy, so leave them where they are technical. A 7-word shared run that is just a product phrase ("zero disruption and zero data loss") can stay.
