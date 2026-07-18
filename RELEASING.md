# Releasing

perfect-brief lives in two places with one version history:

- **GitHub** (`github.com/welance/perfect-brief`) — canonical development,
  community PRs, Pages site. Pushing `main` auto-deploys the **develop**
  environment through the GitLab mirror (ci.skip + trigger token).
- **GitLab** (`gitlab.com/welance/r001-15-perfect-brief`) — the deploy twin
  running the welance git-flow pipeline (`git-flow/node.yml`). Release
  branches deploy **staging**; the MR-to-master pipeline deploys
  **production**, then merges, tags, and publishes the GitLab Release.

Versions are SemVer. The **release branch name is the version**
(`release/1.2.0` → image `1.2.0`, tag `v1.2.0`). The ruleset has its own
independent version (`semver+digest`); a rules change bumps the ruleset
version inside `perfect_brief/`, a service change bumps the service version
described here.

## Release checklist

1. **On `main`:** move the `Unreleased` notes in `CHANGELOG.md` under a new
   `## [X.Y.Z] - <date>` heading (Keep a Changelog format — `release_job`
   publishes this file as the GitLab Release description), bump `version` in
   `pyproject.toml` to `X.Y.Z`, commit, push. The mirror deploys develop;
   verify it.
2. **Cut the release branch** (Maintainer — `release/*` is protected):
   `git push gitlab main:refs/heads/release/X.Y.Z`
   The pipeline builds `X.Y.Z.rcN` and auto-deploys **staging**; verify
   `https://r001-15.staging.welance.space/v1/healthz`.
3. **Open the MR** `release/X.Y.Z` → `master` on GitLab. Its pipeline runs
   `check_prod` and `build_production_job` (image `X.Y.Z`).
4. **From that MR pipeline, in order** (both manual):
   1. `deploy_production_job` — deploys production; verify.
   2. `merge_and_tag` — merges the MR, creates GitLab tag `vX.Y.Z` and a
      `realign/X.Y.Z` branch; `release_job` then publishes the GitLab
      Release automatically.
   Never merge the MR by hand — that skips the tag and the Release (this
   happened with 1.1.0; its tags were backfilled).
5. **Mirror the tag to GitHub** — tag the `main` commit the release branch
   was cut from:
   `git tag vX.Y.Z <main-sha> && git push origin vX.Y.Z`
   The `release` GitHub workflow then publishes the GitHub Release with the
   matching CHANGELOG section. GitHub `vX.Y.Z` and GitLab `vX.Y.Z` point at
   the same tree (GitLab's tag is on the merge commit; content is identical).

## Invariants

- One CHANGELOG, one version, two remotes: GitHub and GitLab tags for the
  same version always reference the same tree.
- The GitLab side is tagged by the pipeline (`merge_and_tag`), never by
  hand; the GitHub side is tagged by hand (step 5), and the Release is
  published by the workflow, never by hand.
- Hotfixes follow the same path with a patch bump (`release/X.Y.(Z+1)` cut
  from `main` after the fix lands there via the normal PR flow).
