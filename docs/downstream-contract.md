# Downstream archive contract — format 2.0

## Repository boundaries

This repository owns original English articles, source provenance, shared article images, canonical grouping identities, ingestion instructions, and content validation/export tooling. The website repository owns Astro pages, templates, styling, search, language routing, and GitHub Pages deployment. The translation repository owns translated bodies, terminology and approval records.

No website or translation is deployed by this repository. Website builds must pin the English source to an exact commit and translations to an explicitly approved snapshot. Never import a moving branch midway through a build. New source hashes flag translation review; they do not authorize machine overwriting of approved translations.

## Authoritative files

| Path | Contract |
|---|---|
| `index.json` | `format_version: "2.0"`, fixed collection paths/language, included `articles`, excluded `skipped` audit. |
| `catalogue.json` | `format_version: "2.0"`, canonical `issues`, `categories`, `topics`, `series`; normalization audit and unresolved review candidates. |
| `content/articles/<uuid>.html` | Exact original English semantic fragment; one matching outer article element. |
| `public/images/articles/<uuid>-<sequence>.<ext>` | One unchanged canonical asset per indexed image. |

All article UUIDs survive the migration. Every grouping entity has its own globally unique UUID. Initial IDs are deterministic UUIDv5 values under the recorded namespace; subsequent IDs are assigned once and preserved, never recomputed after a rename. Registry `name` is a display label, `slug` is a stable route label, and `aliases`/`slug_aliases` prevent duplicate vocabulary and broken old route names. Consumers must implement any public route redirects explicitly; an alias is not a server redirect by itself.

Issue records move from `index.json.issues` to `catalogue.json.issues`. They retain the original `source_id`, exact date precision, publication/publisher, PDF filename and SHA-256, rights statements and all other provenance. `id` becomes the canonical UUID; `slug` initially equals the original human-readable source ID. Included and skipped article `issue_id` values reference that UUID.

Article `categories` is `{ "primary": "<category UUID>", "additional": ["<category UUID>"] }`. Article `topics` is an ordered unique array of topic UUIDs. `series`, when present, retains its source `part`/`total_parts` and replaces the free-text name with `id`. The historical category/topic/series metadata is retained under `source_labels`, explicitly as provenance rather than an independently editable navigation catalogue. The printed `title`, `subtitle`, `section`, byline and body are not normalized. Null or empty source titles remain unchanged; any “Untitled” navigation label belongs to the website interface, not the source article.

## Normalization and review

`Mission` is a reviewed-in-this-PR alias proposal for `Missions`; all original assignments remain in `source_labels`. Case-equivalent topic labels share one identity with aliases. The registry does not infer additional topics from article prose.

Potential `Church`/`Church Matters`, `Editorial`/`Sharpened words`, Courtship-series and Discipleship-series consolidations remain explicit review candidates. In particular, Courtship source records include different total-parts claims (5 and 6). Neither value is silently corrected and the potentially related series identities stay separate until an editorial decision is made.

## Asset and base-path contract

An archive image URL `/images/articles/<uuid>-1.jpg` maps exactly to `public/images/articles/<uuid>-1.jpg`. No hostname or GitHub project prefix belongs in source HTML. The export command applies a validated base path to image `src` values and image `public_path` metadata together. It never globally replaces strings in article prose.

The downstream layout deliberately aligns with Astro's static `public/` directory. Copy the exported `public/` subtree into the website's dedicated article-asset directory without deleting unrelated website assets. Read the exported index and its referenced fragments at build time; do not treat fragments as complete deployable pages. The website controls page routes and uses the same base setting for all generated links.

Current official integration references: [Astro GitHub Pages deployment](https://docs.astro.build/en/guides/deploy/github/), [Astro content collections](https://docs.astro.build/en/guides/content-collections/), and [GitHub custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Use a static/prerendered website build and artifact-based Pages deployment in the website repository; no `gh-pages` output branch or website generator dependency is required in this source repository.

## Deterministic generated files

Run `python3 tools/archive.py derive`, then commit both derived files with the authoritative changes:

- `navigation.json`: maps every issue/category/topic/series UUID to ordered article IDs, plus previous/next included articles within an issue or series. Skipped sequence gaps remain gaps. Missing series parts are not invented. The authoritative issue record order is retained; the file does not infer exact dates from seasons.
- `manifest.json`: canonical index/catalogue SHA-256, per-article raw HTML, normalized text, structure, metadata and translation-metadata fingerprints, and each image's byte count/SHA-256. Its aggregate content hash identifies source content without a self-referential commit hash or nondeterministic timestamp.

Text fingerprints ignore nonsemantic ASCII whitespace and inline tag boundaries; structure fingerprints separately detect emphasis, paragraph/line-break and attribute changes. Neither a matching text hash nor any other single hash means that a translation can be auto-approved. Captions, alt text, bylines and titles are covered by translation-metadata fingerprints; all source metadata remains covered by the full metadata hash.

A direct spelling correction in HTML changes the raw/text fingerprints even when `index.json` is untouched. An image-only replacement changes its asset fingerprint. Validation rejects stale navigation or manifests so such changes cannot be missed by a downstream build.

## Display-only export

From a clean committed checkout:

```bash
python3 tools/archive.py export --output .build/root --base /
python3 tools/archive.py export --output .build/project --base /berean-voice/
```

The project prefix above is a test/example, not an assumption about the future website repository name. Output must be absent or empty. Export validates first, builds in a temporary sibling directory and promotes the finished result; it never erases an existing nonempty destination.

The output contains `index.json`, `catalogue.json`, `navigation.json`, `manifest.json`, referenced HTML, and referenced `public/images/articles/` files. It excludes the skipped-article audit, per-article source verification claims, historical source-label snapshots, editorial normalization/review records, tools, instructions and unindexed files. Issue provenance and article/image credits and rights information remain available for lawful display attribution.

The export manifest records the exact source commit, aggregate source-content hash, deployment base, source article fingerprints and every emitted file's SHA-256 (except itself). Its versioned index is a display projection, not a replacement archive: do not run the archive validator on the stripped export or copy it back upstream.

## Validation and migration acceptance

```bash
python3 tools/archive.py validate
python3 -m unittest discover -s tests -v
python3 tools/archive.py verify-migration --base 301ffa03ad6101c610d545619cb430f6c9ac93ca
```

The last command is a one-time migration acceptance check against the pinned v1 baseline, not a permanent prohibition on adding new issues. Normal CI validates every subsequent archive revision without comparing its article count to that historical baseline.

It verifies unchanged article UUIDs, unchanged image Git blobs, exact article bytes after only the explicitly enumerated markup/alt/asset URL transformations, and lossless reversal of the metadata migration. `docs/migration-adjustments.json` records pre-existing alt inconsistencies and the three minimal malformed-markup repairs, including old/new values and hashes. One pre-existing misnamed image is renamed to match its actual owning article and ordered position. No source wording, published caption, index alt value, credit, PDF provenance, rights decision, or existing verification claim is changed. The migration does not claim a fresh visual comparison against the PDFs.

Structural checks are not a substitute for the mandatory visual source and image decoder checks in `AGENTS.md`. Future ingestion must continue to meet those stricter editorial gates and regenerate all derived files.
