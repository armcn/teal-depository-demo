"""Check every published byte against the local manifest; retry Pages propagation only."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from depository import validate

directory = Path(sys.argv[1])
manifest = validate(directory)
base = manifest["repository_url"]


def download(path):
    request = urllib.request.Request(base + "/" + path, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


for attempt in range(12):
    try:
        remote = download("release.json")
        if remote == (directory / "release.json").read_bytes():
            break
    except urllib.error.HTTPError as error:
        if error.code not in (404, 429, 500, 502, 503, 504):
            raise
    if attempt == 11:
        raise RuntimeError("Published snapshot did not become available within the bounded retry period")
    time.sleep(5)
for name, expected in manifest["files"].items():
    actual = hashlib.sha256(download(name)).hexdigest()
    if actual != expected:
        raise RuntimeError("Published checksum mismatch: " + name)
print("PASS: every published file matches the tested snapshot")
