#!/usr/bin/env python3
"""Validate, fingerprint and export the English archive (Python 3.11+, stdlib only).

This is not a PDF extractor, translator, HTML renderer or website deployer.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit
import uuid
import unicodedata

VERSION = "2.0"
ARTICLE_ROOT = "content/articles"
IMAGE_ROOT = "public/images/articles"
PUBLIC_IMAGE_ROOT = "/images/articles"
COLLECTION = {
    "name": "Berean Voice article archive",
    "language": "en",
    "content_root": ARTICLE_ROOT,
    "image_root": IMAGE_ROOT,
    "public_image_root": PUBLIC_IMAGE_ROOT,
    "index_is_source_of_truth": True,
    "catalogue_path": "catalogue.json",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div", "section", "article", "figure", "figcaption", "br", "td", "th", "tr", "dt", "dd"}
FORBIDDEN = {"script", "iframe", "object", "embed", "style", "link", "base", "form", "input", "button", "html", "head", "body"}
ALT_RE = re.compile(r'''(?<![\w:-])alt\s*=\s*(["\'])(.*?)\1''', re.I | re.S)
SRC_RE = re.compile(r'''(?<![\w:-])src\s*=\s*(["'])(.*?)\1''', re.I | re.S)


class ContractError(ValueError):
    """An archive invariant is violated; no output should be published."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def object_digest(value: Any) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    def invalid(value: str) -> Any:
        raise ContractError(f"Non-finite JSON number in {path}: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object, parse_constant=invalid)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def label_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("’", "'").casefold().strip()


def valid_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value and uuid.UUID(value).variant == uuid.RFC_4122
    except ValueError:
        return False


def safe_file(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and relative != "", "Missing repository path")
    require(not relative.startswith("/") and "\\" not in relative, f"Unsafe path: {relative}")
    require(all(part not in ("", ".", "..") for part in relative.split("/")), f"Unsafe path: {relative}")
    path = root
    for part in relative.split("/"):
        path = path / part
        require(not path.is_symlink(), f"Symlink is not allowed: {relative}")
    require(path.is_file(), f"Missing file: {relative}")
    return path


class Fragment(HTMLParser):
    """Parse for validation without ever serializing or changing source HTML."""
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.source = text
        self.offsets = [0]
        for line in text.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.stack: list[str] = []
        self.article_ids: list[str | None] = []
        self.images: list[dict[str, Any]] = []
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.text_parts: list[str] = []
        self.structure: list[Any] = []
        self.feed(text)
        self.close()
        require(not self.stack, f"Unclosed HTML elements: {self.stack}")
        require(len(self.article_ids) == 1, "HTML must have exactly one outer article")
        for link in self.links:
            if link.startswith("#") and len(link) > 1:
                require(link[1:] in self.anchors, f"Missing internal anchor: {link}")

    def handle_decl(self, decl: str) -> None:
        raise ContractError("HTML fragments must not contain a document declaration")

    def handle_pi(self, data: str) -> None:
        raise ContractError("HTML processing instructions are not allowed")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        require(tag not in FORBIDDEN, f"Unsafe or document-level HTML element: {tag}")
        require(len({k for k, _ in attrs}) == len(attrs), f"Duplicate HTML attribute on {tag}")
        attributes = dict(attrs)
        require(not any(k.startswith("on") or k in {"style", "srcdoc", "srcset"} for k in attributes), f"Unsupported active/style/responsive attribute on {tag}")
        if not self.stack:
            require(tag == "article" and not self.article_ids, "Content outside the single outer article")
        if tag == "article":
            require(not self.stack, "Nested article element")
            self.article_ids.append(attributes.get("data-article-id"))
        if "id" in attributes:
            anchor = attributes["id"]
            require(isinstance(anchor, str) and anchor not in self.anchors, "Duplicate/empty HTML anchor")
            self.anchors.add(anchor)
        if "href" in attributes:
            link = attributes["href"] or ""
            scheme = urlsplit(link).scheme.lower()
            require(scheme in {"http", "https", "mailto", "tel"} or link.startswith("#"), f"Unsupported link: {link}")
            self.links.append(link)
        if "src" in attributes:
            require(tag == "img", "Only img may load a local source asset")
        if tag == "img":
            require(isinstance(attributes.get("src"), str), "Image has no src")
            require("alt" in attributes and attributes["alt"] is not None, "Image has no alt attribute")
            raw = self.get_starttag_text()
            matches = list(SRC_RE.finditer(raw))
            require(len(matches) == 1, "Image src must be quoted exactly once")
            match = matches[0]
            line, col = self.getpos()
            start = self.offsets[line - 1] + col + match.start(2)
            alt_matches = list(ALT_RE.finditer(raw))
            require(len(alt_matches) == 1, "Image alt must be quoted exactly once")
            alt_match = alt_matches[0]
            alt_start = self.offsets[line - 1] + col + alt_match.start(2)
            self.images.append({"src": attributes["src"], "alt": attributes["alt"], "start": start, "end": start + len(match.group(2)), "alt_start": alt_start, "alt_end": alt_start + len(alt_match.group(2))})
        structural = dict(attributes)
        if tag == "img":
            structural["src"] = str(structural["src"]).rsplit("/", 1)[-1]
        self.structure.append(["start", tag, sorted(structural.items())])
        if tag in BLOCK:
            self.text_parts.append("\n")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        require(tag not in VOID, f"Void element has an end tag: {tag}")
        require(bool(self.stack) and self.stack[-1] == tag, f"Mismatched closing HTML tag: {tag}, stack={self.stack}")
        self.stack.pop()
        self.structure.append(["end", tag])
        if tag in BLOCK:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        require(bool(self.stack) or not data.strip(), "Text outside the outer article")
        self.text_parts.append(data)

    def text_fingerprint(self) -> str:
        return digest(re.sub(r"[ \t\r\n\f]+", " ", "".join(self.text_parts)).strip().encode())


def rewrite_images(text: str, replacements: dict[str, str]) -> str:
    parsed = Fragment(text)
    require(len(parsed.images) == len(replacements), "Image replacement map does not match HTML")
    require({image["src"] for image in parsed.images} == set(replacements), "Unexpected or repeated image URL")
    for image in reversed(parsed.images):
        replacement = html.escape(replacements[image["src"]], quote=True)
        text = text[:image["start"]] + replacement + text[image["end"]:]
    return text


def base_path(value: str) -> str:
    require(value.startswith("/") and not value.startswith("//"), "Base path must begin with one slash")
    if value == "/":
        return value
    segments = value.strip("/").split("/")
    require(all(part not in ("", ".", "..") and re.fullmatch(r"[A-Za-z0-9._-]+", part) for part in segments), "Base path contains unsafe URL segments")
    return "/" + "/".join(segments) + "/"


def asset_url(path: str, base: str) -> str:
    require(path.startswith(PUBLIC_IMAGE_ROOT + "/"), f"Noncanonical public image path: {path}")
    return base_path(base) + path.lstrip("/")


def category_ids(article: dict[str, Any]) -> list[str]:
    return [article["categories"]["primary"], *article["categories"]["additional"]]


def validate(root: Path, derived: bool = True) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    index = load(safe_file(root, "index.json"))
    catalogue = load(safe_file(root, "catalogue.json"))
    require(index.get("format_version") == VERSION, "Unsupported index format; expected 2.0")
    require(catalogue.get("format_version") == VERSION, "Unsupported catalogue format; expected 2.0")
    require(index.get("collection") == COLLECTION, "Collection paths/language/registry do not match the contract")
    require("issues" not in index, "Issue records belong in catalogue.json, not two editable catalogues")
    require(isinstance(index.get("articles"), list) and isinstance(index.get("skipped"), list), "Articles and skipped must be arrays")
    all_ids: set[str] = set()
    groups: dict[str, dict[str, Any]] = {}
    for kind in ("issues", "categories", "topics", "series"):
        records = catalogue.get(kind)
        require(isinstance(records, list), f"Missing registry array: {kind}")
        groups[kind] = {}
        slugs: set[str] = set()
        names: dict[str, str] = {}
        route_owners: dict[str, str] = {}
        for record in records:
            identity = record.get("id")
            require(valid_uuid(identity) and identity not in all_ids, f"Duplicate/invalid global UUID: {identity}")
            all_ids.add(identity)
            slug = record.get("slug")
            require(isinstance(slug, str) and bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)) and slug not in slugs, f"Invalid/duplicate {kind} slug: {slug}")
            slugs.add(slug)
            for route in [slug, *record.get("slug_aliases", [])]:
                require(isinstance(route, str) and bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", route)), "Invalid route alias")
                require(route not in route_owners or route_owners[route] == identity, f"Ambiguous {kind} route alias: {route}")
                route_owners[route] = identity
            groups[kind][identity] = record
            if kind == "issues":
                require(isinstance(record.get("source_id"), str) and bool(record["source_id"]), "Issue has no preserved source ID")
                require(isinstance(record.get("date"), dict) and isinstance(record.get("source"), dict), "Issue provenance is missing")
                require(bool(re.fullmatch(r"[0-9a-f]{64}", record["source"].get("sha256", ""))), "Issue PDF SHA-256 is invalid")
            else:
                require(isinstance(record.get("name"), str) and bool(record["name"].strip()), "Empty registry name")
                require(isinstance(record.get("aliases"), list) and all(isinstance(v, str) and v for v in record["aliases"]), "Registry aliases must be strings")
                require(len(set(record["aliases"])) == len(record["aliases"]), "Duplicate registry aliases")
                for name in [record["name"], *record["aliases"]]:
                    key = label_key(name)
                    require(bool(key) and (key not in names or names[key] == identity), f"Ambiguous {kind} name/alias: {name}")
                    names[key] = identity
        if kind == "issues":
            require(len({r["source_id"] for r in records}) == len(records), "Duplicate source issue ID")
    expected_html: set[str] = set()
    expected_images: set[str] = set()
    sequences: set[tuple[str, int]] = set()
    fingerprints: dict[str, Any] = {}
    for article in index["articles"]:
        identity = article.get("id")
        require(valid_uuid(identity) and identity not in all_ids, f"Duplicate/invalid article UUID: {identity}")
        all_ids.add(identity)
        require(article.get("language") == "en", f"Non-English article in English archive: {identity}")
        require(article.get("issue_id") in groups["issues"], f"Unknown issue: {identity}")
        sequence = article.get("sequence")
        require(type(sequence) is int and sequence > 0, f"Invalid article sequence: {identity}")
        pair = (article["issue_id"], sequence)
        require(pair not in sequences, f"Duplicate included/skipped issue sequence: {pair}")
        sequences.add(pair)
        require("title" in article and (article["title"] is None or isinstance(article["title"], str)), f"Invalid source title: {identity}")
        rights = article.get("rights", {})
        require(rights.get("status") == "eligible" and rights.get("article_specific_permission_notice_detected") is False, f"Ineligible article: {identity}")
        categories = article.get("categories", {})
        require(isinstance(categories, dict) and isinstance(categories.get("additional"), list), f"Invalid categories: {identity}")
        ids = category_ids(article)
        require(len(ids) == len(set(ids)) and all(value in groups["categories"] for value in ids), f"Unknown/duplicate category: {identity}")
        topics = article.get("topics", [])
        require(isinstance(topics, list) and len(topics) == len(set(topics)) and all(value in groups["topics"] for value in topics), f"Unknown/duplicate topic: {identity}")
        series = article.get("series")
        if series is not None:
            require(isinstance(series, dict) and series.get("id") in groups["series"], f"Unknown series: {identity}")
            require(series.get("part") is None or type(series.get("part")) is int and series["part"] > 0, "Invalid series part")
        path = article.get("html", {}).get("repository_path")
        require(path == f"{ARTICLE_ROOT}/{identity}.html", f"Noncanonical HTML path: {path}")
        raw = safe_file(root, path).read_bytes()
        parsed = Fragment(raw.decode("utf-8"))
        require(parsed.article_ids == [identity], f"Article element UUID mismatch: {identity}")
        expected_html.add(path)
        images = article.get("images")
        require(isinstance(images, list), f"Images must be an array: {identity}")
        require([im["src"] for im in parsed.images] == [im.get("public_path") for im in images], f"Image references/order differ from index: {identity}")
        image_hashes = []
        for position, image in enumerate(images, 1):
            repository_path = image.get("repository_path", "")
            require(image.get("sequence") == position, f"Image sequence must be consecutive: {identity}")
            suffix = Path(repository_path).suffix
            require(suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}, f"Unsupported image extension: {repository_path}")
            require(repository_path == f"{IMAGE_ROOT}/{identity}-{position}{suffix}", f"Noncanonical image path: {repository_path}")
            require(image.get("public_path") == f"{PUBLIC_IMAGE_ROOT}/{identity}-{position}{suffix}", "Public/repository image path mismatch")
            require(repository_path not in expected_images, f"Duplicate image ownership: {repository_path}")
            require(parsed.images[position - 1]["alt"] == image.get("alt"), f"HTML/index alt text mismatch: {repository_path}")
            data = safe_file(root, repository_path).read_bytes()
            require(bool(data), f"Empty image: {repository_path}")
            expected_images.add(repository_path)
            image_hashes.append({"repository_path": repository_path, "sha256": digest(data), "bytes": len(data)})
        translation_metadata = {key: article.get(key) for key in ("title", "subtitle", "section", "byline", "publication_note", "source_labels")}
        translation_metadata["images"] = [{key: image.get(key) for key in ("alt", "caption", "credit")} for image in images]
        fingerprints[identity] = {
            "html_sha256": digest(raw),
            "text_sha256": parsed.text_fingerprint(),
            "structure_sha256": object_digest(parsed.structure),
            "metadata_sha256": object_digest(article),
            "translation_metadata_sha256": object_digest(translation_metadata),
            "images": image_hashes,
        }
    for skipped in index["skipped"]:
        require(skipped.get("issue_id") in groups["issues"], "Skipped record references an unknown issue")
        sequence = skipped.get("sequence")
        require(type(sequence) is int and sequence > 0, "Invalid skipped sequence")
        pair = (skipped["issue_id"], sequence)
        require(pair not in sequences, f"Duplicate included/skipped issue sequence: {pair}")
        sequences.add(pair)
        require(skipped.get("html_exported") is False and skipped.get("images_exported") is False, "Skipped exports must be false")
        require(not any(key in skipped for key in ("id", "uuid", "html", "images", "repository_path", "public_path")), "Skipped record contains an export/UUID")
    def inventory(directory: str) -> set[str]:
        folder = root / directory
        if not folder.exists():
            return set()
        result = set()
        for path in folder.rglob("*"):
            require(not path.is_symlink(), f"Symlink in managed content: {path}")
            if path.is_file():
                result.add(path.relative_to(root).as_posix())
        return result
    require(inventory(ARTICLE_ROOT) == expected_html, "Missing/orphaned HTML or unexpected file in article root")
    require(inventory(IMAGE_ROOT) == expected_images, "Missing/orphaned image or unexpected file in image root")
    require(not (root / "src").exists(), "Legacy src/ content must not be recreated")
    manifest = {
        "format_version": VERSION,
        "language": "en",
        "index_sha256": digest(safe_file(root, "index.json").read_bytes()),
        "catalogue_sha256": digest(safe_file(root, "catalogue.json").read_bytes()),
        "counts": {"articles": len(expected_html), "images": len(expected_images), "issues": len(groups["issues"]), "skipped": len(index["skipped"])},
        "articles": dict(sorted(fingerprints.items())),
    }
    manifest["content_sha256"] = object_digest(manifest)
    navigation = build_navigation(index, catalogue, manifest["content_sha256"])
    if derived:
        require(safe_file(root, "manifest.json").read_bytes() == json_bytes(manifest), "manifest.json is stale; run tools/archive.py derive")
        require(safe_file(root, "navigation.json").read_bytes() == json_bytes(navigation), "navigation.json is stale; run tools/archive.py derive")
    return index, catalogue, manifest


def build_navigation(index: dict[str, Any], catalogue: dict[str, Any], source_hash: str) -> dict[str, Any]:
    result: dict[str, Any] = {"format_version": VERSION, "source_content_sha256": source_hash}
    articles = sorted(index["articles"], key=lambda a: (a["issue_id"], a["sequence"], a["id"]))
    for kind in ("issues", "categories", "topics", "series"):
        result[kind] = {record["id"]: [] for record in catalogue[kind]}
    result["articles"] = {}
    for article in articles:
        identity = article["id"]
        result["issues"][article["issue_id"]].append(identity)
        for category in category_ids(article):
            result["categories"][category].append(identity)
        for topic in article.get("topics", []):
            result["topics"][topic].append(identity)
        if article.get("series"):
            result["series"][article["series"]["id"]].append(identity)
        result["articles"][identity] = {"issue_id": article["issue_id"], "previous_in_issue": None, "next_in_issue": None, "previous_in_series": None, "next_in_series": None}
    lookup = {a["id"]: a for a in articles}
    for identity, members in result["series"].items():
        members.sort(key=lambda value: (lookup[value]["series"].get("part") or 10**9, lookup[value]["issue_id"], lookup[value]["sequence"], value))
    for group, suffix in (("issues", "issue"), ("series", "series")):
        for members in result[group].values():
            for position, identity in enumerate(members):
                result["articles"][identity][f"previous_in_{suffix}"] = members[position - 1] if position else None
                result["articles"][identity][f"next_in_{suffix}"] = members[position + 1] if position + 1 < len(members) else None
    # No fabricated exact dates: preserve the authoritative issue record order.
    result["issue_order"] = [issue["id"] for issue in catalogue["issues"]]
    return result


def derive(root: Path) -> dict[str, Any]:
    index, catalogue, manifest = validate(root, derived=False)
    write_json(root / "manifest.json", manifest)
    write_json(root / "navigation.json", build_navigation(index, catalogue, manifest["content_sha256"]))
    return manifest


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *arguments], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def export(root: Path, destination: Path, base: str, revision: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    destination = destination.absolute()
    require(not destination.is_symlink(), "Export destination cannot be a symlink")
    # Only an external directory or the explicitly disposable .build/ area is allowed.
    resolved = destination.resolve()
    require(resolved != root and root not in resolved.parents or root / ".build" in resolved.parents, "Export inside the archive is allowed only below .build/")
    require(resolved not in root.parents, "Cannot export over an ancestor of the archive")
    if destination.exists():
        require(destination.is_dir() and not any(destination.iterdir()), "Export destination must be absent or empty; existing data is never deleted")
    base = base_path(base)
    index, catalogue, manifest = validate(root)
    if (root / ".git").exists():
        actual = git(root, "rev-parse", "HEAD").decode().strip()
        require(revision is None or revision == actual, "Explicit revision does not match the checkout")
        revision = actual
        managed = ["index.json", "catalogue.json", "manifest.json", "navigation.json", ARTICLE_ROOT, IMAGE_ROOT]
        require(not git(root, "status", "--porcelain", "--untracked-files=all", "--", *managed).strip(), "Archive content is dirty; commit it before exporting")
    require(isinstance(revision, str) and bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "Export requires the exact 40-character source commit SHA")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".archive-export-", dir=destination.parent))
    try:
        output_index = copy.deepcopy(index)
        output_index.pop("skipped")
        output_index["export"] = {"source_revision": revision, "base_path": base}
        for article in output_index["articles"]:
            path = article["html"]["repository_path"]
            source = safe_file(root, path).read_bytes().decode("utf-8")
            replacements = {image["public_path"]: asset_url(image["public_path"], base) for image in article["images"]}
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rewrite_images(source, replacements), encoding="utf-8")
            article.pop("verification", None)
            article.pop("source_labels", None)
            for image in article["images"]:
                target_image = stage / image["repository_path"]
                target_image.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_file(root, image["repository_path"]), target_image)
                image["public_path"] = replacements[image["public_path"]]
        output_catalogue = copy.deepcopy(catalogue)
        output_catalogue.pop("normalization", None)
        output_catalogue.pop("review_candidates", None)
        write_json(stage / "index.json", output_index)
        write_json(stage / "catalogue.json", output_catalogue)
        shutil.copyfile(root / "navigation.json", stage / "navigation.json")
        output_manifest = {
            "format_version": VERSION,
            "source_repository": "https://github.com/trueChristian/berean-voice",
            "source_revision": revision,
            "source_content_sha256": manifest["content_sha256"],
            "base_path": base,
            "counts": {key: value for key, value in manifest["counts"].items() if key != "skipped"},
            "source_article_fingerprints": manifest["articles"],
            "files": {path.relative_to(stage).as_posix(): digest(path.read_bytes()) for path in sorted(stage.rglob("*")) if path.is_file()},
        }
        write_json(stage / "manifest.json", output_manifest)
        # Verify every emitted image reference under the chosen deployment base.
        for article in output_index["articles"]:
            parsed = Fragment((stage / article["html"]["repository_path"]).read_text())
            for image in parsed.images:
                require(image["src"].startswith(base + "images/articles/"), "Export base path mismatch")
                require((stage / "public" / image["src"][len(base):]).is_file(), "Export image URL does not resolve")
        if destination.exists():
            destination.rmdir()
        os.replace(stage, destination)
        return output_manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def verify_migration(root: Path, base: str) -> dict[str, Any]:
    require(bool(re.fullmatch(r"[0-9a-f]{40}", base)), "Migration baseline must be an exact commit SHA")
    original = json.loads(git(root, "show", f"{base}:index.json"))
    require(original.get("format_version") == "1.0", "Migration baseline must be format 1.0")
    index, catalogue, manifest = validate(root)
    restored = copy.deepcopy(index)
    restored["format_version"] = original["format_version"]
    restored["collection"] = copy.deepcopy(original["collection"])
    source_issues = {}
    restored["issues"] = []
    for issue in catalogue["issues"]:
        old = copy.deepcopy(issue)
        source_issues[old["id"]] = old["source_id"]
        old["id"] = old.pop("source_id")
        old.pop("slug")
        restored["issues"].append(old)
    source_images: dict[str, str] = {}
    for line in git(root, "ls-tree", "-r", base, "--", "src/images").decode().splitlines():
        metadata, path = line.split("\t", 1)
        source_images[path] = metadata.split()[2]
    old_articles = {article["id"]: article for article in original["articles"]}
    for article in restored["articles"]:
        identity = article["id"]
        require(identity in old_articles, f"New/unexpected article during structural migration: {identity}")
        before = old_articles[identity]
        old_html = git(root, "show", f"{base}:{before['html']['repository_path']}").decode()
        new_html = safe_file(root, article["html"]["repository_path"]).read_bytes().decode("utf-8")
        from source_repairs import repair_source_html
        repaired_html, _ = repair_source_html(old_html, before)
        mapping = {old["public_path"]: new["public_path"] for old, new in zip(before["images"], article["images"], strict=True)}
        require(new_html == rewrite_images(repaired_html, mapping), f"Article changed outside the documented HTML repairs and image src values: {identity}")
        article.pop("language")
        labels = article.pop("source_labels")
        for key in ("categories", "topics", "series"):
            if key in labels:
                article[key] = labels[key]
            else:
                article.pop(key, None)
        article["issue_id"] = source_issues[article["issue_id"]]
        article["html"]["repository_path"] = before["html"]["repository_path"]
        for image, old in zip(article["images"], before["images"], strict=True):
            data = safe_file(root, image["repository_path"]).read_bytes()
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            require(source_images[old["repository_path"]] == blob, f"Image bytes changed: {old['repository_path']}")
            image["repository_path"] = old["repository_path"]
            image["public_path"] = old["public_path"]
    for skipped in restored["skipped"]:
        skipped["issue_id"] = source_issues[skipped["issue_id"]]
    require(restored == original, "Source metadata changed outside the documented reversible structural migration")
    return {"baseline_revision": base, "counts": manifest["counts"], "source_article_text_unchanged": True, "only_documented_markup_alt_and_img_src_changes": True, "image_git_blobs_unchanged": True, "source_metadata_reversible_without_loss": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("derive")
    command = sub.add_parser("export")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--base", default="/")
    command.add_argument("--revision")
    command = sub.add_parser("verify-migration")
    command.add_argument("--base", required=True)
    try:
        args = parser.parse_args()
        if args.command == "derive":
            result = derive(args.root)["counts"]
        elif args.command == "export":
            result = export(args.root, args.output, args.base, args.revision)["counts"]
        elif args.command == "verify-migration":
            result = verify_migration(args.root, args.base)
        else:
            result = validate(args.root)[2]["counts"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Archive contract failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
