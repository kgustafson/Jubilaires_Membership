# Release Workflow

This project uses separate development and production lanes. Development work happens locally on the Mac using the development Docker Compose stack. Production runs on the Linode server using the production Docker Compose stack. The two environments have separate containers, databases, volumes, backups, media files, and secrets.

## Environments

Development uses `docker-compose.yml`.

- Runs locally on the Mac.
- Includes the app, PostgreSQL, and Adminer.
- Publishes local convenience ports for development and inspection.
- May run ahead of production while new features are being built.

Production uses `docker-compose.prod.yml`.

- Runs on the Linode server.
- Includes the app, PostgreSQL, and Caddy.
- Does not include Adminer.
- Does not publish PostgreSQL to the public host.
- Uses `.env` for production secrets and deployment-specific settings.

## Branches

`main` is the production branch.

- Contains production-approved release and hotfix history.
- Production deploys from tags on `main`.
- Stable production tags use versions such as `v1.2.0` or `v1.2.1`.

`develop` is the active development branch.

- Day-to-day development and integration happen here.
- Development revision tags use versions such as `v1.1.1`, `v1.1.2`, and `v1.1.3`.
- Development may be ahead of production.

`feature/<short-name>` branches are short-lived work branches.

- Branch from `develop`.
- Merge back into `develop`.
- Keep changes focused on a specific feature, fix, or workflow.

`release/v<major>.<minor>.0` branches are release candidate branches.

- Branch from `develop` when a release milestone is ready.
- Freeze feature development for that release.
- Only stabilization fixes, documentation corrections, migration fixes, and test fixes should land here.
- Release candidate tags use `v<major>.<minor>.0-rc.N`, such as `v1.2.0-rc.1`.

`hotfix/v<major>.<minor>.<revision>` branches are production hotfix branches.

- Branch from `main`.
- Used for urgent production fixes.
- Merge back into both `main` and `develop`.
- Hotfix tags use versions such as `v1.2.1`.

## Versioning

Development revisions use normal revision increments:

```text
v1.1.1
v1.1.2
v1.1.3
```

Release candidates use prerelease tags against the upcoming production release:

```text
v1.2.0-rc.1
v1.2.0-rc.2
```

Production releases use clean major/minor/revision versions:

```text
v1.2.0
```

Production hotfixes increment the revision:

```text
v1.2.1
v1.2.2
```

Major versions are reserved for breaking or foundational changes. Minor versions mark production release milestones. Revisions mark development increments and production hotfixes.

## Normal Development Flow

```text
feature/<short-name> -> develop
develop revision tag -> v1.1.x
```

Before tagging a development revision:

- Update `version.md`.
- Add a newest-first entry to `revision.md`.
- Run smoke tests.
- Commit changes.
- Tag the commit.
- Push the branch and tag.

Manual Git commands:

```bash
git switch develop
git pull origin develop
git switch -c feature/<short-name>

# make changes, run tests
git add .
git commit -m "short description"

git switch develop
git pull origin develop
git merge --no-ff feature/<short-name>
git tag v1.1.x
git push origin develop
git push origin v1.1.x
```

## Release Candidate Flow

```text
develop -> release/v1.2.0
tag v1.2.0-rc.1
test and stabilize
tag v1.2.0-rc.2 if needed
```

Once a release branch is created, feature development for that release is frozen. Fixes on the release branch should be limited to release readiness.

Release candidate testing should include:

- Smoke tests against the app.
- Backup creation.
- Restore testing when database changes are involved.
- Fresh database initialization.
- Migration testing from the current production version.
- Review of `revision.md`, `version.md`, Docker configuration, and deployment notes.

Manual Git commands:

```bash
git switch develop
git pull origin develop
git switch -c release/v1.2.0

# update version.md to v1.2.0-rc.1 and add revision.md RC notes
# run release candidate tests
git add .
git commit -m "v1.2.0-rc.1 release candidate"
git tag v1.2.0-rc.1
git push origin release/v1.2.0
git push origin v1.2.0-rc.1
```

If a second release candidate is needed:

```bash
git switch release/v1.2.0
git pull origin release/v1.2.0

# make stabilization fixes
git add .
git commit -m "v1.2.0-rc.2 stabilization"
git tag v1.2.0-rc.2
git push origin release/v1.2.0
git push origin v1.2.0-rc.2
```

## Production Release Flow

```text
release/v1.2.0 -> main
tag v1.2.0
deploy v1.2.0 to Linode
main -> develop
```

Production deployment should use the tagged release from `main`. After release, merge `main` back into `develop` so active development starts from the production baseline.

Manual Git commands:

```bash
git switch main
git pull origin main
git merge --no-ff release/v1.2.0

# update version.md to v1.2.0 if needed and add final release notes
git add .
git commit -m "v1.2.0 production release"
git tag v1.2.0
git push origin main
git push origin v1.2.0

git switch develop
git pull origin develop
git merge --no-ff main
git push origin develop
```

## Hotfix Flow

```text
main -> hotfix/v1.2.1
fix and test
hotfix/v1.2.1 -> main
tag v1.2.1
deploy v1.2.1
hotfix/v1.2.1 -> develop
```

Hotfixes should be tightly scoped. If a hotfix includes a database change, it must include a forward-only migration and backup/restore verification.

Manual Git commands:

```bash
git switch main
git pull origin main
git switch -c hotfix/v1.2.1

# make hotfix, update version.md and revision.md, run tests
git add .
git commit -m "v1.2.1 hotfix"

git switch main
git merge --no-ff hotfix/v1.2.1
git tag v1.2.1
git push origin main
git push origin v1.2.1

git switch develop
git pull origin develop
git merge --no-ff main
git push origin develop
```

## Database Changes

Production and development databases are separate. Development may contain schema changes that production does not have yet.

Every database structure change must be represented by a migration before it is part of a release candidate. Migrations should be ordered, forward-only, and treated as immutable once they are included in a tagged release candidate.

Release candidate testing must prove that migrations apply cleanly from the current production version to the release candidate version.

## Deployment Rule

Code moves between environments through Git branches and tags. Runtime data, uploaded photos, backups, and secrets do not move automatically between development and production. Any data movement must be intentional, backed up, and documented.
