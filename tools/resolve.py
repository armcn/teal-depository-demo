"""Resolve an approved public source ref and require successful source CI."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "armcn/teal-architecture-demo"


def api(path):
    request = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + "/" + path,
                                    headers={"Accept": "application/vnd.github+json", "User-Agent": "teal-architecture-demo"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    source_ref = os.environ["SOURCE_REF"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,159}", source_ref) or ".." in source_ref:
        raise ValueError("Use a branch name, tag or full commit SHA")
    commit = api("commits/" + urllib.parse.quote(source_ref, safe=""))
    sha = commit["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid commit SHA returned by GitHub")
    runs = api("actions/workflows/ci.yml/runs?head_sha=" + sha + "&status=success&per_page=20")
    passing = [r for r in runs["workflow_runs"] if r["head_sha"] == sha and r["event"] in ("push", "workflow_dispatch")]
    if not passing:
        raise ValueError("This commit has no successful 'Check source' run. Wait for CI or run it first.")
    snapshot = "run-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"] + "-" + sha[:12]
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"sha={sha}\nsnapshot={snapshot}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write(f"## Selected source\n\nCommit: `{sha}`\n\nSnapshot: `{snapshot}`\n\nSource CI: {passing[0]['html_url']}\n")


if __name__ == "__main__":
    main()
