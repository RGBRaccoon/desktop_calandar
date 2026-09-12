"""Run an EXE from an isolated working directory and retain QA evidence."""

import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".local/exe-validation"))
    parser.add_argument("--require-oauth", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=args.output.resolve()))
    screenshot = work / "calendar.png"
    command = [
        str(args.executable.resolve()),
        "--smoke-test",
        "--data-dir",
        str(work / "data"),
        "--screenshot",
        str(screenshot),
    ]
    if args.require_oauth:
        command.append("--require-oauth")
    subprocess.run(command, cwd=work, check=True, timeout=90)
    log = (work / "data/logs/app.log").read_text(encoding="utf-8")
    if not screenshot.is_file() or "Smoke interactions passed" not in log:
        raise RuntimeError("EXE did not complete UI interaction checks")
    print(f"EXE UI validation passed. Evidence: {work}")


if __name__ == "__main__":
    main()
