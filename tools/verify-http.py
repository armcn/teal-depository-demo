"""Verify every public file; retry only while Pages propagates the manifest."""

import hashlib
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from publishing.validation import validate_snapshot


def main():
    directory = Path(sys.argv[1])
    manifest = validate_snapshot(directory)
    repository_url = manifest["repository_url"]
    wait_for_published_manifest(repository_url, directory / "release.json")
    verify_published_files(repository_url, manifest["files"])
    print("PASS: every published file matches the tested snapshot")


def wait_for_published_manifest(repository_url, manifest_path):
    expected = manifest_path.read_bytes()
    retryable_statuses = {404, 429, 500, 502, 503, 504}
    for attempt in range(12):
        try:
            if download_file(repository_url, "release.json") == expected:
                return
        except urllib.error.HTTPError as error:
            if error.code not in retryable_statuses:
                raise
        if attempt < 11:
            time.sleep(5)
    raise RuntimeError(
        "Published snapshot did not become available within the bounded retry period"
    )


def verify_published_files(repository_url, checksums):
    for name, expected in checksums.items():
        content = download_file(repository_url, name)
        if hashlib.sha256(content).hexdigest() != expected:
            raise RuntimeError("Published checksum mismatch: " + name)


def download_file(repository_url, relative_path):
    request = urllib.request.Request(
        repository_url + "/" + relative_path,
        headers={"Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


if __name__ == "__main__":
    main()
