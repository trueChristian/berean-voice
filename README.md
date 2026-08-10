# Berean Voice article archive

This repository stores permission-eligible articles transcribed from *The Heartbeat of the Remnant* PDF issues for later import into Joomla or another CMS.

The transcription rule is strict: article wording, punctuation, capitalization, paragraph structure, emphasis, poetry lines, lists, notes, and captions are preserved. Only print-layout artifacts such as column breaks and discretionary line-end hyphenation are removed.

Articles that contain an article-specific permission requirement are not included. Notices such as “used by permission,” “do not reprint,” or any equivalent instruction to obtain permission cause the complete article and its images to be skipped.

## Repository layout

```text
index.json
src/
  <article-uuid>.html
  images/
    <article-uuid>-1.jpg
    <article-uuid>-2.jpg
    <article-uuid>-3.png
```

- `index.json` is the source of truth that connects every article to its HTML, images, author information, issue data, categories, source pages, credits, rights notes, and verification state.
- `src/<article-uuid>.html` is a semantic HTML fragment containing the article body. Titles, authors, dates, categories, and other import metadata live in `index.json`.
- `src/images/` contains a flat collection of article images. Every filename begins with the owning article UUID and ends with an incrementing image number.
- UUIDs are permanent. Do not rename or reuse an existing article UUID.

## Image paths

HTML uses root-relative paths such as:

```html
<img src="/images/58963510-f56e-43e0-88dd-0eb9941ddea9-1.jpg" alt="...">
```

The repository file for that URL is:

```text
src/images/58963510-f56e-43e0-88dd-0eb9941ddea9-1.jpg
```

Treat `src/` as the export root. For Joomla, copy the contents of `src/images/` to the site’s root `/images/` directory before importing the HTML fragments.

## Using the index

Each entry in `index.json` provides:

- the permanent article UUID;
- exact title, subtitle, section label, byline, author, and author location;
- publication, issue date, date precision, and printed page range;
- primary and additional categories;
- the HTML repository path;
- ordered image metadata, including repository path, public web path, source page, caption, alt text, credit, and rights-review note;
- article reuse status and verification results.

The top-level `skipped` list is an audit trail only. It identifies source articles that were rejected because an article-specific permission notice was detected. Skipped entries never have a UUID, HTML file, or exported image.

The original PDFs are not committed here. Their filenames and SHA-256 checksums are retained in `index.json` for provenance and verification.
