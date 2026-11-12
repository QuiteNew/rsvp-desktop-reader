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
   includes the GUI tests and covers Windows, which GitHub's run does not (it
   runs on Linux). On Windows 8 tests are skipped, because Windows reports the
   number pad Enter as the ordinary Return key; that is expected.

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

5. **Optional dry run.** Go to Actions, then Build & Release, then Run
   workflow, on `main` and with "Create a draft GitHub release" left off. It
   builds all three platforms without releasing anything, and the files come
   out named `RSVPReader-main-<platform>`. Download the Windows and Linux
   ones, start them, open Settings, press the **i** button and check that the
   version and the link look right.

6. **Tag and push the tag.** The tag goes on the tip of `main`, which is the
   merge commit when a branch was merged:

```
   git tag vX.Y.Z
   git push origin vX.Y.Z
```

7. **Watch Build & Release.** It runs the tests first, then builds Windows,
   macOS and Linux, then creates a draft release. If the tests fail, nothing
   is built.

8. **Fill in the draft.** Under Releases, open the draft, set the title and
   description (see below), check the attached files, and publish.

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

Update the macOS line once the macOS build is finished, and the Linux line if
the build machine changes.

## When something goes wrong

**The tests fail on the tag.** Nothing gets built or uploaded. Open the failed
run and read the message. If it says `APP_VERSION is X but the newest release
tag is vY`, the version bump was forgotten.

**A build fails on one platform.** The draft is only created once all three
builds succeed, so no draft appears. The other two builds still finish, which
helps to tell whether the problem is one platform or all of them.

**Moving the tag.** In both cases the fix is the same. Fix the problem, commit
it, push `main`, wait for green, then move the tag so it sits on the fixed
commit:

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