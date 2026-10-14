---
name: case-study-lp
description: Rewrite a Cloud4C case study landing page (LP) into the new revamp template from its existing LP link and its long-form PDF, combining points from both sources and keeping every claim's meaning, figure and technology exactly as the sources state them while rewording the narrative so it does not duplicate the PDF. Produces the LP as Markdown in chat plus a Word document in the client template's styles, then runs the case-study-verify skill. Use when the user gives a case study name, an existing LP link (cloud4c.com/wb/case-study/...) and a PDF (uploaded or linked), or says "revamp this case study", "new LP for this case study", "write the LP in the template", or pastes the Case Study Name / Existing LP Link / Existing Case Study PDF Link block.
---

# Case Study LP Revamp

Turn one existing case study (old LP + PDF) into a new LP that follows `template.md` exactly, using only facts from those two sources.

**The rule that matters most: change the wording, never the claim.** The client has rejected LPs where a reworded sentence said something the source didn't ("specifically" became "starting with", "the rest of the environment" became "every other system"). A sentence that reads a little like the source is a WARN. A sentence that changes what the source says is a FAIL.

## Inputs
Take these from the user's message (usually pasted from the tracker sheet):
- **Case Study Name**: the slug, for example `middle-east-petroleum-company`
- **Existing LP Link**: `https://www.cloud4c.com/wb/case-study/<slug>/` (some use `/wb/case-study/lp/<slug>/`)
- **Existing Case Study PDF**: an uploaded PDF (preferred), or the PDF link

If the LP link or the PDF is missing, ask for it in one short message and stop. A PDF link that ends mid-word (the tracker has one: `…/indian-insurance-lea`) is truncated. Ask for the full link, or try `<LP link><slug>.pdf`.

The template and `example.md` are format references only. **Never take facts, figures or phrasing from `example.md`** (it is a different client).

## Files in this skill
- `template.md`: the LP skeleton. Fixed UI copy is verbatim and `{{slots}}` carry the rules. Read it in full every time.
- `example.md`: a finished LP for a different case study that passes verification. Read it once, for length and tone. Its header lists drifted sentences that were corrected, which are worth reading.
- `scripts/sourcetext.py`: extracts clean text and figures from the PDF and LP.
- `scripts/build_docx.py`: builds the Word document from `lp.md` in the client template's styles.
- `assets/lp-template.docx`: the client template (styles only).

## Step 1: Get clean sources
1. **LP**: fetch the LP link with web fetch and save what it returns, unedited, to `lp_source.md`. If fetching fails, ask the user to paste the page text or upload the saved page (.html).
2. **PDF**: use the uploaded file. If only a link was given, try downloading it in the sandbox (`curl -sL -o case.pdf "<link>"`). If the sandbox can't reach cloud4c.com, ask the user to upload the PDF. Don't rely on a web-fetch text version of the PDF: it loses the `+`, `/`, `<` and `>` symbols in figures.
3. Run the extractor:
   ```bash
   python3 <skill-dir>/scripts/sourcetext.py --pdf case.pdf --lp lp_source.md --out sources/
   ```
   It writes `sources/pdf.txt` (reading order fixed, headings marked `##`), `sources/lp.txt` and `sources/facts.json`. Why this matters: the PDFs store `+ / < > ( ) : -` as private-use glyphs, so a plain extraction turns "24/7" into "247" and "60+ TB" into "60 TB". The script maps them back. If it reports **UNMAPPED GLYPHS**, look at the PDF itself around those spots before using any nearby figure.
4. Read `sources/pdf.txt` and `sources/lp.txt` in full. You can also look at the PDF directly to confirm a figure.

## Step 2: Build the claim ledger (`ledger.md`)
Read both sources and write `ledger.md`, one row per claim. **Use both sources.** The old LP often has points the PDF doesn't (a scale figure, the business reason, an outcome), and the client expects them in the new LP. Leaning on one source is a defect.

```
| ID | Section | Claim | Src | Exact source words | Locked words |
| C1 | Challenge | DR exit was for DR workloads only | PDF | "exit strategy for its DR workloads specifically" | specifically, DR workloads |
| C2 | Challenge | Scale: 80+ apps, multi-TB HANA | LP | "over 80 business critical applications and a HANA database running into terabytes" | over 80, running into terabytes |
| S4 | Solution | Exchange covered by same DR framework | PDF | "under the same framework as the rest of the environment" | Cloud4C, the rest of the environment |
```
- **Src** is PDF, LP or both. If they disagree, the PDF wins: mark the row `conflict` and note the LP version (`facts.json` → `conflicts`). Rows from `lp_only_figures` are tagged LP.
- **Locked words** are the words that carry the claim's meaning. They must survive the rewrite, as these words or an exact equivalent:
  - **Actor**: who did it (Cloud4C, the client, the client's leadership)
  - **Strength**: reduced vs eliminated, helped vs delivered, improved vs transformed
  - **Scope**: entire, core, specifically, only, some, the rest of
  - **Figures and qualifiers**: 80+, approximately 40%, 3 TB+, up to
  - **Modality**: needed, wanted, planned, had to
  - **Time and sequence**: earlier, periodic, ongoing, once on Azure
  - **Cause**: "so", "because", "enabling". Only where the source links the two things.
- Also record the client descriptor (exactly as the sources anonymise it), industry and region (LP breadcrumb), every named technology, the challenge count (it sets the number of ☐ items), and the headline figures (`facts.json` → `headline_figures`).
- Every row must end up in the LP, or be marked `left out: <reason>` (rhetoric such as "Leadership knew the fix wasn't a patch job" can be left out).

Source rules:
- **Never name the real client.** If `client_names_found` is not empty, or the PDF names the client anywhere (european-aviation-services names it), use the anonymised descriptor and flag it in the notes.
- Don't copy the PDF's own errors (typos like "Stablization", stray fragments). Don't invent anything: no new figures, technologies, timelines, team sizes, causes, actors or benefits the sources don't state. Zero is fine as a word ("zero data loss") only where the source says it.

## Step 3: Write `lp.md`
Copy `template.md` (everything after its header comment) and fill every slot in order. Keep each paragraph on one line. Delete the HTML comments.

**Keep exactly as written:** every line without a `{{slot}}`: navigation, buttons, notes, tick-bar copy, quiz screen, dev-team note, next-step block, form. Don't add structural labels such as "<H2>", "Heading:", "Lede:" or "Hero buttons:". The Markdown heading levels carry that.

**Source links (first two lines):** `**Original LP:** <LP link>` and `**Original PDF:** <PDF link>`, exactly as the user gave them.

**Change the wording, never the claim.** Each sentence you write restates one or more ledger rows. Before you move on, check it against the rows' locked words:

| Drift | Wrong (from real LPs) | Source | Right |
|---|---|---|---|
| Scope | "began looking for a way out, **starting with** the DR workloads" | "exit strategy for its DR workloads **specifically**" | "an exit that applied to its DR workloads specifically" |
| Scope | "the same framework as **every other system**" | "the same framework as **the rest of the environment**" | "the same DR framework as the rest of the environment" |
| Requirement | "had to be **dependable at all times**" | "needed… to be **fully managed without fail**" | "needed the environment to be fully managed without fail" |
| Actor / claim | "**Cloud4C's experts supported** the business well beyond the DR function" | "the **groundwork** of Cloud4C experts… **matters** well beyond the DR function" | "the groundwork Cloud4C's experts laid matters well beyond the DR function" |
| Qualifier | "a 3 TB HANA database" | "a 3 TB+ HANA database" | "a 3 TB+ HANA database" |
| Polarity | "A DR footprint that **does not** run in parallel" | "Sustaining production and DR in parallel" | "A way out of running production and DR in parallel" |
| Strength | "The upgrade **cleared** the operational limitations" | "**addressed** the operational limitations" | "addressed the issues that had piled up on the old release" |
| Condition vs time | "**Until** the database problem was resolved, … would remain constrained" | "**Without resolving** the underlying database problem…" | "Without a fix for the underlying database problem, …" |
| Invented detail | "ran on **dedicated hardware**", "**drained budget and staff time**" | "tying up resources, adding cost" | "tied up resources and added cost" |

- If you can't reword a clause without moving one of its locked words, **keep the source's wording for that clause** and reword the rest of the sentence. Meaning beats novelty.
- Don't merge two claims into a new cause and effect ("X, so Y") unless the source links them.
- Don't move a fact into a different role: a result stays a result and a requirement stays a requirement.
- Challenge titles are needs phrased positively ("A way out of…", "A scalable, OpEx-driven…"), and each restates a real source challenge.

**About, Challenge, Solution and Looking ahead must not read like the PDF or the old LP**, but must keep the same claims and technical detail. This avoids duplicate content on the site.
- Rebuild each paragraph from the ledger, not from the source paragraphs. Change the order of points, the sentence boundaries and the angle (for example, About: who they are, then why they acted).
- Keep product names, figures, qualifiers, technical terms and locked words exactly. Rephrase everything around them.
- Don't swap single words in a copied sentence. That still reads as a copy and fails the check.
- Target: no run of 10 or more words shared with either source (FAIL), and under 5% shared 8-word phrases. A 7–9 word run that holds locked words is acceptable (WARN).

**Section rules** (full limits are in `template.md`):
- **H1**: from the PDF title, US spelling, keeping its lead figure. **Lede**: 1–2 sentences, ≤45 words.
- **Tags**: `Case study  |  <Industry in words>  |  <service, 2–4 words>  |  <MEA / APAC / Europe / Americas / India>`.
- **Fact table**: 5 fixed rows. Technology lists only named products.
- **Story in 30 seconds**: 3 cards, each a bold headline (≤14 words) plus exactly 3 bullets (≤15 words, no full stop).
- **About**: exactly 2 paragraphs.
- **Challenge**: a bold lead that opens with the count word ("Four gaps…"), then one `☐` item per source challenge. Each title is the need a visitor would tick. The "Once ticked" line keeps "2 of N" with N = number of items.
- **Solution**: a bold lead, 4–6 past-tense H3s ending in a full stop, one paragraph each, and every technology from the sources' solution. Then the bold readiness line "How ready is your … for …?".
- **Results**: 4–8 `**Label.** Sentence.` bullets. **Every headline figure must appear, with its qualifier** ("approximately 40%", "80+", ">99%"). Outcomes stated in the body can be results too. Then `**Looking ahead.**` plus one paragraph.
- **Looking ahead when the sources have no road-ahead section** (the steel-manufacturing-corporation PDF and LP have none): restate the stated end state and results only. Don't add plans, next phases or "a foundation for future…" claims the sources don't make.
- **How does your project compare?**: a header, then one supporting line ("Five quick questions to see how ready your … is for ….") and exactly 5 short questions (≤10 words, bold, ending "?"). Each maps to this case study's challenges and solutions. Under each question goes one italic **help line** (8–20 words, full stop): it explains to the reader what the question is asking or what "in place" looks like, in plain words, without repeating the question or stating case study facts. Then `Not started   |   In progress   |   In place`.
- **Similar case studies**: only the dev-team note and the button. Never list case studies.
- **Next step**: the PDF link exactly as given, and "More stories in <industry, lower case>."

**Style** for all written copy:
- US English (center, organize, optimize).
- No em or en dashes, and no spaced hyphens as dashes.
- No hype and no AI clichés (the banned list is in case-study-verify).
- Plain, factual sentences of varied length. Third person in the narrative ("The client…", "Cloud4C…"). The UI copy in the template already speaks to the visitor.
- Never mention Capgemini.

## Step 3b: Self-check the meaning
Go through About, Challenge, Solution, Results and Looking ahead sentence by sentence. For each one, name the ledger rows it restates and confirm that every locked word survived. A sentence with no ledger row is invented: remove it. Then check that every ledger row is used or marked `left out`.

## Step 4: Build the Word document
```bash
python3 <skill-dir>/scripts/build_docx.py lp.md --out "/mnt/user-data/outputs/<Case Study Name> - LP Revamp.docx"
```
(Outside claude.ai, write it anywhere the user can download it.) The script recalculates the "N-minute read" line, so update the same line in `lp.md` to match what it prints.

## Step 5: Verify, then fix
Run the **`case-study-verify`** skill on `lp.md` with `--sources sources/`, `--lp-url <LP link>`, `--pdf-url <PDF link>` and `--align align.md`. Fix every FAIL in `lp.md` and every claim the audit marks anything other than Supported (Meaning changed, Understated, Overstated, Unsupported, Contradicted), rebuild the .docx, and re-run. Stop after 2 fix passes and report what still flags.

## Output
1. The full LP in Markdown, exactly as in `lp.md`.
2. The .docx download link.
3. Below a `---` line, short notes for the writer:
   - **Sources**: the LP and PDF links, and the extraction engine
   - **LP vs PDF**: each conflict and which wording was used, the LP-only points used, and any ledger rows left out (with why)
   - **Flags**: a real client name in the source, PDF typos, unmapped glyphs, anything uncertain
   - **Verification**: the script's summary line, plus any WARN left on purpose and why
   - **Tracker**: "Update CLOUD4C PAGE REVAMP.xlsx: column E (LP Word Document) and F (Content Status)."

## Edits after delivery
When the user asks to change part of the LP, change only that part in `lp.md`, keep all the rules above (the locked words especially), rebuild the .docx, re-run case-study-verify, and show the changed section with the new download link.
