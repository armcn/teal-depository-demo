"""Resolve a source ref once and require a successful source CI run."""

import os
import re
import urllib.parse

from github_actions import (
    read_source_api,
    write_workflow_outputs,
    write_workflow_summary,
)


def main():
    source_ref = validate_source_ref(os.environ["SOURCE_REF"])
    source_sha = resolve_source_commit(source_ref)
    passing_run = require_successful_source_ci(source_sha)
    snapshot = snapshot_id(
        os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"], source_sha
    )
    write_workflow_outputs({"sha": source_sha, "snapshot": snapshot})
    write_workflow_summary(
        f"## Selected source\n\nCommit: `{source_sha}`\n\n"
        f"Snapshot: `{snapshot}`\n\nSource CI: {passing_run['html_url']}\n"
    )


def validate_source_ref(source_ref):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,159}", source_ref):
        raise ValueError("Use a branch name, tag or full commit SHA")
    if ".." in source_ref:
        raise ValueError("Use a branch name, tag or full commit SHA")
    return source_ref


def resolve_source_commit(source_ref):
    encoded_ref = urllib.parse.quote(source_ref, safe="")
    commit = read_source_api("commits/" + encoded_ref)
    source_sha = commit["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("Invalid commit SHA returned by GitHub")
    return source_sha


def require_successful_source_ci(source_sha):
    result = read_source_api(
        f"actions/workflows/ci.yml/runs?head_sha={source_sha}"
        "&status=success&per_page=20"
    )
    passing = [
        run
        for run in result["workflow_runs"]
        if run["head_sha"] == source_sha
        and run["event"] in ("push", "workflow_dispatch")
    ]
    if not passing:
        raise ValueError(
            "This commit has no successful 'Check source' run. "
            "Wait for CI or run it first."
        )
    return passing[0]


def snapshot_id(run_id, attempt, source_sha):
    return f"run-{run_id}-{attempt}-{source_sha[:12]}"


if __name__ == "__main__":
    main()
