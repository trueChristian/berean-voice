# Berean Voice article archive

The authoritative English archive of permission-eligible articles transcribed from *The Heartbeat of the Remnant*. Original wording, punctuation, paragraphs, emphasis, captions, credits, and rights decisions remain faithful to the printed source. Articles with their own permission restriction are excluded in full, including their images.

The website and translation projects are separate repositories. This repository contains the originals, shared images, and their catalogue—not translations, translation status, or website code.

## Everyday editing

**Edit the English article and commit it. No hash calculation or generated-file update is required.**

For metadata changes, update `index.json`. For issue, category, topic, or series changes, update `catalogue.json`. A new article needs its permanent UUID, index entry, HTML and associated images. A transcription correction retains the existing UUID. Source-fidelity and rights rules in [AGENTS.md](AGENTS.md) still apply.

CI checks the actual JSON, identifiers, HTML, and image relationships. It does not require a saved manifest to match the edit. Missing files, invalid references, unsafe HTML, duplicate IDs, and ineligible articles remain errors.

```text
index.json                         # authoritative articles and skipped audit
catalogue.json                     # canonical issues, categories, topics, series
content/articles/<uuid>.html       # original English semantic fragments
public/images/articles/<uuid>-1.jpg
AGENTS.md                          # complete source-ingestion rules
tools/archive.py                   # automatic validation and display export
tests/                             # contract regressions
docs/downstream-contract.md        # consumer contract
```

Article and grouping UUIDs are permanent. `source_labels` retains historical grouping metadata; canonical IDs drive navigation. Alias decisions and ambiguous grouping review candidates remain in `catalogue.json`.

## Translation synchronization

`berean-translation` reads current `main` and discovers articles through `index.json`. Its own automation computes and stores article fingerprints. IDs missing from its language records are new work; relevant English changes mark existing translations outdated. No matching `manifest.json` or `navigation.json` is required here. English maintenance does not wait for translations.

The original PDF checksum in issue provenance identifies the source document. It is recorded automatically at ingestion and is not recalculated when someone corrects an HTML transcription.

## HTML and shared images

Articles remain UTF-8 `<article data-article-id="...">` fragments. An image URL `/images/articles/<uuid>-1.jpg` maps to `public/images/articles/<uuid>-1.jpg`. Do not embed the website hostname or deployment prefix in source content. The exporter applies the actual site base to HTML image URLs and their index metadata together.

## Validation and build-only export

Python 3.11+; no third-party dependencies are required here. Maintainers may run these checks locally, and GitHub Actions runs them automatically:

```bash
python3 tools/archive.py validate
python3 -m unittest discover -s tests -v
```

The website can export a clean checkout directly, without a preparatory regeneration step:

```bash
python3 tools/archive.py export --output .build/root --base /
python3 tools/archive.py export --output .build/project --base /berean-voice/
```

Output must be absent or empty; existing data is never erased. The exporter generates navigation and integrity metadata **inside the output bundle**, where they cannot cause source-PR conflicts. It records the selected source revision automatically. Build inputs include only the display index, canonical registry, navigation, export manifest, referenced article HTML, and shared images. Internal verification/audit records, tools, and agent instructions are excluded.

`python3 tools/archive.py derive` is an optional developer utility that writes only to ignored `.build/derived/`. It is not part of ingestion or everyday editing. Root `manifest.json` and `navigation.json` are no longer tracked or consumed. Do not restore them from older extraction branches. The website builds complete pages and deploys separately.

See [the downstream contract](docs/downstream-contract.md) and [AGENTS.md](AGENTS.md).
