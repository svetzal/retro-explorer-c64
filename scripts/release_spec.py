"""The starter's version agrees in pyproject.toml, uv.lock and CHANGELOG.md."""

from pathlib import Path

import pytest
import release

PYPROJECT = '[project]\nname = "starter"\nversion = "0.3.0"\n'
LOCK = (
    'version = 1\n\n[[package]]\nname = "numpy"\nversion = "2.0.0"\n\n'
    '[[package]]\nname = "starter"\nversion = "0.3.0"\n'
)
CHANGELOG = """# Changelog

## [Unreleased]

## [0.3.0] - 2026-11-20

### Added

- A new command.

## [0.2.0] - 2026-11-16

### Changed

- An older change.
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    (tmp_path / "uv.lock").write_text(LOCK)
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    return tmp_path


class DescribeTheVersion:
    def should_agree_in_this_repository(self) -> None:
        assert release.problems(*release.read(release.ROOT)) == []

    def should_pass_when_the_three_records_agree(self, root: Path) -> None:
        assert release.main(["check"], root) == 0

    def should_name_a_lock_that_was_not_updated(self, root: Path) -> None:
        (root / "uv.lock").write_text(LOCK.replace("0.3.0", "0.2.0"))

        assert release.problems(*release.read(root)) == [
            "uv.lock records starter 0.2.0, not 0.3.0; run uv lock."
        ]
        assert release.main(["check"], root) == 1

    def should_name_a_changelog_without_the_new_section(self, root: Path) -> None:
        (root / "pyproject.toml").write_text(PYPROJECT.replace("0.3.0", "0.4.0"))
        (root / "uv.lock").write_text(LOCK.replace("0.3.0", "0.4.0"))

        assert release.problems(*release.read(root)) == [
            "The newest CHANGELOG.md section is 0.3.0, not 0.4.0."
        ]

    def should_ignore_the_unreleased_section(self) -> None:
        assert release.changelog_versions(CHANGELOG) == ["0.3.0", "0.2.0"]

    def should_need_a_released_section(self, root: Path) -> None:
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n")

        assert release.problems(*release.read(root)) == [
            "CHANGELOG.md has no '## [x.y.z] - YYYY-MM-DD' section."
        ]


class DescribeReleaseNotes:
    def should_print_one_section_without_its_heading(self) -> None:
        assert release.notes(CHANGELOG, "0.3.0") == "### Added\n\n- A new command.\n"

    def should_print_the_last_section_to_the_end(self) -> None:
        assert release.notes(CHANGELOG, "0.2.0") == "### Changed\n\n- An older change.\n"

    def should_default_to_the_project_version(
        self, root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert release.main(["notes"], root) == 0
        assert capsys.readouterr().out == "### Added\n\n- A new command.\n"

    def should_refuse_a_version_with_no_section(
        self, root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert release.main(["notes", "9.9.9"], root) == 1
        assert "no section for 9.9.9" in capsys.readouterr().err
