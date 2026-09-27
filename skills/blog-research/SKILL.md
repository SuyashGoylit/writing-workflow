---
name: blog-research
description: Research an SEO blog topic before writing. Finds and summarises 7-8 top-ranking reference articles (excluding competitor sites), gathers secondary keywords, People Also Ask questions, recent sourced statistics and content gaps, then proposes a search-optimised H2/H3 outline for approval. Use whenever the user gives a blog topic and keywords, says "research this", "new blog", "find references", or pastes a topic with primary keywords.
---

# Blog Research

Turn a topic and keyword list into a **research brief** and an **approved outline**. Do not write the blog in this step.

## Inputs
Take these from the user's message:
- **Topic / working title** (required)
- **Primary keywords** (required, usually 3-8 phrases)
- **Reference links** (optional). If the user provides links, include them in the reference set (unless they are competitor domains), then search to fill up to 7-8 total.
- **Word count** (optional, default 1200-1500)
- **Special instructions** (optional, such as an angle, audience, or region)

If the topic or keywords are missing, ask for them in one short question and stop.

## Rules that apply during research
- Read `competitors.md` from project knowledge. **Never choose a competitor domain as a reference, and never take stats from one.** If a search result comes from a competitor, skip it silently. Competitor pages can only inform general understanding.
- Treat `redhat.com` as background-only (IBM subsidiary) unless the user supplied it and confirms it is fine.
- Prefer sources published or updated in the **last 12-18 months**. Note the date of every source.
- Prefer these source types, in order: analyst and research firms (Gartner, IDC, Forrester, Flexera, McKinsey), hyperscaler docs and blogs (AWS, Azure, Google Cloud), reputable trade press, then vendor blogs from non-competitors.
- Never invent a statistic. If a number can't be tied to a named source and year, leave it out.

## Procedure

1. **Search the SERP.** Run web searches for:
   - the topic as a phrase
   - each primary keyword (group near-duplicates, such as "ai cmp services" and "ai cmp platform services", into one search)
   - "<topic> use cases", "<topic> benefits", "<topic> statistics 2026" (use the current year)
   - "what is <core concept>" and "<core concept> vs <nearest alternative>"

   Note recurring title patterns and questions phrased the way people ask them (People Also Ask style).

2. **Pick 7-8 reference articles.** Choose the strongest non-competitor results that rank for the topic. Aim for a mix of explainers, use-case pieces and data-backed articles. Fetch each one and extract:
   - its H2 structure
   - the key points and any unique angle
   - usable statistics (with source, year and URL)
   - anything outdated or missing

3. **Build the secondary keyword list** (8-15 terms). Take them from SERP titles and H2s, People Also Ask questions, related searches, and entities that keep coming up (for example AIOps, FinOps, CSPM, IaC, Kubernetes, governance, observability, cost optimisation, sovereign cloud). Don't repeat the primary keywords.

4. **Find content gaps.** List 3-5 things the top articles miss or handle poorly, such as enterprise-scale concerns, hybrid rather than pure public cloud, regulated industries, agentic AI in operations, or current-year data. The blog should win on these.

5. **Check past articles.** If the project knowledge has the writer's earlier blogs (in `past-articles/`, each with its source URL in the first line), note any angle already covered (so it isn't repeated) and 2-4 internal-link candidates: past blog URLs plus relevant cloud4c.com solution pages from `cloud4c-solutions.md`. If there are no past articles, skip the overlap check and suggest solution-page links only.

6. **Propose the outline.**
   - Title (H1) with the main primary keyword, under about 65 characters if possible.
   - An intro plan of 3-4 paragraphs with no heading: the opening scene (a concrete situation, see `voice-guide.md`), the shift, what it means now, and a signpost. Note which primary keyword appears in the first 100 words.
   - A body shape: **sectioned** (5-7 keyword-led H2s) or **listicle** (framing H2s plus one umbrella H2 with numbered H3s). Topics built on use cases, reasons, trends or questions usually suit the listicle. Phrase headings as searches: keyword first with a colon descriptor, questions, or "X vs Y". At least 40% of body headings should include a primary or secondary keyword.
   - A target word count for each section, summing to the target range.
   - Which primary keywords go in which section, so every keyword is placed once and none is stuffed.
   - Which stats from the stats table go where.
   - The Cloud4C pitch H2, such as "How Cloud4C Supports <audience/outcome>". Name the 2-4 Cloud4C solutions from `cloud4c-solutions.md` that fit the topic.
   - An FAQ after the pitch: 5 PAA-style questions, extra to the word target.

## Output format

```
## Research Brief: <topic>

### Reference articles (7-8)
| # | Title | Source | Date | Why it's useful |
(include each URL)

### Secondary keywords
comma-separated list

### Statistics to use
| Stat | Source (non-competitor) | Year | URL |

### Content gaps to win on
- …

### Past-article overlap and internal links
- …

## Proposed Outline
# <Title>
Intro (≈120 words): hook…, keyword…
## H2 … (≈200 words), keywords: …, stats: …
### H3 …
…
## How Cloud4C Supports … (≈180 words, 2 paragraphs + CTA line), solutions: …
## Frequently Asked Questions: (5 Qs, listed)

**Total ≈ N words (excluding FAQ)**
```

End with one line: **"Reply 'draft it' to write the blog, or tell me what to change in the outline."** Then stop. Don't start drafting until the user approves.
