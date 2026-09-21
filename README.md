# Berean Voice article archive

This is the authoritative English archive of permission-eligible articles transcribed from *The Heartbeat of the Remnant* PDF issues. Original wording, punctuation, paragraph structure, emphasis, poetry, captions, credits and rights decisions remain faithful to the printed source. Articles with an article-specific permission requirement are excluded in full, including their images.

The website and translation projects are separate repositories. This repository supplies validated content; it does not contain or deploy the website, and it does not contain translated articles.

## Layout and ownership

```text
index.json                       # authoritative articles and skipped audit
catalogue.json                   # canonical issues, categories, topics, series
navigation.json                  # generated grouping lists and previous/next links
manifest.json                    # generated source fingerprints
content/articles/<uuid>.html     # original English semantic HTML fragments
public/images/articles/<uuid>-1.jpg
AGENTS.md                        # canonical PDF-ingestion instructions
tools/archive.py                 # validation, derivation and display export
tools/migrate_v2.py              # one-time v1 migration, not an ingestion tool
tests/                           # contract regression tests
docs/downstream-contract.md      # versioned consumer contract
```

Article UUIDs are unchanged. All grouping entities have permanent UUIDs too. Article `issue_id`, category IDs, topic IDs and `series.id` resolve to `catalogue.json`. Issue records retain the original human-readable `source_id` and full PDF provenance. Original PDFs are not committed.

`source_labels` preserves historical descriptive metadata; canonical registry labels drive navigation. `Mission` and `Missions` use one category identity. Uncertain category/series consolidations are listed in `catalogue.json.review_candidates` rather than applied silently. Case-only topic variants share one identity. Printed titles, section names and series part claims remain unchanged.

## HTML and image paths

HTML stays a clean UTF-8 `<article data-article-id="...">` fragment, without document wrappers or website layout. Files use permanent UUID names, never category folders or titles.

An image `src="/images/articles/<uuid>-1.jpg"` maps exactly to `public/images/articles/<uuid>-1.jpg`. The archive never embeds a hostname, `public/`, `src/`, or a GitHub project prefix into image URLs. The exporter applies the website's base path to both the HTML and its image metadata.

## Validation and export

Python 3.11 or later is required. No third-party Python packages are needed.

```bash
python3 tools/archive.py derive
python3 tools/archive.py validate
python3 -m unittest discover -s tests -v
```

Commit the source changes and the regenerated navigation/manifest together. CI rejects missing assets, orphaned content, invalid or duplicate IDs, unresolved group references, inconsistent image order/alt text, active HTML, and stale generated data. Structural validation does **not** replace visual verification against the PDF or the image decoder checks required by `AGENTS.md`.

From a clean, committed checkout, export inputs for a root-domain site:

```bash
python3 tools/archive.py export --output .build/root --base /
```

Or export for a GitHub Pages project site:

```bash
python3 tools/archive.py export --output .build/project --base /berean-voice/
```

The second base path is a test/example; the separate website supplies its actual repository base or `/` for its custom domain. Output directories must be absent or empty. Existing files are never silently erased.

The bundle contains only the display index, canonical registry, navigation, manifest, referenced HTML and referenced public images. It excludes skipped-article audit entries, source verification records, tools, agent instructions and unindexed files. It records the exact source commit and file SHA-256 values. These are build inputs, **not** a deployable website; the website repository adds pages, templates, search, styles, language routing and deployment.

See [the consumer contract](docs/downstream-contract.md) for details, and [AGENTS.md](AGENTS.md) for the complete ingestion and rights-verification workflow.
