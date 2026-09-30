"""The three state changes: publish immutable files, stage, and select production."""

import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .files import file_digest, read_json, write_json_atomically
from .site import render_site
from .validation import (
    validate_published_package_identities,
    validate_snapshot,
    validate_snapshot_id,
)


def publish_snapshot(candidate, site, expected_id, expected_sha):
    candidate, site = Path(candidate), Path(site)
    manifest = validate_snapshot(candidate, expected_id, expected_sha)
    destination = site / "snapshots" / validate_snapshot_id(expected_id)
    if destination.exists():
        require_identical_snapshot(candidate, destination, expected_id, expected_sha)
        return destination
    validate_published_package_identities(site, manifest)
    copy_snapshot_atomically(candidate, destination, expected_id, expected_sha)
    render_site(site)
    return destination


def stage_snapshot(site, snapshot, workflow_url):
    """Called by CI only after the public HTTPS restore and app test pass."""
    site = Path(site)
    directory = site / "snapshots" / validate_snapshot_id(snapshot)
    manifest = validate_snapshot(directory, snapshot)
    record = staging_record(
        manifest, file_digest(directory / "release.json"), workflow_url, utc_now()
    )
    write_json_atomically(site / "evidence" / f"{snapshot}.json", record)
    write_json_atomically(site / "channels/dev.json", record)
    render_site(site)


def promote_snapshot(site, snapshot, expected_current, workflow_url):
    site = Path(site)
    directory = site / "snapshots" / validate_snapshot_id(snapshot)
    manifest = validate_snapshot(directory, snapshot)
    evidence = read_json(site / "evidence" / f"{snapshot}.json")
    validate_promotion_evidence(
        manifest, evidence, file_digest(directory / "release.json")
    )
    target = site / "channels/prod.json"
    current = read_json(target) if target.exists() else {}
    record = plan_production_selection(
        current, evidence, expected_current, workflow_url, utc_now()
    )
    if record is None:
        return  # This workflow already committed the exact requested selection.
    write_json_atomically(target, record)
    write_json_atomically(site / "history" / history_filename(record), record)
    render_site(site)


def require_identical_snapshot(candidate, destination, snapshot, source_sha):
    validate_snapshot(destination, snapshot, source_sha)
    if file_digest(destination / "release.json") != file_digest(
        candidate / "release.json"
    ):
        raise ValueError("Refusing to overwrite an immutable snapshot")


def copy_snapshot_atomically(candidate, destination, snapshot, source_sha):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="publish-", dir=destination.parent) as work:
        staging = Path(work) / "snapshot"
        shutil.copytree(candidate, staging)
        validate_snapshot(staging, snapshot, source_sha)
        staging.rename(destination)


def staging_record(manifest, manifest_digest, workflow_url, verified_at):
    return {
        "snapshot": manifest["snapshot"],
        "manifest_sha256": manifest_digest,
        "source_commit": manifest["source_commit"],
        "verified_at": verified_at,
        "verification": "cold-online-restore-and-app-smoke",
        "workflow_url": workflow_url,
    }


def validate_promotion_evidence(manifest, evidence, manifest_digest):
    if (
        evidence["snapshot"] != manifest["snapshot"]
        or evidence["source_commit"] != manifest["source_commit"]
    ):
        raise ValueError("Staging evidence belongs to another release")
    if evidence["manifest_sha256"] != manifest_digest:
        raise ValueError("Staging evidence does not match these bytes")
    if any(
        len(re.split(r"[.-]", package["version"])) > 3
        for package in manifest["packages"]
    ):
        raise ValueError(
            "Development package versions cannot be promoted to production"
        )


def plan_production_selection(current, evidence, expected_current, workflow_url, now):
    """Pure compare-and-set decision: return a new record, a retry, or an error."""
    if is_same_promotion(current, evidence, expected_current, workflow_url):
        return None
    current_snapshot = current.get("snapshot", "none")
    if current_snapshot != expected_current:
        raise ValueError(
            f"Production changed: expected {expected_current}, found {current_snapshot}"
        )
    return {
        **evidence,
        "previous": current_snapshot,
        "promoted_at": now,
        "promotion_workflow_url": workflow_url,
    }


def is_same_promotion(current, evidence, expected_current, workflow_url):
    # A retry after a successful Git commit must not add another history entry.
    return (
        current.get("snapshot") == evidence["snapshot"]
        and current.get("previous") == expected_current
        and current.get("promotion_workflow_url") == workflow_url
        and current.get("manifest_sha256") == evidence["manifest_sha256"]
    )


def history_filename(record):
    content = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()[:16] + ".json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()
