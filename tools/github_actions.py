"""Small, explicit boundaries for GitHub API reads and workflow output files."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

SOURCE_REPOSITORY = "armcn/teal-architecture-demo"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


def read_source_api(path):
    url = f"https://api.github.com/repos/{SOURCE_REPOSITORY}/{path}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "teal-architecture-demo",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES or attempt == 3:
                raise
            time.sleep(2**attempt)


def write_workflow_outputs(values):
    lines = [f"{name}={value}\n" for name, value in values.items()]
    append_workflow_file("GITHUB_OUTPUT", "".join(lines))


def write_workflow_summary(text):
    append_workflow_file("GITHUB_STEP_SUMMARY", text)


def append_workflow_file(variable, text):
    with Path(os.environ[variable]).open("a") as output:
        output.write(text)
