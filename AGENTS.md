# Berean Voice PDF ingestion instructions

These instructions govern all PDF-to-archive work in this repository. They are intended to make each future extraction repeatable from a very short request.

A sufficient future request is:

> Use the attached PDF as the next authorized issue. Follow this repository's `AGENTS.md` completely and open the draft pull request.

Once the user makes an equivalent request and supplies the PDF, carry out the full workflow below. Do not stop after proposing a plan, showing a sample article, or creating an empty folder structure.

## Purpose and permission model

This repository stores CMS-ready articles from PDF issues published by The Berean Voice. The project owner reports that the publisher has permitted reuse of the material, except where an individual article contains its own notice requiring permission or prohibiting reprinting.

Treat that statement as the project eligibility rule, not as a claim that the material is public domain. Preserve all credits and provenance. Apply the article-level exclusion gate below before transcribing or exporting anything.

Use publication, publisher, issue, title, and byline names exactly as printed in the source. Do not silently normalize a source name if it differs from earlier issues or repository wording.

## Expected outcome

For each supplied issue, complete all of the following:

1. Inspect the existing repository and the complete PDF.
2. Inventory the issue and identify article boundaries and continuation pages.
3. Exclude every article carrying an article-specific reuse restriction.
4. Visually transcribe every eligible article into semantic HTML without changing its text.
5. Export and associate its images.
6. Update the root `index.json`, which is the single source of truth.
7. Validate text, formatting, metadata, files, links, and exclusions.
8. Create a branch from the latest default branch, commit the finished work, push it, and open a draft pull request.
9. Report exactly what was included, skipped, verified, and left uncertain.

## AI-first method; no automatic converter

This is an AI visual-reading and editorial transcription workflow. Do not build, add, or treat a general PDF-to-HTML converter, OCR pipeline, parser, scraper, or extraction script as the source of truth.

Permitted aids include:

- rendering PDF pages at sufficient resolution for visual reading;
- inspecting the PDF text layer or OCR output to locate possible text;
- extracting embedded image assets;
- cropping or rendering a relevant image region;
- calculating hashes and dimensions; and
- using validation tools to parse JSON/HTML and verify IDs, paths, and links.

AI must make and visually verify the decisions about article eligibility, article boundaries, reading order, wording, punctuation, formatting, image ownership, captions, credits, and categories. Never trust mechanically extracted text without checking it against the rendered page.

Do not commit a converter, extraction script, generated OCR dump, page render, contact sheet, temporary working file, or source PDF. Validation helpers may be used locally but are not part of the archive unless the user explicitly changes the repository contract.

## Inspect existing state before editing

Before extracting a new issue:

1. Read this file, `README.md`, and `index.json` completely.
2. Inspect the existing files under `src/` and `src/images/`.
3. Check the repository status, default branch, recent merged work, and open pull requests.
4. Start from the latest remote default branch and preserve all unrelated work.
5. Compute the supplied PDF's SHA-256 hash and compare its filename, hash, issue data, article titles, and pages with existing index records.
6. Do not duplicate content that is already present. If the PDF is a corrected copy of an indexed issue, preserve existing article UUIDs and update the matching records and files.
7. If the intended result is already present byte-for-byte on the default branch, do not create a redundant branch, commit, or pull request. Report that it is already complete.

## Define the issue inventory

Inspect every PDF page in reading order. Reconcile the table of contents, if present, with the actual content pages; the content pages are authoritative.

Include substantive titled or signed editorial content such as articles, editorials, regular columns, stories, poems, and hymn histories. Exclude the cover, table of contents, general masthead, advertisements, order/subscription forms, mailing panels, and standalone decorative matter unless the user specifically asks for them.

For each candidate article, identify:

- exact title and subtitle;
- section or recurring-column label;
- exact byline and stated author location or role;
- first and final printed page;
- all continuation pages, even when nonconsecutive;
- images, captions, credits, footnotes, sidebars, and pull quotes belonging to it; and
- all permission or reprint notices from its first heading through its final line.

Assign a sequence number based on the issue's article order. Keep that sequence number in skipped audit records too, so gaps in the included article sequence are expected and explainable.

## Hard article-eligibility gate

Examine the entire article, including headings, continuation pages, footnotes, captions, sidebars, text embedded in associated graphics, and notices at the beginning or end.

Skip the entire article if any wording anywhere in it says or implies that separate permission is required to copy, use, reproduce, or reprint it. Examples include:

- “Used by permission”;
- “Reprinted by permission”;
- “Please do not reprint without permission”;
- “Permission required”;
- “Obtain permission before reprinting”; or
- any equivalent instruction, even when phrased differently.

This is an automatic whole-article exclusion. It also applies when the restrictive notice appears to concern an image within the article: do not export part of an article while leaving a rights-dependent asset behind. When uncertain whether wording requires separate permission, exclude the article and record the uncertainty rather than guessing that it is eligible.

An ordinary creator, photographer, stock source, or repository credit does not by itself trigger exclusion. Preserve it in image metadata. Do not invent or infer a licence from a credit such as “Wiki Commons” or “Adobe Stock.”

For an excluded article:

- do not assign a UUID;
- do not create an HTML file;
- do not export any image;
- do not add it to the top-level `articles` array;
- do not reproduce its body text elsewhere; and
- add only a minimal top-level `skipped` audit record using the existing schema.

The skipped record should contain the issue ID, issue sequence, exact title and byline when available, printed page range, a concise reason, the exact detected notice or notices, `html_exported: false`, and `images_exported: false`. A skipped record must not contain an article UUID, HTML path, or image path.

Do not confuse a general magazine policy or masthead copyright notice with an article-specific restriction. The project owner's publisher permission governs otherwise eligible material; the stricter article-specific notice overrides it for that article.

## Exact transcription rules

Preserve the published article text exactly. Do not paraphrase, summarize, translate, modernize, fact-check, sanitize, improve, or silently correct it.

Preserve:

- spelling and apparent source errors;
- capitalization and word case;
- punctuation, quotation marks, apostrophes, dashes, ellipses, and scripture references;
- paragraph boundaries and intentional line breaks;
- headings and subheadings;
- italics, bold text, underlining, and genuine highlighting;
- block quotations and lists;
- poem, hymn, and lyric stanza/line structure;
- footnote markers and footnotes;
- exact captions; and
- author conclusions and sign-offs that are part of the body.

Normalize only nonsemantic print-layout artifacts:

- join a sentence split only by a column or page break;
- remove running headers, footers, page numbers, crop marks, and unrelated magazine furniture;
- remove a discretionary line-end hyphen when visual context confirms that the printed word is a single unhyphenated word; and
- retain intentional compound-word hyphens and every meaningful punctuation mark.

Do not duplicate a decorative pull quote when the same words already appear in the article body. Preserve it only when it contains unique substantive text, and record the decision in verification metadata when useful.

Resolve doubtful characters by returning to a high-resolution rendering and surrounding context. Do not invent unreadable text. If wording genuinely cannot be resolved, identify the exact printed page and passage, leave its verification state incomplete, and report the uncertainty.

## Repository contract

The archive structure is flat and UUID-based:

```text
AGENTS.md
README.md
index.json
src/
  <article-uuid>.html
  images/
    <article-uuid>-1.jpg
    <article-uuid>-2.jpg
    <article-uuid>-3.png
```

Rules:

- `index.json` is the only metadata catalogue.
- Do not create per-article JSON files.
- Store every eligible article HTML file directly in `src/`.
- Store every article image directly in the flat `src/images/` directory.
- Categories exist only in index metadata; do not create category folders.
- Do not put dates, titles, authors, or categories in filenames.
- Do not commit source PDFs or intermediate extraction artifacts.
- Do not restructure the repository while processing an issue.

## UUID and filename rules

Only after an article passes the eligibility gate, assign it a new RFC 4122 UUID. Use the UUID as the permanent article ID and HTML basename:

```text
src/<article-uuid>.html
```

Name associated images with the same UUID and a one-based increment in published reading order:

```text
src/images/<article-uuid>-1.jpg
src/images/<article-uuid>-2.jpg
```

Preserve an existing UUID when correcting or reprocessing the same indexed article. Never rename, recycle, or reuse an article UUID. Confirm uniqueness against `index.json`, HTML filenames, `data-article-id` attributes, and image filename prefixes.

## HTML contract

Each HTML file is a clean UTF-8 semantic fragment suitable for importing into Joomla or another CMS. Do not add `<!doctype>`, `<html>`, `<head>`, or `<body>` wrappers.

Use exactly one outer article element:

```html
<article data-article-id="<article-uuid>">
  ...exact article body...
</article>
```

Use appropriate elements such as `<p>`, `<h2>`, `<h3>`, `<em>`, `<strong>`, `<mark>`, `<blockquote>`, `<ul>`, `<ol>`, `<sup>`, `<figure>`, and `<figcaption>`. Preserve poetry, hymn, and lyric lineation with meaningful `<br>` elements or an equally faithful semantic structure.

Small descriptive classes such as `poem`, `lyrics`, `lead`, and `drop-cap` are allowed when they express meaningful source structure. Do not reproduce newspaper columns, absolute positioning, page geometry, decorative fonts, or PDF layout CSS.

The article title, subtitle, section label, byline, issue date, and categories live in `index.json` and normally are not duplicated as a header above the HTML body. A heading, dedication, byline, or sign-off that genuinely occurs within the body remains where printed.

Escape HTML syntax correctly. Do not add editorial explanations, generated citations, new links, advertising, style sheets, or text not present in the source. Alt text is accessibility metadata, not article text, and should be concise and factual.

## Image handling

Export only images that genuinely belong to eligible articles. Associate an image by visual/article context rather than by whichever text object happens to be nearest in the PDF internals.

- Prefer the original embedded asset when it faithfully reproduces the published image.
- Preserve the published content, crop, aspect ratio, orientation, and useful resolution.
- Do not generate replacement artwork or materially retouch an image.
- Crop, rotate, or flip an extracted asset only when needed to reproduce its printed appearance; record that transformation in verification metadata.
- Do not use a full-page screenshot when a clean article asset can be recovered.
- When meaningful vector or font-based content such as sheet music cannot be recovered as a normal embedded image, render only the relevant published region at high resolution, normally 300 dpi or better, and record the render method and resolution.
- Preserve a suitable original extension and avoid unnecessary conversion or recompression.
- Open every final image and visually check corruption, truncation, orientation, crop, ownership, and correspondence with the PDF.
- Preserve captions exactly in `<figcaption>` and index metadata.
- Write concise factual alt text; use an empty alt value for purely decorative images.
- Never export images belonging to skipped articles.

Treat `src/` as the eventual site export root. HTML image URLs must be root-relative:

```html
<img src="/images/<article-uuid>-1.jpg" alt="...">
```

The matching repository path is:

```text
src/images/<article-uuid>-1.jpg
```

Never use `src/images/...`, `../images/...`, repository URLs, temporary URLs, or local filesystem paths in article HTML.

## `index.json` is the single source of truth

Read and preserve the current schema and `format_version`. Append or update issue, article, and skipped records without deleting or reformatting unrelated data. Do not redesign the schema during ordinary ingestion.

### Issue metadata

Create one issue record when the PDF is new. Record all information actually available:

- stable issue ID;
- exact publication and publisher names;
- printed issue date as a structured value with the correct precision (exact day, month, season, or year);
- issue or volume number when present;
- source PDF filename;
- SHA-256 hash;
- PDF page count and printed page range; and
- publisher-permission statement and automatic article-exclusion rule.

Do not invent an exact day or month when the issue gives only a season or year.

### Included article metadata

Each eligible article record should retain all metadata actually present, following existing field names and nesting:

- permanent UUID and issue ID;
- issue sequence;
- exact title, subtitle, and section label;
- exact raw byline with printed line breaks represented faithfully;
- structured author name, location, role, life dates, or other stated details;
- printed `source_pages.start` and `source_pages.end`;
- primary and additional categories;
- series/part information, topics, publication notes, and other genuine metadata when present;
- HTML repository path;
- ordered image metadata;
- eligible rights status and `article_specific_permission_notice_detected: false`; and
- separate text, formatting, and image verification states.

Use `null` or omit an optional field consistently with the existing schema when the source does not supply it. Never infer an author location, date, role, image source, licence, or credit from appearance or outside assumptions.

### Image metadata

For each exported image, record all available fields using the current schema:

- one-based sequence;
- `repository_path` under `src/images/`;
- root-relative `public_path` under `/images/`;
- printed source page;
- role in the article;
- concise alt text;
- exact caption or `null`;
- stated credit/source or `null`;
- rights note that distinguishes stated facts from uncertainty; and
- any crop, flip, rotation, render method, or other necessary transformation.

Do not claim a licence or permission that the PDF does not state. Record uncertainty plainly for later production review.

## Categories

Before categorizing new articles, inspect both:

1. category names already used in `index.json`; and
2. the current category list at <https://truechristian.church/remnant-articles>.

Prefer an existing category whenever it reasonably fits. Preserve the website's spelling and capitalization and use a stable lowercase URL-style slug consistent with existing entries. Multiple categories are allowed when justified, but identify one primary category. Add a new category only when no existing category reasonably fits. Never alter article text to fit a category.

## Required verification gate

Complete every applicable check before committing:

1. Build a page-by-page candidate article inventory, including all continuation pages.
2. Reconcile included and skipped counts and titles with the issue contents.
3. Recheck every article through its final line for reuse restrictions.
4. Confirm that skipped articles have no UUID, HTML, or exported images and occur only in the minimal audit list.
5. Visually compare every included article's text with the PDF page by page.
6. Visually compare meaningful formatting, paragraph order, headings, captions, poetry/lyrics lines, notes, and emphasis.
7. Parse `index.json` successfully.
8. Validate every UUID and confirm global uniqueness.
9. Confirm each UUID matches its index record, HTML filename, HTML `data-article-id`, and image filename prefixes.
10. Confirm every indexed HTML path exists, every HTML file is indexed exactly once, and no HTML file is orphaned.
11. Parse every HTML fragment and confirm it has exactly one outer matching `<article>` element.
12. Confirm every HTML `/images/...` URL maps to exactly one file under `src/images/` and appears in that article's ordered image metadata.
13. Confirm every image file is indexed, belongs to exactly one eligible article, opens correctly, and visually matches the PDF.
14. Check for missing, duplicated, and orphaned HTML/image files.
15. Confirm no source PDF, page render, OCR dump, prompt copy, temporary file, or unrelated change is staged.
16. Review the final diff and repository status.

Do not set a verification value to `verified_by_ai` until that specific visual comparison has actually been completed. Keep incomplete or uncertain verification explicit and report it.

## Git and pull-request delivery

An extraction request that invokes this file authorizes the normal repository delivery steps below unless the user explicitly asks for a read-only trial.

1. Refresh the latest remote default branch and check whether the intended issue is already present.
2. Create a new branch from that latest default branch using `agent/extract-<issue-date-or-name>`, unless the user explicitly identifies an existing branch or pull request to update.
3. Stage only the finished HTML files, image files, `index.json`, and a repository-contract clarification genuinely needed in `README.md` or `AGENTS.md`.
4. Do not edit `README.md` or this file merely to describe one newly ingested issue.
5. Use a terse commit message describing the issue extraction.
6. Run the verification gate on the exact committed tree.
7. Push the branch and open a draft pull request into the default branch.
8. Do not push directly to the default branch, reuse a deleted merged branch, create an empty pull request, or include unrelated changes.

The pull-request description must state:

- source publication and issue;
- included article count and titles;
- skipped count, titles, and detected restriction notices;
- exported image count;
- categories added or reused;
- repository/index changes; and
- validation performed and any remaining uncertainty.

## Completion report

Return a concise final report with:

- branch name and commit;
- draft pull-request link and target branch;
- included articles;
- skipped audit entries with the detected notices;
- image count;
- validation results; and
- unresolved text, metadata, image-credit, or rights uncertainty.

Never claim a push, pull request, exact transcription, completed verification, or clean rights gate unless it was actually completed and checked.
