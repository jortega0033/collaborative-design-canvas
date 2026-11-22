# Releasing

Only the owner releases. An agent never tags, publishes or creates a GitHub release.

## What a release is here

A release is a tagged commit on `main`. There is nothing to publish: no package, no installer and no hosted service. The product runs from a clone with Python 3.12 or newer.

## Before tagging

1. CI is green on `main` (both operating systems, both Python versions).
2. `python -m unittest discover -s tests -t .` passes on a clean checkout; note the test count.
3. The release record `docs/release-check.md` (ticket #10) exists, names this commit, and lists what was skipped.
4. `CHANGELOG.md`: move the Unreleased lines under a new version heading with the date, and leave an empty Unreleased section.
5. `git status` is clean and no data directory, SQLite file or `.env*` is tracked.

## Tagging

The owner creates an annotated tag on the release commit, for example `git tag -a v0.2.0 -m "v0.2.0"`, and pushes it. The version follows the schema and API changes recorded in the changelog.
