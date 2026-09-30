"""Render the small generated release index from retained metadata."""

import html
from pathlib import Path

from .files import file_digest, read_json
from .validation import validate_snapshot_id

WALKTHROUGH_URL = (
    "https://github.com/armcn/teal-architecture-demo/blob/main/docs/WALKTHROUGH.md"
)


def render_site(site):
    site = Path(site)
    sections = [page_introduction(), channel_summary(site), snapshot_list(site)]
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text("\n".join(sections) + "\n</html>\n")
    (site / ".nojekyll").touch()


def page_introduction():
    return "\n".join(
        [
            "<!doctype html><html lang='en'><meta charset='utf-8'>",
            "<title>Teal demo Depository</title>",
            "<h1>Teal demo Depository</h1>",
            "<p>Immutable R package snapshots. Mock code only.</p>",
            "<p>Dev and production are simulated release selections, "
            "not hosted Connect applications.</p>",
            "<p>For normal use, download the dev or prod selection. An unverified "
            "candidate may be incomplete or have failed testing.</p>",
            f"<p><a href='{WALKTHROUGH_URL}'>Developer walkthrough</a></p>",
        ]
    )


def channel_summary(site):
    lines = []
    for channel in ("dev", "prod"):
        path = site / "channels" / f"{channel}.json"
        snapshot = read_json(path)["snapshot"] if path.exists() else "not selected"
        lines.append(f"<p><strong>{channel}:</strong> {html.escape(snapshot)}</p>")
    return "\n".join(lines)


def snapshot_list(site):
    entries = []
    for manifest in sorted((site / "snapshots").glob("*/release.json")):
        snapshot = validate_snapshot_id(manifest.parent.name)
        state = verification_label(site, snapshot, manifest)
        entries.append(
            f"<li><a href='snapshots/{snapshot}/release.json'>{snapshot}</a> — "
            f"<a href='snapshots/{snapshot}/src/contrib/PACKAGES'>packages</a> "
            f"— {state}</li>"
        )
    return "\n".join(["<ul>", *entries, "</ul>"])


def verification_label(site, snapshot, manifest):
    evidence = site / "evidence" / f"{snapshot}.json"
    if evidence.exists():
        if read_json(evidence).get("manifest_sha256") == file_digest(manifest):
            return "verified candidate"
    return "unverified candidate"
