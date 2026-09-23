# Downstream archive contract — format 2.0, index-driven maintenance

## Ownership

The source owns English article content, shared images, canonical catalogue metadata and PDF provenance. The translation repository owns translated articles, terminology, processing history, approval state, and computed change fingerprints. The website owns pages, navigation presentation, search, language routes and deployment.

**Editors commit content, not generated hashes.** Consumers select current `main` automatically and hold one consistent checkout for a run. The internally recorded Git revision is provenance, not a version an editor must coordinate across repositories.

## Authoritative inputs

| Path | Meaning |
| --- | --- |
| `index.json` | `format_version: "2.0"`, English collection, included `articles`, excluded `skipped` audit. |
| `catalogue.json` | Canonical issues, categories, topics, series, aliases and review candidates. |
| `content/articles/<uuid>.html` | Original English semantic fragment with a matching outer article ID. |
| `public/images/articles/<uuid>-<sequence>.<ext>` | Original shared article images. |

Root `manifest.json` and `navigation.json` are not authoritative inputs and are no longer committed. Missing or stale legacy copies do not block validation, export, or translation discovery. No editor or PDF-ingestion agent must run `derive` or update article hashes.

Each article retains its permanent UUID; each grouping entity has its own permanent UUID. `issue_id`, category IDs, topics and `series.id` resolve to the registry. Printed titles, subtitle, section, byline, and series part claims remain unchanged. Null/empty source titles remain empty; fallback interface wording belongs to the website. Historical `source_labels` are preserved, not independently maintained as navigation.

Issues retain source IDs, structured date precision, publication, publisher, original PDF filename/checksum, and rights records. The PDF checksum records provenance at ingestion; it is not a content synchronization lock. Registry aliases and unresolved grouping decisions retain their previous meaning. The source index remains the sole article inventory.

## Automatic downstream synchronization

The translation runtime reads `index.json` and the referenced HTML from English `main`, obtains issue labels from `catalogue.json`, and computes its own text/structure/translation-metadata fingerprints. The resulting state belongs to `berean-translation`, not this repository.

- An article UUID absent from a language's records is new work.
- An existing UUID with unchanged relevant content does not need translation again.
- Changed wording, meaningful markup, or translated metadata marks affected translations outdated.
- Shared image-byte replacements and canonical grouping-only changes do not, by themselves, require new language text.
- Removed or newly excluded articles must not be exported as current translations.
- Human translation edits and review status must survive a source scan; revised suggestions never silently overwrite them.

New/changed work is detected automatically. Manual selection authorizes paid translation under its existing budget and attempt limits. Detection does not silently start a new paid campaign. Approved unreviewed translations may publish immediately with the separate AI notice under the current owner policy. English edits do not wait for translation completion.

## Assets and build output

An image URL `/images/articles/<uuid>-1.jpg` maps to `public/images/articles/<uuid>-1.jpg`. Source URLs contain no host, language prefix, or GitHub project prefix. Exports rewrite image attributes and index URLs consistently for the selected base, without replacing strings in prose.

```bash
python3 tools/archive.py validate
python3 tools/archive.py export --output .build/root --base /
python3 tools/archive.py export --output .build/project --base /berean-voice/
```

`export` validates authoritative inputs, generates the navigation relationships and output checksums in memory, and writes a complete display bundle atomically. No saved core hashes are compared. Output must be absent or empty. Existing output is never silently deleted. Article words and image bytes are unchanged except for the documented image-URL prefix transformation in emitted HTML.

The display bundle preserves the previous paths and format: stripped `index.json`, stripped `catalogue.json`, generated `navigation.json`, generated export `manifest.json`, referenced HTML and images. The manifest identifies the source revision and output file checksums for that build. These are disposable build outputs, not source-maintenance files or a required input to translation. Consumers must not copy them back into the source repository.

The website may use `build_navigation` at build time or read the emitted navigation. It need not infer navigation per visitor. The existing UUID and asset layout remains suitable for a static GitHub Pages build; no site framework is installed here.

## CI, older branches and preserved history

Read-only CI validates source relationships, runs regressions, verifies deterministic build outputs and tests both export base paths. It never commits generated files back into `main`. Thus correcting a word does not require a second commit to repair a manifest.

When updating an extraction branch created under the older instructions, preserve its actual English/index/catalogue/image changes and drop changes to the removed generated root files. Genuine competing edits to the same source content may still need editorial conflict resolution; no mechanism should silently pick a winner. Generated navigation/hash conflicts are eliminated by keeping them out of source control.

Historical migration reports in `docs/` describe the completed layout migration. Their hashes are audit evidence, not live maintenance requirements. The old `verify-migration` utility remains a historical check; normal CI does not freeze article counts to that baseline.

```bash
# Optional developer utility; writes only ignored .build/derived/.
python3 tools/archive.py derive
```

Structural checks do not replace the PDF visual and image-decoder verification obligations in `AGENTS.md`.
