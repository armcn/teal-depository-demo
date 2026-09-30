"""Read immutable files and atomically replace generated metadata."""

import hashlib
import json
import tempfile
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text())


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json_atomically(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
