"""Trusted publisher: validate bytes, add snapshots, and move environment pointers."""
import argparse
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from datetime import datetime, timezone


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement; serialized workflow + git fast-forward provide writer exclusion.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", value):
        raise ValueError("Invalid snapshot ID")
    return value


def safe_path(value):
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("Invalid file path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or not path.parts:
        raise ValueError("Unsafe file path")
    return value


def validate(directory, expected_id=None, expected_sha=None):
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Symlinks are not allowed")
    manifest = read(directory / "release.json")
    snapshot = valid_id(manifest["snapshot"])
    if expected_id and snapshot != expected_id:
        raise ValueError("Unexpected snapshot identity")
    if expected_sha and manifest["source_commit"] != expected_sha:
        raise ValueError("Unexpected source commit")
    if manifest["schema"] != 1 or not re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]):
        raise ValueError("Unsupported manifest or source commit")
    expected_url = "https://armcn.github.io/teal-depository-demo/snapshots/" + snapshot
    if manifest["repository_url"] != expected_url:
        raise ValueError("Unexpected repository URL")
    if manifest["source_repository"] != "armcn/teal-architecture-demo":
        raise ValueError("Unexpected source repository")
    files = manifest["files"]
    actual = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed")
        if path.is_file() and path != directory / "release.json":
            actual.add(str(path.relative_to(directory)))
    if actual != set(files):
        raise ValueError("Missing or unexpected snapshot files")
    required = {"app/app.R", "app/renv.lock", "app/release.json", "app/restore.R", "app/bootstrap.R",
                "smoke.R", "src/contrib/PACKAGES", "src/contrib/PACKAGES.gz", "src/contrib/PACKAGES.rds"}
    if not required <= actual:
        raise ValueError("Incomplete snapshot")
    for name, checksum in files.items():
        safe_path(name)
        if name not in required and not re.fullmatch(r"src/contrib/[A-Za-z][A-Za-z0-9.]*_[0-9.-]+\.tar\.gz", name):
            raise ValueError("Unexpected file type")
        if digest(directory / name) != checksum:
            raise ValueError(f"Checksum mismatch: {name}")
    lock = read(directory / "app/renv.lock")
    if read(directory / "app/release.json") != {k: v for k, v in manifest.items() if k != "files"}:
        raise ValueError("App release identity disagrees with snapshot manifest")
    repos = {r["Name"]: r["URL"] for r in lock["R"]["Repositories"]}
    if repos.get("TBDEMO") != expected_url or lock["R"]["Version"] != manifest["r_version"]:
        raise ValueError("Lockfile provenance does not match release")
    identities = set()
    for package in manifest["packages"]:
        key = (package["name"], package["version"])
        if key in identities:
            raise ValueError("Duplicate package identity")
        identities.add(key)
        expected_file = f"src/contrib/{key[0]}_{key[1]}.tar.gz"
        if package["file"] != expected_file or files.get(expected_file) != package["sha256"]:
            raise ValueError("Package inventory disagrees with file checksums")
        record = lock["Packages"].get(key[0], {})
        if record.get("Version") != key[1] or record.get("Repository") != "TBDEMO":
            raise ValueError("Package inventory disagrees with lockfile")
    if {p["file"] for p in manifest["packages"]} != {p for p in actual if p.endswith(".tar.gz")}:
        raise ValueError("Unexpected package archive")
    return manifest


def publish(candidate, site, expected_id, expected_sha):
    candidate, site = Path(candidate), Path(site)
    manifest = validate(candidate, expected_id, expected_sha)
    destination = site / "snapshots" / valid_id(expected_id)
    if destination.exists():
        validate(destination, expected_id, expected_sha)
        if digest(destination / "release.json") != digest(candidate / "release.json"):
            raise ValueError("Refusing to overwrite an immutable snapshot")
        return destination  # Idempotent retry of identical bytes.
    identities = {(p["name"], p["version"]): p for p in manifest["packages"]}
    for old in (site / "snapshots").glob("*/release.json"):
        for package in read(old)["packages"]:
            replacement = identities.get((package["name"], package["version"]))
            if replacement and replacement["sha256"] != package["sha256"]:
                raise ValueError("Published package versions cannot be replaced; increment Version")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="publish-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "snapshot"
        shutil.copytree(candidate, staging)
        validate(staging, expected_id, expected_sha)
        staging.rename(destination)
    render(site)
    return destination


def stage(site, snapshot, workflow_url):
    site = Path(site)
    directory = site / "snapshots" / valid_id(snapshot)
    manifest = validate(directory, snapshot)
    record = dict(snapshot=snapshot, manifest_sha256=digest(directory / "release.json"),
                  source_commit=manifest["source_commit"], verified_at=datetime.now(timezone.utc).isoformat(),
                  verification="cold-online-restore-and-app-smoke", workflow_url=workflow_url)
    # Called only after the workflow's online restore and smoke step succeeds.
    write(site / "evidence" / f"{snapshot}.json", record)
    write(site / "channels" / "dev.json", record)
    render(site)


def promote(site, snapshot, expected_current, workflow_url):
    site = Path(site)
    directory = site / "snapshots" / valid_id(snapshot)
    manifest = validate(directory, snapshot)
    evidence = read(site / "evidence" / f"{snapshot}.json")
    if evidence["snapshot"] != snapshot or evidence["source_commit"] != manifest["source_commit"]:
        raise ValueError("Staging evidence belongs to another release")
    if evidence["manifest_sha256"] != digest(directory / "release.json"):
        raise ValueError("Staging evidence does not match these bytes")
    if any(len(re.split(r"[.-]", p["version"])) > 3 for p in manifest["packages"]):
        raise ValueError("Development package versions cannot be promoted to production")
    target = site / "channels" / "prod.json"
    current_record = read(target) if target.exists() else {}
    current = current_record.get("snapshot", "none")
    if (current == snapshot and current_record.get("previous") == expected_current
            and current_record.get("promotion_workflow_url") == workflow_url
            and current_record.get("manifest_sha256") == evidence["manifest_sha256"]):
        # A failed upload/deployment may be retried after the Git commit succeeded.
        # Only this exact workflow operation is an idempotent retry.
        return
    if current != expected_current:
        raise ValueError(f"Production changed: expected {expected_current}, found {current}")
    record = dict(evidence, previous=current, promoted_at=datetime.now(timezone.utc).isoformat(),
                  promotion_workflow_url=workflow_url)
    write(target, record)
    history_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    write(site / "history" / f"{history_id}.json", record)
    render(site)


def render(site):
    site = Path(site)
    lines = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>Teal demo Depository</title>",
             "<h1>Teal demo Depository</h1><p>Immutable R package snapshots. Mock code only.</p>",
             "<p>Dev and production are simulated release selections, not hosted Connect applications.</p>"]
    for channel in ("dev", "prod"):
        path = site / "channels" / f"{channel}.json"
        value = read(path)["snapshot"] if path.exists() else "not selected"
        lines.append(f"<p><strong>{channel}:</strong> {html.escape(value)}</p>")
    lines.append("<ul>")
    for path in sorted((site / "snapshots").glob("*/release.json")):
        snapshot = valid_id(path.parent.name)
        lines.append(f"<li><a href='snapshots/{snapshot}/release.json'>{snapshot}</a> — "
                     f"<a href='snapshots/{snapshot}/src/contrib/PACKAGES'>packages</a></li>")
    lines.append("</ul></html>")
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text("\n".join(lines) + "\n")
    (site / ".nojekyll").touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("directory")
    add = sub.add_parser("publish")
    add.add_argument("candidate")
    add.add_argument("site")
    add.add_argument("snapshot")
    add.add_argument("sha")
    for name in ("stage", "promote"):
        command = sub.add_parser(name)
        command.add_argument("site")
        command.add_argument("snapshot")
        command.add_argument("--workflow-url", required=True)
        if name == "promote":
            command.add_argument("--expected-current", required=True)
    args = parser.parse_args()
    if args.command == "validate":
        validate(args.directory)
    elif args.command == "publish":
        publish(args.candidate, args.site, args.snapshot, args.sha)
    elif args.command == "stage":
        stage(args.site, args.snapshot, args.workflow_url)
    else:
        promote(args.site, args.snapshot, args.expected_current, args.workflow_url)
    print("PASS:", args.command)


if __name__ == "__main__":
    main()
