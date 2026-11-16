"""Tool discovery and installation decisions, with the host system behind a gateway."""

import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import Mock

import native
import pytest
from native import HostGateway, install, main, missing_tools, tool_path, vice_data_directory


@pytest.fixture
def empty_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A PATH with no tools, on a host that is not Apple Silicon macOS."""
    for variable in native.VARIABLES.values():
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(native.platform, "system", lambda: "Linux")
    return tmp_path


def executable(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def host(system: str = "Darwin", machine: str = "arm64", ubuntu: bool = False) -> Mock:
    gateway = Mock(spec=HostGateway)
    gateway.system.return_value = system
    gateway.machine.return_value = machine
    gateway.ubuntu_supported.return_value = ubuntu
    gateway.brew.return_value = "/opt/homebrew/bin/brew"
    gateway.sudo_prefix.return_value = ["sudo", "-n"]
    return gateway


class DescribeToolDiscovery:
    def should_find_tools_on_path(self, empty_path: Path) -> None:
        found = executable(empty_path, "64tass")

        assert tool_path("64tass") == str(found)
        assert tool_path("x64sc") is None

    def should_honour_an_override(self, empty_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        other = executable(empty_path / "..", "my-vice")
        monkeypatch.setenv("X64SC", str(other))

        assert Path(tool_path("x64sc")).resolve() == other.resolve()

    def should_reject_an_override_that_names_nothing(
        self, empty_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("C1541", str(empty_path / "absent"))

        with pytest.raises(ValueError, match="C1541"):
            missing_tools()

    def should_find_vice_data_beside_the_installed_binary(self, tmp_path: Path) -> None:
        (tmp_path / "prefix/bin").mkdir(parents=True)
        binary = executable(tmp_path / "prefix/bin", "x64sc")

        assert vice_data_directory(str(binary)) == (tmp_path / "prefix/share/vice").resolve()


class DescribeInstall:
    def should_install_missing_tools_with_homebrew(self, empty_path: Path, monkeypatch) -> None:
        gateway = host()
        gateway.run.side_effect = lambda command: [
            executable(empty_path, n) for n in native.VARIABLES
        ]

        install(gateway)

        gateway.run.assert_called_once_with(["/opt/homebrew/bin/brew", "install", "tass64", "vice"])

    def should_install_missing_tools_with_apt_on_ubuntu(self, empty_path: Path) -> None:
        gateway = host(system="Linux", ubuntu=True)
        gateway.run.side_effect = lambda command: [
            executable(empty_path, n) for n in native.VARIABLES
        ]

        install(gateway)

        assert gateway.run.call_args_list[-1].args[0] == [
            "sudo",
            "-n",
            "apt-get",
            "install",
            "-y",
            "64tass",
            "vice",
        ]

    def should_do_nothing_when_every_tool_is_present(self, empty_path: Path) -> None:
        for name in native.VARIABLES:
            executable(empty_path, name)
        gateway = host()

        install(gateway)

        gateway.run.assert_not_called()

    @pytest.mark.parametrize(
        "system, machine, ubuntu", [("Darwin", "x86_64", False), ("Linux", "x86_64", False)]
    )
    def should_refuse_unsupported_hosts(self, empty_path: Path, system, machine, ubuntu) -> None:
        with pytest.raises(ValueError, match="supported-hosts"):
            install(host(system, machine, ubuntu))

    def should_report_tools_that_stay_missing(self, empty_path: Path) -> None:
        with pytest.raises(ValueError, match="not discoverable: 64tass, x64sc, c1541"):
            install(host())

    def should_turn_failures_into_an_exit_status(self, empty_path: Path, capsys) -> None:
        gateway = host()
        gateway.run.side_effect = subprocess.CalledProcessError(1, ["brew"])

        assert main(gateway) == 1
        assert "Tool installation stopped" in capsys.readouterr().err


class DescribeHostGateway:
    def should_name_the_sudo_prefix_for_this_account(self) -> None:
        expected = [] if os.geteuid() == 0 else ["sudo", "-n"]

        assert HostGateway().sudo_prefix() == expected
