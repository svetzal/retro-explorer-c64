"""Setup behavior through its command and real download boundaries."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import setup
from references import ConversionError, ConvertedPage, DoclingGateway, Resource, conversion_profile


class DescribeProjectSetup:
    @pytest.mark.parametrize("target", [None, *setup.TARGETS])
    def should_write_the_index_without_creating_project_notes(
        self, project: Path, target: str | None
    ) -> None:
        arguments = ["--guidance-only"] + (["--target", target] if target else [])

        assert setup.main(arguments, project) == 0

        assert (project / "local/INDEX.md").is_file()
        assert not (project / "local/PROJECT.md").exists()
        assert not (project / "projects").exists()

    def should_leave_owner_projects_untouched(self, project: Path) -> None:
        notes = project / "projects/demo/PROJECT.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("# Demo\nTarget: C64 PAL\nOwner notes.")
        saved = notes.read_bytes()

        assert setup.main(["--guidance-only", "--target", "c64-pal"], project) == 0
        assert setup.main(["--guidance-only", "--target", "c64-ntsc"], project) == 0

        assert notes.read_bytes() == saved

    def should_ask_for_the_firmware_target_only_when_downloading_firmware(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        console = Mock(spec=setup.ConsoleGateway)
        console.choose_target.return_value = "c64-ntsc"
        provision = Mock()
        monkeypatch.setattr(setup, "provision", provision)

        assert setup.main(["--guidance-only"], project, console=console) == 0
        console.choose_target.assert_not_called()
        assert setup.main(["--firmware-only"], project, console=console) == 0

        provision.assert_called_once_with(project, "c64-ntsc", None)

    def should_explain_a_missing_firmware_target_without_a_traceback(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        console = Mock(spec=setup.ConsoleGateway)
        console.choose_target.side_effect = ValueError(
            "Choose a target with --target: c64-pal, c64-ntsc"
        )

        result = setup.main(["--firmware-only"], project, console=console)

        assert result == 1
        assert "Choose a target" in capsys.readouterr().err
        assert not (project / "local").exists()

    @pytest.mark.parametrize("value", ["invalid", "0:1", "2:1"])
    def should_reject_invalid_page_ranges_before_writing_anything(
        self, project: Path, value: str
    ) -> None:
        assert setup.main(["--pages", value], project) == 1
        assert not (project / "local").exists()

    @pytest.mark.parametrize("arguments", [["--list"], ["--resource", "unknown"]])
    def should_not_initialize_when_listing_or_rejecting_a_selection(
        self, project: Path, arguments: list[str]
    ) -> None:
        expected = 0 if arguments == ["--list"] else 1
        assert setup.main(arguments, project) == expected
        assert not (project / "local").exists()

    def should_report_damaged_resources_as_unconverted(self, project: Path) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(b"corrupted")

        result = setup.main(["--target", "c64-pal"], project)

        assert result == 1
        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_keep_failed_conversions_unconverted(self, project: Path, pdf_bytes: bytes) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.side_effect = ConversionError("model unavailable")

        result = setup.main(["--target", "c64-pal"], project, documents=documents)

        assert result == 1
        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_convert_only_requested_resources_and_index_all_of_them(
        self,
        project: Path,
        resource: Resource,
        pdf_bytes: bytes,
    ) -> None:
        other = resource.model_copy(update={"id": "other-book"})
        (project / "resources.json").write_text(
            json.dumps([resource.model_dump(), other.model_dump()])
        )
        directory = project / "local/references/other-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.return_value = ConvertedPage(
            markdown="selected content", document={}
        )

        result = setup.main(
            ["--target", "c64-pal", "--resource", "other-book", "--pages", "1:1"],
            project,
            documents=documents,
        )

        assert result == 0
        assert not (project / "local/references/test-book").exists()
        assert "selected content" in (directory / "text.md").read_text()
        index = (project / "local/INDEX.md").read_text()
        assert "--resource test-book" in index
        assert "references/other-book/text.md" in index

    @pytest.mark.parametrize("damage", ["source", "metadata", "legacy"])
    def should_not_advertise_stale_or_legacy_outputs(
        self,
        project: Path,
        resource: Resource,
        pdf_bytes: bytes,
        damage: str,
    ) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.return_value = ConvertedPage(markdown="content", document={})
        assert (
            setup.main(["--target", "c64-pal", "--pages", "1:1"], project, documents=documents) == 0
        )
        metadata = directory / "extraction.json"
        record = json.loads(metadata.read_text())
        if damage == "source":
            (directory / "source.pdf").write_bytes(b"damaged")
        elif damage == "metadata":
            record["sha256"] = "0" * 64
        else:
            del record["profile"]
        metadata.write_text(json.dumps(record))

        assert setup.main(["--guidance-only"], project) == 0

        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_report_unreadable_manifest(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert setup.main(["--list"], tmp_path) == 1
        assert "Setup failed" in capsys.readouterr().err

    def should_run_the_script_entry_point(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(setup.__file__)), "--list"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "c64-prg" in result.stdout


class DescribeManifestValidation:
    @pytest.mark.parametrize(
        "change",
        [
            {"id": "../outside"},
            {"url": "http://example.com/book.pdf"},
            {"sha256": ""},
            {"title": ""},
        ],
    )
    def should_reject_unsafe_or_incomplete_resources(
        self, project: Path, resource: Resource, change: dict[str, str]
    ) -> None:
        data = resource.model_dump() | change
        (project / "resources.json").write_text(json.dumps([data]))

        with pytest.raises(ValueError):
            setup.ProjectStore(project).resources()

    def should_reject_duplicate_identifiers(self, project: Path, resource: Resource) -> None:
        (project / "resources.json").write_text(json.dumps([resource.model_dump()] * 2))

        with pytest.raises(ValueError, match="Duplicate"):
            setup.ProjectStore(project).resources()


class DescribeReferenceDownloads:
    def should_reuse_a_verified_pdf_even_when_its_server_is_unavailable(
        self,
        tmp_path: Path,
        resource: Resource,
        pdf_server: str,
        pdf_bytes: bytes,
    ) -> None:
        gateway = setup.DownloadGateway()
        destination = tmp_path / "reference.pdf"
        remote = resource.model_copy(update={"url": pdf_server + "/reference.pdf"})
        gateway.fetch(remote, destination)
        cached = remote.model_copy(update={"url": pdf_server + "/missing"})

        gateway.fetch(cached, destination)

        assert destination.read_bytes() == pdf_bytes

    def should_reject_a_corrupted_cached_pdf(self, tmp_path: Path, resource: Resource) -> None:
        destination = tmp_path / "reference.pdf"
        destination.write_bytes(b"corrupted")

        with pytest.raises(ValueError, match="checksum mismatch"):
            setup.DownloadGateway().fetch(resource, destination)

        assert destination.read_bytes() == b"corrupted"

    @pytest.mark.parametrize("failure", ["missing", "checksum", "invalid"])
    def should_leave_no_partial_files_after_a_failed_download(
        self,
        tmp_path: Path,
        resource: Resource,
        pdf_server: str,
        failure: str,
    ) -> None:
        changes = {"url": pdf_server + ("/missing" if failure == "missing" else "/reference.pdf")}
        if failure == "checksum":
            changes["sha256"] = "0" * 64
        elif failure == "invalid":
            changes = {
                "url": pdf_server + "/invalid",
                "sha256": hashlib.sha256(b"not a PDF").hexdigest(),
            }
        remote = resource.model_copy(update=changes)

        with pytest.raises((OSError, ValueError)):
            setup.DownloadGateway().fetch(remote, tmp_path / "reference.pdf")

        assert list(tmp_path.iterdir()) == []
