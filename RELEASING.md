# Releasing

How a release of RSVP Desktop Reader gets made, from the last commit to the
published release. It is written to be followed cold, without having to
remember how it went last time.

## Version numbers

Releases are tagged `vMAJOR.MINOR.PATCH`. So far a new feature has bumped the
minor number (v3.2.0, v3.3.0) and a fix on its own has bumped the patch number
(v2.10.1).

The version lives in exactly one place: `APP_VERSION` in `core/app_info.py`,
which is what the About dialog shows. It is changed by hand and nothing reads
it from the git tag. That is why the checklist below has a step for it, and why
a test fails when a release tag is newer than the number written there.

## Checklist

1. **Finish the work.** Everything for the release is committed and
   `git status` is clean.

2. **Run the tests on your own machine.** From the project folder, with the
   virtual environment active:

```
   python -m pytest
   python -m pyflakes core gui tests main.py
```

   Every test should pass and pyflakes should print nothing. This run
   includes the GUI tests and covers Windows. GitHub's everyday run is on Linux
   only, but a release also runs the suite on Windows (step 7), and finding a
   failure here is quicker than finding it after the tag. On Windows 8 tests
   are skipped, because Windows reports the number pad Enter as the ordinary
   Return key; that is expected.

   `pyproject.toml` tells pytest to capture output with `--capture=sys`.
   Leave that in: with pytest's default capture, Tk on Windows now and then
   failed to start at all, unable to read its own library files.

3. **Make the docs commits.** Update the docs pages the release touches. Then,
   in the last commit, update the README (feature list, roadmap), this file if
   the steps changed, and bump `APP_VERSION` in `core/app_info.py`. That last
   commit is the one that gets tagged, and the version bump is the last edit
   in it.

4. **Get it onto `main` and wait.** If the work was done on a branch, open a pull
   request and merge it with **Create a merge commit** (not squash and not
   rebase, so the commits keep their own dates), then update local `main`. If it
   was done on `main`, just push. Open the Actions tab and wait for **Tests**
   and **Docs** to go green on `main`. Don't tag before they do.

   A push that only touches the docs, this file or the build and release files
   doesn't start **Tests**, because the 15 minute run can't change anything
   for those. That is fine: nothing is waiting for a run that never starts.
   Pushing again while **Tests** is still running stops the older run.

5. **Optional dry run.** Go to Actions, then Build & Release, then Run
   workflow, on `main`. There is nothing to tick. A run started by hand never
   makes a release, only a pushed tag does. It runs the tests on Linux and
   Windows, builds all three platforms and starts each packaged app to check
   it (see below), and it takes about half an hour. The files come out named
   `RSVPReader-main-<platform>`. Download the Windows and Linux ones, start
   them, open Settings, press the **i** button and check that the version and
   the link look right.

6. **Tag and push the tag.** The tag goes on the tip of `main`, which is the
   merge commit when a branch was merged:

```
   git tag vX.Y.Z
   git push origin vX.Y.Z
```

   The first thing the workflow does is look at the tag. It fails within
   seconds, before anything slow starts, if the tag doesn't match
   `APP_VERSION` or if the tagged commit isn't on `main`.

7. **Watch Build & Release.** In order, it checks the tag, runs the tests on
   Linux and on Windows at the same time, builds Windows, macOS and Linux, and
   starts each built app with `--self-check` to see that it really works.
   Only then does it create a draft release. If the tests or a check fail,
   nothing is released.

8. **Fill in the draft.** Under Releases, open the draft, set the title and
   description (see below), check the attached files, and publish. Besides the
   three downloads there is a `SHA256SUMS.txt` with one line per download.

## Release notes

The title is `vX.Y.Z - a short name for the main change`, for example
`v3.3.0 - About dialog with app version info`.

The description has a section for what is new (one heading per feature if
there are several), an "Under the hood" section for changes nobody sees, and a
"Downloads" section:

```
## What is new
What it does, in plain words, from the point of view of someone using the app.

## Under the hood
Tests, refactors, tooling. Leave this out if there is nothing to say.

## Downloads
Windows (.zip) and Linux (.tar.gz) builds are attached below. The Linux build needs Ubuntu 24.04 or newer, or another distribution with glibc 2.39 or newer.
The macOS build is not finished yet, so macOS users need to run from source.
```

Mention `SHA256SUMS.txt` in the Downloads section when the release has it, for
example "`SHA256SUMS.txt` lists a checksum for each download". To check a
download, run this in the folder with the file and the list. It only looks at
the files that are there:

```
sha256sum -c SHA256SUMS.txt --ignore-missing
```

On Windows PowerShell, `Get-FileHash -Algorithm SHA256 <file>` prints the
checksum to compare with that file's line in the list.

Update the macOS line once the macOS build is finished, and the Linux line if
the build machine changes.

## When something goes wrong

**The tag check fails.** The run stops in the first job, within seconds. The
message says which of the two it is: the tag doesn't match `APP_VERSION`
(the version bump was forgotten or mistyped), or the tagged commit isn't on
`main`. Fix it, then move the tag as described below.

**The tests fail on the tag.** Nothing gets built or uploaded. Open the failed
run and read the message. If it says `APP_VERSION is X but the newest release
tag is vY`, the version bump was forgotten. The tests run on both Linux and
Windows, so a test can fail on one of them only.

**The check of the built app fails.** The build job for that platform stops
before anything is packaged, so no draft appears. Open the step called "Check
the packaged app works" (on Linux its name ends in "(Linux)"). It prints the
report, one line per check, and the line that says `FAIL` names what is wrong,
for example a library or a font file the build left out. If the app was still
running after two minutes it was stopped, which is what an error window that
nobody clicks away looks like.

**A build fails on one platform.** The draft is only created once all three
builds succeed, so no draft appears. The other two builds still finish, which
helps to tell whether the problem is one platform or all of them.

**A release page named after a branch.** This can't happen any more. A run
started by hand has no release step, and the release step only runs for a
pushed `v` tag. If one ever turns up anyway, delete the release and the stray
tag it made.

**Moving the tag.** In every one of these cases the fix is the same. Fix the
problem, commit it, push `main`, wait for green, then move the tag so it sits
on the fixed commit:

```
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z
git tag vX.Y.Z
git push origin vX.Y.Z
```

Only do this while nobody has downloaded that release. Once it is public, fix
forward with a new patch version instead.

**Linux says "Could not load PyInstaller's embedded PKG archive" (PYI-2886).**
The executable is damaged or incomplete. In the one case so far it was an
incomplete copy of the download, not the build. Download the archive again and
extract it with `tar xzf`, which should finish without any errors.

## Dependency updates

Once a month Dependabot opens pull requests for the actions the workflows use
and the packages pinned in `requirements.txt` and `docs/requirements.txt`.
They are grouped, so there are only a few at a time. Each one runs the tests
before it can be merged. Merge one when the tests are green, or close it. A
new version of PyInstaller, Pillow or cryptography can break the built app
without breaking a test, so after merging one of those, do the dry run in step
5 before the next release.