"""Contract regressions use synthetic articles, never PDF extraction or live APIs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive
import migrate_v2
from source_repairs import literal_text, repair_source_html

A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
REVISION = "1" * 40


def fixture(root: Path) -> dict:
    issue = {"id": "heartbeat-remnant-2024-summer", "publication": "The Heartbeat of the Remnant", "publisher": "The Berean Voice", "date": {"label": "Summer 2024", "year": 2024, "season": "Summer", "precision": "season"}, "issue_number": None, "source": {"filename": "synthetic.pdf", "sha256": "0" * 64, "pdf_page_count": 4, "printed_page_range": "1-4"}, "rights": {"publisher_permission_reported_by_project_owner": True}}
    articles = []
    for number, identity in enumerate((A, B), 1):
        image_path = f"src/images/{identity}-1.jpg"
        public_path = f"/images/{identity}-1.jpg"
        image = {"sequence": 1, "repository_path": image_path, "public_path": public_path, "alt": "Existing index description", "caption": None, "credit": "Example credit", "rights_note": "Synthetic fixture", "source_page": number, "role": "illustration"}
        article = {"id": identity, "issue_id": issue["id"], "sequence": number, "title": f"Synthetic article {number}", "subtitle": None, "section": None, "byline": {"raw": "Example Author", "authors": [{"name": "Example Author"}]}, "source_pages": {"start": number, "end": number}, "categories": {"primary": {"name": "Mission" if number == 1 else "Missions", "slug": "mission" if number == 1 else "missions"}, "additional": []}, "topics": ["Faith" if number == 1 else "faith"], "html": {"repository_path": f"src/{identity}.html"}, "images": [image], "rights": {"status": "eligible", "article_specific_permission_notice_detected": False}, "verification": {"text_against_pdf": "synthetic_not_verified"}}
        articles.append(article)
        path = root / image_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic binary asset for byte comparison\x00\xff")
        (root / article["html"]["repository_path"]).write_text(f'<article data-article-id="{identity}">\n<p>Faith &amp; hope. <em>Exact words.</em></p>\n<img src="{public_path}" alt="Older HTML description">\n</article>\n', encoding="utf-8")
    index = {"format_version": "1.0", "collection": {"name": "Berean Voice article archive", "content_root": "src", "image_root": "src/images", "public_image_root": "/images", "index_is_source_of_truth": True}, "issues": [issue], "articles": articles, "skipped": [{"issue_id": issue["id"], "sequence": 3, "title": "Excluded synthetic article", "reason": "Synthetic restriction", "detected_notices": ["Permission required"], "html_exported": False, "images_exported": False}]}
    archive.write_json(root / "index.json", index)
    return index


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "archive"
        self.root.mkdir()
        self.before = fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def migrate(self):
        migrate_v2.repairs(self.root)
        migrate_v2.layout(self.root)
        migrate_v2.catalogue(self.root)
        return archive.validate(self.root)

    def test_reversible_migration_retains_ids_text_and_image_bytes(self):
        before_text = [(self.root / a["html"]["repository_path"]).read_text() for a in self.before["articles"]]
        before_image = (self.root / self.before["articles"][0]["images"][0]["repository_path"]).read_bytes()
        index, catalogue, manifest = self.migrate()
        self.assertEqual([a["id"] for a in index["articles"]], [A, B])
        self.assertEqual(len(catalogue["categories"]), 1)
        self.assertEqual(catalogue["categories"][0]["aliases"], ["Mission"])
        self.assertEqual(len(catalogue["topics"]), 1)
        self.assertEqual(index["articles"][0]["source_labels"]["categories"], self.before["articles"][0]["categories"])
        for old, article in zip(before_text, index["articles"]):
            self.assertEqual(literal_text(old), literal_text((self.root / article["html"]["repository_path"]).read_text()))
        self.assertEqual(before_image, (self.root / index["articles"][0]["images"][0]["repository_path"]).read_bytes())
        self.assertEqual(manifest["counts"], {"articles": 2, "images": 2, "issues": 1, "skipped": 1})
        self.assertFalse((self.root / "src").exists())

    def test_derive_is_deterministic(self):
        self.migrate()
        before = [(self.root / name).read_bytes() for name in ("manifest.json", "navigation.json")]
        archive.derive(self.root)
        self.assertEqual(before, [(self.root / name).read_bytes() for name in ("manifest.json", "navigation.json")])

    def test_registry_ids_survive_label_change(self):
        self.migrate()
        catalogue = archive.load(self.root / "catalogue.json")
        identity = catalogue["categories"][0]["id"]
        catalogue["categories"][0]["aliases"].append("Missions")
        catalogue["categories"][0]["name"] = "Mission work"
        archive.write_json(self.root / "catalogue.json", catalogue)
        archive.derive(self.root)
        self.assertEqual(archive.validate(self.root)[1]["categories"][0]["id"], identity)

    def test_stale_manifest_rejected(self):
        self.migrate()
        path = self.root / f"{archive.ARTICLE_ROOT}/{A}.html"
        path.write_text(path.read_text().replace("Faith", "Hope"))
        with self.assertRaisesRegex(archive.ContractError, "stale"):
            archive.validate(self.root)

    def test_orphaned_and_missing_images_rejected(self):
        self.migrate()
        orphan = self.root / archive.IMAGE_ROOT / "orphan.jpg"
        orphan.write_bytes(b"orphan")
        with self.assertRaisesRegex(archive.ContractError, "orphaned"):
            archive.validate(self.root)
        orphan.unlink()
        (self.root / archive.IMAGE_ROOT / f"{A}-1.jpg").unlink()
        with self.assertRaisesRegex(archive.ContractError, "Missing file"):
            archive.validate(self.root)

    def test_unknown_category_and_duplicate_topic_rejected(self):
        index, _, _ = self.migrate()
        original = copy.deepcopy(index)
        index["articles"][0]["categories"]["primary"] = REVISION
        archive.write_json(self.root / "index.json", index)
        with self.assertRaises(archive.ContractError):
            archive.validate(self.root, derived=False)
        original["articles"][0]["topics"] *= 2
        archive.write_json(self.root / "index.json", original)
        with self.assertRaisesRegex(archive.ContractError, "topic"):
            archive.validate(self.root, derived=False)

    def test_global_id_collision_rejected(self):
        self.migrate()
        catalogue = archive.load(self.root / "catalogue.json")
        catalogue["topics"][0]["id"] = catalogue["categories"][0]["id"]
        archive.write_json(self.root / "catalogue.json", catalogue)
        with self.assertRaisesRegex(archive.ContractError, "global UUID"):
            archive.validate(self.root)

    def test_skipped_record_cannot_export_content(self):
        index, _, _ = self.migrate()
        index["skipped"][0]["id"] = A
        archive.write_json(self.root / "index.json", index)
        with self.assertRaisesRegex(archive.ContractError, "Skipped record"):
            archive.validate(self.root, derived=False)

    def test_included_skipped_sequence_collision_rejected(self):
        index, _, _ = self.migrate()
        index["skipped"][0]["sequence"] = 1
        archive.write_json(self.root / "index.json", index)
        with self.assertRaisesRegex(archive.ContractError, "sequence"):
            archive.validate(self.root, derived=False)

    def test_navigation_previous_next_and_shared_groups(self):
        self.migrate()
        navigation = archive.load(self.root / "navigation.json")
        self.assertEqual(navigation["articles"][A]["next_in_issue"], B)
        self.assertEqual(navigation["articles"][B]["previous_in_issue"], A)
        self.assertEqual(list(navigation["categories"].values()), [[A, B]])

    def test_export_root_and_project_resolve_all_assets(self):
        self.migrate()
        for base in ("/", "/website/", "/nested/site"):
            destination = Path(self.temp.name) / ("export-" + base.replace("/", "_"))
            result = archive.export(self.root, destination, base, REVISION)
            index = archive.load(destination / "index.json")
            self.assertNotIn("skipped", index)
            self.assertEqual(result["source_revision"], REVISION)
            for article in index["articles"]:
                self.assertNotIn("verification", article)
                self.assertNotIn("source_labels", article)
                fragment = archive.Fragment((destination / article["html"]["repository_path"]).read_text())
                url = fragment.images[0]["src"]
                self.assertTrue(url.startswith(archive.base_path(base) + "images/articles/"))
                self.assertTrue((destination / "public" / url[len(archive.base_path(base)):]).is_file())
            self.assertFalse((destination / "docs").exists())
            for path, checksum in result["files"].items():
                self.assertEqual(checksum, archive.digest((destination / path).read_bytes()))

    def test_export_never_erases_existing_files(self):
        self.migrate()
        destination = Path(self.temp.name) / "existing"
        destination.mkdir()
        (destination / "keep.txt").write_text("retain")
        with self.assertRaisesRegex(archive.ContractError, "never deleted"):
            archive.export(self.root, destination, "/", REVISION)
        self.assertEqual((destination / "keep.txt").read_text(), "retain")

    def test_export_is_blocked_before_output_on_validation_error(self):
        self.migrate()
        (self.root / "manifest.json").write_text("{}")
        destination = Path(self.temp.name) / "blocked"
        with self.assertRaises(archive.ContractError):
            archive.export(self.root, destination, "/", REVISION)
        self.assertFalse(destination.exists())

    def test_export_cannot_overwrite_source_or_an_ancestor(self):
        self.migrate()
        for destination in (self.root, self.root / "content/export", Path(self.temp.name)):
            with self.assertRaises(archive.ContractError):
                archive.export(self.root, destination, "/", REVISION)

    def test_rejected_base_paths(self):
        for value in ("https://example.org", "//example.org/", "/../", "/site/../", "/a//b", "/a?b", "/%2e%2e/", "/a\\b"):
            with self.subTest(value=value), self.assertRaises(archive.ContractError):
                archive.base_path(value)

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a": NaN}'):
            path = self.root / "bad.json"
            path.write_text(text)
            with self.assertRaises(archive.ContractError):
                archive.load(path)

    def test_path_traversal_and_symlink_rejected(self):
        for path in ("../index.json", "/index.json", "src//bad", "src/./bad"):
            with self.assertRaises(archive.ContractError):
                archive.safe_file(self.root, path)
        (self.root / "link.json").symlink_to(self.root / "index.json")
        with self.assertRaisesRegex(archive.ContractError, "Symlink"):
            archive.safe_file(self.root, "link.json")

    def test_active_or_malformed_html_rejected(self):
        bodies = ['<script>alert(1)</script>', '<p onclick="x()">Words</p>', '<img src="x" src="y" alt="">', '<p><em>Words</p>', '<iframe src="x"></iframe>', '<a href="javascript:alert(1)">Words</a>', '<img src="x" srcset="x 1x" alt="">']
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(archive.ContractError):
                archive.Fragment(f'<article data-article-id="{A}">{body}</article>')

    def test_url_rewriting_changes_only_src_values_not_text(self):
        old = f'<article data-article-id="{A}"><p>/images/example.jpg stays literal.</p><img src="/images/example.jpg" alt="Image"></article>'
        new = archive.rewrite_images(old, {"/images/example.jpg": "/images/articles/example.jpg"})
        self.assertIn('<p>/images/example.jpg stays literal.</p>', new)
        self.assertEqual(literal_text(old), literal_text(new))

    def test_text_vs_structure_fingerprints(self):
        first = archive.Fragment(f'<article data-article-id="{A}"><p>Faith and hope</p></article>')
        second = archive.Fragment(f'<article data-article-id="{A}"><p>Faith and <em>hope</em></p></article>')
        self.assertEqual(first.text_fingerprint(), second.text_fingerprint())
        self.assertNotEqual(archive.object_digest(first.structure), archive.object_digest(second.structure))

    def test_migration_cannot_regenerate_existing_registry(self):
        self.migrate()
        with self.assertRaises(archive.ContractError):
            migrate_v2.catalogue(self.root)

    def test_untitled_source_records_remain_untitled(self):
        index = archive.load(self.root / "index.json")
        index["articles"][0]["title"] = None
        index["articles"][1]["title"] = ""
        archive.write_json(self.root / "index.json", index)
        migrated, _, _ = self.migrate()
        self.assertIsNone(migrated["articles"][0]["title"])
        self.assertEqual(migrated["articles"][1]["title"], "")

    def test_wrong_image_filename_is_aligned_to_its_owner(self):
        index = archive.load(self.root / "index.json")
        image = index["articles"][0]["images"][0]
        old_path = image["repository_path"]
        old_url = image["public_path"]
        image["repository_path"] = "src/images/cccccccc-cccc-4ccc-8ccc-cccccccccccc-1.jpg"
        image["public_path"] = "/images/cccccccc-cccc-4ccc-8ccc-cccccccccccc-1.jpg"
        (self.root / old_path).rename(self.root / image["repository_path"])
        path = self.root / index["articles"][0]["html"]["repository_path"]
        path.write_text(path.read_text().replace(old_url, image["public_path"]))
        archive.write_json(self.root / "index.json", index)
        migrated, _, _ = self.migrate()
        self.assertEqual(migrated["articles"][0]["images"][0]["repository_path"], f"{archive.IMAGE_ROOT}/{A}-1.jpg")

    def test_ambiguous_registry_alias_is_rejected(self):
        self.migrate()
        catalogue = archive.load(self.root / "catalogue.json")
        catalogue["topics"].append({"id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc", "name": "Another topic", "slug": "another-topic", "aliases": ["FAITH"]})
        archive.write_json(self.root / "catalogue.json", catalogue)
        with self.assertRaisesRegex(archive.ContractError, "Ambiguous"):
            archive.validate(self.root, derived=False)

    def test_git_baseline_proves_reversibility_and_rejects_dirty_export(self):
        def git(*args):
            return subprocess.run(["git", "-C", str(self.root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
        git("init", "-q")
        git("config", "user.name", "Contract Test")
        git("config", "user.email", "contract-test@example.invalid")
        git("add", ".")
        git("commit", "-qm", "v1 fixture")
        baseline = git("rev-parse", "HEAD")
        self.migrate()
        git("add", ".")
        git("commit", "-qm", "v2 fixture")
        report = archive.verify_migration(self.root, baseline)
        self.assertTrue(report["source_metadata_reversible_without_loss"])
        self.assertTrue(report["image_git_blobs_unchanged"])
        archive.export(self.root, Path(self.temp.name) / "clean", "/")
        with self.assertRaisesRegex(archive.ContractError, "does not match"):
            archive.export(self.root, Path(self.temp.name) / "wrong-revision", "/", REVISION)
        path = self.root / f"{archive.ARTICLE_ROOT}/{A}.html"
        path.write_text(path.read_text().replace("Faith", "Hope"))
        archive.derive(self.root)
        with self.assertRaisesRegex(archive.ContractError, "dirty"):
            archive.export(self.root, Path(self.temp.name) / "dirty", "/")


if __name__ == "__main__":
    unittest.main()
