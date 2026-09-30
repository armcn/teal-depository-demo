"""Command-line entry point for trusted publication operations. Start here."""

import argparse
from pathlib import Path

from publishing.operations import promote_snapshot, publish_snapshot, stage_snapshot
from publishing.validation import validate_snapshot


def main():
    arguments = parse_arguments()
    command = arguments.command
    if command == "validate":
        validate_snapshot(arguments.directory)
    elif command == "validate-site":
        validate_retained_snapshots(arguments.site)
    elif command == "publish":
        publish_snapshot(
            arguments.candidate, arguments.site, arguments.snapshot, arguments.sha
        )
    elif command == "stage":
        stage_snapshot(arguments.site, arguments.snapshot, arguments.workflow_url)
    else:
        promote_snapshot(
            arguments.site,
            arguments.snapshot,
            arguments.expected_current,
            arguments.workflow_url,
        )
    print("PASS:", command)


def validate_retained_snapshots(site):
    for manifest in sorted((Path(site) / "snapshots").glob("*/release.json")):
        validate_snapshot(manifest.parent)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check one retained snapshot")
    validate.add_argument("directory")
    validate_site = commands.add_parser("validate-site", help="Check all snapshots")
    validate_site.add_argument("site")
    publish = commands.add_parser("publish", help="Save a new immutable snapshot")
    publish.add_argument("candidate")
    publish.add_argument("site")
    publish.add_argument("snapshot")
    publish.add_argument("sha")
    for name in ("stage", "promote"):
        command = commands.add_parser(name)
        command.add_argument("site")
        command.add_argument("snapshot")
        command.add_argument("--workflow-url", required=True)
        if name == "promote":
            command.add_argument("--expected-current", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
