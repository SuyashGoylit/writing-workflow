# Cloud4C Blog Workflow for claude.ai

A setup that replaces the two copy-pasted prompts with:
- a **claude.ai Project** that holds the permanent rules and reference files
- a **custom Style** built from past articles
- **three skills**: `blog-research` → `blog-draft` → `blog-audit`

Research and reference-finding are automated, and the rules are checked by a script.

```
Topic + keywords ──► blog-research ──► brief + outline ──(she approves)──► blog-draft ──► blog-audit ──► iterate ──► Quillbot ──► deliver
                     (web search,        (7-8 refs, secondary                (1200-1500 words,   (script checks,
                      skips competitors)  keywords, stats, H2s)                Cloud4C pitch)      auto-fixes)
```

## What's in this repo

| Path | What it's for |
|---|---|
| `project/instructions.md` | Paste into the Project's **custom instructions** |
| `project/knowledge/style-rules.md` | Full writing rules (the cleaned-up version of the old prompt 2) |
| `project/knowledge/competitors.md` | Competitor names and domains that must never be used |
| `project/knowledge/cloud4c-solutions.md` | Cloud4C facts and solutions for the closing pitch |
| `project/knowledge/voice-guide.md` | How her published blogs actually read, drawn from her 6 articles |
| `project/knowledge/past-articles/` | Her 6 published blogs as .md (fetched from cloud4c.com), plus `sources.txt` |
| `skills/blog-research/` | Web research, reference articles, secondary keywords, outline |
| `skills/blog-draft/` | Writes the blog from the approved outline |
| `skills/blog-audit/` | Python script that checks every rule, plus fix instructions |
| `scripts/package.sh` | Builds `dist/*.zip` for uploading skills |
| `scripts/fetch_articles.py` | Downloads published cloud4c.com blog posts into `past-articles/` as Markdown |
| `tests/samples/` | Bad and clean samples for testing the audit script |

## One-time setup (about 15 minutes)

Needs a **Pro or Max** plan.

1. **Turn on the capabilities.** Go to claude.ai → Settings → Capabilities and turn on **Code execution and file creation** (the skills need it) and **Skills**. Make sure web search is available in chats.
2. **Upload the skills.** Run `./scripts/package.sh`, then in Settings → Capabilities → Skills, choose **Upload skill** for each zip in `dist/`: `blog-research.zip`, `blog-draft.zip` and `blog-audit.zip`. Make sure all three are toggled on.
3. **Create the project.** Go to Projects → New project and name it **Cloud4C Blogs**.
   - **Custom instructions:** paste the contents of `project/instructions.md`.
   - **Project knowledge:** upload `style-rules.md`, `voice-guide.md`, `competitors.md`, `cloud4c-solutions.md` and the six `.md` files in `past-articles/`. Skip that folder's `README.md` and `sources.txt`.
4. **Create the Style.** In any chat, open the style menu → Create & edit styles → **Create custom style** and upload these four from `past-articles/`, which cover her different formats:
   - `top-trends-in-energy-and-utility-cloud-offerings.md` (listicle)
   - `ai-msp-in-the-middle-east-an-overview.md` (long-form overview)
   - `traditional-managed-ops-versus-aiops-which-one-to-choose.md` (comparison)
   - `10-questions-to-ask-an-mssp-in-2026.md` (questions format)

   Name it after her ("Her voice") and select it whenever she writes in the project.

## Daily use

1. Open **Cloud4C Blogs**, start a new chat, and select her Style. For unfamiliar domains she can also turn on **Research** mode for the first step.
2. Send the topic and keywords. Links are optional; the skill finds the rest:
   ```
   New blog.
   Topic: AI-assisted Cloud Management Portals: Use-cases and Reasons why they are a Must for Enterprises with Large-scale Hybrid/Multi-cloud Landscapes
   Primary keywords: ai powered cloud management platform; ai cloud management platform; ai powered cmp; ai powered multi cloud management; ai powered multi cloud management services; ai cmp platform services; ai cmp services
   Links (optional): https://www.yugabyte.com/key-concepts/benefits-of-ai-in-cloud-computing/
   ```
3. Review the **research brief and outline**. Change anything ("swap H2 3 for a FinOps section", "drop the FAQ"), then reply **"draft it"**.
4. The draft comes back already audited. Iterate as usual ("make the intro shorter", "rewrite the security use case with a banking example").
5. After manual edits, paste the text (or upload the .docx) and say **"audit"**.
6. Run the final **Quillbot** check yourself. Claude can't see Quillbot scores; the audit only targets the patterns detectors tend to flag.

## Maintaining it

- **New banned phrase or AI tell spotted:** add it to `skills/blog-audit/banned_phrases.txt`, rebuild with `./scripts/package.sh`, and re-upload `blog-audit.zip`.
- **Competitor list changes:** update both `project/knowledge/competitors.md` (re-upload it to the Project) and `skills/blog-audit/competitors.txt` (rebuild and re-upload).
- **She publishes a new article:** run `python3 scripts/fetch_articles.py <url>`. This needs `pip install beautifulsoup4 html2text`. The URL is added to `sources.txt` and the post is saved to `past-articles/`. Upload the new .md to the Project.
- **Cloud4C offerings change:** update `cloud4c-solutions.md` and re-upload it. Check the company figures on cloud4c.com every few months.
- **Test the audit script locally:**
  ```bash
  python3 skills/blog-audit/scripts/audit.py tests/samples/bad_sample.md --keywords "ai powered cmp"
  python3 skills/blog-audit/scripts/audit.py path/to/article.docx --keywords "kw1; kw2"
  ```

## Important notes

- **What her published posts taught the setup:** they open with a scene, use keyword-led headings, often as numbered-H3 listicles, and include bold internal links, numbered citations with a Sources list, and a 5-question FAQ after the pitch. All of that is now built into the rules and skills. The audit also flagged places where the published posts break her own brief (see `voice-guide.md` §9). The rules still follow the brief.
- **Assumption to confirm:** the 1200-1500 target excludes the FAQ. Her published posts fit that reading (about 1,400 words each before the FAQ where the brief was likely 1200-1500).

- **Cloud4C is part of Capgemini**, and Capgemini is on the competitor list. The pitch never mentions the parent company. This is built into the rules and the audit.
- **Red Hat is IBM-owned.** One of the original example references was redhat.com. It's treated as background-only unless she decides otherwise (see `competitors.md`).
- **Changes from the old prompts:**
  - The "0-3% on Quillbot" line was replaced with rules that can be checked, because Claude can't measure detector scores.
  - The "if we're clear…" handshake became the outline-approval step.
  - The contradictory "write as you speak" and "no you/I" rules were reconciled into third-person conversational writing.
  - The missing "Structure of blog" section was written out in `style-rules.md` §4.
