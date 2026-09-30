"""Write the next action in a successful workflow's GitHub summary."""

import os
import sys

from github_actions import write_workflow_summary


def main():
    snapshot = os.environ["SNAPSHOT"]
    if sys.argv[1] == "candidate":
        summary = candidate_summary(snapshot)
    else:
        summary = production_summary(snapshot, os.environ["EXPECTED_CURRENT"])
    write_workflow_summary(summary)


def candidate_summary(snapshot):
    return (
        "## Candidate ready\n\n"
        f"Snapshot: `{snapshot}`\n\n"
        "Clean restore over HTTPS passed.\n\n"
        "Use **Promote or roll back** with this snapshot to select production.\n"
    )


def production_summary(snapshot, previous):
    return (
        "## Production selection\n\n"
        f"Snapshot: `{snapshot}`\n\n"
        f"Previous: `{previous}`\n\n"
        "No package archives were rebuilt or changed.\n"
    )


if __name__ == "__main__":
    main()
