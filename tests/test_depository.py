import tempfile
import unittest
from pathlib import Path

from tools.publishing import files, operations, validation


def fixture(path, snapshot="one", content=b"package source", version="1.0.0"):
    path.mkdir(parents=True)
    required_files = [
        "app/app.R",
        "app/restore.R",
        "app/bootstrap.R",
        "smoke.R",
        "src/contrib/PACKAGES",
        "src/contrib/PACKAGES.gz",
        "src/contrib/PACKAGES.rds",
    ]
    for name in required_files:
        p = path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture")
    archive = f"src/contrib/tb.example_{version}.tar.gz"
    (path / archive).write_bytes(content)
    url = f"https://armcn.github.io/teal-depository-demo/snapshots/{snapshot}"
    files.write_json_atomically(
        path / "app/renv.lock",
        {
            "R": {"Version": "4.6.1", "Repositories": [{"Name": "TBDEMO", "URL": url}]},
            "Packages": {"tb.example": {"Version": version, "Repository": "TBDEMO"}},
        },
    )
    metadata = dict(
        schema=1,
        snapshot=snapshot,
        source_commit="a" * 40,
        source_repository="armcn/teal-architecture-demo",
        repository_url=url,
        r_version="4.6.1",
        packages=[
            dict(
                name="tb.example",
                version=version,
                file=archive,
                sha256=files.file_digest(path / archive),
                source_sha256="b" * 64,
            )
        ],
    )
    files.write_json_atomically(path / "app/release.json", metadata)
    metadata["files"] = {
        str(p.relative_to(path)): files.file_digest(p)
        for p in path.rglob("*")
        if p.is_file()
    }
    files.write_json_atomically(path / "release.json", metadata)
    return path


class DepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.candidate = fixture(self.root / "candidate")
        self.site = self.root / "site"

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self):
        return operations.publish_snapshot(self.candidate, self.site, "one", "a" * 40)

    def test_publish_and_identical_retry(self):
        first = self.publish()
        before = files.file_digest(first / "release.json")
        self.publish()
        self.assertEqual(before, files.file_digest(first / "release.json"))

    def test_corrupt_bytes_rejected_without_publishing(self):
        (self.candidate / "app/app.R").write_text("changed")
        with self.assertRaisesRegex(ValueError, "Checksum"):
            self.publish()
        self.assertFalse((self.site / "snapshots/one").exists())

    def test_unknown_file_rejected(self):
        (self.candidate / "extra.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.publish()

    def test_symlink_rejected(self):
        (self.candidate / "app/app.R").unlink()
        (self.candidate / "app/app.R").symlink_to(self.candidate / "smoke.R")
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            self.publish()

    def test_source_commit_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "source commit"):
            operations.publish_snapshot(self.candidate, self.site, "one", "c" * 40)

    def test_same_snapshot_different_bytes_rejected(self):
        self.publish()
        other = fixture(self.root / "other", content=b"new bytes")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            operations.publish_snapshot(other, self.site, "one", "a" * 40)

    def test_same_package_version_different_bytes_rejected(self):
        self.publish()
        other = fixture(self.root / "other", snapshot="two", content=b"new bytes")
        with self.assertRaisesRegex(ValueError, "versions cannot"):
            operations.publish_snapshot(other, self.site, "two", "a" * 40)

    def test_promotion_requires_staging_evidence(self):
        self.publish()
        with self.assertRaises(FileNotFoundError):
            operations.promote_snapshot(
                self.site, "one", "none", "https://example.org/run"
            )
        self.assertFalse((self.site / "channels/prod.json").exists())

    def test_promotion_preserves_bytes_and_records_history(self):
        path = self.publish()
        before = files.file_digest(path / "release.json")
        operations.stage_snapshot(self.site, "one", "https://example.org/staging")
        operations.promote_snapshot(
            self.site, "one", "none", "https://example.org/production"
        )
        self.assertEqual(before, files.file_digest(path / "release.json"))
        self.assertEqual(
            files.read_json(self.site / "channels/prod.json")["snapshot"], "one"
        )
        self.assertEqual(len(list((self.site / "history").glob("*.json"))), 1)

    def test_stale_promotion_rejected(self):
        self.publish()
        operations.stage_snapshot(self.site, "one", "https://example.org/staging")
        operations.promote_snapshot(
            self.site, "one", "none", "https://example.org/production"
        )
        with self.assertRaisesRegex(ValueError, "Production changed"):
            operations.promote_snapshot(
                self.site, "one", "none", "https://example.org/different-run"
            )

    def test_promotion_retry_after_commit_preserves_history(self):
        self.publish()
        operations.stage_snapshot(self.site, "one", "https://example.org/staging")
        operations.promote_snapshot(
            self.site, "one", "none", "https://example.org/production"
        )
        before = (self.site / "channels/prod.json").read_bytes()
        operations.promote_snapshot(
            self.site, "one", "none", "https://example.org/production"
        )
        self.assertEqual(before, (self.site / "channels/prod.json").read_bytes())
        self.assertEqual(len(list((self.site / "history").glob("*.json"))), 1)

    def test_development_version_cannot_reach_production(self):
        other = fixture(self.root / "other", snapshot="dev", version="1.0.0.9001")
        operations.publish_snapshot(other, self.site, "dev", "a" * 40)
        operations.stage_snapshot(self.site, "dev", "https://example.org/staging")
        with self.assertRaisesRegex(ValueError, "Development"):
            operations.promote_snapshot(
                self.site, "dev", "none", "https://example.org/production"
            )

    def test_paths_cannot_escape_snapshot(self):
        for value in ("../file", "/tmp/file", "a/../../file", "a\\file", "./file", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validation.validate_relative_path(value)

    def test_production_plan_does_not_modify_inputs(self):
        current = {"snapshot": "one"}
        evidence = {"snapshot": "two", "manifest_sha256": "verified"}
        record = operations.plan_production_selection(
            current, evidence, "one", "https://example.org/run", "now"
        )
        self.assertEqual(current, {"snapshot": "one"})
        self.assertNotIn("previous", evidence)
        self.assertEqual(record["previous"], "one")
        self.assertEqual(record["snapshot"], "two")


if __name__ == "__main__":
    unittest.main()
