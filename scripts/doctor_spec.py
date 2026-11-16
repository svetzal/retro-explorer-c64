"""Doctor reports tools and firmware bytes, and its exit status follows them."""

import shutil
from pathlib import Path
from unittest.mock import Mock

import doctor
import pytest
from doctor import ExecutableGateway, main

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copy(ROOT / "firmware.json", tmp_path / "firmware.json")
    return tmp_path


def executables(missing: tuple[str, ...] = ()) -> Mock:
    gateway = Mock(spec=ExecutableGateway)
    gateway.find.side_effect = lambda name: None if name in missing else f"/bin/{name}"
    return gateway


class DescribeDoctor:
    def should_pass_with_tools_and_no_target_but_say_firmware_is_unchecked(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([], root=project, executables=executables()) == 0

        output = capsys.readouterr().out
        assert "Firmware NOT checked" in output
        assert "They do not start VICE" in output

    def should_fail_and_name_a_missing_tool(self, project: Path, capsys) -> None:
        assert main([], root=project, executables=executables(("c1541",))) == 1

        assert "c1541: missing" in capsys.readouterr().out

    def should_fail_when_the_target_firmware_is_absent(self, project: Path, capsys) -> None:
        assert main(["--target", "c64-ntsc"], root=project, executables=executables()) == 1

        assert "--target c64-ntsc --firmware-only" in capsys.readouterr().out

    def should_pass_when_the_target_firmware_bytes_match(self, project: Path, capsys) -> None:
        firmware = ROOT / "local/roms/C64"
        if not firmware.is_dir():
            pytest.skip("firmware not prepared; run sh scripts/bootstrap.sh c64-pal")
        shutil.copytree(firmware, project / "local/roms/C64")

        assert main(["--target", "c64-pal"], root=project, executables=executables()) == 0

        assert "Firmware verified: KERNAL" in capsys.readouterr().out

    def should_resolve_tools_as_the_installer_does(self, monkeypatch) -> None:
        monkeypatch.setattr(doctor, "tool_path", lambda name: f"/found/{name}")

        assert ExecutableGateway().find("x64sc") == "/found/x64sc"
