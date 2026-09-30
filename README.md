# Teal demo Depository

Generated CRAN-style R package snapshots for [teal-architecture-demo](https://github.com/armcn/teal-architecture-demo). Mock code only.

**[Open the Depository](https://armcn.github.io/teal-depository-demo/)** · **[Developer walkthrough](https://github.com/armcn/teal-architecture-demo/blob/main/docs/WALKTHROUGH.md)**

## Daily use

1. Make changes and pass **Check source** in the source repository.
2. Run **Publish candidate** here with the source branch or commit. The workflow builds packages, publishes an immutable snapshot, verifies a clean installation over HTTPS, and selects it as dev.
3. Run **Promote or roll back** with a tested release snapshot ID and the current production ID. Package bytes remain unchanged.

Dev and production are simulated release selections, not hosted Connect apps. The example Shiny app runs locally.

Use the **dev** or **prod** selections for routine downloads. The snapshot list also retains unverified candidates, including builds stopped after publication but before staging verification. Their presence on the site does not make them eligible for production.

## Repository layout

- `main`: publication workflows, validation code, and tests. Change these through reviewed pull requests.
- `published`: generated `site/` contents. CI writes this branch; consumers read it. Do not edit package files manually.
- `site/snapshots/<id>/src/contrib/`: package tarballs and CRAN indexes.
- `site/snapshots/<id>/app/`: saved app files and exact lockfile.
- `site/channels/{dev,prod}.json`: current selections.
- `site/evidence/`: successful staging verification records.
- `site/history/`: promotion and rollback records.

There are no feature branches corresponding to branches in the source repository. A single source branch can produce multiple immutable snapshots.

## Maintenance and recovery

**Republish retained site** validates stored snapshots and republishes Pages without building packages. Use it after a transient Pages failure. Then rerun failed jobs in the original publication workflow if it still needs to record successful staging.

This example retains all snapshots. Actions artifacts expire after seven days, but they are only transport. Published packages and app files are retained in Git and served through Pages.

Run publisher tests locally:

```sh
python3 -m unittest discover -s tests -v
```

The workflows use pinned actions, read-only defaults, a shared publication concurrency group, bounded timeouts, checksummed artifacts, isolated build jobs, and fast-forward-only Git writes. No cross-repository personal access token is required for these public example repositories.

GitHub Pages must be configured with **Source: GitHub Actions**. The `published` branch must exist before the first publication. The setup creates it with an empty `site/` directory and index page.

Read the [automation guide](docs/AUTOMATION.md) for the code layers, reading order,
and local formatting checks.
