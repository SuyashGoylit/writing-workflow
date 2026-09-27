# Blog Style Rules (Cloud4C)

These are the full writing rules for every blog. The project instructions summarise them; this file is the authoritative version.

## 1. Voice and tone
- Professional and conversational, written in the **third person**. No "you", "your", "I", "we", "our", "us", "let's".
  - Instead of: "You can cut costs by…" write: "Enterprises can cut costs by…" or "Teams that adopt X cut costs by…"
- Direct and concise. Get to the point and cut words that don't add meaning.
  - Instead of: "It is important to note that organizations should consider…" write: "Organizations should consider…"
- Plain, natural sentences. Starting a sentence with "And" or "But" is fine occasionally (no more than 2-3 times per blog).
- No marketing hype, including in the body sections. Save the promotional tone for the Cloud4C pitch at the end, and even there keep it factual.
  - Instead of: "This revolutionary platform will transform operations." write: "The platform can help teams detect incidents earlier."
- No fluff. Remove adjectives and adverbs that don't carry information (very, truly, incredibly, highly, extremely, seamlessly, significantly).
- Aim for clarity. One idea per sentence and one topic per paragraph. Paragraphs of 2-5 sentences, mostly under about 100 words.

## 2. Banned constructions
- **No em dashes (—) or en dashes (–)**, and no spaced hyphens used as dashes (" - "). Use a full stop, comma, colon or parentheses instead.
- **No "It's no longer just about…"**, "not just X, but Y", "X isn't just Y, it's Z", "more than just", or other contrast-reveal framing.
- **No rhetorical questions** in body text. Questions are allowed only as H2/H3 headings and in an FAQ section.
- **No forced dramatic statements** ("The result? Chaos." / "Here's the catch." / "The truth is…").
- **No AI-giveaway clichés**: dive into, delve, unleash, unlock the potential, game-changer, in today's fast-paced world, ever-evolving landscape, harness the power, navigate the complexities, tapestry, testament to, realm. The full list is in the audit skill's `banned_phrases.txt`.
- Acceptable direct phrasing: "Here's how it works.", "This matters because…", "The main benefit is…"

## 3. Rhythm (what AI detectors pick up on)
- Vary sentence length. Mix short sentences (5-8 words) with medium and long ones (20-30 words). Don't write runs of sentences that are all the same length.
- Vary sentence openers. Don't start consecutive sentences with the same word, and limit "This", "These", "It", "Additionally", "Moreover" and "Furthermore".
- Use concrete specifics: named technologies (Kubernetes, Terraform, FinOps, AIOps, CSPM), realistic scenarios, and numbers with sources. Generic statements read as machine-written.
- Avoid symmetrical lists of three in every paragraph. Use two items, four items, or a single strong point.
- Don't open or close each section with a summary sentence that repeats the heading.

## 4. Structure
See `voice-guide.md` for real examples of each element.

1. **Title (H1)**: contains the main primary keyword. Under about 65 characters if possible.
2. **Introduction**: 3-4 paragraphs with no heading. Open with a concrete scene, then the shift, then what it means now, then a one-line signpost to the body. Use a primary keyword in the first 100 words.
3. **Body**: choose the shape that fits the topic:
   - **Sectioned:** 5-7 keyword-led H2s, with H3s where needed.
   - **Listicle** (use cases, reasons, trends, questions, differences): 1-2 framing H2s, then one umbrella H2 with **numbered H3s** ("### 1. …").
   - Write headings the way people search. Keyword first, colon descriptor ("AI Cloud Management Platform for Hybrid Estates: Where Automation Pays Off"), questions, or "X vs Y".
   - At least 40% of body H2s and H3s include a primary or secondary keyword, used naturally.
   - Use bullet points only where content really is list-like. Don't turn everything into bullets.
4. **Closing (instead of a conclusion)**: an H2 such as "How Cloud4C Supports [Audience/Outcome]" followed by **exactly 2 paragraphs** pitching Cloud4C's multi-cloud and hybrid cloud expertise and the solutions relevant to the topic, plus an optional **one-line bold CTA link**. Use `cloud4c-solutions.md`. Never add a "Conclusion" heading.
5. **FAQ (after the pitch)**: "## Frequently Asked Questions:" with **5 bulleted questions** phrased as searches, each with a 1-2 sentence direct answer. Include primary keywords naturally. This is standard in all her published posts, so include it unless told otherwise.
6. **Sources (very end)**: a "**Sources:**" list matching the numbered citation markers in the text.

## 4a. Links
- Add 2-5 **internal links** to relevant cloud4c.com pages, using bold keyword anchors, in the intro and body. For example, `[**hybrid cloud managed services**](https://www.cloud4c.com/solutions/hybrid-cloud)`. Pick URLs from `cloud4c-solutions.md`.
- The pitch links the Self-Healing Operations Platform and 1-2 relevant services.
- Never link to competitors.

## 5. Length and keywords
- **1200-1500 words** by default, or whatever length is given for that blog. This counts the title, intro, body and pitch. The FAQ (about 150-250 words) and Sources come **on top**.
- Use every primary keyword at least once, naturally. Don't use any single keyword phrase more than 3-4 times.
- Secondary keywords come from research (SERP titles, People Also Ask, related searches). Use 5-10 of them across headings and body.
- Don't stuff keywords into sentences where they read awkwardly. If a keyword phrase is ungrammatical (for example "ai cmp services"), use it once in a natural frame ("AI CMP services such as…").

## 6. Accuracy and currency
- Every statistic needs a named source and year. Prefer sources from the last 12-18 months. Don't invent numbers. If a claim can't be sourced, write it qualitatively.
- Cite with a numbered marker straight after the claim (…binding time limits on permitting¹), and list each source under "**Sources:**" at the end.
- Expand acronyms on first use: "SCADA (Supervisory Control and Data Acquisition)".
- Use named regulations, programs, dates and places rather than generic statements. This specificity is the core of the voice.
- Use current terminology (agentic AI, AIOps, FinOps, platform engineering, sovereign cloud) where relevant, without buzzword stacking.

## 7. Competitors (hard rule)
See `competitors.md`. Never name, cite, quote, link to, or use stats from any competitor. Competitor websites may only be used for background understanding during research.
