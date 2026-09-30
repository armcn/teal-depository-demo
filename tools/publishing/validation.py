"""Validate candidate data without executing any code contained in the snapshot."""

import re
from pathlib import Path, PurePosixPath

from .files import file_digest, read_json

REPOSITORY_URL = "https://armcn.github.io/teal-depository-demo"
SOURCE_REPOSITORY = "armcn/teal-architecture-demo"
REQUIRED_FILES = {
    "app/app.R",
    "app/renv.lock",
    "app/release.json",
    "app/restore.R",
    "app/bootstrap.R",
    "smoke.R",
    "src/contrib/PACKAGES",
    "src/contrib/PACKAGES.gz",
    "src/contrib/PACKAGES.rds",
}


def validate_snapshot(directory, expected_id=None, expected_sha=None):
    """Check identity, allowed files, checksums, lockfile, and package inventory."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Symlinks are not allowed")
    manifest = read_json(directory / "release.json")
    validate_release_identity(manifest, expected_id, expected_sha)
    actual_files = snapshot_file_names(directory)
    validate_file_inventory(actual_files, manifest["files"])
    validate_file_checksums(directory, manifest["files"])
    lock = read_json(directory / "app/renv.lock")
    validate_app_metadata(directory, manifest, lock)
    validate_package_inventory(manifest, lock, actual_files)
    return manifest


def validate_snapshot_id(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9-]{0,79}", value
    ):
        raise ValueError("Invalid snapshot ID")
    return value


def validate_relative_path(value):
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("Invalid file path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or not path.parts:
        raise ValueError("Unsafe file path")
    return value


def validate_release_identity(manifest, expected_id, expected_sha):
    snapshot = validate_snapshot_id(manifest["snapshot"])
    if expected_id and snapshot != expected_id:
        raise ValueError("Unexpected snapshot identity")
    if expected_sha and manifest["source_commit"] != expected_sha:
        raise ValueError("Unexpected source commit")
    if manifest["schema"] != 1 or not re.fullmatch(
        r"[0-9a-f]{40}", manifest["source_commit"]
    ):
        raise ValueError("Unsupported manifest or source commit")
    if manifest["repository_url"] != f"{REPOSITORY_URL}/snapshots/{snapshot}":
        raise ValueError("Unexpected repository URL")
    if manifest["source_repository"] != SOURCE_REPOSITORY:
        raise ValueError("Unexpected source repository")


def snapshot_file_names(directory):
    names = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed")
        if path.is_file() and path != directory / "release.json":
            names.add(str(path.relative_to(directory)))
    return names


def validate_file_inventory(actual_files, checksums):
    if actual_files != set(checksums):
        raise ValueError("Missing or unexpected snapshot files")
    if not REQUIRED_FILES <= actual_files:
        raise ValueError("Incomplete snapshot")
    for name in actual_files:
        validate_relative_path(name)
        is_archive = re.fullmatch(
            r"src/contrib/[A-Za-z][A-Za-z0-9.]*_[0-9.-]+\.tar\.gz", name
        )
        if name not in REQUIRED_FILES and not is_archive:
            raise ValueError("Unexpected file type")


def validate_file_checksums(directory, checksums):
    for name, expected in checksums.items():
        if file_digest(directory / name) != expected:
            raise ValueError(f"Checksum mismatch: {name}")


def validate_app_metadata(directory, manifest, lock):
    expected_metadata = {
        key: value for key, value in manifest.items() if key != "files"
    }
    if read_json(directory / "app/release.json") != expected_metadata:
        raise ValueError("App release identity disagrees with snapshot manifest")
    repositories = {item["Name"]: item["URL"] for item in lock["R"]["Repositories"]}
    if (
        repositories.get("TBDEMO") != manifest["repository_url"]
        or lock["R"]["Version"] != manifest["r_version"]
    ):
        raise ValueError("Lockfile provenance does not match release")


def validate_package_inventory(manifest, lock, actual_files):
    identities = set()
    for package in manifest["packages"]:
        identity = (package["name"], package["version"])
        if identity in identities:
            raise ValueError("Duplicate package identity")
        identities.add(identity)
        validate_package_record(package, manifest["files"], lock)
    listed_archives = {package["file"] for package in manifest["packages"]}
    actual_archives = {name for name in actual_files if name.endswith(".tar.gz")}
    if listed_archives != actual_archives:
        raise ValueError("Unexpected package archive")


def validate_package_record(package, checksums, lock):
    name, version = package["name"], package["version"]
    expected_file = f"src/contrib/{name}_{version}.tar.gz"
    if (
        package["file"] != expected_file
        or checksums.get(expected_file) != package["sha256"]
    ):
        raise ValueError("Package inventory disagrees with file checksums")
    record = lock["Packages"].get(name, {})
    if record.get("Version") != version or record.get("Repository") != "TBDEMO":
        raise ValueError("Package inventory disagrees with lockfile")


def validate_published_package_identities(site, manifest):
    replacements = {
        (package["name"], package["version"]): package
        for package in manifest["packages"]
    }
    for path in (site / "snapshots").glob("*/release.json"):
        for package in read_json(path)["packages"]:
            replacement = replacements.get((package["name"], package["version"]))
            if replacement and replacement["sha256"] != package["sha256"]:
                raise ValueError(
                    "Published package versions cannot be replaced; increment Version"
                )
