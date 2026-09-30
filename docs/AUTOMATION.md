# How to read the publishing automation

The workflows show the order of operations and the permissions of each job.
The Python entry points select an operation. The operation modules implement
it using small helpers. Start with the first function in each file.

## Reading order

| File | Responsibility |
|---|---|
| `.github/workflows/publish.yml` | Resolve, build, publish, verify HTTPS, select dev |
| `.github/workflows/promote.yml` | Reverify a retained release, then select production |
| `.github/workflows/redeploy.yml` | Recover Pages from the retained files |
| `tools/resolve.py` | Resolve a ref once and require passing source CI |
| `tools/depository.py` | Select the requested publication operation |
| `tools/publishing/operations.py` | Publish, stage, and promote snapshots |
| `tools/publishing/validation.py` | Validate identity, inventory, checksums, and lockfiles |
| `tools/publishing/site.py` | Render the small release index |
| `tools/publishing/files.py` | Read files and replace metadata atomically |
| `tools/assert-main.py` | Require release source to belong to main |
| `tools/verify-http.py` | Verify the actual public files against retained checksums |
| `tools/github_actions.py` | GitHub API reads and workflow output files |
| `tools/summary.py` | Explain the next step in workflow summaries |
| `tools/commit-site.sh` | Commit generated files and push without force |

## Where the rules live

`validate_snapshot` reads as a checklist of specific validations. It never runs
code from an incoming archive. The privileged publication job calls it before
copying candidate files into retained storage.

`plan_production_selection` is a pure function. Its arguments include the current
selection, verification evidence, expected previous release, workflow identity,
and time. It returns the new selection, returns no change for an identical retry,
or rejects a stale request. It does not read files, change its arguments, or call
GitHub. `promote_snapshot` handles those external actions around the decision.

`staging_record` and `history_filename` are also pure transformations. File writes,
network requests, timestamps, and Git commands are explicit boundaries. Use this
pattern when adding Connect integration: keep the selection rules separate from
the command that performs a deployment.

## Conventions and checks

Use descriptive action names and keep each function at one level of detail.
Avoid embedded Python programs and long shell expressions in workflow YAML.
Do not hide job permissions or trust boundaries inside a generic framework.

The runtime uses the Python standard library. Ruff is the only development
package, pinned in `requirements-dev.txt`. CI enforces its formatting and lint
rules, including an 88-character Python line limit. On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
python3 -m unittest discover -s tests -v
```

Use `ruff format .` to apply formatting. Changes still need the integrity,
immutability, staging, and promotion tests; formatting alone proves no behavior.
