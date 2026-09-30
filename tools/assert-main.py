"""Production accepts only source commits reachable from main."""
import json
import os
import re
import sys
from pathlib import Path
from resolve import api

snapshot = sys.argv[1]
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", snapshot):
    raise ValueError("Invalid snapshot")
release = json.loads((Path("storage/site/snapshots") / snapshot / "release.json").read_text())
sha = release["source_commit"]
comparison = api("compare/" + sha + "...main")
if comparison["status"] not in ("ahead", "identical"):
    raise ValueError("Release source is not an ancestor of main; merge and publish the merged commit first")
print("PASS: release source belongs to main")
with open(os.environ["GITHUB_OUTPUT"], "a") as output:
    output.write(f"sha={sha}\n")
