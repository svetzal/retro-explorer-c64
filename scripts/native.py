"""Install and find 64tass and VICE on Apple Silicon macOS or Ubuntu 24.04."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOMEBREW_BIN = Path("/opt/homebrew/bin")
# Each tool's override variable, in the order the doctor reports them.
VARIABLES = {"64tass": "TASS64", "x64sc": "X64SC", "c1541": "C1541"}
# The package that supplies each tool, by host package manager.
HOMEBREW_PACKAGES = {"64tass": "tass64", "x64sc": "vice", "c1541": "vice"}
APT_PACKAGES = {"64tass": "64tass", "x64sc": "vice", "c1541": "vice"}


def tool_path(name: str) -> str | None:
    """Honor an override, then PATH, then Apple Silicon Homebrew."""
    variable = VARIABLES[name]
    if variable in os.environ:
        return shutil.which(os.environ[variable])
    found = shutil.which(name)
    if found:
        return found
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return shutil.which(str(HOMEBREW_BIN / name))
    return None


def vice_data_directory(x64sc: str) -> Path:
    """VICE installs its machine data in <prefix>/share/vice beside <prefix>/bin."""
    return Path(x64sc).resolve().parents[1] / "share/vice"


class HostGateway:
    """System changes stay at one boundary."""

    def system(self) -> str:
        return platform.system()

    def machine(self) -> str:
        return platform.machine()

    def ubuntu_supported(self) -> bool:
        release = platform.freedesktop_os_release()
        return release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04"

    def run(self, command: list[str]) -> None:
        subprocess.run(command, check=True)

    def brew(self) -> str:
        found = shutil.which("brew") or shutil.which(str(HOMEBREW_BIN / "brew"))
        if not found:
            raise ValueError(
                "Homebrew is missing. Install it from https://brew.sh, then run bootstrap again."
            )
        return found

    def sudo_prefix(self) -> list[str]:
        return [] if os.geteuid() == 0 else ["sudo", "-n"]


def missing_tools() -> list[str]:
    """Tools to install; an override that names an unavailable executable is an error."""
    missing = [name for name in VARIABLES if not tool_path(name)]
    for name in missing:
        if VARIABLES[name] in os.environ:
            raise ValueError(
                f"{VARIABLES[name]} points to an unavailable executable; correct the override."
            )
    return missing


def install(host: HostGateway | None = None) -> None:
    host = host or HostGateway()
    if host.system() == "Darwin" and host.machine() != "arm64":
        raise ValueError(
            "macOS requires Apple Silicon (arm64); Intel Macs are unsupported. "
            "See guidance/starter/toolchain.md#supported-hosts."
        )
    missing = missing_tools()
    if not missing:
        print("64tass and VICE are already available.")
        return
    if host.system() == "Darwin":
        packages = list(dict.fromkeys(HOMEBREW_PACKAGES[name] for name in missing))
        host.run([host.brew(), "install", *packages])
    elif host.system() == "Linux" and host.ubuntu_supported():
        packages = list(dict.fromkeys(APT_PACKAGES[name] for name in missing))
        prefix = host.sudo_prefix()
        host.run([*prefix, "apt-get", "update"])
        host.run([*prefix, "apt-get", "install", "-y", *packages])
    else:
        raise ValueError(
            "Automatic installation supports Apple Silicon macOS and Ubuntu 24.04. "
            "See guidance/starter/toolchain.md#supported-hosts."
        )
    still_missing = [name for name in missing if not tool_path(name)]
    if still_missing:
        raise ValueError(
            "Installation finished but these tools are not discoverable: "
            + ", ".join(still_missing)
            + ". See guidance/starter/toolchain.md#tool-roles."
        )


def main(host: HostGateway | None = None) -> int:
    try:
        install(host)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Tool installation stopped: {error}", file=sys.stderr)
        print(
            "Your agent may need your approval for system installation. Rerun after resolving it.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
