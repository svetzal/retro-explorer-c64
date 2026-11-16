"""Place checksum-verified C64 ROMs in ignored local storage, and verify them before launch."""

import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path
from typing import Annotated

from native import tool_path, vice_data_directory
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from references import atomic_bytes

MANIFEST = "firmware.json"
# VICE looks for the C64 ROMs in the C64/ folder of each entry of its system file
# search path (-directory; src/sysfile.c, set_system_path, in the VICE 3.10 source).
# The launcher puts this folder first. guidance/starter/toolchain.md records the measurement.
ROM_DIRECTORY = Path("local/roms")
MACHINE_DIRECTORY = "C64"
SOURCE_CACHE = Path("local/firmware-sources")
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Rom(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str = Field(pattern=r"^(kernal|basic|chargen)$")
    description: str = Field(min_length=1)
    size: int = Field(gt=0, le=65536)
    sha256: Sha256


class Release(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    url: str = Field(pattern=r"^https://")
    sha256: Sha256
    directory: str


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    release: Release
    roms: dict[str, Rom]
    targets: dict[str, tuple[str, ...]]

    def names(self, target: str) -> tuple[str, ...]:
        if target not in self.targets:
            raise ValueError(f"No firmware profile for {target}")
        return self.targets[target]


def load_manifest(root: Path) -> Manifest:
    return Manifest.model_validate_json((root / MANIFEST).read_text())


def targets(root: Path) -> tuple[str, ...]:
    return tuple(load_manifest(root).targets)


def checked(data: bytes, rom: Rom, label: str) -> bytes:
    if len(data) != rom.size:
        raise ValueError(f"{label}: expected {rom.size} bytes, found {len(data)}")
    if hashlib.sha256(data).hexdigest() != rom.sha256:
        raise ValueError(f"{label}: checksum mismatch")
    return data


def rom_directory(root: Path) -> Path:
    """The folder to put first in VICE's system file search path."""
    return root / ROM_DIRECTORY


def recovery_command(target: str) -> str:
    return f"uv run python scripts/setup.py --target {target} --firmware-only"


def verify_installed(
    root: Path, target: str, names: tuple[str, ...] | None = None
) -> dict[str, Path]:
    """Check the installed bytes before launch, without downloads or replacements."""
    try:
        manifest = load_manifest(root)
        selected = manifest.names(target) if names is None else names
        paths = {}
        for name in selected:
            if name not in manifest.roms:
                raise ValueError(f"{name}: not listed in {MANIFEST}")
            path = rom_directory(root) / MACHINE_DIRECTORY / name
            checked(path.read_bytes(), manifest.roms[name], str(path))
            paths[name] = path
        return paths
    except (OSError, ValueError) as error:
        raise ValueError(
            f"Cannot use {target} firmware: {error}. Run {recovery_command(target)}. "
            "If a file differs, inspect it before you replace it. "
            "Do not launch VICE until the check passes."
        ) from error


class FirmwareSourceGateway:
    """Read ROMs from the installed VICE, or download VICE's pinned source release."""

    def installed(self, name: str) -> bytes | None:
        x64sc = tool_path("x64sc")
        if x64sc is None:
            return None
        path = vice_data_directory(x64sc) / MACHINE_DIRECTORY / name
        return path.read_bytes() if path.is_file() else None

    def download(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "retro-explorer/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()


def release_archive(root: Path, release: Release, sources: FirmwareSourceGateway) -> bytes:
    """The pinned source release, downloaded once; its bytes must match the pin."""
    cache = root / SOURCE_CACHE / Path(release.url).name
    data = cache.read_bytes() if cache.exists() else sources.download(release.url)
    if hashlib.sha256(data).hexdigest() != release.sha256:
        raise ValueError(f"{release.url}: checksum mismatch; inspect {cache} if it exists")
    atomic_bytes(cache, data)
    return data


def from_release(archive: bytes, release: Release, name: str) -> bytes:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            member = source.extractfile(f"{release.directory}/{name}")
            if member is None:
                raise ValueError(f"{name}: not a regular file in {release.name}")
            return member.read()
    except (tarfile.TarError, KeyError) as error:
        raise ValueError(f"{name}: not found in {release.name}: {error}") from error


def acquire(
    root: Path, manifest: Manifest, name: str, sources: FirmwareSourceGateway
) -> tuple[bytes, str]:
    """The verified ROM and where it came from: the installed VICE, else the release."""
    rom = manifest.roms[name]
    installed = sources.installed(name)
    if installed is not None:
        try:
            return checked(installed, rom, name), "installed VICE"
        except ValueError as error:
            print(f"Installed VICE copy rejected: {error}. Trying {manifest.release.name}.")
    archive = release_archive(root, manifest.release, sources)
    return checked(from_release(archive, manifest.release, name), rom, name), manifest.release.name


def provision(root: Path, target: str, sources: FirmwareSourceGateway | None = None) -> None:
    """Validate every selected ROM before publishing any of them."""
    sources = sources or FirmwareSourceGateway()
    manifest = load_manifest(root)
    directory = rom_directory(root) / MACHINE_DIRECTORY
    verified = {}
    for name in manifest.names(target):
        path = directory / name
        if path.exists():
            existing = path.read_bytes()
            try:
                checked(existing, manifest.roms[name], str(path))
            except ValueError as error:
                raise ValueError(
                    f"{error}; existing ROM differs, inspect it before replacing it"
                ) from error
            verified[name] = (existing, "existing copy")
            continue
        verified[name] = acquire(root, manifest, name, sources)
    for name, (content, origin) in verified.items():
        atomic_bytes(directory / name, content)
        print(f"Verified firmware: {ROM_DIRECTORY / MACHINE_DIRECTORY / name} ({origin})")
