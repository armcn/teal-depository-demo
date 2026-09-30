"""Production accepts only source commits reachable from main."""

import sys
from pathlib import Path

from github_actions import read_source_api, write_workflow_outputs
from publishing.files import read_json
from publishing.validation import validate_snapshot_id


def main():
    snapshot = validate_snapshot_id(sys.argv[1])
    manifest_path = Path("storage/site/snapshots") / snapshot / "release.json"
    source_sha = read_json(manifest_path)["source_commit"]
    require_source_on_main(source_sha)
    write_workflow_outputs({"sha": source_sha})
    print("PASS: release source belongs to main")


def require_source_on_main(source_sha):
    comparison = read_source_api(f"compare/{source_sha}...main")
    if comparison["status"] not in ("ahead", "identical"):
        raise ValueError(
            "Release source is not an ancestor of main; "
            "merge and publish the merged commit first"
        )


if __name__ == "__main__":
    main()
