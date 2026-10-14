<!--
CASE STUDY LP TEMPLATE (canonical skeleton for lp.md)

How to use this file
- Copy everything below the end of this comment into lp.md and replace every {{slot}}.
- Lines without a {{slot}} are fixed UI copy. Keep them exactly as written, including the
  curly quotes, the spacing around "|" and the square-bracket buttons.
- One paragraph per line. Leave a blank line between blocks. Don't hard-wrap.
- Markdown used: "#", "##" and "###" headings, "- " bullets, "1. " numbered items,
  **bold**, *italic* and one "| Fact | Detail |" table. build_docx.py turns these into
  the client template's Word styles. verify_lp.py reads the same markup (or the .docx).
- Repeat blocks marked "repeat" as many times as the rule says. Delete every HTML comment.
- Facts come only from the case study's own PDF and existing LP, never from example.md.

Slot rules (limits are checked by verify_lp.py)
- SOURCE LINKS: the first two lines. The existing LP link and the PDF link exactly as the user
  gave them, so the reviewer can open both originals from the top of the document.
- H1: built from the PDF title, US spelling, about 60-90 characters. Keep its lead figure.
- LEDE: 1-2 sentences, at most 45 words. Says what Cloud4C did and the headline outcome.
  Rewrite the PDF subtitle. Don't copy it.
- TAGS: "Case study  |  <Industry>  |  <Service, 2-4 words>  |  <Region code>". Take the
  industry from the LP breadcrumb, written in words ("Oil and Gas", not "Oil & Gas").
  Region codes: MEA, APAC, Europe, Americas, India.
- READ TIME: write any number. build_docx.py recalculates it.
- FACT TABLE: exactly these 5 rows. Client = the anonymised descriptor (never a real name).
  Sector = industry (sub-sector). Region = full region name. Technology = only products and
  platforms the sources name, comma-separated. Cloud4C role = one line, what Cloud4C did.
- STORY CARDS: 3 cards. Each has a bold one-line headline (at most 14 words) and exactly
  3 bullets (at most 15 words each, no full stop at the end).
- ABOUT: exactly 2 paragraphs, 35-80 words each. Who the client is, then why they acted.
- CHALLENGE LEAD: one bold sentence that states the number of challenges as a word
  ("Three", "Four", ...) and that must match the number of ☐ items.
- CHALLENGE ITEMS: one ☐ item per challenge in the sources (usually 3-6). The title is the
  need a visitor would tick, ending with a full stop. The paragraph after it is 30-70 words.
- ONCE TICKED: keep "2 of N", where N = the number of ☐ items.
- SOLUTION LEAD: one bold sentence that sums up the whole solution.
- SOLUTION ITEMS: 4-6 H3s, each a past-tense verb phrase ending with a full stop
  ("Migrated…", "Automated…"), with one 25-60 word paragraph each. Every technology in the
  sources' solution must appear somewhere in this section.
- READINESS CTA: "How ready is your <thing> for <outcome>?" in bold, matching this case.
- RESULTS: 4-8 bullets, each "**Label.** One sentence." Every headline figure (from the
  title, the subtitle and the results block of the PDF or LP) must appear with its qualifier
  (80+, approximately 40%, >99%, up to). Outcomes stated in the body can be results too.
- LOOKING AHEAD: one paragraph, 50-90 words, starting with "**Looking ahead.**".
  Built from the sources' road-ahead section. If there is none, restate the stated end state
  and results only, with no new plans or future claims.
- COMPARE LINE: "Five quick questions to see how ready your <thing> is for <goal>."
- COMPARE QUESTIONS: exactly 5 yes/no questions, at most 10 words each, in bold. Each maps to
  a challenge or solution in this case study.
- QUESTION HELP: one italic line under each question, 8-20 words, ending with a full stop. It
  tells the reader what the question is asking about or what "in place" looks like, in plain
  words. It doesn't repeat the question and it states no case study facts. The toggle line
  comes after it.
- INDUSTRY (next step): "More stories in <industry in lower case>."
- PDF URL: the case study's PDF link exactly as given.
-->
**Original LP:** {{existing LP URL}}

**Original PDF:** {{PDF URL}}

**Top navigation:** Challenge  |  Solution  |  Results  |  Self-check  |  More stories

[ Get the PDF ]

# {{H1}}

{{LEDE}}

**Case study  |  {{Industry}}  |  {{Service}}  |  {{Region code}}**

[ Read the story ]   [ Get the PDF ]

*{{N}}-minute read*

| Fact | Detail |
|---|---|
| Client | {{anonymised client descriptor}} |
| Sector | {{sector}} |
| Region | {{region}} |
| Technology | {{technologies named in the sources}} |
| Cloud4C role | {{one line}} |

## The story in 30 seconds

*Plays as you scroll. Pause, go back or jump to any part. Controls: Pause | Back | Next*

**1 of 3: The challenge**

**{{challenge headline}}**

- {{challenge bullet 1}}
- {{challenge bullet 2}}
- {{challenge bullet 3}}

[ Read the full challenge ]

**2 of 3: The solution**

**{{solution headline}}**

- {{solution bullet 1}}
- {{solution bullet 2}}
- {{solution bullet 3}}

[ Read the full solution ]

**3 of 3: The result**

**{{result headline}}**

- {{result bullet 1}}
- {{result bullet 2}}
- {{result bullet 3}}

[ See all the results ]   [ Get the PDF ]

## About the client

{{about paragraph 1}}

{{about paragraph 2}}

## The challenge

*Tick the ones that sound familiar. We’ll tailor the conversation.*

**{{Count word}} {{challenge lead sentence}}**

<!-- repeat: one per challenge -->
☐ **{{challenge need}}.**

{{challenge paragraph}}

**Tick bar:** *“Tick any that sound familiar or talk to an expert anyway.”*

**Once ticked:** *“2 of {{N}} sound familiar. Talk to someone who has solved them.”*

[ Talk to an expert ]

## The solution

**{{solution lead sentence}}**

<!-- repeat: 4-6 -->
### {{Past-tense solution step}}.

{{solution paragraph}}

**How ready is your {{thing}} for {{outcome}}?**

[ Take the readiness check ]

## The results

<!-- repeat: 4-8 -->
- **{{Result label}}.** {{result sentence}}

**Looking ahead.** {{looking ahead paragraph}}

## How does your project compare?

Five quick questions to see how ready your {{thing}} is for {{goal}}.

1. **{{Question 1}}?**
   *{{Question 1 help line}}.*
   Not started   |   In progress   |   In place
2. **{{Question 2}}?**
   *{{Question 2 help line}}.*
   Not started   |   In progress   |   In place
3. **{{Question 3}}?**
   *{{Question 3 help line}}.*
   Not started   |   In progress   |   In place
4. **{{Question 4}}?**
   *{{Question 4 help line}}.*
   Not started   |   In progress   |   In place
5. **{{Question 5}}?**
   *{{Question 5 help line}}.*
   Not started   |   In progress   |   In place

### Quiz result screen

Score and tier, then: “Here is where you stand against what this program had to solve.”

[ See how it was solved ]

*Shown per item.*

[ Email me my readiness summary ]   [ Retake ]

## Similar case studies

*Note for the Dev team: add related or similar case studies here from the case study library.*

[ Browse all case studies ]

## Take the next step

Read it offline or talk to the team that did it.

### The full case study

The complete story as a PDF, ready to share with your team.

[ Get the PDF ]

{{PDF URL}}

### An expert call

Thirty minutes with someone who has solved this.

[ Talk to an expert ]

### More stories in {{industry}}.

Get new case studies by email.

Work email (field)

[ Follow ]

## Talk to the team that built it

Tell us what you are working on and an expert will reply to set up a call.

1. You send a short note.
2. An expert reads it, along with what you explored on this page if you choose to share it.
3. You get a reply to arrange a 30-minute call.

### FORM FIELDS

- Name
- Work email
- Company
- Your role
- What would you like to talk about? (A project like this one | A readiness review of our platform | Engagement and pricing | Just exploring)
- Anything we should know? (optional)
- Share what I explored on this page (tick box, shown when the visitor has ticked challenges or taken the quiz)

[ Request a call ]

**Confirmation:** *“Thanks, [first name]. An expert will reply to [email] to set up a call.”*
