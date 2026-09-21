#!/usr/bin/env python3
"""One-time, reversible v1 -> v2 structural migration; never a PDF extractor."""
from __future__ import annotations

import argparse
import collections
import copy
import json
from pathlib import Path
import re
import sys
import unicodedata
import uuid

from archive import ARTICLE_ROOT, COLLECTION, IMAGE_ROOT, PUBLIC_IMAGE_ROOT, VERSION
from archive import ContractError, derive, load, require, rewrite_images, safe_file, write_json

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/trueChristian/berean-voice")


def identity(kind: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}"))


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("’", "'").casefold().strip()


def slug(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    result = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    require(bool(result), f"A manually reviewed slug is needed for {value!r}")
    return result


def repairs(root: Path) -> None:
    from source_repairs import repair_source_html
    index = load(root / "index.json")
    require(index.get("format_version") == "1.0" and index["collection"]["content_root"] == "src", "Source repairs expect the original v1 layout")
    require(not (root / "docs/migration-adjustments.json").exists(), "Repair report already exists; do not rerun")
    reports = []
    changed = []
    for article in index["articles"]:
        path = safe_file(root, article["html"]["repository_path"])
        text, report = repair_source_html(path.read_bytes().decode("utf-8"), article)
        if report:
            reports.append(report)
            changed.append((path, text))
    for path, text in changed:
        path.write_bytes(text.encode("utf-8"))
    write_json(root / "docs/migration-adjustments.json", {"purpose": "Reviewable repairs of pre-existing HTML inconsistencies; no source wording, image bytes, index alt values or verification claims changed.", "articles": reports})


def layout(root: Path) -> None:
    index = load(root / "index.json")
    require(index.get("format_version") == "1.0" and index["collection"]["content_root"] == "src", "Layout migration expects the untouched v1 layout")
    require(not (root / "content").exists() and not (root / "public").exists(), "Migration destination already exists")
    old_files = {a["html"]["repository_path"] for a in index["articles"]}
    old_files |= {im["repository_path"] for a in index["articles"] for im in a["images"]}
    actual = {p.relative_to(root).as_posix() for p in (root / "src").rglob("*") if p.is_file()}
    require(old_files == actual, "Resolve unindexed/missing v1 files before migrating")
    prepared = []
    for article in index["articles"]:
        old_path = article["html"]["repository_path"]
        require(old_path == f"src/{article['id']}.html", f"Unexpected v1 HTML path: {old_path}")
        text = safe_file(root, old_path).read_bytes().decode("utf-8")
        replacements = {}
        for position, image in enumerate(article["images"], 1):
            path = image["repository_path"]
            require(path.startswith("src/images/") and path.count("/") == 2, f"Unexpected v1 image path: {path}")
            safe_file(root, path)
            replacements[image["public_path"]] = f"{PUBLIC_IMAGE_ROOT}/{article['id']}-{position}{Path(path).suffix}"
        prepared.append((article, old_path, rewrite_images(text, replacements)))
    # Every precondition has passed before moving any archive file.
    (root / ARTICLE_ROOT).mkdir(parents=True)
    (root / IMAGE_ROOT).mkdir(parents=True)
    for article, old_path, rewritten in prepared:
        new_path = f"{ARTICLE_ROOT}/{article['id']}.html"
        (root / new_path).write_bytes(rewritten.encode("utf-8"))
        (root / old_path).unlink()
        article["html"]["repository_path"] = new_path
        for position, image in enumerate(article["images"], 1):
            destination = f"{IMAGE_ROOT}/{article['id']}-{position}{Path(image['repository_path']).suffix}"
            (root / image["repository_path"]).rename(root / destination)
            image["repository_path"] = destination
            image["public_path"] = f"{PUBLIC_IMAGE_ROOT}/{Path(destination).name}"
    (root / "src/images").rmdir()
    (root / "src").rmdir()
    index["collection"].update(content_root=ARTICLE_ROOT, image_root=IMAGE_ROOT, public_image_root=PUBLIC_IMAGE_ROOT)
    write_json(root / "index.json", index)


def catalogue(root: Path) -> None:
    index = load(root / "index.json")
    require(index.get("format_version") == "1.0" and index["collection"]["content_root"] == ARTICLE_ROOT, "Catalogue migration requires the migrated v1 layout")
    require(not (root / "catalogue.json").exists(), "Catalogue already exists; never regenerate persistent IDs")
    result = {"format_version": VERSION, "id_namespace": str(NAMESPACE), "issues": [], "categories": [], "topics": [], "series": [], "normalization": [], "review_candidates": []}
    issue_ids = {}
    for source in index.pop("issues"):
        record = copy.deepcopy(source)
        old = record["id"]
        issue_ids[old] = identity("issue", old)
        record.update(id=issue_ids[old], source_id=old, slug=old)
        result["issues"].append(record)
    category_names: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    topic_names: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    series_names: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for article in index["articles"]:
        for category in [article["categories"]["primary"], *article["categories"]["additional"]]:
            key = "missions" if category["slug"] == "mission" else category["slug"]
            category_names[key][category["name"]] += 1
        for topic in article.get("topics") or []:
            topic_names[normalized(topic)][topic] += 1
        if article.get("series"):
            name = article["series"]["name"]
            series_names[normalized(name)][name] += 1
    maps = {}
    for kind, names in (("categories", category_names), ("topics", topic_names), ("series", series_names)):
        maps[kind] = {}
        used_slugs = set()
        for key, variants in sorted(names.items()):
            name = min(variants, key=lambda value: (-variants[value], value))
            if kind == "categories" and key == "missions":
                name = "Missions"
            entity_id = identity(kind, key)
            entity_slug = key if kind == "categories" else slug(name)
            if entity_slug in used_slugs:
                entity_slug += "-" + entity_id[:8]
            used_slugs.add(entity_slug)
            aliases = sorted(value for value in variants if value != name)
            record = {"id": entity_id, "name": name, "slug": entity_slug, "aliases": aliases}
            if kind == "categories" and key == "missions":
                record["slug_aliases"] = ["mission"]
            result[kind].append(record)
            maps[kind][key] = entity_id
            if aliases:
                result["normalization"].append({"kind": kind, "id": entity_id, "name": name, "aliases": aliases, "reason": "Singular/plural navigation consolidation proposed for review in this PR; original assignments retained." if kind == "categories" else "Case/typographic-equivalent labels share one identity; original labels retained."})
    for article in index["articles"]:
        article["source_labels"] = {key: copy.deepcopy(article[key]) for key in ("categories", "topics", "series") if key in article}
        article["language"] = "en"
        article["issue_id"] = issue_ids[article["issue_id"]]
        original_categories = article["categories"]
        def category_id(category):
            key = "missions" if category["slug"] == "mission" else category["slug"]
            return maps["categories"][key]
        primary = category_id(original_categories["primary"])
        additional = list(dict.fromkeys(category_id(c) for c in original_categories["additional"]))
        article["categories"] = {"primary": primary, "additional": [c for c in additional if c != primary]}
        article["topics"] = list(dict.fromkeys(maps["topics"][normalized(t)] for t in article.get("topics") or []))
        if article.get("series"):
            series = article["series"]
            series["id"] = maps["series"][normalized(series.pop("name"))]
    for skipped in index["skipped"]:
        skipped["issue_id"] = issue_ids[skipped["issue_id"]]
    candidates = [
        ("categories", ["church", "church-matters"], "Labels overlap but their intended editorial scope is not established; keep separate pending review."),
        ("categories", ["editorial", "sharpened-words"], "Both have editorial use; do not infer identical category scope from that alone."),
        ("series", ["a christ-centered courtship", "a christ-centered courtship series"], "Same named author and related titles, but printed total_parts values include 5 and 6. Preserve both totals and keep identities separate until reviewed."),
        ("series", ["discipleship", "discipleship series"], "Related titles and the same named author suggest a shared series; confirmation against the printed series labels is still needed."),
    ]
    for kind, keys, reason in candidates:
        if all(key in maps[kind] for key in keys):
            ids = [maps[kind][key] for key in keys]
            affected = [a["id"] for a in index["articles"] if any(value in ids for value in ([a["categories"]["primary"], *a["categories"]["additional"]] if kind == "categories" else [a.get("series", {}).get("id")]))]
            result["review_candidates"].append({"kind": kind, "ids": ids, "action": "keep_separate_pending_review", "reason": reason, "article_ids": affected})
    index["format_version"] = VERSION
    index["collection"] = copy.deepcopy(COLLECTION)
    write_json(root / "index.json", index)
    write_json(root / "catalogue.json", result)
    derive(root)


def replace_once(text: str, old: str, new: str) -> str:
    require(text.count(old) == 1, f"Instruction precondition failed: {old[:100]!r}")
    return text.replace(old, new, 1)


def instructions(root: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    require("The archive structure is flat and UUID-based:" in agents, "Instructions have already migrated or changed; review rather than overwrite")
    agents = agents.replace("This repository stores CMS-ready articles from PDF issues published by The Berean Voice.", "This repository stores the authoritative English article archive from PDF issues published by The Berean Voice. A separate website repository builds and deploys the site; a separate translation repository owns translations and approval. Do not add website pages, templates, styles, translated articles, or deployment workflows here.")
    agents = agents.replace("Update the root `index.json`, which is the single source of truth.", "Update the authoritative article catalogue `index.json` and canonical grouping registry `catalogue.json`, then regenerate `navigation.json` and `manifest.json`.")
    agents = agents.replace("Validation helpers may be used locally but are not part of the archive unless the user explicitly changes the repository contract.", "The versioned validation/export tools in `tools/`, their regression tests, and the read-only archive CI workflow are explicitly part of this repository contract. They may validate, fingerprint, reorganize existing files during an authorized migration, and export a display-only snapshot. They must never transcribe PDFs, decide source wording, translate articles, or replace visual verification.")
    agents = agents.replace("Read this file, `README.md`, and `index.json` completely.", "Read this file, `README.md`, `docs/downstream-contract.md`, `index.json`, and `catalogue.json` completely.")
    agents = agents.replace("Inspect the existing files under `src/` and `src/images/`.", "Inspect the existing files under `content/articles/` and `public/images/articles/`.")
    start = agents.index("The archive structure is flat and UUID-based:")
    end = agents.index("## UUID and filename rules", start)
    agents = agents[:start] + '''The English archive has a versioned, UUID-based downstream contract:

```text
AGENTS.md
README.md
index.json
catalogue.json
navigation.json
manifest.json
content/articles/<article-uuid>.html
public/images/articles/<article-uuid>-1.jpg
tools/
tests/
docs/downstream-contract.md
.github/workflows/archive-contract.yml
```

- `index.json` is the authoritative article catalogue and skipped-article audit trail.
- `catalogue.json` is the authoritative registry for issues, categories, topics and series. Issue provenance lives here, not in a second editable issue list.
- `navigation.json` and `manifest.json` are deterministic generated projections. Never hand-edit them. Run `python3 tools/archive.py derive` after changing content or metadata.
- Do not create per-article JSON files, category folders, translated article files, website templates, or deployment code.
- HTML belongs directly under `content/articles/`; image files belong directly under `public/images/articles/`.
- Do not put dates, titles, authors, or categories in filenames. Do not commit source PDFs or intermediate extraction artifacts.
- Keep `format_version` at `2.0`; do not redesign the schema or restructure the repository during ordinary ingestion.
- Website consumers read the index, registry, HTML and assets from the same immutable commit. Do not copy unindexed files into exports.

''' + agents[end:]
    agents = agents.replace("src/images/", "public/images/articles/")
    agents = agents.replace("src/<article-uuid>.html", "content/articles/<article-uuid>.html")
    start = agents.index("Treat `src/` as the eventual site export root.")
    end = agents.index("### Issue metadata", start)
    agents = agents[:start] + '''Treat `public/` as the static asset root. Canonical archive HTML uses:

```html
<img src="/images/articles/<article-uuid>-1.jpg" alt="...">
```

The matching repository file is `public/images/articles/<article-uuid>-1.jpg`.
Never put `public/`, `src/`, `../`, a hostname, a GitHub repository URL, or a deployment-specific project prefix in article image URLs.
The display exporter applies the website's `--base` prefix to image `src` values and image `public_path` metadata together. It does not change article wording or guess a hostname. This supports both `/` and a GitHub Pages project path without another source migration.

## Authoritative metadata and derived outputs

Preserve `format_version: "2.0"` and the documented fields. Append/update article and skipped records in `index.json`; register issue, category, topic and series identities in `catalogue.json`. Do not maintain duplicate editable registries.

All article references use canonical UUIDs: `issue_id`, `categories.primary`, each entry of `categories.additional`, each entry of `topics`, and `series.id` when present. Preserve `series.part` and `series.total_parts` exactly as recorded from the source. Omit `series` when not established; an article without topic metadata has `topics: []`.

Historical `source_labels` preserve the pre-migration category/topic/series metadata for provenance. They are not a second navigation catalogue and are not a claim that these labels were printed. Never overwrite those historical values merely to rename a navigation label. New articles may retain their actual original assignments here as well; all public grouping uses the canonical IDs.

Every included article has `language: "en"`. Translation statuses and translated bodies belong in the separate translation repository, keyed by the unchanged article UUID and the source fingerprints in `manifest.json`. A metadata or HTML change must not silently approve or overwrite translations.

### Issue metadata
''' + agents[end + len("### Issue metadata\n"):]
    agents = agents.replace("Create one issue record when the PDF is new. Derive its stable lowercase issue ID from the existing publication slug followed by the normalized date from most to least significant. Follow the established patterns:", "Create one issue record in `catalogue.json.issues` when the PDF is new. Assign a globally unique permanent UUID to `id`; reuse that UUID for corrected copies. Preserve a stable human-readable `source_id` and `slug` using the existing publication/date patterns:")
    agents = agents.replace("A corrected PDF of the same issue retains the same issue ID.", "A corrected PDF of the same issue retains the same UUID, source ID and slug.")
    agents = agents.replace("- stable issue ID;", "- permanent issue UUID, preserved human-readable `source_id`, and stable `slug`;")
    agents = agents.replace("- permanent UUID and issue ID;", "- permanent article UUID, `language: \"en\"`, and canonical issue UUID;")
    agents = agents.replace("- root-relative `public_path` under `/images/`;", "- root-relative `public_path` under `/images/articles/`;")
    start = agents.index("## Categories\n")
    end = agents.index("## Required verification gate", start)
    agents = agents[:start] + '''## Categories, topics and series

`catalogue.json` is the sole navigation vocabulary. Reuse its canonical entity IDs after checking names, aliases and any `slug_aliases`; never create a duplicate just because capitalization, punctuation or a singular/plural spelling differs. `Mission` is an alias of the canonical `Missions` category. Never alter article text or a printed section label to fit navigation.

Each category, topic and series record has a globally unique permanent UUID, a canonical display `name`, a stable URL `slug`, and an `aliases` array. UUIDs are assigned once; they must not be regenerated when labels or slugs change. Check uniqueness across every entity type and all article IDs. Create a new entity only when no existing entity reasonably fits. Add useful prior labels/slugs as aliases when making an explicitly reviewed normalization.

Use one `categories.primary` UUID and an ordered, nonduplicated `categories.additional` array. Topic/tag names are centralized in `catalogue.json.topics`; article `topics` is an ordered, nonduplicated UUID array. `series.id` is a canonical series UUID, not a free-text title. Preserve source part numbers and total-parts claims without trying to reconcile contradictory printed values.

Review candidates in `catalogue.json.review_candidates` are intentionally not automatically merged. They preserve uncertain distinctions until editorial approval. Do not infer a category hierarchy, author identity, common series, or theological equivalence from similar labels. The migration review documents known cases, including conflicting Courtship total-parts values.

The live website is not an independent category authority. Navigation changes begin in this registry and are consumed downstream. Website menu styling and which groups to feature remain website responsibilities.

''' + agents[end:]
    agents = agents.replace("7. Parse `index.json` successfully.", "7. Parse `index.json` and `catalogue.json` successfully and validate canonical references. Run `python3 tools/archive.py derive` followed by `python3 tools/archive.py validate` and `python3 -m unittest discover -s tests -v`. Generated navigation and fingerprints must match this exact content tree.")
    agents = agents.replace("Confirm every HTML `/images/...` URL", "Confirm every HTML `/images/articles/...` URL")
    agents = agents.replace("Stage only the finished HTML files, image files, `index.json`, and a repository-contract clarification genuinely needed in `README.md` or `AGENTS.md`.", "Stage only the finished HTML files, image files, `index.json`, changed canonical records in `catalogue.json`, regenerated `navigation.json` and `manifest.json`, and a repository-contract clarification genuinely needed in `README.md` or `AGENTS.md`. Do not edit tools or tests just to bypass a validation failure.")
    require("src/images/" not in agents and "under `src/`" not in agents, "Legacy ingestion instructions remain")
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    readme = '''# Berean Voice article archive

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
'''
    (root / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("repairs", "layout", "catalogue", "instructions"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        {"repairs": repairs, "layout": layout, "catalogue": catalogue, "instructions": instructions}[args.step](args.root)
        print(f"Completed structural migration step: {args.step}")
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Migration stopped without publication: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
