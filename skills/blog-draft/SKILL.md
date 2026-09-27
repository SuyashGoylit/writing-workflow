---
name: blog-draft
description: Write the full SEO blog draft from an approved research brief and outline, following the Cloud4C style rules (third person, no em dashes, no AI clichés, 1200-1500 words, search-optimised H2s, closing 2-paragraph Cloud4C pitch), then run the blog-audit skill on it. Use when the user approves an outline ("draft it", "write it", "go ahead"), or asks to write or rewrite a full blog.
---

# Blog Draft

Write the complete blog from the approved outline in this conversation. If there is no outline yet, run the `blog-research` skill first.

## Before writing
Re-read these from project knowledge and follow them exactly:
- `style-rules.md`: all rules
- `competitors.md`: names that must never appear
- `cloud4c-solutions.md`: for the closing pitch and internal-link URLs
- `voice-guide.md`: how her published blogs open, build headings, cite, link and close
- 1-2 of the writer's past articles in `past-articles/` that are closest in topic, to match voice and rhythm. If there are none, rely on `voice-guide.md` alone.

## Writing guidelines
Beyond the style rules:

**Intro**
- 3-4 paragraphs. Open with a concrete scene an enterprise would recognise (see the examples in `voice-guide.md`). Never open with a definition, a question, or "In today's…".
- Widen to the shift and what it means now, then end on a one-line signpost to the body.
- Use a primary keyword within the first 100 words.

**Sections**
- Each H2 section opens with its main point in the first sentence. No throat-clearing, and don't restate the heading.
- Use specifics: named clouds, tools, regulations (NIS2, DORA and so on), programs, dates and realistic operational scenarios. Use numbers only from the research brief's stats table, with a numbered citation marker after the claim (…in 2026³). Expand acronyms on first use.
- Add 2-5 internal links as bold keyword anchors to relevant cloud4c.com pages (URLs in `cloud4c-solutions.md`, or past-article URLs from the brief).
- Use H3s for individual use cases or reasons. Give each H3 2-3 short paragraphs, or a short paragraph plus a tight bullet list. Don't make every section the same shape.
- Hit the per-section word targets from the outline.

**Keywords**
- Place each primary keyword where the outline assigned it, in a grammatical frame. Awkward phrases such as "ai cmp services" get one natural use ("AI CMP services such as…").
- Use secondary keywords in headings and body where they fit.

**Rhythm**
- Mix short and long sentences, vary openers, and use "And" or "But" to start a sentence at most 2-3 times.
- Avoid lists of three in every paragraph.
- Keep paragraphs to 2-5 sentences, mostly under about 100 words.

**Pitch, FAQ, Sources**
- The Cloud4C H2 comes after the body: exactly 2 paragraphs plus an optional one-line bold CTA link, following the pitch format in `cloud4c-solutions.md`.
- Tie it back to the specific problems the blog raised.
- Never mention Capgemini, and never write "we", "our" or "us".
- Then add "## Frequently Asked Questions:" with 5 bulleted questions and 1-2 sentence answers, using primary keywords naturally.
- End with "**Sources:**", listing the numbered sources.

## Self-check while writing
Before showing anything, scan the draft yourself for:
- em or en dashes
- you, your, I, we, our or let's
- rhetorical questions outside headings or the FAQ
- "not just… but", "no longer just", or "it's not X, it's Y"
- any banned cliché
- competitor names
- a "Conclusion" heading

Fix them first.

## Output
1. The full blog in Markdown (`#` title, `##` H2, `###` H3), with no commentary inside it.
2. Save the same Markdown to a file (for example `draft.md`) and immediately run the **`blog-audit`** skill on it, passing the primary keywords and the secondary keywords from the brief.
3. Below a `---` line, add short writer notes: the final word count, the sources cited (with URLs), internal-link suggestions from past articles, and the audit summary.

If the audit shows FAIL items, fix them (as the audit skill describes) before presenting the final version, so the user sees the corrected blog.
