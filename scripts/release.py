"""Check that the starter's version agrees everywhere, and print a release's notes.

The version lives in pyproject.toml, in uv.lock's entry for the project, and in
the newest "## [x.y.z] - YYYY-MM-DD" section of CHANGELOG.md. check fails
unless the three agree. notes prints one version's section for a GitHub release.
The procedure is in guidance/starter/system.md.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)


def project_version(pyproject: str) -> tuple[str, str]:
    """The project's name and version from pyproject.toml."""
    project = tomllib.loads(pyproject)["project"]
    return project["name"], project["version"]


def locked_version(lock: str, name: str) -> str | None:
    """The version that uv.lock records for the project, if it records one."""
    for package in tomllib.loads(lock).get("package", []):
        if package.get("name") == name:
            return package.get("version")
    return None


def changelog_versions(changelog: str) -> list[str]:
    """The released versions in CHANGELOG.md, newest first."""
    return SECTION.findall(changelog)


def notes(changelog: str, version: str) -> str:
    """The body of one version's section, without its heading."""
    match = re.search(rf"^## \[{re.escape(version)}\] - .*$", changelog, re.MULTILINE)
    if not match:
        raise ValueError(f"CHANGELOG.md has no section for {version}.")
    following = SECTION.search(changelog, match.end())
    end = following.start() if following else len(changelog)
    return changelog[match.end() : end].strip() + "\n"


def problems(pyproject: str, lock: str, changelog: str) -> list[str]:
    """Each way the three records of the version disagree."""
    name, version = project_version(pyproject)
    found = []
    locked = locked_version(lock, name)
    if locked != version:
        found.append(f"uv.lock records {name} {locked}, not {version}; run uv lock.")
    released = changelog_versions(changelog)
    if not released:
        found.append("CHANGELOG.md has no '## [x.y.z] - YYYY-MM-DD' section.")
    elif released[0] != version:
        found.append(f"The newest CHANGELOG.md section is {released[0]}, not {version}.")
    return found


def read(root: Path) -> tuple[str, str, str]:
    return tuple(
        (root / name).read_text() for name in ("pyproject.toml", "uv.lock", "CHANGELOG.md")
    )


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="require one version in all three records")
    shown = commands.add_parser("notes", help="print a version's CHANGELOG.md section")
    shown.add_argument("version", nargs="?", help="default: the version in pyproject.toml")
    arguments = parser.parse_args(argv)
    try:
        pyproject, lock, changelog = read(root)
        if arguments.command == "notes":
            print(notes(changelog, arguments.version or project_version(pyproject)[1]), end="")
            return 0
        if found := problems(pyproject, lock, changelog):
            for problem in found:
                print(f"FAIL: {problem}", file=sys.stderr)
            return 1
        print(f"Version {project_version(pyproject)[1]} agrees in all three records.")
        return 0
    except (OSError, KeyError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
