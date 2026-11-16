"""Check the C64 executables and the target firmware bytes without launching VICE."""

import argparse
import sys
from pathlib import Path

from firmware import load_manifest, targets, verify_installed
from native import ROOT, VARIABLES, tool_path

TOOLS = {
    "64tass": "6502 assembler",
    "x64sc": "VICE C64 emulator (cycle-exact)",
    "c1541": "VICE disk image tool",
}


class ExecutableGateway:
    """Resolve overrides, PATH and Apple Silicon Homebrew, as the installer does."""

    def find(self, command: str) -> str | None:
        return tool_path(command)


def report_tools(executables: ExecutableGateway) -> list[str]:
    missing = []
    for command, purpose in TOOLS.items():
        executable = executables.find(command)
        if executable:
            print(f"{command}: {executable} ({purpose})")
        else:
            print(f"{command}: missing ({purpose}); set {VARIABLES[command]} or add it to PATH")
            missing.append(command)
    return missing


def report_firmware(root: Path, target: str | None) -> bool:
    if target is None:
        print("Firmware NOT checked. Add --target with one of " + ", ".join(targets(root)) + ".")
        return True
    roms = load_manifest(root).roms
    try:
        paths = verify_installed(root, target)
    except ValueError as error:
        print(str(error))
        return False
    for name, path in paths.items():
        print(f"Firmware verified: {roms[name].description}: {path}")
    return True


def main(
    argv: list[str] | None = None,
    *,
    root: Path = ROOT,
    executables: ExecutableGateway | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=targets(root), help="also check the firmware bytes for this target"
    )
    options = parser.parse_args(argv)
    print(f"Python: {sys.executable}")
    missing = report_tools(executables or ExecutableGateway())
    firmware_ok = report_firmware(root, options.target)
    print(
        "These checks find files and compare checksums. They do not start VICE. "
        "Run the check command of an example to see a program run."
    )
    if missing:
        print("Setup is incomplete. Run: uv run python scripts/native.py")
    print("Read guidance/starter/toolchain.md for installation and verification.")
    return 1 if missing or not firmware_ok else 0


if __name__ == "__main__":
    sys.exit(main())
