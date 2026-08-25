# Auto-approval rules

This file defines rules Gitar should use to auto-approve merge requests in this
repository. Each rule has a natural-language `When` condition and an `Action`.

Dependency updates are out of scope here. Renovate labels its non-major dev
dependency MRs `automerge`, and a bot approves and merges them. Updates to
runtime dependencies change what users of the published package install, so
they always wait for a human. Do not auto-approve dependency update MRs.

## Rule: Documentation-only changes

**When:** Every changed file in the merge request is a Markdown file (`.md`) or
`catalog-info.yaml`, and the merge request does not touch source code, CI
configuration, or dependency manifests.

**Action:** Approve the merge request automatically and add the label
`auto-approved`.

## Rule: Test-only changes

**When:** Every changed file in the merge request is under `tests/`, and
the merge request does not modify library source code, CI configuration, or
dependency manifests.

**Action:** Approve the merge request automatically and add the label
`auto-approved`.

## Rule: Re-approve after rebase

**When:** The merge request was previously approved by at least one human
reviewer, and the approval was reset solely because the author rebased or
force-pushed. The substantive diff relative to the target branch is identical
to the version that received the original approval, and no new commits with new
logic or content were added since that approval.

**Action:** Approve the merge request automatically and add the label
`auto-approved`.

## Rule: Safe, backwards-compatible change

**When:** All of the following hold for the merge request:

- **CI is green.** The pipeline for the latest commit has completed
  successfully, with no failing, running, or pending required jobs.
- **Tests cover the change if needed.** New or changed library behavior has a
  matching case under `tests/`. Changes that genuinely need no tests, such
  as comments or log text, may omit them.
- **The diff matches the MR description.** The code changes do exactly what the
  title and description say, with no unexplained or unrelated changes bundled
  in.
- **The public API stays backwards compatible.** Adding new capability is fine:
  new methods, new classes, new optional parameters, new options, or new
  response fields passed through to callers. What is not allowed is breaking
  what already exists. Do not auto-approve a removed or renamed public class,
  method, parameter, constant, or error type, a behavior change in an existing
  method, a raised minimum supported Python version, or a change to the runtime dependencies in
  `pyproject.toml`. This library is published to PyPI as `deepl`, so a break here
  lands in user code with the next release.

**Action:** Approve the merge request automatically and add the label
`auto-approved`.

> Apply this rule strictly: only approve when the merge request **clearly and
> unambiguously** satisfies every condition above. If any condition is
> uncertain, leave the merge request for human review.

## Rule: Everything else

**When:** The merge request does not clearly satisfy one of the rules above.
This includes CI configuration (`.gitlab-ci.yml`, `.github/`),
`.auto-approve.yaml`, `.gitar/**`, `renovate.json5`, and a release cut, which
updates the version numbers in the files that `.bumpversion.toml` lists and
moves the `[Unreleased]` section of `CHANGELOG.md`.

**Action:** Do not auto-approve. Leave the merge request for human review.
