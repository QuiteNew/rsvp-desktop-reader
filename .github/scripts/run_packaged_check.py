"""Starts a packaged copy of the app with --self-check and decides whether it
passed. A workflow runs this on each platform after PyInstaller has built the
app, so a build that starts but doesn't work (a library or a file the packaging
left out) fails the run instead of going out.

It fails when the app doesn't finish in time, exits with anything but 0, leaves
no report, or the report doesn't say it passed. A packaged Windows app that
crashes shows an error dialog and waits for someone to click it, so a program
that hangs is treated as a failure, not waited for. The report is printed so
the log shows what was checked and what went wrong.

Usage: python run_packaged_check.py <app executable> [--report FILE] [--timeout SECONDS]
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

PASSED_MARK = "SELF-CHECK PASSED"


def run(executable, report_path, timeout):
    """Returns 0 if the packaged app passed its own check, 1 otherwise."""
    if not executable.is_file():
        print(f"There is no app at {executable}. Did the build put it somewhere else?")
        return 1
    # A full path, so a bare file name is found in the current folder and not
    # looked for on PATH.
    executable = executable.resolve()

    report_path.unlink(missing_ok=True)
    print(f"Starting {executable} --self-check (gives up after {timeout} seconds)")
    try:
        finished = subprocess.run(
            [str(executable), "--self-check", str(report_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"The app was still running after {timeout} seconds, so it was stopped. "
              "A crash that leaves an error dialog open looks like this.")
        _print_report(report_path)
        return 1
    except OSError as error:
        print(f"The app could not be started: {error}")
        return 1

    report = _print_report(report_path)
    # The app also prints its report, so what it printed is only shown when it
    # holds something the report file doesn't.
    for name, text in (("output", finished.stdout), ("error output", finished.stderr)):
        if text and text.strip() and text.strip() != (report or "").strip():
            print(f"--- the app's {name} ---\n{text.rstrip()}")

    if report is None:
        print("The app finished but wrote no report.")
        return 1
    if finished.returncode != 0:
        print(f"The app exited with code {finished.returncode}.")
        return 1
    if PASSED_MARK not in report:
        print(f'The app exited with 0, but its report has no "{PASSED_MARK}" line.')
        return 1
    print("The packaged app passed its self-check.")
    return 0


def _print_report(report_path):
    """Prints the report and gives its text, or None when there isn't one."""
    if not report_path.is_file():
        return None
    text = report_path.read_text(encoding="utf-8", errors="replace")
    print("--- self-check report ---")
    print(text.rstrip())
    print("-------------------------")
    return text


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("executable", type=Path, help="the packaged app to start")
    parser.add_argument("--report", type=Path, default=None,
                        help="where the app writes its report (default: a temporary file)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="seconds to wait for the app (default: 120)")
    args = parser.parse_args(argv)

    # The runner's own output should never be what fails the step, whatever
    # the console can show.
    sys.stdout.reconfigure(errors="replace")

    if args.report is not None:
        return run(args.executable, args.report, args.timeout)
    with tempfile.TemporaryDirectory() as folder:
        return run(args.executable, Path(folder) / "report.txt", args.timeout)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))