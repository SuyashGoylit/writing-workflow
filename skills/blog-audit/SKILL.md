---
name: blog-audit
description: Check a blog draft against the Cloud4C style rules with a script. Covers word count, em/en dashes, banned AI-cliché phrases, you/I/we, competitor names, rhetorical questions, conclusion vs Cloud4C pitch, keyword coverage and H2 optimisation, sentence-length variety and repeated openers. Then fixes the issues. Use after every draft, or when the user says "audit", "check this", "check the rules", "is this ok", or pastes a blog or uploads a .docx to review.
---

# Blog Audit

Check a draft with `scripts/audit.py`, report the results, then fix what failed.

## 1. Get the draft into a file
- If the blog is in the conversation, write the latest full version to `draft.md` exactly as it stands, in Markdown with `#`/`##`/`###` headings.
- If the user uploaded a `.docx`, `.md` or `.txt` file, audit that file directly. The script reads Word headings.
- Leave out writer notes. The script ignores anything after a final `---` line, and a trailing "Sources:" list. The word-count target applies to everything except the FAQ.

## 2. Run the script
The script lives in this skill's folder (`scripts/audit.py`, next to `banned_phrases.txt` and `competitors.txt`). Run it with Python 3 (standard library only):

```bash
python3 <skill-dir>/scripts/audit.py draft.md \
  --keywords "primary kw 1; primary kw 2; …" \
  --secondary "secondary kw 1; secondary kw 2; …" \
  --min 1200 --max 1500
```

- Take the keywords from the conversation: the user's primary keywords and the research brief's secondary keywords.
- Change `--min` and `--max` if the user asked for a different length.
- Exit code 1 means there is at least one FAIL.

## 3. Report
Show the user the script's summary table. Then, in 2-4 bullets, explain what matters, such as "3 em dashes, 1 rhetorical question, keyword 'ai cmp services' missing". Don't paste the whole details list unless asked.

## 4. Fix
- **FAIL items must be fixed.** Rewrite only the affected sentences, keeping meaning and voice:
  - Dashes: split into two sentences, or use a comma, colon or parentheses.
  - You/we: rephrase in the third person ("Enterprises…", "IT teams…", "Cloud4C…").
  - Rhetorical question: turn it into a direct statement.
  - "Not just X but Y" or "no longer just": state Y directly.
  - Competitor name: remove it and rephrase generically. If a stat came from that competitor, drop it.
  - Missing keyword: work it naturally into the section the outline assigned it to.
  - Word count: expand or trim the section furthest from its target. Don't pad.
  - Conclusion heading or missing pitch: replace with the 2-paragraph Cloud4C pitch.
  - Missing FAQ: add 5 search-style questions with short answers after the pitch.
- **WARN items: use judgement.**
  - Watch-list words: cut most of them and keep only ones that are technically necessary.
  - Low sentence-length variation or similar-length runs: break some long sentences into short ones and merge a few mid-length ones.
  - Repeated openers: vary them.
  - Keywords missing from H2s: rephrase 1-2 H2s as searches.
  - Competitor hits that aren't brand usage (such as "orange" as a colour): ignore them and say so.
- Re-run the script after fixing. Stop after 2 fix passes and report anything that still flags.
- Show the corrected blog in full (or only the changed sections if the user is iterating on a part), followed by the final summary table.

## Notes
- The script can't measure AI-detector scores such as Quillbot's. It checks the patterns detectors tend to pick up: uniform sentence length, stock phrases, and dashes. Remind the user to run the final Quillbot check themselves.
- To add new banned phrases, the user can say "add '<phrase>' to the banned list". Tell them to update `banned_phrases.txt` in the skill, because skill files can't be edited from chat. Until then, avoid the phrase manually for the rest of the conversation.
